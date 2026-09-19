"""J1 request-horizon SLA ledger over the frozen AICCC J0 trajectory.

J1 is not a new execution simulator. J0 remains the only progress engine;
profiling fixes the trajectory. J1 only changes the SLA accounting horizon to
standard first-output TTFT and request-average post-first TPOT, then uses the
unchanged AICCC residual-time -> omega -> delta -> b_req network kernel.
"""
from __future__ import annotations

import math
import time

from aiccc_evaluator import BLOCKING_POLICY, DEFAULT_DECODE_BLOCK_SIZE, evaluate as evaluate_j0
from aiccc_math import EPS, NonPositiveLinkCapacity, path_commitments, residual_network_budget
from research import H, Profiles
from sla_aware_mvp.domain import sorted_workload

VERSION = "AICCC-J1-STANDARD-LEDGER-v1"
LEDGER_POLICY = "j0-profile-trajectory-standard-request-horizons"


def _demand(pipeline, tokens):
    out = {k: 0.0 for k in pipeline.links}
    for boundary in pipeline.boundaries:
        for link_id in boundary.route_link_ids:
            out[link_id] += pipeline.model.activation_bytes_per_token * tokens
    return out


def _ideal_serialization(demand, capacities):
    total = 0.0
    for link_id, size in demand.items():
        if not size:
            continue
        cap = capacities[link_id]
        if cap <= 0:
            return math.inf
        total += size / cap
    return total


def _network_json(commitments):
    return {
        k: {
            "bytes": x.bytes,
            "omega": x.weight,
            "delta_s": x.allocated_time_s,
            "required_bandwidth_bytes_per_s": x.required_bandwidth_bytes_per_s,
            "relative_capacity": x.relative_capacity,
        }
        for k, x in commitments.items()
    }


