# Claim boundary

| Supported wording | Unsupported wording |
|---|---|
| Under the pinned HELIX reference simulator and tested configurations | Real deployment guarantee |
| No optimistic disagreement was observed in a specified tested set | False acceptance probability is zero |
| Optimistic disagreement: evaluator SAFE, reference UNSAFE | Population false-acceptance probability from a deterministic stress grid |
| Conservative disagreement: evaluator UNSAFE, reference SAFE | Every rejected point is physically safe |
| Reference-best candidate within the tested family and load grid | Globally optimal partition |
| Controlled 10% evaluator profile underestimation | Real GPUs exhibit 10% profiling noise |
| Largest observed reference-safe intensity; retain all sampled verdicts | Exact continuous capacity or stability limit |
| A sampled transition bracket when observed monotonicity permits it | Every lower intensity is safe without checking it |
| A directly reference-validated operating point | A deployment-wide safety certificate |
| Simulator wall-clock planning savings on this host | GPU throughput acceleration |
| Journal method is a candidate until budget-matched held-out comparisons pass | Proven journal-level novelty or guaranteed acceptance |

Nominal model mismatch and controlled profile mismatch must be reported separately. Use all reference-unsafe and reference-safe points, not only evaluator-safe probes. Report tested denominators and selection rules. Preserve failures, censored cases, ties, and nonmonotonicity.

The final paper-1 implementation is not present in the fetched branches. New experiments use an explicitly labeled recovered implementation that numerically reproduces key supplied results. This is not a claim that all published tests/regression counts were rerun.

Paper-2 reproduction retains its analytical model. Unified HELIX-profile diagnostics are new experiments with separately stated SLAs and semantics, not retroactive replacement of conference results.
