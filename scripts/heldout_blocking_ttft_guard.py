"""Held-out mechanism test on pre-existing formal-workload HELIX records.

This experiment evaluates two accounting-only Prefill-blocking formulas and four
TTFT profile-uncertainty reserves while keeping the frozen AICCC/J0 progress and
network equations unchanged.

The evaluation population is h103-h106 from existing formal-workload records.
These workloads are held out from the current mechanism-design step, although
they are not globally unseen historical data.
"""
from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import json
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from aiccc_j1_evaluator import evaluate as evaluate_j1
from formal_core import CONFIG, load_workload
from j2_reference_profile_validation import (
    CachedProfiles,
    classify_pair,
    inventory_fingerprint,
    load_reference,
    monotonic_summary,
)
from research import SLA, pipeline
from sla_aware_mvp.capacity import scale_workload

PROTOCOL_PATH = ROOT / "config" / "heldout_blocking_ttft_guard_experiment.json"
OUTPUT = ROOT / "results" / "heldout_blocking_ttft_guard"
RAW = ROOT / "results" / "raw_reference"


def candidate_settings(protocol):
    out = []
    for blocking in protocol["candidate_mechanisms"]["blocking"]:
        for reserve in protocol["candidate_mechanisms"]["ttft_profile_uncertainty_fraction"]:
            out.append(
                {
                    "blocking_label": blocking["label"],
                    "blocking_mode": blocking["mode"],
                    "ttft_reserve_fraction": reserve,
                    "label": f"{blocking['label']} + TTFT reserve {reserve:.3f}",
                }
            )
    return out


def sla_for(kind):
    if kind == "a100":
        cfg = CONFIG["a100_slas"]["decode"]
    else:
        cfg = CONFIG["heterogeneous_slas"]["decode"]
    return SLA(**cfg, fixed_overhead_s=CONFIG["fixed_overhead_s"])


def process_group(args):
    path_string, settings = args
    path = Path(path_string)
    data = json.loads(path.read_text(encoding="utf-8"))
    group = data["group"]
    workload_meta, base = load_workload(group["workload"])
    hetero = group["kind"] == "heterogeneous"
    sla = sla_for(group["kind"])
    prof = CachedProfiles()

    rows = []
    for saved in data["rows"]:
        if saved.get("status") != "ok":
            continue
        shift = saved["shift"]
        intensity = saved["intensity"]
        p = pipeline(group["link"], shift, hetero)
        w = scale_workload(base, intensity)
        cache_key = saved["reference_cache_key"]
        reference, detail = load_reference(cache_key, sla)

        baseline_hash = None
        baseline_final = None
        for setting in settings:
            result = evaluate_j1(
                p,
                w,
                sla,
                prof,
                intrinsic=True,
                blocking_policy="active-prefill-full-service-recovered-assumption",
                blocking_scale=1.0,
                blocking_mode=setting["blocking_mode"],
                ttft_profile_uncertainty_fraction=setting["ttft_reserve_fraction"],
                decode_block_size=16,
            )
            if baseline_hash is None:
                baseline_hash = result["core_trajectory_hash"]
                baseline_final = result["final_time_s"]
            elif result["core_trajectory_hash"] != baseline_hash or result["final_time_s"] != baseline_final:
                raise RuntimeError("accounting-only candidate changed the frozen J0 trajectory")

            first = result["first_violation"]
            rows.append(
                {
                    "group": group["id"],
                    "workload": group["workload"],
                    "kind": group["kind"],
                    "link": group["link"],
                    "shift": shift,
                    "intensity": intensity,
                    "requests": len(base),
                    "candidate": setting["label"],
                    "blocking_label": setting["blocking_label"],
                    "blocking_mode": setting["blocking_mode"],
                    "ttft_reserve_fraction": setting["ttft_reserve_fraction"],
                    "evaluator_safe": result["safe"],
                    "reference_safe": reference["safe"],
                    "class": classify_pair(result["safe"], reference["safe"]),
                    "evaluator_first_kind": None if first is None else first["kind"],
                    "evaluator_first_object": None if first is None else first["object"],
                    "evaluator_peak_network_utilization": result["peak_network_utilization"],
                    "evaluator_max_standard_ttft_s": result["max_standard_ttft_s"],
                    "evaluator_max_average_tpot_s": result["max_average_tpot_s"],
                    "evaluator_runtime_s": result["runtime_s"],
                    "core_trajectory_hash": result["core_trajectory_hash"],
                    "reference_cache_key": cache_key,
                    **{f"reference_{k}": v for k, v in detail.items()},
                }
            )
    return rows