def evaluate(
    pipeline,
    workload,
    sla,
    prof=None,
    *,
    intrinsic=True,
    trace=False,
    activation_buffers=True,
    blocking_policy=BLOCKING_POLICY,
    blocking_scale=1.0,
    decode_block_size=DEFAULT_DECODE_BLOCK_SIZE,
    max_events=100_000,
):
    """Evaluate strict standard TTFT and request-average TPOT on J0 progress.

    First-output times are analytical ledger boundaries reconstructed from
    continuous J0 Decode progress. They never enter J0's event queue.
    Fixed/queue overhead is charged once to TTFT and once per post-first output
    interval. The recovered active-Prefill blocking debt is integrated over
    equivalent Decode progress; it remains an explicit recovered assumption.
    """
    started = time.perf_counter()
    if blocking_policy not in (None, "none", BLOCKING_POLICY):
        raise ValueError(f"unsupported blocking policy: {blocking_policy}")
    if (
        isinstance(blocking_scale, bool)
        or not isinstance(blocking_scale, (int, float))
        or not math.isfinite(blocking_scale)
        or blocking_scale < 0
    ):
        raise ValueError("blocking_scale must be a finite nonnegative number")
    blocking_scale = float(blocking_scale)
    requests = sorted_workload(workload)
    specs = {r.id: r for r in requests}
    prof = prof or Profiles()

    core = evaluate_j0(
        pipeline,
        requests,
        sla,
        prof,
        intrinsic=intrinsic,
        trace=True,
        drain=True,
        activation_buffers=activation_buffers,
        blocking_policy=blocking_policy,
        decode_block_size=decode_block_size,
        max_events=max_events,
    )
    history = core["trace"]
    capacities = {k: v.capacity_bytes_per_s for k, v in pipeline.links.items()}

    if not requests:
        return {
            "evaluator_version": VERSION,
            "mother_evaluator": "AICCC-accounting-only",
            "ledger_policy": LEDGER_POLICY,
            "blocking_scale": blocking_scale,
            "strict_all_request_safety": True,
            "safe": True,
            "first_violation": None,
            "first_violations": [],
            "decode_block_size": decode_block_size,
            "core_evaluator_version": core["evaluator_version"],
            "core_trajectory_hash": core["trajectory_hash"],
            "core_safe_under_phase_local_sla": core["safe"],
            "final_time_s": core["final_time_s"],
            "peak_network_utilization": 0.0,
            "peak_memory_bytes": core["peak_memory_bytes"],
            "max_standard_ttft_s": 0.0,
            "max_average_tpot_s": 0.0,
            "runtime_s": time.perf_counter() - started,
        }

    prefill_compute, finish = {}, {}
    for snap in history:
        for rid, ledger in snap["ledger"].items():
            if ledger["phase"] == "prefill" and rid not in prefill_compute:
                prefill_compute[rid] = ledger["compute_s"]
        if snap["side"] == "post":
            for event, rid in snap["events"]:
                if event == "Finish":
                    finish[rid] = snap["time_s"]
    if set(prefill_compute) != set(specs) or set(finish) != set(specs):
        raise RuntimeError("incomplete J0 trajectory")

    first = {}
    block_first = {rid: 0.0 for rid in specs}
    block_post = {rid: 0.0 for rid in specs}
    for i, left in enumerate(history[:-1]):
        if left["side"] != "post":
            continue
        right = history[i + 1]
        if right["side"] != "pre":
            raise RuntimeError("unexpected J0 trace ordering")
        t0, t1 = left["time_s"], right["time_s"]
        if blocking_policy in (None, "none"):
            debt = 0.0
        else:
            debt = blocking_scale * sum(
                prefill_compute[rid] + (H * specs[rid].input_tokens if intrinsic else 0.0)
                for rid, ledger in left["ledger"].items()
                if ledger["phase"] == "prefill"
            )
        for rid in set(left["ledger"]) & set(right["ledger"]):
            a, b = left["ledger"][rid], right["ledger"][rid]
            if a["phase"] != "decode" or b["phase"] != "decode":
                continue
            g0, g1 = float(a["progress"]), float(b["progress"])
            if g1 < g0 - EPS:
                raise RuntimeError(f"decode progress regressed for {rid}")
            g1 = max(g0, g1)
            block_first[rid] += debt * max(0.0, min(g1, 1.0) - max(g0, 0.0))
            block_post[rid] += debt * max(0.0, min(g1, specs[rid].output_tokens) - max(g0, 1.0))
            if rid not in first and g0 < 1.0 - EPS <= g1:
                first[rid] = t1 if g1 - g0 <= EPS else t0 + (1.0 - g0) * (t1 - t0) / (g1 - g0)
    if set(first) != set(specs):
        raise RuntimeError("first-token boundary unavailable")

    core_times = sorted({float(x["time_s"]) for x in history})
    for rid, value in list(first.items()):
        nearest = min(core_times, key=lambda t: abs(t - value))
        if abs(nearest - value) <= EPS:
            first[rid] = nearest

    decode_one = {rid: _demand(pipeline, 1.0) for rid in specs}
    horizons, violations = {}, []
    max_ttft = max_tpot = 0.0

    def make_horizon(rid, name, units, start_s, end_s, limit_total, intrinsic_s, blocking_s, demand):
        nonlocal max_ttft, max_tpot
        fixed_s = units * sla.fixed_overhead_s
        queue_s = units * sla.queue_overhead_s
        budget = residual_network_budget(
            limit_total,
            end_s - start_s,
            intrinsic_s=intrinsic_s,
            blocking_s=blocking_s,
            fixed_s=fixed_s,
            queue_s=queue_s,
        )
        serial = _ideal_serialization(demand, capacities)
        commitments = {}
        if budget.network_s <= EPS:
            violations.append({
                "kind": "sla_time", "object": name, "request_id": rid,
                "required": budget.accounted_s / units, "limit": limit_total / units,
                "time_s": start_s, "side": "post",
            })
        elif math.isinf(serial):
            violations.append({
                "kind": "network", "object": "non_positive_capacity", "request_id": rid,
                "required": math.inf, "limit": 0.0, "time_s": start_s, "side": "post",
            })
        else:
            try:
                commitments = path_commitments(demand, capacities, budget.network_s)
            except NonPositiveLinkCapacity:
                violations.append({
                    "kind": "network", "object": "non_positive_capacity", "request_id": rid,
                    "required": math.inf, "limit": 0.0, "time_s": start_s, "side": "post",
                })
        predicted_total = budget.accounted_s + serial
        predicted_metric = predicted_total / units
        if name == "standard_ttft":
            max_ttft = max(max_ttft, predicted_metric)
        else:
            max_tpot = max(max_tpot, predicted_metric)
        return {
            "kind": name,
            "units": units,
            "start_s": start_s,
            "end_s": end_s,
            "limit_total_s": limit_total,
            "profile_elapsed_s": end_s - start_s,
            "intrinsic_s": intrinsic_s,
            "blocking_s": blocking_s,
            "fixed_s": fixed_s,
            "queue_s": queue_s,
            "accounted_s": budget.accounted_s,
            "residual_network_s": budget.network_s,
            "ideal_serialization_s": serial,
            "predicted_total_s": predicted_total,
            "predicted_metric_s": predicted_metric,
            "demand_bytes": demand,
            "commitments": commitments,
        }

    for rid, spec in specs.items():
        prompt = _demand(pipeline, spec.input_tokens)
        ttft_demand = {k: prompt[k] + decode_one[rid][k] for k in prompt}
        horizons[rid, "ttft"] = make_horizon(
            rid, "standard_ttft", 1, spec.arrival_time_s, first[rid], sla.ttft_s,
            H * spec.input_tokens if intrinsic else 0.0, block_first[rid], ttft_demand,
        )
        if spec.output_tokens > 1:
            units = spec.output_tokens - 1
            post_demand = {k: v * units for k, v in decode_one[rid].items()}
            horizons[rid, "tpot"] = make_horizon(
                rid, "average_tpot", units, first[rid], finish[rid], units * sla.tpot_s,
                0.0, block_post[rid], post_demand,
            )

    peak_memory = {n: 0.0 for n in pipeline.nodes}
    for snap in history:
        for node_id, used in snap["memory"].items():
            peak_memory[node_id] = max(peak_memory[node_id], used)
            limit = pipeline.nodes[node_id].memory_capacity_bytes
            if used > limit:
                violations.append({
                    "kind": "memory", "object": node_id, "required": used, "limit": limit,
                    "time_s": snap["time_s"], "side": snap["side"],
                })

    def active_horizon(rid, t, side):
        spec = specs[rid]
        if t < spec.arrival_time_s - EPS or t > finish[rid] + EPS:
            return None
        if abs(t - spec.arrival_time_s) <= EPS and side == "pre":
            return None
        if abs(t - finish[rid]) <= EPS and side == "post":
            return None
        if t < first[rid] - EPS or (abs(t - first[rid]) <= EPS and side == "pre"):
            return horizons[rid, "ttft"]
        return horizons.get((rid, "tpot"))

    network_checks, peak_util = [], 0.0
    for t in sorted(set(core_times) | set(first.values())):
        for side in ("pre", "post"):
            links = {k: 0.0 for k in pipeline.links}
            active = {}
            for rid in specs:
                h = active_horizon(rid, t, side)
                if h is None:
                    continue
                active[rid] = h["kind"]
                for link_id, item in h["commitments"].items():
                    links[link_id] += item.required_bandwidth_bytes_per_s
            local = []
            for link_id, required in links.items():
                cap = capacities[link_id]
                util = required / cap if cap > 0 else (math.inf if required else 0.0)
                peak_util = max(peak_util, util)
                if required > cap + EPS:
                    v = {
                        "kind": "network", "object": link_id, "required": required,
                        "limit": cap, "time_s": t, "side": side,
                    }
                    violations.append(v)
                    local.append(v)
            if trace:
                network_checks.append({
                    "time_s": t, "side": side, "active_horizons": active,
                    "link_commitments": links, "violations": local,
                })

    rank = {"pre": 0, "post": 1}
    violations.sort(key=lambda v: (v["time_s"], rank.get(v["side"], 1), v["kind"], str(v["object"]), str(v.get("request_id", ""))))
    first_set = []
    if violations:
        key = (violations[0]["time_s"], rank.get(violations[0]["side"], 1))
        first_set = [v for v in violations if (v["time_s"], rank.get(v["side"], 1)) == key]

    result = {
        "evaluator_version": VERSION,
        "mother_evaluator": "AICCC-accounting-only",
        "ledger_policy": LEDGER_POLICY,
        "blocking_policy": blocking_policy,
        "blocking_scale": blocking_scale,
        "strict_all_request_safety": True,
        "decode_block_size": decode_block_size,
        "safe": not first_set,
        "first_violation": first_set[0] if first_set else None,
        "first_violations": first_set,
        "all_violation_count": len(violations),
        "core_evaluator_version": core["evaluator_version"],
        "core_trajectory_hash": core["trajectory_hash"],
        "core_safe_under_phase_local_sla": core["safe"],
        "final_time_s": core["final_time_s"],
        "peak_network_utilization": peak_util,
        "peak_memory_bytes": peak_memory,
        "max_standard_ttft_s": max_ttft,
        "max_average_tpot_s": max_tpot,
        "runtime_s": time.perf_counter() - started,
    }
    if trace:
        result.update(
            request_ledgers={
                rid: {
                    key: {
                        **{k: v for k, v in h.items() if k != "commitments"},
                        "network": _network_json(h["commitments"]),
                    }
                    for key in ("ttft", "tpot")
                    if (h := horizons.get((rid, key))) is not None
                }
                for rid in specs
            },
            first_token_time_s=first,
            finish_time_s=finish,
            network_checks=network_checks,
            violations=violations,
        )
    return result
