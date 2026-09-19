"""Fresh four-point HELIX stage trace for the first output token.

The frozen experiment instruments only request.location_history in the pinned
HELIX execution reference. Scheduling, model profiles, workload construction,
pipeline, and AICCC/J1 code are not changed.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import json
import math
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / ".deps" / "evaluator" / "src"))

from research import RequestSpec, SLA, pipeline
from sla_aware_mvp.capacity import scale_workload
from sla_aware_mvp.helix_fixed_reference import (
    _build_helix_simulator,
    _issue_fixed_query,
    _load_helix_runtime,
    extract_helix_query_metrics,
)

PROTOCOL = ROOT / "config" / "high_load_ttft_stage_trace_v1.json"
OUTPUT = ROOT / "results" / "high_load_ttft_stage_trace_v1"


def _case(seed: int):
    path = ROOT / "results" / "diagnostic" / "nominal_gap" / f"a100-s{seed}-slow-prefill.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw, tuple(RequestSpec(**x) for x in raw["requests"]), SLA(**raw["sla"])


def _location_breakdown(history, uid_to_logical):
    if len(history) < 2:
        raise RuntimeError("incomplete first-Decode location history")
    rows = []
    compute = defaultdict(float)
    link_total = 0.0
    source_total = 0.0
    other_total = 0.0
    for (loc, t0), (_, t1) in zip(history[:-1], history[1:]):
        dt = float(t1) - float(t0)
        if dt < -1e-12:
            raise RuntimeError("location time regressed")
        if loc.startswith("RequestLocation.ComputeNode-"):
            uid = int(loc.rsplit("-", 1)[1])
            label = uid_to_logical.get(uid, f"compute-{uid}")
            compute[label] += dt
            category = f"compute:{label}"
        elif loc.startswith("RequestLocation.Link-"):
            link_total += dt
            category = "link"
        elif loc.startswith("RequestLocation.SourceNode-"):
            source_total += dt
            category = "source"
        else:
            other_total += dt
            category = "other"
        rows.append({"location": loc, "category": category, "start_s": float(t0), "end_s": float(t1), "duration_s": dt})
    total = float(history[-1][1]) - float(history[0][1])
    components = source_total + link_total + other_total + sum(compute.values())
    if abs(total - components) > 1e-8:
        raise RuntimeError("location decomposition does not close")
    return {
        "total_runtime_s": total,
        "source_wait_s": source_total,
        "link_time_s": link_total,
        "other_time_s": other_total,
        "compute_residence_s": dict(sorted(compute.items())),
        "compute_residence_total_s": sum(compute.values()),
        "timeline": rows,
    }


def run_point(seed: int, intensity: float, focus_request_id: str):
    source, base, sla = _case(seed)
    case = source["case"]
    p = pipeline(case["placement"], case.get("shift", 0), case.get("hetero", False))
    workload = scale_workload(base, intensity)
    runtime = _load_helix_runtime(ROOT / ".deps" / "helix")
    captured = {}
    original_submit = runtime.Query.submit_finished_request

    def patched_submit(self, request):
        # Before the original call, len(history)==1 exactly for the first Decode
        # iteration because Prefill has already been appended.
        if len(self.inference_history) == 1:
            captured[self.query_uid] = {
                "request_uid": request.request_uid,
                "phase": str(request.phase),
                "prev_num_tokens": request.prev_num_tokens,
                "location_history": [(str(loc), float(ts)) for loc, ts in request.location_history],
            }
        return original_submit(self, request)

    runtime.Query.submit_finished_request = patched_submit
    try:
        simulator, mini_pipeline, helix_uid_by_node = _build_helix_simulator(
            pipeline=p, runtime=runtime
        )
        uid_to_logical = {uid: node for node, uid in helix_uid_by_node.items()}
        base_time = simulator.current_time
        query_uid_to_request_id = {}
        for req in workload:
            qid = _issue_fixed_query(
                simulator=simulator,
                runtime=runtime,
                creation_time=base_time + req.arrival_time_s,
                input_tokens=req.input_tokens,
                output_tokens=req.output_tokens,
                mini_pipeline=mini_pipeline,
            )
            query_uid_to_request_id[qid] = req.id

        events = 0
        while simulator.query_manager.queries_on_the_fly:
            ok, _ = simulator.simulate_next_event()
            events += 1
            if not ok:
                raise RuntimeError("HELIX event queue drained with unfinished queries")
            if events > 5_000_000:
                raise RuntimeError("HELIX stage-trace event limit exceeded")

        overhead = sla.fixed_overhead_s + sla.queue_overhead_s
        by_id = {}
        for qid, (_, query) in simulator.query_manager.finished_queries.items():
            rid = query_uid_to_request_id[qid]
            metric = extract_helix_query_metrics(
                request_id=rid, query=query, overhead_s=overhead
            )
            first_trace = captured.get(qid)
            if first_trace is None:
                raise RuntimeError(f"first Decode trace missing for {rid}")
            breakdown = _location_breakdown(
                first_trace["location_history"], uid_to_logical
            )
            # Stored decode TPOT includes the explicit record overhead; the
            # location timeline is pure HELIX runtime.
            expected_runtime = metric.decode_tpot_s[0] - overhead
            if abs(expected_runtime - breakdown["total_runtime_s"]) > 1e-8:
                raise RuntimeError(
                    f"first Decode location identity failed for {rid}: "
                    f"{expected_runtime} vs {breakdown['total_runtime_s']}"
                )
            by_id[rid] = {
                "request_id": rid,
                "aligned_ttft_s": metric.aligned_ttft_s,
                "true_first_token_ttft_s": metric.true_first_token_ttft_s,
                "first_decode_accounted_s": metric.decode_tpot_s[0],
                "first_decode_runtime_s": expected_runtime,
                "location": breakdown,
            }

        if focus_request_id not in by_id:
            raise RuntimeError(f"focus request missing: {focus_request_id}")
        worst = max(by_id.values(), key=lambda x: x["true_first_token_ttft_s"])
        if worst["request_id"] != focus_request_id:
            raise RuntimeError(
                f"frozen focus request changed: expected {focus_request_id}, "
                f"observed worst {worst['request_id']}"
            )
        return {
            "seed": seed,
            "intensity": intensity,
            "role": next(
                x["role"]
                for x in json.loads(PROTOCOL.read_text(encoding="utf-8"))["points"]
                if x["seed"] == seed and abs(float(x["intensity"]) - intensity) < 1e-12
            ),
            "events": events,
            "finished_requests": len(by_id),
            "final_time_s": simulator.current_time - base_time,
            "focus": by_id[focus_request_id],
        }
    finally:
        runtime.Query.submit_finished_request = original_submit


def compare_pair(low, high):
    a = low["focus"]
    b = high["focus"]
    nodes = sorted(set(a["location"]["compute_residence_s"]) | set(b["location"]["compute_residence_s"]))
    node_rows = []
    for node in nodes:
        av = a["location"]["compute_residence_s"].get(node, 0.0)
        bv = b["location"]["compute_residence_s"].get(node, 0.0)
        node_rows.append({
            "node": node,
            "lower_s": av,
            "higher_s": bv,
            "increase_s": bv - av,
            "increase_fraction_of_total_first_decode_increase": None,
        })
    total_inc = b["first_decode_runtime_s"] - a["first_decode_runtime_s"]
    if abs(total_inc) > 1e-12:
        for row in node_rows:
            row["increase_fraction_of_total_first_decode_increase"] = row["increase_s"] / total_inc
    return {
        "seed": low["seed"],
        "request_id": a["request_id"],
        "lower_intensity": low["intensity"],
        "higher_intensity": high["intensity"],
        "aligned_ttft_increase_s": b["aligned_ttft_s"] - a["aligned_ttft_s"],
        "true_first_token_ttft_increase_s": b["true_first_token_ttft_s"] - a["true_first_token_ttft_s"],
        "first_decode_runtime_increase_s": total_inc,
        "source_wait_increase_s": b["location"]["source_wait_s"] - a["location"]["source_wait_s"],
        "link_time_increase_s": b["location"]["link_time_s"] - a["location"]["link_time_s"],
        "compute_residence_increase_s": b["location"]["compute_residence_total_s"] - a["location"]["compute_residence_total_s"],
        "per_node": node_rows,
    }


def main():
    started = time.perf_counter()
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    focus = {int(k): v for k, v in protocol["focused_requests_from_prior_cache_only_diagnosis"].items()}
    points = []
    for spec in protocol["points"]:
        points.append(run_point(int(spec["seed"]), float(spec["intensity"]), focus[int(spec["seed"])]))

    grouped = defaultdict(list)
    for point in points:
        grouped[point["seed"]].append(point)
    comparisons = []
    for seed, group in sorted(grouped.items()):
        group.sort(key=lambda x: x["intensity"])
        if len(group) != 2:
            raise RuntimeError(f"expected exactly two frozen points for seed {seed}")
        comparisons.append(compare_pair(group[0], group[1]))

    summary = {
        "schema": 1,
        "experiment_id": protocol["experiment_id"],
        "status": "complete",
        "fresh_helix_runs": len(points),
        "points": points,
        "comparisons": comparisons,
        "elapsed_s": time.perf_counter() - started,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    compact = {
        "fresh_helix_runs": len(points),
        "comparisons": comparisons,
        "elapsed_s": summary["elapsed_s"],
    }
    print("HIGH_LOAD_TTFT_STAGE_TRACE " + json.dumps(compact, sort_keys=True, allow_nan=False), flush=True)
    print(f"HIGH_LOAD_TTFT_STAGE_TRACE_OUTPUT {OUTPUT}", flush=True)


if __name__ == "__main__":
    main()
