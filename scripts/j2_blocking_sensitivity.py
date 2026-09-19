"""J2 blocking-term sensitivity on the broader cached reference set.

This experiment changes only the weight of the recovered accounting-only
Decode blocking term. J0 progress, J1 standard request horizons, the AICCC
network commitment equations, memory accounting, and strict safety semantics
remain unchanged. No blocking weight is selected by this script.
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
from j2_reference_profile_validation import (
    CachedProfiles,
    classify_pair,
    inventory_fingerprint,
    load_reference,
    monotonic_summary,
)
from research import RequestSpec, SLA, pipeline
from sla_aware_mvp.capacity import scale_workload

PROTOCOL_PATH = ROOT / "config" / "j2_blocking_sensitivity_v1.json"
OUTPUT = ROOT / "results" / "j2" / "blocking_sensitivity_v1"
RAW = ROOT / "results" / "raw_reference"


def process_case(args):
    source, path_string, scales = args
    path = Path(path_string)
    d = json.loads(path.read_text(encoding="utf-8"))
    if "reference_summary" not in d:
        return []
    case = d["case"]
    p = pipeline(
        case["placement"],
        case.get("shift", 0),
        case.get("hetero", False),
    )
    base = tuple(RequestSpec(**r) for r in d["requests"])
    sla = SLA(**d["sla"])

    points = []
    for saved in d["rows"]:
        intensity = saved["lambda"]
        cache_key = saved["reference"]["cache_key"]
        ref, detail = load_reference(cache_key, sla)
        points.append(
            {
                "intensity": intensity,
                "workload": scale_workload(base, intensity),
                "reference_safe": ref["safe"],
                "reference": detail,
                "cache_key": cache_key,
            }
        )

    out = []
    prof = CachedProfiles()
    for scale in scales:
        for point in points:
            result = evaluate_j1(
                p,
                point["workload"],
                sla,
                prof,
                intrinsic=True,
                blocking_policy="active-prefill-full-service-recovered-assumption",
                blocking_scale=scale,
                decode_block_size=16,
            )
            first = result["first_violation"]
            out.append(
                {
                    "source": source,
                    "case": case["id"],
                    "seed": case["seed"],
                    "placement": case["placement"],
                    "shift": case.get("shift", 0),
                    "heterogeneous": bool(case.get("hetero", False)),
                    "ttft_s": sla.ttft_s,
                    "tpot_s": sla.tpot_s,
                    "intensity": point["intensity"],
                    "blocking_scale": scale,
                    "evaluator_safe": result["safe"],
                    "reference_safe": point["reference_safe"],
                    "class": classify_pair(result["safe"], point["reference_safe"]),
                    "evaluator_first_kind": None if first is None else first["kind"],
                    "evaluator_first_object": None if first is None else first["object"],
                    "evaluator_peak_network_utilization": result["peak_network_utilization"],
                    "evaluator_max_standard_ttft_s": result["max_standard_ttft_s"],
                    "evaluator_max_average_tpot_s": result["max_average_tpot_s"],
                    "evaluator_runtime_s": result["runtime_s"],
                    "core_trajectory_hash": result["core_trajectory_hash"],
                    "reference_cache_key": point["cache_key"],
                    **{f"reference_{k}": v for k, v in point["reference"].items()},
                }
            )
    return out


def summarize_scale(rows, scale):
    group = [r for r in rows if r["blocking_scale"] == scale]
    counts = {
        k: sum(r["class"] == k for r in group)
        for k in ("safe_safe", "false_acceptance", "false_rejection", "unsafe_unsafe")
    }
    ref_safe = sum(r["reference_safe"] for r in group)
    ref_unsafe = len(group) - ref_safe
    fas = [r for r in group if r["class"] == "false_acceptance"]
    first_kinds = defaultdict(int)
    for r in group:
        key = "safe" if r["evaluator_first_kind"] is None else f"{r['evaluator_first_kind']}:{r['evaluator_first_object']}"
        first_kinds[key] += 1
    return {
        "blocking_scale": scale,
        "pairs": len(group),
        **counts,
        "agreement": (counts["safe_safe"] + counts["unsafe_unsafe"]) / len(group),
        "false_acceptance_rate_given_reference_unsafe": counts["false_acceptance"] / ref_unsafe if ref_unsafe else None,
        "false_rejection_rate_given_reference_safe": counts["false_rejection"] / ref_safe if ref_safe else None,
        "false_acceptance_max_reference_normalized_excess": max((r["reference_max_normalized_excess"] for r in fas), default=0.0),
        "false_acceptance_mean_reference_normalized_excess": statistics.fmean(r["reference_max_normalized_excess"] for r in fas) if fas else 0.0,
        "false_acceptance_max_violating_request_fraction": max((r["reference_violating_request_fraction"] for r in fas), default=0.0),
        "first_verdict_kinds": dict(sorted(first_kinds.items())),
        "median_runtime_ms": statistics.median(r["evaluator_runtime_s"] for r in group) * 1000,
        "false_acceptance_cases": [
            {
                "source": r["source"],
                "case": r["case"],
                "intensity": r["intensity"],
                "reference_max_normalized_excess": r["reference_max_normalized_excess"],
                "reference_violating_request_fraction": r["reference_violating_request_fraction"],
            }
            for r in fas
        ],
    }


def capacity_for_scale(rows, scale):
    selected = [r for r in rows if r["blocking_scale"] == scale]
    groups = defaultdict(list)
    for r in selected:
        groups[(r["source"], r["case"])].append(r)
    details = []
    for (source, case), group in sorted(groups.items()):
        e = monotonic_summary(group, "evaluator_safe")
        ref = monotonic_summary(group, "reference_safe")
        comparable = e["single_boundary_supported"] and ref["single_boundary_supported"]
        details.append(
            {
                "source": source,
                "case": case,
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
        "blocking_scale": scale,
        "cases": len(details),
        "comparable_edges": len(comparable),
        "exact_edges": sum(x["exact_edge"] for x in comparable),
        "evaluator_nonmonotone_cases": sum(x["evaluator"]["nonmonotone"] for x in details),
        "reference_nonmonotone_cases": sum(x["reference"]["nonmonotone"] for x in details),
        "details": details,
    }


def main():
    started = time.perf_counter()
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    before = inventory_fingerprint(RAW)

    tasks = []
    expected = {}
    for pop in protocol["populations"]:
        folder = ROOT / pop["source"]
        source = folder.name
        paths = []
        for path in sorted(folder.glob("*.json")):
            d = json.loads(path.read_text(encoding="utf-8"))
            if "reference_summary" in d:
                paths.append(path)
        tasks.extend((source, str(path), protocol["blocking_scales"]) for path in paths)
        expected[source] = pop["expected_pairs"]

    rows = []
    with ProcessPoolExecutor(max_workers=protocol["workers"]) as pool:
        for case_rows in pool.map(process_case, tasks):
            rows.extend(case_rows)

    counts_by_source = defaultdict(int)
    for r in rows:
        if r["blocking_scale"] == 1.0:
            counts_by_source[r["source"]] += 1
    for source, expected_count in expected.items():
        if counts_by_source[source] != expected_count:
            raise RuntimeError(
                f"unexpected pair count for {source}: "
                f"{counts_by_source[source]} != {expected_count}"
            )

    after = inventory_fingerprint(RAW)
    if before != after:
        raise RuntimeError("raw-reference inventory changed during blocking sensitivity")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    scales = protocol["blocking_scales"]
    summaries = [summarize_scale(rows, scale) for scale in scales]
    capacities = [capacity_for_scale(rows, scale) for scale in scales]

    summary = {
        "protocol_id": protocol["protocol_id"],
        "status": "complete",
        "interpretation": protocol["interpretation"],
        "new_helix_runs": 0,
        "raw_reference_inventory_before": before,
        "raw_reference_inventory_after": after,
        "pairs_per_scale": sum(counts_by_source.values()),
        "pairs_by_source": dict(counts_by_source),
        "scales": summaries,
        "capacity": capacities,
        "total_evaluator_trials": len(rows),
        "elapsed_s": time.perf_counter() - started,
    }
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    compact = {
        "scales": [
            {
                "blocking_scale": s["blocking_scale"],
                "agreement": s["agreement"],
                "false_acceptance": s["false_acceptance"],
                "false_rejection": s["false_rejection"],
                "fa_rate": s["false_acceptance_rate_given_reference_unsafe"],
                "fr_rate": s["false_rejection_rate_given_reference_safe"],
                "fa_max_norm_excess": s["false_acceptance_max_reference_normalized_excess"],
            }
            for s in summaries
        ],
        "capacity": [
            {
                "blocking_scale": c["blocking_scale"],
                "comparable_edges": c["comparable_edges"],
                "exact_edges": c["exact_edges"],
                "evaluator_nonmonotone_cases": c["evaluator_nonmonotone_cases"],
            }
            for c in capacities
        ],
        "total_evaluator_trials": len(rows),
        "elapsed_s": summary["elapsed_s"],
    }
    print("J2_BLOCKING_SUMMARY " + json.dumps(compact, sort_keys=True), flush=True)
    print(f"J2_BLOCKING_OUTPUT {OUTPUT}", flush=True)


if __name__ == "__main__":
    main()
