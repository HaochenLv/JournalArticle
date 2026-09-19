"""Mechanism diagnosis for high-load standard-TTFT optimism.

This is a cache-only diagnostic. It does not modify J0/J1 semantics and does not
select a guard. It decomposes HELIX first-output TTFT using the exact stored
identity

    true_first_token_ttft
      = aligned_ttft + (first_decode_tpot - record_overhead)

and compares the same request across the nearest sampled TTFT-safe and
TTFT-unsafe intensities.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import csv
import gzip
import json
import math
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from aiccc_evaluator import evaluate as evaluate_j0
from aiccc_j1_evaluator import (
    BLOCKING_MODE_REMAINING,
    evaluate as evaluate_j1,
)
from j2_reference_profile_validation import CachedProfiles, inventory_fingerprint
from research import RequestSpec, SLA, pipeline
from sla_aware_mvp.capacity import scale_workload

PROTOCOL = ROOT / "config" / "high_load_ttft_diagnosis_v1.json"
RAW = ROOT / "results" / "raw_reference"
OUTPUT = ROOT / "results" / "high_load_ttft_diagnosis_v1"


def finite_rate(workload):
    if len(workload) <= 1:
        return 0.0
    span = workload[-1].arrival_time_s - workload[0].arrival_time_s
    return (len(workload) - 1) / span if span > 0 else math.inf


def read_record(cache_key):
    path = RAW / f"{cache_key}.json.gz"
    if not path.exists():
        raise RuntimeError(f"missing cached HELIX record: {cache_key}")
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def prefill_end_times(core):
    out = {}
    for snap in core["trace"]:
        if snap["side"] != "post":
            continue
        for event, rid in snap["events"]:
            if event == "PrefillToDecode":
                out[rid] = float(snap["time_s"])
    return out


def interval_load(core, start, end):
    if end <= start:
        return {
            "duration_s": max(0.0, end - start),
            "mean_prefill": 0.0,
            "mean_decode": 0.0,
            "max_prefill": 0,
            "max_decode": 0,
        }
    post = [x for x in core["trace"] if x["side"] == "post"]
    p_area = d_area = 0.0
    max_p = max_d = 0
    covered = 0.0
    for i, snap in enumerate(post):
        t0 = float(snap["time_s"])
        t1 = float(post[i + 1]["time_s"]) if i + 1 < len(post) else core["final_time_s"]
        left = max(start, t0)
        right = min(end, t1)
        if right <= left:
            continue
        dt = right - left
        covered += dt
        p_area += dt * snap["num_prefill"]
        d_area += dt * snap["num_decode"]
        max_p = max(max_p, int(snap["num_prefill"]))
        max_d = max(max_d, int(snap["num_decode"]))
    duration = end - start
    if covered < duration - 1e-7:
        raise RuntimeError(
            f"J0 trace did not cover requested interval: {covered} < {duration}"
        )
    return {
        "duration_s": duration,
        "mean_prefill": p_area / duration,
        "mean_decode": d_area / duration,
        "max_prefill": max_p,
        "max_decode": max_d,
    }


def point_rows(case_path, protocol):
    source = json.loads(case_path.read_text(encoding="utf-8"))
    case = source["case"]
    base = tuple(RequestSpec(**r) for r in source["requests"])
    p = pipeline(case["placement"], case.get("shift", 0), case.get("hetero", False))
    sla = SLA(**source["sla"])
    prof = CachedProfiles()
    rows = []

    for saved in source["rows"]:
        intensity = float(saved["lambda"])
        cache_key = saved["reference"]["cache_key"]
        record = read_record(cache_key)
        raw_metrics = record["raw"]["query_metrics"]
        overhead_meta = record["inputs"]["sla"]
        record_overhead = (
            float(overhead_meta.get("fixed_overhead_s", 0.0))
            + float(overhead_meta.get("queue_overhead_s", 0.0))
        )
        workload = scale_workload(base, intensity)

        j1 = evaluate_j1(
            p,
            workload,
            sla,
            prof,
            intrinsic=True,
            trace=True,
            blocking_policy="active-prefill-full-service-recovered-assumption",
            blocking_scale=1.0,
            blocking_mode=BLOCKING_MODE_REMAINING,
            ttft_profile_uncertainty_fraction=0.0,
            decode_block_size=16,
        )
        core = evaluate_j0(
            p,
            workload,
            sla,
            prof,
            intrinsic=True,
            trace=True,
            drain=True,
            blocking_policy="active-prefill-full-service-recovered-assumption",
            decode_block_size=16,
        )
        if j1["core_trajectory_hash"] != core["trajectory_hash"]:
            raise RuntimeError("J1 changed the frozen J0 trajectory")
        if abs(j1["final_time_s"] - core["final_time_s"]) > 1e-10:
            raise RuntimeError("J1/J0 final-time mismatch")

        ends = prefill_end_times(core)
        by_id = {r.id: r for r in workload}
        for rid, spec in by_id.items():
            rm = raw_metrics[rid]
            true_ttft = float(rm["true_first_token_ttft_s"])
            aligned_ttft = float(rm["aligned_ttft_s"])
            first_decode_accounted = float(rm["decode_tpot_s"][0])
            first_decode_runtime = first_decode_accounted - record_overhead
            identity_residual = (
                true_ttft - aligned_ttft - first_decode_runtime
            )

            ledger = j1["request_ledgers"][rid]["ttft"]
            first_time = float(j1["first_token_time_s"][rid])
            p_end = float(ends[rid])
            predicted_first_decode_profile = first_time - p_end
            if predicted_first_decode_profile < -1e-9:
                raise RuntimeError("negative predicted first-Decode interval")

            overall_load = interval_load(
                core, spec.arrival_time_s, first_time
            )
            first_decode_load = interval_load(
                core, p_end, first_time
            )

            rows.append(
                {
                    "seed": case["seed"],
                    "case_id": case["id"],
                    "intensity": intensity,
                    "arrival_rate_rps": finite_rate(workload),
                    "request_id": rid,
                    "input_tokens": spec.input_tokens,
                    "output_tokens": spec.output_tokens,
                    "reference_true_ttft_s": true_ttft,
                    "reference_aligned_ttft_s": aligned_ttft,
                    "reference_first_decode_runtime_s": first_decode_runtime,
                    "reference_first_decode_accounted_s": first_decode_accounted,
                    "record_overhead_s": record_overhead,
                    "reference_identity_residual_s": identity_residual,
                    "j1_predicted_ttft_s": float(ledger["predicted_metric_s"]),
                    "j1_profile_elapsed_s": float(ledger["profile_elapsed_s"]),
                    "j1_intrinsic_s": float(ledger["intrinsic_s"]),
                    "j1_blocking_s": float(ledger["blocking_s"]),
                    "j1_fixed_s": float(ledger["fixed_s"]),
                    "j1_ideal_serialization_s": float(ledger["ideal_serialization_s"]),
                    "j1_residual_network_s": float(ledger["residual_network_s"]),
                    "j1_prefill_end_s": p_end,
                    "j1_first_token_time_s": first_time,
                    "j1_predicted_first_decode_profile_s": predicted_first_decode_profile,
                    "ttft_gap_reference_minus_j1_s": true_ttft - float(ledger["predicted_metric_s"]),
                    "overall_mean_prefill": overall_load["mean_prefill"],
                    "overall_mean_decode": overall_load["mean_decode"],
                    "overall_max_prefill": overall_load["max_prefill"],
                    "overall_max_decode": overall_load["max_decode"],
                    "first_decode_mean_prefill": first_decode_load["mean_prefill"],
                    "first_decode_mean_decode": first_decode_load["mean_decode"],
                    "first_decode_max_prefill": first_decode_load["max_prefill"],
                    "first_decode_max_decode": first_decode_load["max_decode"],
                    "core_trajectory_hash": core["trajectory_hash"],
                    "reference_cache_key": cache_key,
                }
            )
    return rows


def summarize_points(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[(r["seed"], r["intensity"])].append(r)
    out = []
    for (seed, intensity), group in sorted(groups.items()):
        worst = max(group, key=lambda x: x["reference_true_ttft_s"])
        biggest_gap = max(group, key=lambda x: x["ttft_gap_reference_minus_j1_s"])
        out.append(
            {
                "seed": seed,
                "intensity": intensity,
                "arrival_rate_rps": worst["arrival_rate_rps"],
                "max_reference_true_ttft_s": worst["reference_true_ttft_s"],
                "max_reference_ttft_request": worst["request_id"],
                "that_request_aligned_ttft_s": worst["reference_aligned_ttft_s"],
                "that_request_first_decode_runtime_s": worst["reference_first_decode_runtime_s"],
                "that_request_j1_predicted_ttft_s": worst["j1_predicted_ttft_s"],
                "that_request_j1_predicted_first_decode_profile_s": worst[
                    "j1_predicted_first_decode_profile_s"
                ],
                "that_request_j1_blocking_s": worst["j1_blocking_s"],
                "that_request_first_decode_mean_prefill": worst[
                    "first_decode_mean_prefill"
                ],
                "that_request_first_decode_mean_decode": worst[
                    "first_decode_mean_decode"
                ],
                "max_reference_minus_j1_gap_s": biggest_gap[
                    "ttft_gap_reference_minus_j1_s"
                ],
                "max_gap_request": biggest_gap["request_id"],
            }
        )
    return out


def threshold_comparisons(rows, protocol):
    indexed = defaultdict(dict)
    for r in rows:
        indexed[(r["seed"], r["intensity"])][r["request_id"]] = r

    intensities = defaultdict(list)
    for seed, intensity in indexed:
        intensities[seed].append(intensity)
    for seed in intensities:
        intensities[seed] = sorted(set(intensities[seed]))

    out = []
    for view in protocol["threshold_views"]:
        seed = view["seed"]
        threshold = float(view["ttft_s"])
        points = []
        for intensity in intensities[seed]:
            group = list(indexed[(seed, intensity)].values())
            worst = max(group, key=lambda x: x["reference_true_ttft_s"])
            points.append(
                {
                    "intensity": intensity,
                    "max_ttft": worst["reference_true_ttft_s"],
                    "worst_request": worst["request_id"],
                }
            )
        unsafe = next((x for x in points if x["max_ttft"] > threshold), None)
        if unsafe is None:
            out.append(
                {
                    "label": view["label"],
                    "seed": seed,
                    "ttft_limit_s": threshold,
                    "first_sampled_ttft_unsafe": None,
                    "note": "No sampled TTFT violation in this source grid.",
                }
            )
            continue
        lower = [
            x for x in points
            if x["intensity"] < unsafe["intensity"] and x["max_ttft"] <= threshold
        ]
        if not lower:
            out.append(
                {
                    "label": view["label"],
                    "seed": seed,
                    "ttft_limit_s": threshold,
                    "first_sampled_ttft_unsafe": unsafe["intensity"],
                    "note": "No lower sampled TTFT-safe point.",
                }
            )
            continue
        safe = lower[-1]
        rid = unsafe["worst_request"]
        u = indexed[(seed, unsafe["intensity"])][rid]
        s = indexed[(seed, safe["intensity"])][rid]

        d_true = u["reference_true_ttft_s"] - s["reference_true_ttft_s"]
        d_aligned = u["reference_aligned_ttft_s"] - s["reference_aligned_ttft_s"]
        d_first = (
            u["reference_first_decode_runtime_s"]
            - s["reference_first_decode_runtime_s"]
        )
        d_pred = u["j1_predicted_ttft_s"] - s["j1_predicted_ttft_s"]
        out.append(
            {
                "label": view["label"],
                "seed": seed,
                "ttft_limit_s": threshold,
                "safe_intensity": safe["intensity"],
                "safe_arrival_rate_rps": s["arrival_rate_rps"],
                "unsafe_intensity": unsafe["intensity"],
                "unsafe_arrival_rate_rps": u["arrival_rate_rps"],
                "same_request_id": rid,
                "input_tokens": u["input_tokens"],
                "output_tokens": u["output_tokens"],
                "safe_reference_true_ttft_s": s["reference_true_ttft_s"],
                "unsafe_reference_true_ttft_s": u["reference_true_ttft_s"],
                "safe_reference_aligned_ttft_s": s["reference_aligned_ttft_s"],
                "unsafe_reference_aligned_ttft_s": u["reference_aligned_ttft_s"],
                "safe_reference_first_decode_runtime_s": s[
                    "reference_first_decode_runtime_s"
                ],
                "unsafe_reference_first_decode_runtime_s": u[
                    "reference_first_decode_runtime_s"
                ],
                "safe_j1_predicted_ttft_s": s["j1_predicted_ttft_s"],
                "unsafe_j1_predicted_ttft_s": u["j1_predicted_ttft_s"],
                "delta_reference_true_ttft_s": d_true,
                "delta_reference_aligned_ttft_s": d_aligned,
                "delta_reference_first_decode_runtime_s": d_first,
                "delta_j1_predicted_ttft_s": d_pred,
                "delta_identity_residual_s": d_true - d_aligned - d_first,
                "first_decode_share_of_reference_ttft_increase": (
                    d_first / d_true if d_true > 1e-12 else None
                ),
                "safe_first_decode_mean_prefill": s["first_decode_mean_prefill"],
                "unsafe_first_decode_mean_prefill": u["first_decode_mean_prefill"],
                "safe_first_decode_mean_decode": s["first_decode_mean_decode"],
                "unsafe_first_decode_mean_decode": u["first_decode_mean_decode"],
                "safe_first_decode_max_prefill": s["first_decode_max_prefill"],
                "unsafe_first_decode_max_prefill": u["first_decode_max_prefill"],
                "safe_first_decode_max_decode": s["first_decode_max_decode"],
                "unsafe_first_decode_max_decode": u["first_decode_max_decode"],
                "unsafe_reference_minus_j1_gap_s": u[
                    "ttft_gap_reference_minus_j1_s"
                ],
                "unsafe_reference_identity_residual_s": u[
                    "reference_identity_residual_s"
                ],
            }
        )
    return out


def write_csv(rows):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "per_request.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=list(rows[0].keys()), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    started = time.perf_counter()
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    before = inventory_fingerprint(RAW)

    rows = []
    for rel in protocol["physical_case_files"]:
        rows.extend(point_rows(ROOT / rel, protocol))

    after = inventory_fingerprint(RAW)
    if before != after:
        raise RuntimeError("cache-only TTFT diagnosis changed raw reference inventory")

    identity_max = max(abs(r["reference_identity_residual_s"]) for r in rows)
    if identity_max > 1e-7:
        raise RuntimeError(f"stored TTFT identity failed: {identity_max}")

    points = summarize_points(rows)
    comparisons = threshold_comparisons(rows, protocol)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_csv(rows)
    summary = {
        "status": "complete",
        "experiment_id": protocol["experiment_id"],
        "new_helix_runs": 0,
        "raw_reference_inventory_before": before,
        "raw_reference_inventory_after": after,
        "physical_points": len({(r["seed"], r["intensity"]) for r in rows}),
        "request_rows": len(rows),
        "max_abs_reference_identity_residual_s": identity_max,
        "point_summary": points,
        "threshold_comparisons": comparisons,
        "elapsed_s": time.perf_counter() - started,
    }
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    compact = {
        "physical_points": summary["physical_points"],
        "request_rows": summary["request_rows"],
        "identity_max_abs_s": identity_max,
        "comparisons": comparisons,
        "elapsed_s": summary["elapsed_s"],
    }
    print(
        "HIGH_LOAD_TTFT_DIAG_SUMMARY "
        + json.dumps(compact, sort_keys=True, allow_nan=False),
        flush=True,
    )
    print(f"HIGH_LOAD_TTFT_DIAG_OUTPUT {OUTPUT}", flush=True)


if __name__ == "__main__":
    main()
