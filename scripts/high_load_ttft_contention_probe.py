"""Cache-only structural probe for high-load first-token contention."""
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

from high_load_ttft_diagnosis import point_rows
from j2_reference_profile_validation import inventory_fingerprint

RAW = ROOT / "results" / "raw_reference"
PROTOCOL = ROOT / "config" / "high_load_ttft_contention_probe_v1.json"
BASE_PROTOCOL = ROOT / "config" / "high_load_ttft_diagnosis_v1.json"
OUTPUT = ROOT / "results" / "high_load_ttft_contention_probe_v1"


def pct(values, q):
    xs = sorted(float(x) for x in values)
    if not xs:
        return None
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    w = pos - lo
    return xs[lo] * (1 - w) + xs[hi] * w


def summarize(rows):
    if not rows:
        return {"count": 0}
    runtime = [r["reference_first_decode_runtime_s"] for r in rows]
    predicted = [r["j1_predicted_first_decode_profile_s"] for r in rows]
    excess = [a - b for a, b in zip(runtime, predicted)]
    ratios = [a / b for a, b in zip(runtime, predicted) if b > 0]
    return {
        "count": len(rows),
        "runtime_mean_s": statistics.fmean(runtime),
        "runtime_median_s": statistics.median(runtime),
        "runtime_p95_s": pct(runtime, 0.95),
        "runtime_max_s": max(runtime),
        "predicted_mean_s": statistics.fmean(predicted),
        "excess_mean_s": statistics.fmean(excess),
        "excess_median_s": statistics.median(excess),
        "excess_p95_s": pct(excess, 0.95),
        "excess_max_s": max(excess),
        "ratio_median": statistics.median(ratios),
        "ratio_p95": pct(ratios, 0.95),
        "ratio_max": max(ratios),
    }


def main():
    started = time.perf_counter()
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    base_protocol = json.loads(BASE_PROTOCOL.read_text(encoding="utf-8"))
    before = inventory_fingerprint(RAW)

    rows = []
    for rel in base_protocol["physical_case_files"]:
        rows.extend(point_rows(ROOT / rel, base_protocol))

    after = inventory_fingerprint(RAW)
    if before != after:
        raise RuntimeError("cache-only contention probe changed raw reference inventory")

    k = int(protocol["pipeline_stage_count"])
    exact = defaultdict(list)
    for r in rows:
        exact[int(r["first_decode_max_decode"])].append(r)

    exact_summary = {str(n): summarize(group) for n, group in sorted(exact.items())}
    low = [r for r in rows if int(r["first_decode_max_decode"]) <= k]
    high = [r for r in rows if int(r["first_decode_max_decode"]) > k]
    split = {
        f"max_decode_le_{k}": summarize(low),
        f"max_decode_gt_{k}": summarize(high),
    }

    pair_groups = defaultdict(list)
    for r in rows:
        pair_groups[(int(r["first_decode_max_prefill"]), int(r["first_decode_max_decode"]))].append(r)
    by_concurrency_pair = {
        f"P{np}_D{nd}": summarize(group)
        for (np, nd), group in sorted(pair_groups.items())
    }
    top_outliers = []
    for r in sorted(
        rows,
        key=lambda x: x["reference_first_decode_runtime_s"] - x["j1_predicted_first_decode_profile_s"],
        reverse=True,
    )[:30]:
        top_outliers.append({
            "seed": r["seed"],
            "case_id": r["case_id"],
            "intensity": r["intensity"],
            "arrival_rate_rps": r["arrival_rate_rps"],
            "request_id": r["request_id"],
            "input_tokens": r["input_tokens"],
            "output_tokens": r["output_tokens"],
            "max_prefill": r["first_decode_max_prefill"],
            "max_decode": r["first_decode_max_decode"],
            "mean_prefill": r["first_decode_mean_prefill"],
            "mean_decode": r["first_decode_mean_decode"],
            "reference_runtime_s": r["reference_first_decode_runtime_s"],
            "predicted_profile_s": r["j1_predicted_first_decode_profile_s"],
            "excess_s": r["reference_first_decode_runtime_s"] - r["j1_predicted_first_decode_profile_s"],
        })

    # This is not a fitted threshold: it reports the two previously observed
    # high-load false-acceptance focus requests under the structural split.
    focus_rows = []
    for seed, rid in ((0, "azure-00011"), (7, "azure-00014")):
        candidates = [
            r for r in rows
            if int(r["seed"]) == seed and r["request_id"] == rid
        ]
        focus_rows.append({
            "seed": seed,
            "request_id": rid,
            "samples": [
                {
                    "intensity": r["intensity"],
                    "max_decode": r["first_decode_max_decode"],
                    "runtime_s": r["reference_first_decode_runtime_s"],
                    "predicted_s": r["j1_predicted_first_decode_profile_s"],
                    "excess_s": r["reference_first_decode_runtime_s"] - r["j1_predicted_first_decode_profile_s"],
                }
                for r in sorted(candidates, key=lambda x: x["intensity"])
            ],
        })

    summary = {
        "schema": 1,
        "experiment_id": protocol["experiment_id"],
        "status": "complete",
        "new_helix_runs": 0,
        "physical_points": len({(r["seed"], r["intensity"]) for r in rows}),
        "request_rows": len(rows),
        "raw_reference_inventory_before": before,
        "raw_reference_inventory_after": after,
        "pipeline_stage_count": k,
        "structural_split": split,
        "by_exact_first_decode_max_decode": exact_summary,
        "by_first_decode_concurrency_pair": by_concurrency_pair,
        "top_excess_rows_posthoc": top_outliers,
        "focus_request_series": focus_rows,
        "elapsed_s": time.perf_counter() - started,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        "HIGH_LOAD_TTFT_CONTENTION_PROBE "
        + json.dumps({
            "physical_points": summary["physical_points"],
            "request_rows": summary["request_rows"],
            "structural_split": split,
            "by_exact_first_decode_max_decode": exact_summary,
            "top_excess_rows_posthoc": top_outliers,
            "elapsed_s": summary["elapsed_s"],
        }, sort_keys=True, allow_nan=False),
        flush=True,
    )


if __name__ == "__main__":
    main()
