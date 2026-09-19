"""Cache-only mechanism probe for current-token Decode backlog at TTFT boundary."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import json
import math
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from aiccc_evaluator import evaluate as evaluate_j0
from high_load_ttft_diagnosis import point_rows
from j2_reference_profile_validation import CachedProfiles, inventory_fingerprint
from research import RequestSpec, SLA, pipeline
from sla_aware_mvp.capacity import scale_workload

RAW = ROOT / "results" / "raw_reference"
PROTOCOL = ROOT / "config" / "first_token_current_work_backlog_probe_v1.json"
BASE_PROTOCOL = ROOT / "config" / "high_load_ttft_diagnosis_v1.json"
OUTPUT = ROOT / "results" / "first_token_current_work_backlog_probe_v1"


def pearson(xs, ys):
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    den = math.sqrt(sum(x*x for x in dx) * sum(y*y for y in dy))
    if den <= 0:
        return None
    return sum(x*y for x, y in zip(dx, dy)) / den


def pct(values, q):
    xs = sorted(float(x) for x in values)
    if not xs:
        return None
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return xs[lo]
    w = pos - lo
    return xs[lo] * (1-w) + xs[hi] * w


def summarize(rows):
    if not rows:
        return {"count": 0}
    out = [r["first_decode_excess_s"] for r in rows]
    rem = [r["remaining_current_decode_work_s"] for r in rows]
    full = [r["full_competing_decode_service_s"] for r in rows]
    nd = [r["competing_decode_count"] for r in rows]
    return {
        "count": len(rows),
        "excess_median_s": statistics.median(out),
        "excess_p95_s": pct(out, 0.95),
        "excess_max_s": max(out),
        "remaining_work_median_s": statistics.median(rem),
        "remaining_work_p95_s": pct(rem, 0.95),
        "remaining_work_max_s": max(rem),
        "full_service_median_s": statistics.median(full),
        "competing_decode_median": statistics.median(nd),
    }


def backlog_for_core(core):
    boundary = {}
    for snap in core["trace"]:
        if snap["side"] != "post":
            continue
        for event, rid in snap["events"]:
            if event == "PrefillToDecode":
                boundary[rid] = snap
    return boundary


def rem_fraction(progress):
    nearest = round(progress)
    if abs(progress - nearest) <= 1e-9:
        return 1.0
    frac = progress - math.floor(progress)
    return 1.0 - frac


def main():
    started = time.perf_counter()
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    base_protocol = json.loads(BASE_PROTOCOL.read_text(encoding="utf-8"))
    before = inventory_fingerprint(RAW)

    reference_rows = []
    for rel in base_protocol["physical_case_files"]:
        reference_rows.extend(point_rows(ROOT / rel, base_protocol))
    reference_index = {
        (int(r["seed"]), float(r["intensity"]), r["request_id"]): r
        for r in reference_rows
    }

    rows = []
    prof = CachedProfiles()
    for rel in base_protocol["physical_case_files"]:
        source = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        case = source["case"]
        seed = int(case["seed"])
        base = tuple(RequestSpec(**r) for r in source["requests"])
        sla = SLA(**source["sla"])
        p = pipeline(case["placement"], case.get("shift", 0), case.get("hetero", False))
        for saved in source["rows"]:
            intensity = float(saved["lambda"])
            workload = scale_workload(base, intensity)
            core = evaluate_j0(
                p, workload, sla, prof,
                intrinsic=True, trace=True, drain=True,
                blocking_policy="active-prefill-full-service-recovered-assumption",
                decode_block_size=16,
            )
            boundaries = backlog_for_core(core)
            for target in workload:
                snap = boundaries.get(target.id)
                if snap is None:
                    raise RuntimeError(f"missing PrefillToDecode boundary for {target.id}")
                remaining = 0.0
                full = 0.0
                count = 0
                details = []
                for rid, ledger in snap["ledger"].items():
                    if rid == target.id or ledger["phase"] != "decode":
                        continue
                    g = float(ledger["progress"])
                    service = float(ledger["compute_s"])
                    rf = rem_fraction(g)
                    work = rf * service
                    remaining += work
                    full += service
                    count += 1
                    details.append({
                        "request_id": rid,
                        "progress": g,
                        "profile_service_s": service,
                        "remaining_fraction": rf,
                        "remaining_work_s": work,
                    })
                ref = reference_index[(seed, intensity, target.id)]
                rows.append({
                    "seed": seed,
                    "case_id": case["id"],
                    "intensity": intensity,
                    "request_id": target.id,
                    "input_tokens": target.input_tokens,
                    "output_tokens": target.output_tokens,
                    "competing_decode_count": count,
                    "remaining_current_decode_work_s": remaining,
                    "full_competing_decode_service_s": full,
                    "reference_first_decode_runtime_s": ref["reference_first_decode_runtime_s"],
                    "predicted_first_decode_profile_s": ref["j1_predicted_first_decode_profile_s"],
                    "first_decode_excess_s": ref["reference_first_decode_runtime_s"] - ref["j1_predicted_first_decode_profile_s"],
                    "first_decode_max_decode": ref["first_decode_max_decode"],
                    "first_decode_max_prefill": ref["first_decode_max_prefill"],
                    "competitor_details": details,
                })

    after = inventory_fingerprint(RAW)
    if before != after:
        raise RuntimeError("cache-only current-work probe changed raw reference inventory")

    outcome = [r["first_decode_excess_s"] for r in rows]
    correlations = {
        "competing_decode_count": pearson([r["competing_decode_count"] for r in rows], outcome),
        "full_competing_decode_service_s": pearson([r["full_competing_decode_service_s"] for r in rows], outcome),
        "remaining_current_decode_work_s": pearson([r["remaining_current_decode_work_s"] for r in rows], outcome),
    }

    top = []
    for r in sorted(rows, key=lambda x: x["first_decode_excess_s"], reverse=True)[:30]:
        top.append({k: r[k] for k in (
            "seed", "case_id", "intensity", "request_id", "input_tokens", "output_tokens",
            "competing_decode_count", "remaining_current_decode_work_s",
            "full_competing_decode_service_s", "reference_first_decode_runtime_s",
            "predicted_first_decode_profile_s", "first_decode_excess_s",
            "first_decode_max_decode", "first_decode_max_prefill"
        )})

    focus = []
    for seed, rid, lo, hi in (
        (0, "azure-00011", 0.96, 1.28),
        (7, "azure-00014", 0.32, 0.64),
    ):
        pair = []
        for intensity in (lo, hi):
            match = next(r for r in rows if r["seed"] == seed and r["request_id"] == rid and abs(r["intensity"]-intensity) < 1e-12)
            pair.append({k: match[k] for k in (
                "intensity", "competing_decode_count", "remaining_current_decode_work_s",
                "full_competing_decode_service_s", "reference_first_decode_runtime_s",
                "predicted_first_decode_profile_s", "first_decode_excess_s"
            )})
        focus.append({"seed": seed, "request_id": rid, "lower": pair[0], "higher": pair[1]})

    summary = {
        "schema": 1,
        "experiment_id": protocol["experiment_id"],
        "status": "complete",
        "new_helix_runs": 0,
        "physical_points": len({(r["seed"], r["intensity"]) for r in rows}),
        "request_rows": len(rows),
        "correlations": correlations,
        "all_rows_summary": summarize(rows),
        "top_excess_rows": top,
        "focus_pairs": focus,
        "raw_reference_inventory_before": before,
        "raw_reference_inventory_after": after,
        "elapsed_s": time.perf_counter() - started,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8", newline="\n"
    )
    print("FIRST_TOKEN_CURRENT_WORK_BACKLOG_PROBE " + json.dumps({
        "correlations": correlations,
        "focus_pairs": focus,
        "top_excess_rows": top,
        "elapsed_s": summary["elapsed_s"],
    }, sort_keys=True, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