def summarize_candidate(rows, label):
    group = [r for r in rows if r["candidate"] == label]
    counts = {
        k: sum(r["class"] == k for r in group)
        for k in ("safe_safe", "false_acceptance", "false_rejection", "unsafe_unsafe")
    }
    ref_safe = sum(r["reference_safe"] for r in group)
    ref_unsafe = len(group) - ref_safe
    fas = [r for r in group if r["class"] == "false_acceptance"]
    frs = [r for r in group if r["class"] == "false_rejection"]
    first_kinds = defaultdict(int)
    for r in group:
        key = "safe" if r["evaluator_first_kind"] is None else f"{r['evaluator_first_kind']}:{r['evaluator_first_object']}"
        first_kinds[key] += 1

    return {
        "candidate": label,
        "blocking_label": group[0]["blocking_label"] if group else None,
        "ttft_reserve_fraction": group[0]["ttft_reserve_fraction"] if group else None,
        "pairs": len(group),
        **counts,
        "agreement": (counts["safe_safe"] + counts["unsafe_unsafe"]) / len(group) if group else None,
        "reference_safe": ref_safe,
        "reference_unsafe": ref_unsafe,
        "false_acceptance_rate_given_reference_unsafe": counts["false_acceptance"] / ref_unsafe if ref_unsafe else None,
        "false_rejection_rate_given_reference_safe": counts["false_rejection"] / ref_safe if ref_safe else None,
        "false_acceptance_max_reference_normalized_excess": max((r["reference_max_normalized_excess"] for r in fas), default=0.0),
        "false_acceptance_mean_reference_normalized_excess": statistics.fmean(r["reference_max_normalized_excess"] for r in fas) if fas else 0.0,
        "false_acceptance_max_violating_request_fraction": max((r["reference_violating_request_fraction"] for r in fas), default=0.0),
        "false_rejection_count_by_kind": dict(
            sorted(
                (
                    key,
                    sum(
                        r["evaluator_first_kind"] == key
                        for r in frs
                    ),
                )
                for key in {r["evaluator_first_kind"] for r in frs}
            )
        ),
        "first_verdict_kinds": dict(sorted(first_kinds.items())),
        "median_runtime_ms": statistics.median(r["evaluator_runtime_s"] for r in group) * 1000 if group else None,
        "false_acceptance_cases": [
            {
                "group": r["group"],
                "shift": r["shift"],
                "intensity": r["intensity"],
                "reference_max_normalized_excess": r["reference_max_normalized_excess"],
                "reference_violating_request_fraction": r["reference_violating_request_fraction"],
            }
            for r in fas
        ],
    }


def capacity_summary(rows, label):
    selected = [r for r in rows if r["candidate"] == label]
    groups = defaultdict(list)
    for r in selected:
        groups[(r["group"], r["shift"])].append(r)

    details = []
    for (group_name, shift), group in sorted(groups.items()):
        e = monotonic_summary(group, "evaluator_safe")
        ref = monotonic_summary(group, "reference_safe")
        comparable = e["single_boundary_supported"] and ref["single_boundary_supported"]
        details.append(
            {
                "group": group_name,
                "shift": shift,
                "evaluator": e,
                "reference": ref,
                "comparable_edge": comparable,
                "exact_edge": comparable and (
                    e["largest_safe"],
                    e["nearest_unsafe_above"],
                ) == (
                    ref["largest_safe"],
                    ref["nearest_unsafe_above"],
                ),
            }
        )
    comparable = [x for x in details if x["comparable_edge"]]
    return {
        "candidate": label,
        "case_shift_sequences": len(details),
        "comparable_edges": len(comparable),
        "exact_edges": sum(x["exact_edge"] for x in comparable),
        "evaluator_nonmonotone_sequences": sum(x["evaluator"]["nonmonotone"] for x in details),
        "reference_nonmonotone_sequences": sum(x["reference"]["nonmonotone"] for x in details),
        "details": details,
    }


