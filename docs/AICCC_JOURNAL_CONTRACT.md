# AICCC journal evaluator contract

## 1. Non-negotiable research object

The Future Internet journal work inherits the **AICCC mathematical evaluator** as its only mother evaluator. The journal may extend SLA semantics and validation, but it may not replace the evaluator with a different execution model.

The defining chain is:

\`\`\`text
profiled request state
    -> SLA time ledger
    -> residual network time
    -> per-link time allocation
    -> per-link bandwidth commitment
    -> network / memory / SLA feasibility
\`\`\`

This is the research object. A model that instead advances requests using compute + network serialization and then applies a post-hoc pass-rate classifier is a different evaluator type.

## 2. Progress/accounting separation

Request progress is profiling-driven.

- Prefill-to-Decode timing uses the profiled Prefill compute time.
- Decode progress uses the profiled per-token Decode compute time.
- Intrinsic Prefill overhead, fixed overhead, and any other cost whose temporal placement is not explicitly modeled are **ledger charges only**.
- Changing an SLA threshold or an accounting-only charge must not change the profiling-driven trajectory.

This preserves the central AICCC accounting-only principle.

## 3. Residual network budget

For the active phase of request r, the evaluator first forms a residual network-time budget.

Prefill:

\[
\Delta_r^P =
\tau_r^T
- T_r^P
- T_r^{P,\mathrm{intr}}
- T_r^{\mathrm{fix}}
- T_r^{\mathrm{other,acct}}.
\]

Decode:

\[
\Delta_r^D =
\tau_r^D
- T_r^D
- T_r^{\mathrm{block}}
- T_r^{\mathrm{fix}}
- T_r^{\mathrm{other,acct}}.
\]

The current code keeps the existing \`queue_overhead_s\` field only as an explicit accounting-only compatibility term. It is not allowed to alter progress.

A non-positive residual budget is immediately unsafe.

## 4. Residual time -> link commitments

For request r traversing physical path H_r, with S_e,r bytes on link e and physical capacity B_e:

\[
\omega_{e,r}
=
\frac{S_{e,r}/B_e}
{\sum_{j\in H_r} S_{j,r}/B_j},
\]

\[
\delta_{e,r}
=
\omega_{e,r}\Delta_r,
\]

\[
b_{e,r}^{\mathrm{req}}
=
\frac{S_{e,r}}{\delta_{e,r}}.
\]

Therefore

\[
\frac{b_{e,r}^{\mathrm{req}}}{B_e}
=
\frac{\sum_j S_{j,r}/B_j}{\Delta_r},
\]

so one request consumes the same **relative link capacity** on every traversed link under this deterministic accounting rule.

For every physical link:

\[
\sum_{r\in A_e(t)}
b_{e,r}^{\mathrm{req}}(t)
\le B_e.
\]

The implementation must preserve the actual physical path and aggregate multiple request commitments on shared links.

## 5. Strict safety semantics

A finite workload is safe only if every checked epoch satisfies all three classes of constraints:

1. every active request has a positive residual SLA/network budget;
2. every physical link has aggregate commitment no larger than its capacity;
3. every node remains within its memory capacity.

Any violation makes the workload unsafe. There is **no 90% pass-rate rule** in the mother evaluator.

The capacity wrapper may sample workload intensity, check sampled monotonicity, report the largest safe probe, and preserve censoring. Those are wrappers around the evaluator; they do not redefine workload safety.

## 6. Event semantics retained from AICCC

The evaluator remains event-driven and scheduler-free.

- Arrival
- Prefill -> Decode transition
- Decode block update
- Finish

Decode progress remains continuous between events, while block boundaries only determine when profile/resource state is recomputed. Tied events are processed atomically and pre/post checks may retain simultaneous first violations.

## 7. Recovered assumption that is not promoted to a theorem

The available AICCC text contains a Decode blocking term T_block, but it does not uniquely define its recurrence. The existing recovered JB1 code charges the full service of active Prefill requests as Decode blocking debt. The rebuild preserves that behavior behind the explicit policy name:

\`active-prefill-full-service-recovered-assumption\`.

It must remain labeled as a recovered implementation assumption until source evidence establishes a unique rule. Journal experiments may test or replace this **accounting term**, but may not use that as permission to replace the evaluator type.

## 8. Journal semantic-extension boundary

Allowed journal extensions include:

- extending the ledger horizon to a more standard TTFT definition;
- extending Decode accounting to request-average post-first TPOT;
- adding profile-noise sensitivity, confusion matrices, false-acceptance analysis, and reference validation;
- adding explicitly documented accounting terms.

Every such extension must still end in:

\[
\text{residual SLA time}
\rightarrow
\text{per-link time}
\rightarrow
\text{per-link bandwidth commitment}.
\]

Not allowed:

- virtual-round execution as the primary evaluator;
- adding network serialization to the progress clock and then calling that AICCC;
- \`simulate -> 90% classify\` as workload safety;
- silently letting accounting-only overhead change overlap or event timing.

## 9. Current rebuild stage

This branch first rebuilds and tests the AICCC mother evaluator. It does **not** yet activate a new standard-TTFT / average-TPOT journal ledger. That semantic extension is the next layer and must be tested against this frozen core rather than replacing it.

Historical \`JB-Avg-v1\` / Stage 6B code and results stay in the repository for provenance only.
