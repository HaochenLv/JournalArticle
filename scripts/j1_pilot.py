"""Bounded cache-only J1 semantic pilot.

This script never calls the HELIX reference runner. It reuses existing pinned
raw reference records, reconstructs standard TTFT/request-average TPOT through
standard_metrics_v1, and compares strict all-request safety with the J1 AICCC
ledger overlay on the same finite workloads.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import gzip
import hashlib
import json
import math
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aiccc_j1_evaluator import evaluate as evaluate_j1
from research import HELIX_COMMIT, Profiles, SLA, pipeline, workload, write_json
from sla_aware_mvp.capacity import scale_workload
from standard_metrics_v1 import classify, execution_identity, migrate_record

ADAPTER_COMMIT = "1cd5c56365b084fb06e3ca14f67448ddbf45275a"
PROTOCOL_PATH = ROOT / "config" / "j1_pilot_protocol_v1.json"
OUTPUT_PATH = ROOT / "results" / "j1" / "pilot_v1.json"


def file_name_fingerprint(paths):
    h = hashlib.sha256()
    for path in sorted(paths, key=lambda p: p.name):
        h.update(path.name.encode())
        h.update(b"\0")
    return h.hexdigest()


def build_reference_index(folder):
    index = {}
    aliases = 0
    malformed = []
    files = sorted(folder.glob("*.json.gz"))
    for path in files:
        try:
            with gzip.open(path, "rt", encoding="utf-8") as f:
                record = json.load(f)
            inputs = record.get("inputs")
            raw = record.get("raw")
            if not isinstance(inputs, dict) or not isinstance(raw, dict):
                continue
            if "pipeline" not in inputs or "workload" not in inputs:
                continue
            key = execution_identity(inputs)
            if key in index:
                aliases += 1
            else:
                index[key] = path
        except Exception as exc:
            malformed.append({"file": path.name, "error": type(exc).__name__})
    return files, index, aliases, malformed


def target_inputs(p, w, sla):
    return {
        "schema": 1,
        "helix_commit": HELIX_COMMIT,
        "adapter_commit": ADAPTER_COMMIT,
        "group_dispatch_extension": 1,
        "pipeline": asdict(p),
        "workload": [asdict(r) for r in w],
        "sla": asdict(sla),
    }


def max_reference_metrics(metrics):
    requests = metrics["request_metrics"].values()
    max_ttft = max((r["ttft_s"] for r in requests), default=0.0)
    tpots = [r["average_tpot_s"] for r in requests if r["average_tpot_s"] is not None]
    return max_ttft, max(tpots, default=0.0)


def apply_explicit_reference_accounting(metrics, sla):
    """Apply the same explicit fixed/queue charges used by the J1 ledger."""
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


def confusion(rows, field):
    out = {
        "safe_safe": 0,
        "safe_unsafe_false_acceptance": 0,
        "unsafe_safe_false_rejection": 0,
        "unsafe_unsafe": 0,
    }
    for row in rows:
        pred, truth = row[field]["safe"], row["reference"]["safe"]
        if pred and truth:
            out["safe_safe"] += 1
        elif pred and not truth:
            out["safe_unsafe_false_acceptance"] += 1
        elif not pred and truth:
            out["unsafe_safe_false_rejection"] += 1
        else:
            out["unsafe_unsafe"] += 1
    out["total"] = len(rows)
    out["agreement"] = (
        (out["safe_safe"] + out["unsafe_unsafe"]) / len(rows) if rows else None
    )
    return out


def main():
    started = time.perf_counter()
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    raw_folder = ROOT / "results" / "raw_reference"
    files_before, index, aliases, malformed = build_reference_index(raw_folder)
    names_before = file_name_fingerprint(files_before)

    cfg = protocol["sla"]
    sla = SLA(
        cfg["ttft_s"],
        cfg["tpot_s"],
        fixed_overhead_s=cfg["fixed_overhead_s"],
        queue_overhead_s=cfg["queue_overhead_s"],
    )
    prof = Profiles()
    rows, misses = [], []

    for seed in protocol["workload"]["seeds"]:
        base = workload(seed, protocol["workload"]["duration_s"])
        for placement in protocol["workload"]["placements"]:
            p = pipeline(placement)
            for intensity in protocol["workload"]["intensities"]:
                w = scale_workload(base, intensity)
                physical = execution_identity(target_inputs(p, w, sla))
                source = index.get(physical)
                if source is None:
                    misses.append({
                        "seed": seed,
                        "placement": placement,
                        "intensity": intensity,
                        "physical_point_id": physical,
                    })
                    continue

                with gzip.open(source, "rt", encoding="utf-8") as f:
                    record = json.load(f)
                source_sla = record.get("inputs", {}).get("sla", {})
                expected_overhead = sla.fixed_overhead_s + sla.queue_overhead_s
                source_overhead = (
                    source_sla.get("fixed_overhead_s", math.nan)
                    + source_sla.get("queue_overhead_s", math.nan)
                )
                if not math.isclose(
                    source_overhead, expected_overhead, rel_tol=0.0, abs_tol=1e-12
                ):
                    raise RuntimeError(
                        f"reference accounting mismatch for {source.name}: "
                        f"{source_overhead} vs {expected_overhead}"
                    )

                migrated = migrate_record(record)
                if migrated["status"] != "complete":
                    raise RuntimeError(
                        f"reference migration failed for {source.name}: "
                        f"{migrated.get('error_code')} {migrated.get('error_detail')}"
                    )
                accounted_reference = apply_explicit_reference_accounting(migrated, sla)
                reference = classify(accounted_reference, sla, target=1.0)
                if reference["safe"] is None:
                    raise RuntimeError(f"unclassifiable reference {source.name}")
                ref_ttft, ref_tpot = max_reference_metrics(accounted_reference)

                j1 = evaluate_j1(
                    p,
                    w,
                    sla,
                    prof,
                    intrinsic=protocol["evaluator"]["intrinsic"],
                    blocking_policy=protocol["evaluator"]["blocking_policy"],
                    decode_block_size=protocol["evaluator"]["decode_block_size"],
                )
                rows.append({
                    "seed": seed,
                    "placement": placement,
                    "intensity": intensity,
                    "physical_point_id": physical,
                    "reference_source": str(source.relative_to(ROOT)).replace("\\", "/"),
                    "j1": {
                        "safe": j1["safe"],
                        "first_violation": j1["first_violation"],
                        "peak_network_utilization": j1["peak_network_utilization"],
                        "max_standard_ttft_s": j1["max_standard_ttft_s"],
                        "max_average_tpot_s": j1["max_average_tpot_s"],
                        "runtime_s": j1["runtime_s"],
                        "core_trajectory_hash": j1["core_trajectory_hash"],
                    },
                    "j0_phase_local": {"safe": j1["core_safe_under_phase_local_sla"]},
                    "reference": {
                        "safe": reference["safe"],
                        "joint_pass_count": reference["joint_pass_count"],
                        "required_pass_count": reference["required_pass_count"],
                        "ttft_fail_count": reference["ttft_fail_count"],
                        "tpot_fail_count": reference["tpot_fail_count"],
                        "both_fail_count": reference["both_fail_count"],
                        "max_standard_ttft_s": ref_ttft,
                        "max_average_tpot_s": ref_tpot,
                    },
                })

    if misses:
        raise RuntimeError(
            "J1 pilot is cache-only and required reference points are missing: "
            + json.dumps(misses[:5], sort_keys=True)
        )

    files_after = sorted(raw_folder.glob("*.json.gz"))
    names_after = file_name_fingerprint(files_after)
    if len(files_before) != len(files_after) or names_before != names_after:
        raise RuntimeError("raw reference cache changed during cache-only J1 pilot")

    def disagreement_view(row):
        return {
            "seed": row["seed"],
            "placement": row["placement"],
            "intensity": row["intensity"],
            "physical_point_id": row["physical_point_id"],
            "j1_first_violation": row["j1"]["first_violation"],
            "j1_max_standard_ttft_s": row["j1"]["max_standard_ttft_s"],
            "j1_max_average_tpot_s": row["j1"]["max_average_tpot_s"],
            "reference_max_standard_ttft_s": row["reference"]["max_standard_ttft_s"],
            "reference_max_average_tpot_s": row["reference"]["max_average_tpot_s"],
            "reference_ttft_fail_count": row["reference"]["ttft_fail_count"],
            "reference_tpot_fail_count": row["reference"]["tpot_fail_count"],
        }

    j1_conf = confusion(rows, "j1")
    j0_conf = confusion(rows, "j0_phase_local")
    false_acceptances = [
        disagreement_view(row)
        for row in rows
        if row["j1"]["safe"] and not row["reference"]["safe"]
    ]
    false_rejections = [
        disagreement_view(row)
        for row in rows
        if not row["j1"]["safe"] and row["reference"]["safe"]
    ]
    first_kinds = {}
    for row in rows:
        first_v = row["j1"]["first_violation"]
        kind = "safe" if first_v is None else f"{first_v['kind']}:{first_v['object']}"
        first_kinds[kind] = first_kinds.get(kind, 0) + 1

    ttft_gaps = [
        row["j1"]["max_standard_ttft_s"] - row["reference"]["max_standard_ttft_s"]
        for row in rows
    ]
    tpot_gaps = [
        row["j1"]["max_average_tpot_s"] - row["reference"]["max_average_tpot_s"]
        for row in rows
    ]

    result = {
        "protocol": protocol,
        "status": "complete",
        "reference_policy": (
            "cache-only standard endpoints with the same explicit fixed/queue "
            "ledger charge; no evaluator H/blocking correction"
        ),
        "new_helix_runs": 0,
        "rows": rows,
        "summary": {
            "points": len(rows),
            "reference_index_files": len(files_before),
            "reference_index_unique_physical": len(index),
            "reference_index_aliases": aliases,
            "reference_index_malformed": malformed,
            "cache_misses": 0,
            "raw_reference_name_fingerprint_before": names_before,
            "raw_reference_name_fingerprint_after": names_after,
            "j1_confusion": j1_conf,
            "j0_phase_local_confusion_against_standard_reference": j0_conf,
            "false_acceptance_cases": false_acceptances,
            "false_rejection_cases": false_rejections,
            "j1_first_verdict_kinds": first_kinds,
            "max_j1_minus_reference_ttft_s": max(ttft_gaps, default=0.0),
            "min_j1_minus_reference_ttft_s": min(ttft_gaps, default=0.0),
            "max_j1_minus_reference_average_tpot_s": max(tpot_gaps, default=0.0),
            "min_j1_minus_reference_average_tpot_s": min(tpot_gaps, default=0.0),
            "j1_runtime_median_ms": (
                sorted(row["j1"]["runtime_s"] for row in rows)[len(rows) // 2] * 1000
            ),
            "elapsed_s": time.perf_counter() - started,
        },
    }
    write_json(OUTPUT_PATH, result)
    print("J1_PILOT_SUMMARY " + json.dumps(result["summary"], sort_keys=True), flush=True)
    print(f"J1_PILOT_OUTPUT {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
