# J2 — Broader reference validation, profile-error stress, and blocking-term sensitivity

Date: 2026-09-19 (Asia/Shanghai)

Status: **RELIABILITY_RISK_CHARACTERIZED; no final model change selected**

## 1. Modeling direction is unchanged

J2 preserves the frozen AICCC/J0 research object:

```text
profile-driven request progress
    -> J1 standard TTFT / request-average TPOT ledger
    -> residual network time
    -> omega
    -> per-link time allocation
    -> required bandwidth commitment
    -> shared-link / memory / SLA feasibility
```

J2 does not introduce a virtual-round simulator, does not insert network serialization into the progress clock, and does not use a 90% workload-attainment classifier. Workload safety remains strict: one applicable request/resource violation is unsafe.

The J0 core files and contract remain byte-identical to the J0 freeze checkpoint. J1 gained one diagnostic-only parameter, `blocking_scale`, whose default is 1.0 and whose value affects only the recovered blocking accounting charge. Deterministic run `35416897937` passed J0 math 5/5, J0 evaluator 13/13, and J1 standard-ledger guards 11/11. The scale-0/scale-1 test confirms that changing this parameter does not change the underlying J0 trajectory hash or final profile time.

## 2. Why J2 was run

The bounded J1 pilot had 42/42 agreement, but that grid was intentionally small. J2 therefore asked two reliability questions before any larger capacity or partition claim:

1. Does nominal J1 remain safe against a much broader set of existing pinned HELIX executions?
2. What happens when the profiling measurements that drive request progress are systematically wrong?

A third mechanism diagnostic was added after the broader nominal run showed that most false rejections were average-TPOT SLA-time failures. Because the recovered Decode-blocking recurrence is explicitly not a theorem, J2 varied only the weight of that accounting term while leaving progress and network equations unchanged.

## 3. Broader cache-only reference population

Run `35416485936` reuses only existing pinned HELIX raw-reference records. It performs no HELIX execution and no new workload generation.

The population is the union of two pre-existing diagnostic families:

| Source family | Pairs | Role |
| --- | ---: | --- |
| `nominal_gap` | 175 | A100 / slow-fast nominal-gap cases |
| `partition_ranking` | 502 | heterogeneous five-shift cases |
| **Total** | **677** | 30 case families |

The standard execution reference reconstructs first-output TTFT and request-average post-first TPOT, reapplies the record's explicit fixed/queue overhead, and uses an all-request pass rule. The 677 points contain 366 reference-safe and 311 reference-unsafe cases.

The raw-reference inventory fingerprint is unchanged before and after the experiment. New HELIX runs: **0**.

## 4. Nominal J1 result

| Outcome | Count |
| --- | ---: |
| safe / safe | 297 |
| false acceptance | **4** |
| false rejection | **69** |
| unsafe / unsafe | 307 |
| agreement | **89.22%** |

Conditional error rates:

- false acceptance among reference-unsafe points: **4/311 = 1.29%**
- false rejection among reference-safe points: **69/366 = 18.85%**

The source split is important:

| Source | Pairs | False acceptance | False rejection | Agreement |
| --- | ---: | ---: | ---: | ---: |
| A100 `nominal_gap` | 175 | 4 | 12 | 90.86% |
| heterogeneous `partition_ranking` | 502 | 0 | 57 | 88.65% |

The four nominal false acceptances are all high-intensity A100 slow-placement TTFT misses:

| Case | Intensity | TTFT limit | Reference max TTFT | Violating requests |
| --- | ---: | ---: | ---: | ---: |
| seed 0, slow, prefill regime | 1.28 | 2.0 s | 2.2943 s | 1/17 |
| seed 0, slow, TTFT regime | 1.28 | 1.8 s | 2.2943 s | 1/17 |
| seed 7, slow, prefill regime | 0.64 | 2.0 s | 2.3547 s | 1/17 |
| seed 7, slow, TTFT regime | 0.64 | 1.8 s | 2.3547 s | 2/17 |

Their mean maximum normalized SLA excess is 22.68%; the worst is **30.82%**. Thus false acceptance is not merely a threshold-tie artifact.

The 69 false rejections are mostly a different mechanism: 62/69 are average-TPOT SLA-time rejections, and 50 of those occur in the heterogeneous family. This identifies a conservative bias in the recovered blocking-accounting path rather than in the standard-TTFT extension itself.

## 5. Sampled capacity signal

The 30 source case families are also treated as sampled-intensity sequences. The reference is monotone on all observed sequences; nominal J1 is also monotone on all 30.

Of the 28 cases where both sides have a finite sampled safe/unsafe edge, only **3/28** have the exact same edge under nominal J1.

This is a critical result: good pointwise agreement is not sufficient for an accurate capacity edge. Conservative false rejections can move the sampled safe boundary substantially even when false acceptance is rare.

