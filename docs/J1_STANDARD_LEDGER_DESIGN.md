# J1 — Standard TTFT / request-average TPOT ledger design

Status: **experimental until the J1 validation checkpoint passes**.

## 1. Source boundary and design goal

The frozen AICCC mother evaluator defines phase-local residual budgets and the unchanged network chain `residual time -> omega -> delta -> b_req`. It also requires profiling-driven progress to remain separate from accounting-only overhead. J0 froze that evaluator and its event/resource invariants.

J1 changes only the **semantic horizon represented by the SLA ledger**. The target service metrics are:

- standard TTFT: arrival to completion of the first output token;
- request-average TPOT: `(finish - first_output)/(m-1)` when `m>1`;
- a one-output request has no TPOT horizon.

These standard horizons are a J1 design choice. They are not silently attributed to the AICCC equations, whose published residual budgets are Prefill TTFT and per-token Decode TPOT.

## 2. Two-pass accounting, not a new simulator

J1 deliberately avoids a second execution model.

**Pass 1 — frozen trajectory.** Run J0 with `drain=True` and `trace=True`. Profiling alone determines Prefill-to-Decode timing and continuous Decode progress. SLA thresholds, intrinsic overhead, fixed/queue overhead and network commitments cannot alter that trajectory.

**Pass 2 — horizon ledger overlay.** Reconstruct the first-token time analytically inside the corresponding J0 interval. Because J0 Decode progress is linear within an interval of fixed profile, crossing `g=1` is obtained by interpolation. This timestamp is a ledger boundary only; it is not inserted into the J0 event queue and does not change any J0 state transition.

This construction gives a direct parity invariant: J1 must report the exact J0 trajectory hash and final profile time used by its ledger.

## 3. Standard TTFT horizon

For request `r`, let `a_r` be arrival time and `f_r` the reconstructed first-output time on the J0 trajectory. Let `B_r^[0,1]` be the recovered blocking debt integrated over equivalent Decode progress from 0 to 1. J1 defines

`A_r^T = (f_r-a_r) + T_r^{P,intr} + B_r^[0,1] + T_r^{fix} + T_r^{queue}`.

The standard-TTFT residual network budget is

`Delta_r^T = tau_r^T - A_r^T`.

The network horizon contains all prompt activation transfers plus one Decode-token activation transfer. The total horizon demand is passed unchanged into the J0/AICCC path-allocation kernel. A non-positive residual is immediately unsafe.

Charging fixed/queue overhead once avoids double charging the first output interval: that interval belongs to TTFT, not to post-first average TPOT.

## 4. Request-average TPOT horizon

For `m_r>1`, let `l_r` be the J0 finish time and `B_r^[1,m]` the recovered blocking debt integrated over post-first Decode progress. The total allowed post-first time is

`L_r^D = (m_r-1) tau_r^D`.

J1 accounts

`A_r^D = (l_r-f_r) + B_r^[1,m] + (m_r-1)(T_r^{fix}+T_r^{queue})`,

and defines

`Delta_r^D,avg = L_r^D - A_r^D`.

The network horizon contains `(m_r-1)` Decode-token activation transfers. That total demand is mapped through the same AICCC `omega -> delta -> b_req` equations. The diagnostic predicted request-average TPOT is

`(A_r^D + ideal_serialization_r^D)/(m_r-1)`.

For `m_r=1`, no average-TPOT ledger exists and TTFT is the only latency horizon.

## 5. Integrated recovered blocking term

The AICCC manuscript includes a Decode blocking term but does not uniquely define its recurrence. J0 explicitly preserved the recovered `active-prefill-full-service` assumption without promoting it to a theorem.

J1 does not invent a new blocking model. For each J0 interval, the recovered per-token debt is constant under the interval state. If Decode progress advances by `dg`, J1 adds `T_block * dg`. Summing these products yields the first-token and post-first blocking integrals. This is an explicit extension of the recovered assumption and remains a sensitivity target, not a theoretical fact.

## 6. Strict safety and shared links

A request uses its TTFT commitment before the first-output boundary and its average-TPOT commitment after that boundary. Commitments switch atomically at the analytically reconstructed first-token timestamp. Multiple active requests are summed on every physical link exactly as in J0.

The workload is safe iff every checked epoch satisfies:

1. positive residual time for every applicable request horizon;
2. aggregate shared-link commitment no larger than physical capacity;
3. J0 memory usage no larger than device capacity.

There is no 90% attainment target. One violating request or resource is sufficient for an unsafe verdict.

## 7. Validation plan for J1

Deterministic tests must establish first-token reconstruction, exclusion of the first token from average TPOT, `m=1` behavior, J0 trajectory identity, decode-block-size independence of first-token semantics, integrated blocking accounting, strict safety, and shared-link aggregation. A constructed case must demonstrate that request-average TPOT can pass even when a phase-local per-token TPOT check rejects.

The bounded pilot then reuses pinned HELIX raw records only. It compares J1 against standard first-output TTFT and request-average TPOT reconstructed from those executions, with a strict all-request reference rule (`target=1.0`). The pilot reports false acceptance and false rejection explicitly, because false acceptance is the more safety-critical disagreement. It does not launch HELIX, refine capacity, search partitions, stress profiles, or make a manuscript claim.
