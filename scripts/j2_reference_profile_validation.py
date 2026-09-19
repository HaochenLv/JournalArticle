"""J2: broader J1 reference validation and deterministic profile-error stress.

The experiment is deliberately cache-only. It never calls research.reference()
or the HELIX execution adapter. Existing pinned raw-reference records referenced
by the frozen diagnostic datasets supply the execution truth.

The modeling direction is fixed:
J0 profiling-driven progress -> J1 request-horizon ledger -> unchanged AICCC
residual-time / omega / delta / b_req commitments -> strict feasibility.
"""
from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path
import csv
import gzip
import hashlib
import json
import math
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aiccc_j1_evaluator import evaluate as evaluate_j1
from research import Profiles, RequestSpec, SLA, pipeline
from sla_aware_mvp.capacity import scale_workload
from standard_metrics_v1 import classify, migrate_record

PROTOCOL_PATH = ROOT / "config" / "j2_reference_profile_protocol_v1.json"
OUTPUT = ROOT / "results" / "j2" / "reference_profile_v1"
RAW = ROOT / "results" / "raw_reference"


class CachedProfiles(Profiles):
    """Same profile semantics as research.Profiles, with pure lookup caching."""

    def __init__(self, p_scale=1.0, d_scale=1.0, device_bias=None):
        super().__init__(p_scale, d_scale, device_bias)
        self._pc = {}
        self._dc = {}

    @staticmethod
    def _pipe_key(p):
        return tuple(
            (s.id, s.num_layers, p.nodes[s.node_id].hardware_type)
            for s in p.stages
        )

    def prefill_time(self, r, p, np, nd):
        key = (self._pipe_key(p), r.input_tokens)
        if key not in self._pc:
            self._pc[key] = super().prefill_time(r, p, np, nd)
        return self._pc[key]

    def decode_time_per_token(self, r, ctx, p, np, nd):
        key = (self._pipe_key(p), nd)
        if key not in self._dc:
            self._dc[key] = super().decode_time_per_token(r, ctx, p, np, nd)
        return self._dc[key]


def inventory_fingerprint(folder):
    h = hashlib.sha256()
    count = 0
    total = 0
    for path in sorted(folder.glob("*.json.gz"), key=lambda p: p.name):
        stat = path.stat()
        h.update(path.name.encode())
        h.update(b"\0")
        h.update(str(stat.st_size).encode())
        h.update(b"\n")
        count += 1
        total += stat.st_size
    return {"count": count, "bytes": total, "sha256_name_size": h.hexdigest()}


def variants(heterogeneous):
    out = [("nominal", 1.0, 1.0, None)]
    for phase in ("prefill", "decode", "both"):
        for scale in (0.8, 0.9, 0.95, 1.05, 1.1, 1.2):
            ps = scale if phase in ("prefill", "both") else 1.0
            ds = scale if phase in ("decode", "both") else 1.0
            out.append((f"{phase}_x{scale:.2f}", ps, ds, None))
    if heterogeneous:
        for device in ("l4x2", "t4x4"):
            for scale in (0.9, 1.1):
                out.append((f"{device}_x{scale:.2f}", 1.0, 1.0, (device, scale)))
    return out


def add_explicit_overhead(metrics, sla):
    overhead = sla.fixed_overhead_s + sla.queue_overhead_s
    return {
        **metrics,
        "request_metrics": {
            rid: {
                **row,
                "ttft_s": row["ttft_s"] + overhead,
                "average_tpot_s": (
                    None
                    if row["average_tpot_s"] is None
                    else row["average_tpot_s"] + overhead
                ),
            }
            for rid, row in metrics["request_metrics"].items()
        },
    }


def reference_details(metrics, sla):
    rows = list(metrics["request_metrics"].values())
    bad = []
    max_ttft = 0.0
    max_tpot = 0.0
    max_norm = 0.0
    max_ttft_excess = 0.0
    max_tpot_excess = 0.0
    for row in rows:
        ttft = row["ttft_s"]
        tpot = row["average_tpot_s"]
        max_ttft = max(max_ttft, ttft)
        ttft_excess = max(0.0, ttft - sla.ttft_s)
        max_ttft_excess = max(max_ttft_excess, ttft_excess)
        norm = max(0.0, ttft / sla.ttft_s - 1.0) if sla.ttft_s > 0 else (math.inf if ttft > 0 else 0.0)
        fail = ttft > sla.ttft_s
        if tpot is not None:
            max_tpot = max(max_tpot, tpot)
            tpot_excess = max(0.0, tpot - sla.tpot_s)
            max_tpot_excess = max(max_tpot_excess, tpot_excess)
            tnorm = max(0.0, tpot / sla.tpot_s - 1.0) if sla.tpot_s > 0 else (math.inf if tpot > 0 else 0.0)
            norm = max(norm, tnorm)
            fail = fail or tpot > sla.tpot_s
        max_norm = max(max_norm, norm)
        bad.append(fail)
    return {
        "max_standard_ttft_s": max_ttft,
        "max_average_tpot_s": max_tpot,
        "violating_requests": sum(bad),
        "request_count": len(rows),
        "violating_request_fraction": sum(bad) / len(rows) if rows else 0.0,
        "max_ttft_excess_s": max_ttft_excess,
        "max_average_tpot_excess_s": max_tpot_excess,
        "max_normalized_excess": max_norm,
    }