def main():
    started = time.perf_counter()
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    settings = candidate_settings(protocol)
    before = inventory_fingerprint(RAW)

    paths = []
    for workload_name in protocol["held_out_workloads"]:
        for kind in ("a100", "heterogeneous"):
            matches = sorted(
                (ROOT / "results" / "formal" / "groups").glob(
                    f"{workload_name}-{kind}-*.json"
                )
            )
            if len(matches) != 1:
                raise RuntimeError(
                    f"expected exactly one primary formal group for {workload_name} {kind}, got {len(matches)}"
                )
            paths.append(matches[0])

    rows = []
    with ProcessPoolExecutor(max_workers=protocol["workers"]) as pool:
        for group_rows in pool.map(process_group, [(str(p), settings) for p in paths]):
            rows.extend(group_rows)

    after = inventory_fingerprint(RAW)
    if before != after:
        raise RuntimeError("raw reference inventory changed during held-out experiment")

    labels = [s["label"] for s in settings]
    summaries = [summarize_candidate(rows, label) for label in labels]
    capacities = [capacity_summary(rows, label) for label in labels]

    # Candidate comparison uses the pre-frozen rule only; do not silently pick
    # a scalar solely by best aggregate agreement.
    baseline_label = labels[0]
    baseline = next(x for x in summaries if x["candidate"] == baseline_label)
    candidates_not_worse_on_fa_and_better_on_fr = [
        {
            "candidate": x["candidate"],
            "false_acceptance": x["false_acceptance"],
            "false_rejection": x["false_rejection"],
            "agreement": x["agreement"],
        }
        for x in summaries
        if x["candidate"] != baseline_label
        and x["false_acceptance"] <= baseline["false_acceptance"]
        and x["false_rejection"] < baseline["false_rejection"]
    ]

    OUTPUT.mkdir(parents=True, exist_ok=True)
    result = {
        "status": "complete",
        "protocol": protocol,
        "new_helix_runs": 0,
        "raw_reference_inventory_before": before,
        "raw_reference_inventory_after": after,
        "physical_rows": len(rows) // len(settings),
        "candidate_evaluations": len(rows),
        "candidates": summaries,
        "capacity": capacities,
        "baseline_candidate": baseline_label,
        "candidates_meeting_prefrozen_nonworsening_rule": candidates_not_worse_on_fa_and_better_on_fr,
        "elapsed_s": time.perf_counter() - started,
    }
    (OUTPUT / "summary.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    compact = {
        "physical_rows": result["physical_rows"],
        "candidate_evaluations": result["candidate_evaluations"],
        "candidates": [
            {
                "candidate": x["candidate"],
                "false_acceptance": x["false_acceptance"],
                "false_rejection": x["false_rejection"],
                "agreement": x["agreement"],
                "fa_rate": x["false_acceptance_rate_given_reference_unsafe"],
                "fr_rate": x["false_rejection_rate_given_reference_safe"],
            }
            for x in summaries
        ],
        "capacity": [
            {
                "candidate": x["candidate"],
                "comparable_edges": x["comparable_edges"],
                "exact_edges": x["exact_edges"],
                "evaluator_nonmonotone_sequences": x["evaluator_nonmonotone_sequences"],
            }
            for x in capacities
        ],
        "nonworsening_candidates": candidates_not_worse_on_fa_and_better_on_fr,
        "elapsed_s": result["elapsed_s"],
    }
    print("HELDOUT_MECHANISM_SUMMARY " + json.dumps(compact, sort_keys=True), flush=True)
    print(f"HELDOUT_MECHANISM_OUTPUT {OUTPUT}", flush=True)


if __name__ == "__main__":
    main()
