"""Confirm the frozen accounting candidate on the two long formal workloads.

The candidate was selected before this run. This script compares only the
current accounting and the frozen candidate on h104/h106, reusing existing
pinned HELIX records. No HELIX execution is launched.
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

PROTOCOL = ROOT / "config" / "long_workload_confirmation.json"
OUTPUT = ROOT / "results" / "long_workload_confirmation"
RAW = ROOT / "results" / "raw_reference"


def sla_for(kind):
    cfg = (
        CONFIG["a100_slas"]["decode"]
        if kind == "a100"
        else CONFIG["heterogeneous_slas"]["decode"]
    )
    return SLA(**cfg, fixed_overhead_s=CONFIG["fixed_overhead_s"])


def process_group(args):
    path_string, comparisons = args
    path = Path(path_string)
    data = json.loads(path.read_text(encoding="utf-8"))
    group = data["group"]
    _, base = load_workload(group["workload"])
    hetero = group["kind"] == "heterogeneous"
    sla = sla_for(group["kind"])
    prof = CachedProfiles()
    out = []

    for saved in data["rows"]:
        if saved.get("status") != "ok":
            continue
        shift = saved["shift"]
        intensity = saved["intensity"]
        p = pipeline(group["link"], shift, hetero)
        w = scale_workload(base, intensity)
        reference, detail = load_reference(saved["reference_cache_key"], sla)

        baseline_hash = None
        baseline_final = None
        for comp in comparisons:
            result = evaluate_j1(
                p,
                w,
                sla,
                prof,
                intrinsic=True,
                blocking_policy="active-prefill-full-service-recovered-assumption",
                blocking_scale=1.0,
                blocking_mode=comp["blocking_mode"],
                ttft_profile_uncertainty_fraction=comp["ttft_profile_uncertainty_fraction"],
                decode_block_size=16,
            )
            if baseline_hash is None:
                baseline_hash = result["core_trajectory_hash"]
                baseline_final = result["final_time_s"]
            elif result["core_trajectory_hash"] != baseline_hash or result["final_time_s"] != baseline_final:
                raise RuntimeError("accounting candidate changed the frozen J0 trajectory")

            first = result["first_violation"]
            out.append(
                {
                    "group": group["id"],
                    "workload": group["workload"],
                    "kind": group["kind"],
                    "link": group["link"],
                    "shift": shift,
                    "intensity": intensity,
                    "requests": len(base),
                    "comparison": comp["label"],
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
                    "reference_cache_key": saved["reference_cache_key"],
                    **{f"reference_{k}": v for k, v in detail.items()},
                }
            )
    return out


def summarize(rows, label):
    group = [r for r in rows if r["comparison"] == label]
    counts = {
        k: sum(r["class"] == k for r in group)
        for k in ("safe_safe", "false_acceptance", "false_rejection", "unsafe_unsafe")
    }
    ref_safe = sum(r["reference_safe"] for r in group)
    ref_unsafe = len(group) - ref_safe
    fas = [r for r in group if r["class"] == "false_acceptance"]
    frs = [r for r in group if r["class"] == "false_rejection"]
    return {
        "comparison": label,
        "pairs": len(group),
        **counts,
        "agreement": (counts["safe_safe"] + counts["unsafe_unsafe"]) / len(group),
        "false_acceptance_rate_given_reference_unsafe": counts["false_acceptance"] / ref_unsafe if ref_unsafe else None,
        "false_rejection_rate_given_reference_safe": counts["false_rejection"] / ref_safe if ref_safe else None,
        "false_acceptance_max_reference_normalized_excess": max((r["reference_max_normalized_excess"] for r in fas), default=0.0),
        "false_acceptance_mean_reference_normalized_excess": statistics.fmean(r["reference_max_normalized_excess"] for r in fas) if fas else 0.0,
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
        "false_rejection_by_kind": {
            kind: sum(r["evaluator_first_kind"] == kind for r in frs)
            for kind in sorted({r["evaluator_first_kind"] for r in frs})
        },
    }


def capacity(rows, label):
    selected = [r for r in rows if r["comparison"] == label]
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
                    e["largest_safe"], e["nearest_unsafe_above"]
                ) == (
                    ref["largest_safe"], ref["nearest_unsafe_above"]
                ),
            }
        )
    comparable = [x for x in details if x["comparable_edge"]]
    return {
        "comparison": label,
        "case_shift_sequences": len(details),
        "comparable_edges": len(comparable),
        "exact_edges": sum(x["exact_edge"] for x in comparable),
        "evaluator_nonmonotone_sequences": sum(x["evaluator"]["nonmonotone"] for x in details),
        "reference_nonmonotone_sequences": sum(x["reference"]["nonmonotone"] for x in details),
        "details": details,
    }


def main():
    started = time.perf_counter()
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    comparisons = protocol["comparison"]
    before = inventory_fingerprint(RAW)

    paths = []
    for workload_name in protocol["reserved_confirmation_workloads"]:
        for kind in ("a100", "heterogeneous"):
            matches = sorted(
                (ROOT / "results" / "formal" / "groups").glob(
                    f"{workload_name}-{kind}-*.json"
                )
            )
            if len(matches) != 1:
                raise RuntimeError(
                    f"expected one group for {workload_name} {kind}, got {len(matches)}"
                )
            paths.append(matches[0])

    rows = []
    with ProcessPoolExecutor(max_workers=protocol["workers"]) as pool:
        for group_rows in pool.map(process_group, [(str(p), comparisons) for p in paths]):
            rows.extend(group_rows)

    after = inventory_fingerprint(RAW)
    if before != after:
        raise RuntimeError("raw-reference inventory changed during confirmation")

    labels = [x["label"] for x in comparisons]
    summaries = [summarize(rows, label) for label in labels]
    capacities = [capacity(rows, label) for label in labels]

    current = next(x for x in summaries if x["comparison"] == "current accounting")
    candidate = next(x for x in summaries if x["comparison"] == "candidate accounting")
    decision = {
        "does_not_increase_false_acceptance": candidate["false_acceptance"] <= current["false_acceptance"],
        "reduces_false_rejection": candidate["false_rejection"] < current["false_rejection"],
        "agreement_change": candidate["agreement"] - current["agreement"],
    }

    result = {
        "status": "complete",
        "protocol": protocol,
        "new_helix_runs": 0,
        "raw_reference_inventory_before": before,
        "raw_reference_inventory_after": after,
        "physical_rows": len(rows) // len(comparisons),
        "candidate_evaluations": len(rows),
        "summaries": summaries,
        "capacity": capacities,
        "prefrozen_confirmation_questions": decision,
        "elapsed_s": time.perf_counter() - started,
    }

    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "summary.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    compact = {
        "physical_rows": result["physical_rows"],
        "summaries": summaries,
        "capacity": [
            {
                "comparison": x["comparison"],
                "comparable_edges": x["comparable_edges"],
                "exact_edges": x["exact_edges"],
                "evaluator_nonmonotone_sequences": x["evaluator_nonmonotone_sequences"],
            }
            for x in capacities
        ],
        "confirmation": decision,
        "elapsed_s": result["elapsed_s"],
    }
    print("LONG_CONFIRMATION_SUMMARY " + json.dumps(compact, sort_keys=True), flush=True)
    print(f"LONG_CONFIRMATION_OUTPUT {OUTPUT}", flush=True)


if __name__ == "__main__":
    main()
