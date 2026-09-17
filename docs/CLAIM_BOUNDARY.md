# Claim boundary

Stage2 completion (2026-09-17):1634 physical points,3268 SLA pairs,35,688 stress rows and336 mitigation rows have passed formal integrity checks. Five metric-identical explanatory traces and one evaluator-only progress ablation are available. The Chinese `FORMAL_EVIDENCE_REPORT.md` is the final assessment; older exploratory paragraphs below describe separate evidence.

Nominal decision transfer is correct in6/6 Decode-tight main trials and wrong in6/6 Prefill-oriented main trials, with8.30–26.16% sampled candidate-capacity regret in the latter. These12 deterministic trials do not estimate a population error rate. The h106 Prefill reference sequence is nonmonotone: its largest safe point is not a continuous operating-capacity guarantee. Three reference configuration/regime sequences are nonmonotone overall; eight configurations have no sampled safe point in either model. None is silently omitted or credited as a correct winner.

The large-gap/correct-winner mechanism example is from controlled Both−5%/−10% stress, not a nominal success. Profile underestimation can improve a Prefill-oriented ranking while worsening safety; the effect is not monotonically harmful in every metric. Fixed margin and four-scenario guards have identical observed outputs here; no superiority for extra scenario evaluation is claimed.

Mitigation quality averages exclude two group/regime cases with zero reference oracle capacity (26 defined denominators out of28 trials per policy/bias); unsafe-output and abstention counts retain all28. Main five-candidate figure panels have12 trials and are not the same aggregate. Reference-validated safe outputs are guaranteed only for the queried simulator cases by policy construction; zero observed unsafe output is not a generalization result. Query counts are logical oracle calls with separately deduplicated physical queries, not newly executed policy-timing experiments. Existing mixed-host parallel runtime sums cannot justify a speedup.

Fresh Windows sequential measurements show reference/evaluator median planning-time ratios1328.6 and1389.1 on two predeclared cases. They are neither inference throughput speedups nor a campaign-level policy speedup. Recovered JB1, HELIX simulation, limited candidate family and incomplete workload/link crossing remain explicit scope limits. Future Internet readiness is an evidence assessment for a narrow empirical contribution, not verified novelty or guaranteed acceptance.

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

Final exploratory outcome: no claim that budgeted E-seeded allocation beats strong reference-only controls is supported. Uniform reference-only bisection matches four coarse-grid optima with five queries; E-seeded allocation takes ten. Six stress-induced selection changes on candidate-specific refined probes are provisional: the common19 grid produces ties and no reference-quality loss. Do not report them as a robust ranking-error probability. Selected journal direction is an empirical reliability assessment, with held-out publication evidence still required.

Stage2 uses the frozen JB1 recovered implementation, not the unavailable final CA source. Raw-compute progress follows the manuscript equations but changes all12 published sampled endpoint pairs; the legacy fixed-overhead-progress ablation restores them. New formal labels must be recomputed. Missing40-test/140-row historical bundles do not block the research; they limit reproduction claims. Formal workload/link design is incomplete, with two within-workload link anchors; marginal duration/link differences are not causal estimates. Structured stress is evaluated on identical nominal common grids and must retain unresolved/censored stress edges.
