"""AICCC-mother evaluator for the Future Internet journal extension.

The evaluator type is intentionally fixed:
- profiling drives request progress and event timing;
- SLA accounting converts the remaining phase budget into per-link bandwidth
  commitments;
- network and memory are feasibility constraints;
- any first violation makes the workload unsafe.

This module must not become a post-hoc attainment classifier or a virtual-round
execution simulator. Journal work may extend SLA semantics through an explicit
ledger policy, but it must preserve the same evaluator type.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import time

from aiccc_math import (
    EPS,
    NonPositiveLinkCapacity,
    path_commitments,
    residual_network_budget,
)
from research import H, Profiles, fingerprint
from sla_aware_mvp.domain import sorted_workload

VERSION = "AICCC-JOURNAL-BASE-v1.1"
BLOCKING_POLICY = "active-prefill-full-service-recovered-assumption"
DEFAULT_DECODE_BLOCK_SIZE = 16


@dataclass
class State:
    spec: object
    phase: str = "prefill"
    progress: float = 0.0
    block: int = 0
    prefill_compute: float = 0.0
    prefill_end: float = 0.0
    decode_compute: float = 0.0


def evaluate(
    pipeline,
    workload,
    sla,
    prof=None,
    *,
    intrinsic=True,
    trace=False,
    drain=False,
    precheck=True,
    activation_buffers=True,
    blocking_policy=BLOCKING_POLICY,
    decode_block_size=DEFAULT_DECODE_BLOCK_SIZE,
    max_events=100_000,
):
    """Evaluate one finite workload using the AICCC accounting model.

    No SLA-derived quantity is allowed to alter request progress. Prefill
    progress uses only the profiled Prefill compute time. Decode progress uses
    only the profiled per-token Decode compute time. Intrinsic/fixed/queue and
    recovered blocking charges tighten the ledger only.

    drain=True is diagnostic: evaluation continues after the first violation
    so trajectories can be compared, but safe is still set by first violation.

    decode_block_size controls only Decode profile/resource recomputation
    granularity. The compatibility default is 16; it is not a mathematical
    constant of the evaluator.
    """
    started = time.perf_counter()
    pipeline.validate()
    requests = sorted_workload(workload)
    prof = prof or Profiles()
    if (
        isinstance(decode_block_size, bool)
        or not isinstance(decode_block_size, int)
        or decode_block_size <= 0
    ):
        raise ValueError("decode_block_size must be a positive integer")

    active = {}
    index = 0
    t = requests[0].arrival_time_s if requests else 0.0
    epoch = 0
    first = []
    history = []
    trajectory = []

    peak_p = 0
    peak_d = 0
    peak_memory = {n: 0.0 for n in pipeline.nodes}
    peak_util = 0.0
    max_ttft = 0.0
    max_tpot = 0.0

    layers = pipeline.layers_by_node()
    stages = {
        n: sum(stage.node_id == n for stage in pipeline.stages)
        for n in pipeline.nodes
    }
    static = {
        n: (
            pipeline.model.weight_bytes * layers[n] / pipeline.model.num_layers
            + (
                node.workspace_bytes + node.memory_margin_bytes
                if layers[n]
                else 0
            )
        )
        for n, node in pipeline.nodes.items()
    }

    demands = {}
    for request in requests:
        for phase, tokens in (("prefill", request.input_tokens), ("decode", 1)):
            by_link = {link_id: 0.0 for link_id in pipeline.links}
            for boundary in pipeline.boundaries:
                for link_id in boundary.route_link_ids:
                    by_link[link_id] += pipeline.model.activation_bytes_per_token * tokens
            demands[request.id, phase] = by_link

    capacities = {
        link_id: link.capacity_bytes_per_s
        for link_id, link in pipeline.links.items()
    }

    def counts():
        return (
            sum(x.phase == "prefill" for x in active.values()),
            sum(x.phase == "decode" for x in active.values()),
        )

    def context(x):
        if x.phase != "decode":
            return x.spec.input_tokens
        return x.spec.input_tokens + min(
            (x.block + 1) * decode_block_size,
            x.spec.output_tokens,
        )

    def blocking_debt():
        if blocking_policy in (None, "none"):
            return 0.0
        if blocking_policy != BLOCKING_POLICY:
            raise ValueError(f"unsupported blocking policy: {blocking_policy}")
        # The available AICCC text contains T_block but does not uniquely
        # specify a recurrence. Preserve the recovered JB1 assumption
        # explicitly rather than silently treating it as a theorem.
        return sum(
            x.prefill_compute + (H * x.spec.input_tokens if intrinsic else 0.0)
            for x in active.values()
            if x.phase == "prefill"
        )

    def check(side, events):
        nonlocal peak_p, peak_d, peak_util, max_ttft, max_tpot

        np, nd = counts()
        peak_p = max(peak_p, np)
        peak_d = max(peak_d, nd)
        debt = blocking_debt()

        links = {link_id: 0.0 for link_id in pipeline.links}
        memory = dict(static)
        violations = []
        ledgers = {}

        for rid, x in sorted(active.items()):
            if x.phase == "prefill":
                compute = x.prefill_compute
                intrinsic_s = H * x.spec.input_tokens if intrinsic else 0.0
                blocking_s = 0.0
                limit = sla.ttft_s
            else:
                compute = prof.decode_time_per_token(
                    x.spec,
                    context(x),
                    pipeline,
                    np,
                    nd,
                )
                intrinsic_s = 0.0
                blocking_s = debt
                limit = sla.tpot_s

            budget = residual_network_budget(
                limit,
                compute,
                intrinsic_s=intrinsic_s,
                blocking_s=blocking_s,
                fixed_s=sla.fixed_overhead_s,
                queue_s=sla.queue_overhead_s,
            )
            residual = budget.network_s
            demand = demands[rid, x.phase]
            serialization = 0.0
            for link_id, size in demand.items():
                if size == 0:
                    continue
                capacity = capacities[link_id]
                serialization += size / capacity if capacity > 0 else math.inf

            predicted = budget.accounted_s + serialization
            if x.phase == "prefill":
                max_ttft = max(max_ttft, predicted)
            else:
                max_tpot = max(max_tpot, predicted)

            request_commitments = {}
            if residual <= EPS:
                violations.append(
                    {
                        "kind": "sla_time",
                        "object": x.phase,
                        "request_id": rid,
                        "required": budget.accounted_s,
                        "limit": limit,
                    }
                )
            elif any(
                size > 0 and capacities[link_id] <= 0
                for link_id, size in demand.items()
            ):
                violations.append(
                    {
                        "kind": "network",
                        "object": "non_positive_capacity",
                        "request_id": rid,
                        "required": math.inf,
                        "limit": 0.0,
                    }
                )
            else:
                try:
                    request_commitments = path_commitments(
                        demand,
                        capacities,
                        residual,
                    )
                except NonPositiveLinkCapacity:
                    violations.append(
                        {
                            "kind": "network",
                            "object": "non_positive_capacity",
                            "request_id": rid,
                            "required": math.inf,
                            "limit": 0.0,
                        }
                    )
                else:
                    for link_id, item in request_commitments.items():
                        links[link_id] += item.required_bandwidth_bytes_per_s

            for node_id in memory:
                memory[node_id] += (
                    pipeline.model.kv_bytes_per_token_per_layer
                    * context(x)
                    * layers[node_id]
                )
                if activation_buffers:
                    memory[node_id] += (
                        stages[node_id]
                        * pipeline.model.activation_bytes_per_token
                        * (x.spec.input_tokens if x.phase == "prefill" else 1)
                    )

            ledgers[rid] = {
                "phase": x.phase,
                "limit_s": limit,
                "compute_s": compute,
                "intrinsic_s": intrinsic_s,
                "blocking_s": blocking_s,
                "fixed_s": sla.fixed_overhead_s,
                "queue_s": sla.queue_overhead_s,
                "accounted_s": budget.accounted_s,
                "residual_network_s": residual,
                "serialization_s": serialization,
                "context": context(x),
                "progress": x.progress,
                "block": x.block,
                "network": {
                    link_id: {
                        "bytes": item.bytes,
                        "omega": item.weight,
                        "delta_s": item.allocated_time_s,
                        "required_bandwidth_bytes_per_s": item.required_bandwidth_bytes_per_s,
                        "relative_capacity": item.relative_capacity,
                    }
                    for link_id, item in request_commitments.items()
                },
            }

        for link_id, required in links.items():
            capacity = capacities[link_id]
            utilization = (
                required / capacity
                if capacity > 0
                else (math.inf if required else 0.0)
            )
            peak_util = max(peak_util, utilization)
            if required > capacity + EPS:
                violations.append(
                    {
                        "kind": "network",
                        "object": link_id,
                        "required": required,
                        "limit": capacity,
                    }
                )

        for node_id, used in memory.items():
            peak_memory[node_id] = max(peak_memory[node_id], used)
            limit = pipeline.nodes[node_id].memory_capacity_bytes
            if used > limit:
                violations.append(
                    {
                        "kind": "memory",
                        "object": node_id,
                        "required": used,
                        "limit": limit,
                    }
                )

        for violation in violations:
            violation.update(
                time_s=t,
                side=side,
                num_prefill=np,
                num_decode=nd,
            )

        if trace:
            history.append(
                {
                    "time_s": t,
                    "side": side,
                    "events": events,
                    "num_prefill": np,
                    "num_decode": nd,
                    "ledger": ledgers,
                    "link_commitments": links,
                    "memory": memory,
                    "violations": violations,
                }
            )
        return violations

    def finish():
        return {
            "evaluator_version": VERSION,
            "mother_evaluator": "AICCC-accounting-only",
            "blocking_policy": blocking_policy,
            "strict_all_request_safety": True,
            "decode_block_size": decode_block_size,
            "safe": not first,
            "first_violation": first[0] if first else None,
            "first_violations": first,
            "events": epoch,
            "drained": index == len(requests) and not active,
            "final_time_s": t,
            "peak_prefill": peak_p,
            "peak_decode": peak_d,
            "peak_network_utilization": peak_util,
            "peak_memory_bytes": peak_memory,
            "max_accounted_ttft_s": max_ttft,
            "max_accounted_tpot_s": max_tpot,
            "trajectory_hash": fingerprint(trajectory) if trace or drain else None,
            "runtime_s": time.perf_counter() - started,
            **({"trace": history, "trajectory": trajectory} if trace else {}),
        }

    while index < len(requests) or active:
        if epoch >= max_events:
            raise RuntimeError("AICCC evaluator event limit exceeded")

        np, nd = counts()
        candidates = []
        due = {}

        if index < len(requests):
            candidates.append(requests[index].arrival_time_s)

        for rid, x in active.items():
            if x.phase == "prefill":
                candidates.append(x.prefill_end)
                continue

            x.decode_compute = prof.decode_time_per_token(
                x.spec,
                context(x),
                pipeline,
                np,
                nd,
            )
            if x.decode_compute <= 0:
                raise ValueError("positive profiled Decode compute required")

            target = min((x.block + 1) * decode_block_size, x.spec.output_tokens)
            when = t + (target - x.progress) * x.decode_compute
            due[rid] = (when, target)
            candidates.append(when)

        nt = min(candidates)
        if nt < t - EPS:
            raise RuntimeError("backwards event")

        for x in active.values():
            if x.phase == "decode":
                x.progress = min(
                    x.spec.output_tokens,
                    x.progress + max(0.0, nt - t) / x.decode_compute,
                )

        t = nt
        epoch += 1
        events = []

        if precheck:
            violations = check("pre", events)
            if violations and not first:
                first = violations
            if first and not drain:
                return finish()

        for rid, (when, target) in due.items():
            if abs(when - t) <= EPS:
                x = active[rid]
                x.progress = float(target)
                if target == x.spec.output_tokens:
                    events.append(("Finish", rid))
                    del active[rid]
                else:
                    x.block = target // decode_block_size
                    events.append(("DecodeBlockUpdate", rid))

        for rid, x in active.items():
            if x.phase == "prefill" and x.prefill_end <= t + EPS:
                x.phase = "decode"
                events.append(("PrefillToDecode", rid))

        arrivals = []
        while index < len(requests) and requests[index].arrival_time_s <= t + EPS:
            request = requests[index]
            active[request.id] = State(request)
            arrivals.append(request)
            events.append(("Arrival", request.id))
            index += 1

        np, nd = counts()
        for request in arrivals:
            x = active[request.id]
            x.prefill_compute = prof.prefill_time(
                request,
                pipeline,
                np,
                nd,
            )
            if x.prefill_compute <= 0:
                raise ValueError("positive profiled Prefill compute required")
            # Critical invariant: accounting charges do NOT move this event.
            x.prefill_end = t + x.prefill_compute

        if trace or drain:
            trajectory.append(
                {
                    "time_s": t,
                    "events": sorted(events),
                    "active": {
                        rid: {
                            "phase": x.phase,
                            "progress": x.progress,
                            "block": x.block,
                            "context": context(x),
                        }
                        for rid, x in sorted(active.items())
                    },
                    "num_prefill": np,
                    "num_decode": nd,
                }
            )

        violations = check("post", events)
        if violations and not first:
            first = violations
        if first and not drain:
            return finish()

    return finish()