No continuous-domain capacity claim is made; these are finite-grid observations only.

## 6. Profile-error stress

The evaluator profile is perturbed while the execution reference remains fixed. This is a deterministic sensitivity grid, not a probability distribution.

### 6.1 Underestimating compute time

A scale below 1 means that J1 believes compute is faster than the nominal execution profile. This is the safety-critical direction.

Selected results:

| Variant | False acceptance | False rejection | Agreement |
| --- | ---: | ---: | ---: |
| nominal | 4 | 69 | 89.22% |
| Prefill ×0.95 | 20 | 63 | 87.74% |
| Decode ×0.95 | 15 | 64 | 88.33% |
| Both ×0.95 | 20 | 55 | 88.92% |
| Both ×0.90 | 21 | 42 | 90.69% |
| Both ×0.80 | 22 | 34 | 91.73% |

The apparent increase in overall agreement at large underestimation is not a safety improvement. It occurs because conservative rejections disappear while unsafe approvals increase. Under both-phase 20% underestimation, false acceptance rises from 4 to 22.

A heterogeneous device-specific 10% underestimation also creates false acceptance where nominal J1 had none in that family:

- L4×2 ×0.90: 5 false acceptances / 502 pairs
- T4×4 ×0.90: 5 false acceptances / 502 pairs

### 6.2 Overestimating compute time

Profile inflation reduces optimism only modestly while increasing conservatism sharply:

| Variant | False acceptance | False rejection | Agreement |
| --- | ---: | ---: | ---: |
| Both ×1.05 | 3 | 168 | 74.74% |
| Both ×1.10 | 3 | 175 | 73.71% |
| Both ×1.20 | 2 | 229 | 65.88% |

For the heterogeneous family, +10% device-specific inflation removes observed false acceptance but produces 143–144 false rejections out of 502.

Therefore a simple global "inflate every profile" rule is not an acceptable journal fix: it trades a small reduction in unsafe approvals for a very large loss in usable safe capacity.

## 7. Recovered blocking-term sensitivity

Run `35416969225` varies only the multiplier on the recovered accounting-only Decode blocking charge. No multiplier is selected or calibrated from these data.

| Blocking scale | False acceptance | False rejection | Agreement | Exact finite edges |
| ---: | ---: | ---: | ---: | ---: |
| 0.00 | 206 | 0 | 69.57% | 0 |
| 0.25 | 21 | 23 | 93.50% | 3 |
| 0.50 | 7 | 44 | 92.47% | 4 |
| 0.75 | 4 | 53 | 91.58% | 5 |
| 1.00 | 4 | 69 | 89.22% | 3 |

Two conclusions are robust:

1. The recovered full-service blocking term is a major source of conservative average-TPOT rejections.
2. The blocking term cannot simply be removed: scale 0 creates 206 false acceptances and a worst observed false-acceptance normalized SLA excess of 176.5%.

Scale 0.75 happens to retain the same four nominal false acceptances while reducing false rejections from 69 to 53, but choosing 0.75 from this dataset would be post-hoc tuning without a physical derivation. It is therefore **not adopted**.

Scale 0.25 also creates six nonmonotone evaluator case sequences, another reason not to optimize a scalar weight for aggregate agreement.

## 8. Mechanism diagnosis

J2 exposes two distinct reliability modes.

### A. Safety-critical TTFT optimism

The four nominal false acceptances are high-intensity slow-placement cases where HELIX first-output latency rises far above the J1 profile trajectory. They persist when the blocking weight is reduced or left at the default, so they are not caused by the recovered blocking term.

This is the mechanism that profile-noise experiments make worse: optimistic profiles reduce modeled elapsed time and leave too much residual network budget.

### B. Capacity-limiting TPOT conservatism

Most nominal false rejections are average-TPOT SLA-time failures. Their count falls as the recovered blocking charge is reduced, showing that the current full-service recurrence is over-conservative for many request-average horizons.

The two modes require different treatment. A single scalar profile margin or blocking multiplier cannot solve both without an unacceptable safety/capacity trade-off.

## 9. Research decision after J2

The main model is **not changed**.

The next journal step should preserve J0/J1 and study two bounded additions:

1. a physically motivated replacement for the recovered blocking-accounting recurrence, still accounting-only and still unable to change the profiling-driven trajectory;
2. a safety guard for high-intensity/profile-uncertain cases, evaluated explicitly by false acceptance and capacity loss rather than by overall agreement.

Any candidate mechanism must be frozen before its held-out evaluation. The J2 datasets may be used for mechanism diagnosis, but not as the sole evidence for selecting and claiming a final correction.

No new HELIX run, formal partition search, or manuscript claim is authorized by this checkpoint.

Machine-readable checkpoint: `results/j2/j2_checkpoint_summary.json`.
Protocols: `config/j2_reference_profile_protocol_v1.json` and `config/j2_blocking_sensitivity_v1.json`.