def load_reference(cache_key, sla):
    path = RAW / (cache_key + ".json.gz")
    if not path.exists():
        raise RuntimeError(f"missing pinned raw reference: {cache_key}")
    with gzip.open(path, "rt", encoding="utf-8") as f:
        record = json.load(f)
    migrated = migrate_record(record)
    if migrated["status"] != "complete":
        raise RuntimeError(
            f"standard metric migration failed for {cache_key}: "
            f"{migrated.get('error_code')} {migrated.get('error_detail')}"
        )
    accounted = add_explicit_overhead(migrated, sla)
    verdict = classify(accounted, sla, target=1.0)
    if verdict["safe"] is None:
        raise RuntimeError(f"unclassifiable reference: {cache_key}")
    return verdict, reference_details(accounted, sla)


def classify_pair(pred, truth):
    if pred and truth:
        return "safe_safe"
    if pred and not truth:
        return "false_acceptance"
    if not pred and truth:
        return "false_rejection"
    return "unsafe_unsafe"


def process_case(args):
    source, path_string = args
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
        reference, detail = load_reference(cache_key, sla)
        points.append(
            {
                "intensity": intensity,
                "workload": scale_workload(base, intensity),
                "cache_key": cache_key,
                "reference_safe": reference["safe"],
                "reference": detail,
            }
        )

    out = []
    for label, ps, ds, device_bias in variants(case.get("hetero", False)):
        prof = CachedProfiles(ps, ds, device_bias)
        for point in points:
            result = evaluate_j1(
                p,
                point["workload"],
                sla,
                prof,
                intrinsic=True,
                blocking_policy="active-prefill-full-service-recovered-assumption",
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
                    "variant": label,
                    "prefill_scale": ps,
                    "decode_scale": ds,
                    "device_bias": None if device_bias is None else f"{device_bias[0]}:{device_bias[1]}",
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


def monotonic_summary(rows, safe_key):
    ordered = sorted(rows, key=lambda r: r["intensity"])
    seen_unsafe = False
    nonmonotone = False
    for row in ordered:
        safe = row[safe_key]
        if not safe:
            seen_unsafe = True
        elif seen_unsafe:
            nonmonotone = True
    safe_values = [r["intensity"] for r in ordered if r[safe_key]]
    largest = max(safe_values) if safe_values else None
    unsafe_above = [
        r["intensity"]
        for r in ordered
        if largest is not None and r["intensity"] > largest and not r[safe_key]
    ]
    nearest = min(unsafe_above) if unsafe_above else None
    return {
        "largest_safe": largest,
        "nearest_unsafe_above": nearest,
        "all_unsafe": not safe_values,
        "right_censored": bool(ordered and ordered[-1][safe_key]),
        "nonmonotone": nonmonotone,
        "single_boundary_supported": (
            bool(safe_values)
            and nearest is not None
            and not nonmonotone
        ),
    }


def summarize_variant(rows, label):
    group = [r for r in rows if r["variant"] == label]
    ref_safe = sum(r["reference_safe"] for r in group)
    ref_unsafe = len(group) - ref_safe
    counts = {k: 0 for k in ("safe_safe", "false_acceptance", "false_rejection", "unsafe_unsafe")}
    for row in group:
        counts[row["class"]] += 1
    fas = [r for r in group if r["class"] == "false_acceptance"]
    frs = [r for r in group if r["class"] == "false_rejection"]
    first_kinds = defaultdict(int)
    for row in group:
        key = "safe" if row["evaluator_first_kind"] is None else f"{row['evaluator_first_kind']}:{row['evaluator_first_object']}"
        first_kinds[key] += 1
    return {
        "variant": label,
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
        "false_rejection_mean_reference_headroom_not_reported": None,
        "first_verdict_kinds": dict(sorted(first_kinds.items())),
        "median_runtime_ms": statistics.median(r["evaluator_runtime_s"] for r in group) * 1000 if group else None,
        "false_acceptance_cases": [
            {
                "source": r["source"],
                "case": r["case"],
                "intensity": r["intensity"],
                "reference_max_normalized_excess": r["reference_max_normalized_excess"],
                "reference_violating_request_fraction": r["reference_violating_request_fraction"],
                "first_kind": r["evaluator_first_kind"],
            }
            for r in fas
        ],
        "false_rejection_cases": [
            {
                "source": r["source"],
                "case": r["case"],
                "intensity": r["intensity"],
                "first_kind": r["evaluator_first_kind"],
            }
            for r in frs
        ],
    }


def capacity_summary(rows, label):
    selected = [r for r in rows if r["variant"] == label]
    groups = defaultdict(list)
    for row in selected:
        groups[(row["source"], row["case"])].append(row)
    details = []
    for (source, case), group in sorted(groups.items()):
        e = monotonic_summary(group, "evaluator_safe")
        r = monotonic_summary(group, "reference_safe")
        comparable = e["single_boundary_supported"] and r["single_boundary_supported"]
        details.append(
            {
                "source": source,
                "case": case,
                "evaluator": e,
                "reference": r,
                "comparable_edge": comparable,
                "exact_edge": comparable and (
                    e["largest_safe"],
                    e["nearest_unsafe_above"],
                ) == (
                    r["largest_safe"],
                    r["nearest_unsafe_above"],
                ),
            }
        )
    comparable = [x for x in details if x["comparable_edge"]]
    return {
        "variant": label,
        "cases": len(details),
        "comparable_edges": len(comparable),
        "exact_edges": sum(x["exact_edge"] for x in comparable),
        "evaluator_nonmonotone_cases": sum(x["evaluator"]["nonmonotone"] for x in details),
        "reference_nonmonotone_cases": sum(x["reference"]["nonmonotone"] for x in details),
        "details": details,
    }


def write_trials(rows):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "trials.csv"
    keys = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


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
        tasks.extend((source, str(path)) for path in paths)
        expected[source] = pop["expected_nominal_pairs"]

    rows = []
    with ProcessPoolExecutor(max_workers=protocol["workers"]) as pool:
        for case_rows in pool.map(process_case, tasks):
            rows.extend(case_rows)

    nominal_counts = defaultdict(int)
    for row in rows:
        if row["variant"] == "nominal":
            nominal_counts[row["source"]] += 1
    for source, count in expected.items():
        if nominal_counts[source] != count:
            raise RuntimeError(
                f"unexpected nominal pair count for {source}: "
                f"{nominal_counts[source]} != {count}"
            )

    after = inventory_fingerprint(RAW)
    if before != after:
        raise RuntimeError("raw-reference inventory changed during cache-only J2")

    write_trials(rows)
    labels = sorted({r["variant"] for r in rows}, key=lambda x: (x != "nominal", x))
    variants_summary = [summarize_variant(rows, label) for label in labels]
    capacity = [capacity_summary(rows, label) for label in labels]

    nominal = next(x for x in variants_summary if x["variant"] == "nominal")
    by_source = {}
    for source in sorted({r["source"] for r in rows}):
        sub = [r for r in rows if r["source"] == source and r["variant"] == "nominal"]
        counts = {k: sum(r["class"] == k for r in sub) for k in ("safe_safe", "false_acceptance", "false_rejection", "unsafe_unsafe")}
        by_source[source] = {
            "pairs": len(sub),
            **counts,
            "agreement": (counts["safe_safe"] + counts["unsafe_unsafe"]) / len(sub),
        }

    summary = {
        "protocol_id": protocol["protocol_id"],
        "status": "complete",
        "interpretation": protocol["interpretation"],
        "new_helix_runs": 0,
        "raw_reference_inventory_before": before,
        "raw_reference_inventory_after": after,
        "nominal_pairs": sum(nominal_counts.values()),
        "nominal_pairs_by_source": dict(nominal_counts),
        "nominal_confusion": {
            k: nominal[k]
            for k in (
                "pairs",
                "safe_safe",
                "false_acceptance",
                "false_rejection",
                "unsafe_unsafe",
                "agreement",
                "false_acceptance_rate_given_reference_unsafe",
                "false_rejection_rate_given_reference_safe",
            )
        },
        "nominal_by_source": by_source,
        "variants": variants_summary,
        "capacity": capacity,
        "total_evaluator_trials": len(rows),
        "elapsed_s": time.perf_counter() - started,
    }
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    compact = {
        "nominal_confusion": summary["nominal_confusion"],
        "nominal_by_source": by_source,
        "profile_variants": [
            {
                "variant": x["variant"],
                "pairs": x["pairs"],
                "false_acceptance": x["false_acceptance"],
                "false_rejection": x["false_rejection"],
                "agreement": x["agreement"],
                "fa_rate": x["false_acceptance_rate_given_reference_unsafe"],
                "fr_rate": x["false_rejection_rate_given_reference_safe"],
                "fa_max_norm_excess": x["false_acceptance_max_reference_normalized_excess"],
            }
            for x in variants_summary
        ],
        "capacity": [
            {
                "variant": x["variant"],
                "cases": x["cases"],
                "comparable_edges": x["comparable_edges"],
                "exact_edges": x["exact_edges"],
                "evaluator_nonmonotone_cases": x["evaluator_nonmonotone_cases"],
                "reference_nonmonotone_cases": x["reference_nonmonotone_cases"],
            }
            for x in capacity
        ],
        "total_evaluator_trials": len(rows),
        "elapsed_s": summary["elapsed_s"],
    }
    print("J2_SUMMARY " + json.dumps(compact, sort_keys=True), flush=True)
    print(f"J2_OUTPUT {OUTPUT}", flush=True)


if __name__ == "__main__":
    main()
