# Prefill-blocking accounting correction: experimental checkpoint

Date: 2026-09-19

Status: **remaining-Prefill blocking is supported for the next stage; a global TTFT reserve is rejected**

## What was changed

The AICCC/J0 request-progress model is unchanged.

The only accounting change tested here is how much active Prefill work is charged as Decode blocking.

The old recovered rule charges the full profiled Prefill service of every active Prefill request. The new rule charges only the **average remaining fraction** of that known profiled Prefill service during each overlap interval.

The intrinsic overhead term remains fully charged because its temporal placement is unknown.

No candidate change is allowed to move request progress, add network serialization to the progress clock, replace the bandwidth-commitment equations, or weaken strict all-request safety.

## Why this change was tested

Broader validation showed many cases where the evaluator said "unsafe" while HELIX was actually safe, especially because average TPOT was charged too much blocking time.

A separate problem also exists: a small number of high-load slow-link cases are unsafe in HELIX because first-token latency is too high, while the evaluator still says safe.

These two errors have different causes and should not be repaired with one arbitrary scalar.

## Deterministic checks

Self-hosted test run `35417857624` passed:

- frozen AICCC math: 5/5
- frozen AICCC evaluator: 13/13
- standard-ledger and candidate-accounting guards: 14/14

The new accounting options preserve the exact same J0 trajectory hash and final profile-driven completion time.

## Short-workload mechanism screen

The first mechanism screen used two short formal workloads, h103 and h105, across A100 and heterogeneous deployments.

It contained **528 existing HELIX physical conditions**. No new HELIX execution was launched.

| Accounting | Unsafe approvals | Conservative rejections | Agreement |
| --- | ---: | ---: | ---: |
| Full Prefill blocking | 0 | 16 | 96.97% |
| Remaining Prefill blocking | 0 | **11** | **97.92%** |

So the new blocking calculation removed five conservative mistakes without creating a single new unsafe approval.

For the finite sampled maximum-safe-load edge, exact agreement improved from 0/12 comparable sequences to 1/12. This is an improvement, but the capacity boundary is still far from solved.

## Reserved long-workload confirmation

Before screening finished, two longer workloads, h104 and h106, were explicitly reserved and not inspected.

They were then used to confirm the blocking correction on **490 cached physical conditions**.

The existing accounting result on this exact population was:

- unsafe approvals: 0
- conservative rejections: 14
- agreement: 97.14%

The remaining-Prefill blocking result was:

- unsafe approvals: **0**
- conservative rejections: **12**
- agreement: **97.55%**

Again, the new blocking formula reduces conservative rejection without introducing unsafe approval.

The sampled maximum-safe-load edge still matches exactly in 0/6 comparable long-workload sequences. Therefore the blocking correction is useful, but it is not sufficient to solve capacity estimation.

## Back-check on the earlier 677-condition diagnostic set

This set was already used for mechanism diagnosis, so it is not held-out evidence. It is used only to understand whether the correction behaves consistently.

| Accounting | Unsafe approvals | Conservative rejections | Agreement |
| --- | ---: | ---: | ---: |
| Full Prefill blocking | 4 | 69 | 89.22% |
| Remaining Prefill blocking | 4 | **47** | **92.47%** |

This is consistent with the held-out results: the blocking correction attacks the conservative TPOT problem, but it does **not** solve the four high-load TTFT unsafe approvals.

## Why the global 5% TTFT reserve is rejected

A simple idea was to add 5% of the profile-driven TTFT as an extra accounting reserve.

On the earlier 677-condition diagnostic set, combining this reserve with remaining-Prefill blocking changed the result to:

- unsafe approvals: 3
- conservative rejections: **151**
- agreement: 77.25%

So it catches only one of the four unsafe approvals while causing a very large number of new conservative mistakes.

This global reserve is therefore rejected as a general fix.

## Research decision

The current evidence supports keeping the **remaining-Prefill blocking formula** as the blocking-accounting candidate for the next stage.

It does not justify changing the AICCC mother model.

The remaining unresolved safety problem is separate:

> At high request load, especially on slow links, the evaluator can still underestimate first-token latency and approve a workload that HELIX shows is unsafe.

The next mechanism should target that high-load TTFT optimism specifically. It should not globally inflate every profile or SLA budget, because that destroys usable safe capacity.

Any new safety guard should remain accounting-only and should be frozen before its own held-out validation.

Machine-readable checkpoint: `results/accounting_correction_checkpoint.json`.
