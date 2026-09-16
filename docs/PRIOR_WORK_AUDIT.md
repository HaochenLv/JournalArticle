# Prior work audit

Audit date: 2026-09-17. The two supplied accepted conference manuscripts (10 and 6 pages, including appendices/references) and the review form were read in full. Originals and extracted text remain outside this public repository. This document paraphrases the scientific issues; it does not reproduce the private review.

## Paper 1: An SLA-Safe Capacity Evaluator for Layer-Level LLM Pipelines

Already contributed, and not available as new journal contributions:

- Scheduler-free event-driven evaluation of a fixed contiguous pipeline and finite workload; arrival, atomic Prefill completion, continuous equivalent-token Decode progression with block updates, completion.
- Evaluator-induced sampled SLA-safe capacity. Intensity compresses arrival gaps without changing requests or token lengths. It is not a stationary maximum throughput or a queue-stability limit.
- TTFT/TPOT residual budgets, proportional network service commitments, aggregate physical-link checks, and static/dynamic memory checks.
- Progress/accounting separation: overhead without a modeled temporal location tightens the latency ledger without moving progress events.
- The isolated 2051-token counterexample, independently calibrated intrinsic Prefill charge, accounting-only correction, trajectory fingerprints, historical regression, capacity sweep, and runtime comparison.

Exact interpretation of central numbers:

| Reported result | What it actually means | What it does not establish |
|---|---|---|
| 2051 tokens | One held-out long prompt on the slow/interleaved 8-stage A100 pipeline; baseline predicts 1.894040 s, corrected ledger 2.015823 s, aligned reference 2.015105 s against 2 s TTFT | General accuracy over arbitrary prompt distributions |
| 0/136 | No **new** rejection by accounting-only correction among 136 archived workload–placement configurations safe under both baseline and reference | Zero false acceptance probability, or zero total conservative disagreement |
| 17/136 | Trajectory-coupled correction rejects 17 previously both-safe configurations; 12.5%; deduplicated 16/116 | 17 individual requests or independent statistical draws |
| 140 historical cases | 136 previously both-safe; 4 already baseline-unsafe/reference-safe | A balanced safety classification benchmark |
| 12 configurations | Six seeds × two placements; 24 evaluator-variant sequences preserve the same sampled edge | Evaluator/reference capacity equality |
| 12 nearest evaluator-unsafe probes | All also reference-safe | The reference boundary has been located |
| about 488× | Same-host wall-clock ratio for one 17-request workload, seed 7, lambda 0.0131; 30 evaluator and 10 reference repetitions after warm-up; medians 16.482/16.427 ms vs 8.034/8.028 s | GPU execution speedup, serving throughput improvement, or universal evaluator speedup |

Frozen paper setup: 80 layers, eight A100 40 GB stages, 10 layers per stage; 1.25 GB/s sequential and 312.5 MB/s interleaved links; 2 s TTFT, 150 ms TPOT, 5 ms fixed overhead, 59.3772 microseconds/input-token intrinsic charge, 16-token Decode blocks. Six 30 s source windows use seeds 0,1,2,3,7,19; seeds change sampled paired lengths, not arrival times. Capacity grid 0.006–0.022 in 0.0001 increments.

The paper appropriately distinguishes finite sampled monotonicity from a continuous-domain theorem. It does not establish a distributional reliability bound. Its final source snapshot/40-test suite is not in the fetched public branches; the recovered implementation and what was verified are documented separately.

## Paper 2: Evaluator-Guided SLA-Aware Layer Partitioning for Heterogeneous LLM Pipelines

Already contributed:

- Using evaluator-induced capacity as the partition score under fixed stage order.
- Phase-specific heterogeneity and the chain from layer allocation through compute and residual SLA budget to network commitment.
- Alternating L4x2/T4x4 stage groups, normalized Prefill/Decode speeds approximately (0.294,0.378)/(0.253,0.600).
- One-dimensional shift family p(s) = [10+s,10-s] repeated four times, radii 2/3/4 (5/7/9 candidates).
- Four-probe local search (initial -1,0,+1; extend in the better non-decreasing direction), and stride-two coarse-to-fine search with local refinement. Ties favor smaller absolute shift, then negative shift.
- Six-seed compact-family study, 20-seed family scaling, and 0.5/1/2× link sensitivity.

The oracle is **exhaustive scoring with the same evaluator within the tested shift family**. It is neither a reference simulator oracle nor a global partition optimum. The nine-shift coarse-to-fine result is 20/20 exact Decode, 16/20 exact and 19/20 near-oracle Prefill; mean ratios 1.000 and 0.996. The 33.3%/26.8% reductions count underlying evaluator calls, not only candidate probes. Near-oracle means ratio >=0.98. Link sensitivity uses six seeds × two SLAs × three bandwidths, 36 trials.

The 42.4%/16.5% seed-7 gains in the controlled phase-preference figure are a different workload experiment from the 120 s Azure-derived validation. The reproduced 120 s seed-7 trial has Decode ties at shifts -2,-1,0 and a Prefill best at -1; those are not contradictory results.

The absolute compute functions in the public implementation remain analytical, scaled by median ratios of HELIX profile samples. The paper's phrase “HELIX phase profiles” must not be expanded into a claim that its evaluator directly replays absolute HELIX compute times. Constant 2 MB traffic, context/interference coefficients, and block-event behavior also differ from paper 1. See CODE_REUSE_AUDIT.

## Review-derived research questions (paraphrased)

The review requests clearer denominators/ground-truth criteria and attention to inaccurate profiling and unsafe approvals, rather than only counting newly introduced rejections. These are motivations, not evidence that profiling noise is the dominant practical failure. A suitable journal study should report both directions of disagreement, original per-request metrics, inputs, and the tested reference's limitations.

## Unproved questions available to the journal

1. Where are the reference's own safe and unsafe regions beyond the evaluator's edge? Are they monotonic under finite-trace arrival scaling?
2. Do controlled evaluator-only profile biases change safety decisions after accounting for nominal model mismatch?
3. Does evaluator capacity ranking transfer to reference ranking on matched inputs?
4. Can a small, explicitly counted reference-call budget recover validated operating points and improve candidate selection over simple budget-matched baselines?

Merely adding 5–20% noise, repeating the accounting-only correction, extending to more shifts, or rebranding the coarse-to-fine search is not sufficient new contribution.
