# Claim boundary — Stage 3 evidence freeze

Final writing authority: [STAGE3_EVIDENCE_REPORT.md](../STAGE3_EVIDENCE_REPORT.md). Assessment: **Yes, but modified**. Scope: recovered JB1 against pinned HELIX, six held-out finite workloads, five heterogeneous shifts, A100 controls and two opposite-link anchors.

| Supported wording | Unsupported wording |
|---|---|
| JB1 shows the reported differences under the pinned HELIX reference simulator | The unavailable CA-final evaluator shows these failures |
| Legacy-progress control changes/preserves the explicitly listed results | Legacy control is confirmed final CA code |
| Raw: 4 strict best-set mismatches, h101–h104 | 6 strict ranking reversals |
| Raw: 2 tie-break mismatches, h105/h106 | All best sets are disjoint |
| Legacy: 3 strict mismatches, h101–h103, and 1 tie-break mismatch, h106 | Legacy eliminates planning unreliability or uniformly improves every metric |
| Tight-TPOT: 6/6 winner agreement in both implementations | Population success probability is 100% |
| Relaxed-TPOT (fixed TTFT): Raw0/6, legacy2/6 agreement | Raw6/6 mismatch is independent of implementation semantics |
| Partition-selection loss and operating-point loss are distinct, with exact point safety reported | Selected partition quality certifies the recommended operating point |
| Conditional reference-validation replay on a preconstructed grid | 5 reference calls are sufficient from scratch |
| 20%-target derating with grid snapping, measured realized reductions | Exactly20% realized capacity reduction |
| Largest observed reference-safe intensity in this grid | Continuous capacity, steady-state throughput or a safe prefix |
| Reference-best candidate within the tested family and grid | Globally optimal partition |
| Directly queried point is reference-safe | Real deployment or unqueried-load safety guarantee |
| Structured evaluator profile underestimation with immutable reference | Measured real GPU noise distribution |
| CPU simulator/evaluator planning-time ratios on two declared cases | GPU inference acceleration or whole-policy end-to-end speedup |

## Denominators and flags

Stage2:1634 physical runs,3268 SLA-paired judgments,76 configuration/regime rows,35,688 stress rows,336 mitigation rows. Stage3 adds3268 evaluator-only control judgments; no new reference run. Raw O/C=23/413; legacy17/460. Same physical point has two SLAs; neither adaptive-grid point counts nor12 deterministic decisions are population risk estimates.

Raw and legacy each retain8 no-safe configurations,0 evaluator nonmonotone and0 evaluator right-censored configurations. Reference retains3 nonmonotone configurations and0 right-censoring: h102/A100/tight and h106/heterogeneous/relaxed shifts1/2. Largest safe points in those sequences do not establish continuous safe intervals. Legacy uses the original Raw/R-informed grid; it has no separately refined capacity-resolution guarantee.

All profile stresses except L4x2-only use3268 paired points; L4x2-only uses3008 heterogeneous points. Profile stress remains Raw JB1 evidence, not an unperformed legacy×profile sensitivity experiment. The large-gap/correct-winner mechanism example is Both−5%/−10% stress, not nominal evidence.

## Loss and validation interpretation

Raw relaxed partition loss8.30%–26.16% is different from operating-point loss68.95%–95.86%. h106's exact recommendation is unsafe, so safety-gated usable loss is100%. Both implementations have11 safe and1 unsafe main recommendation. Legacy h105 picks the correct partition but retains87.77% operating-point loss. It is invalid to add partition loss to operating-point loss, because the latter already includes it.

Mitigation has28 trials per policy/bias,26 with defined reference oracle quality; error/abstention counts retain all28. Core figure04 shows only12 five-candidate trials. Grid construction used reference transitions and its cost is excluded from post-selection replay query counts. Zero unsafe validated outputs follows from only returning directly queried safe points, not a generalization theorem. Boundary replay does not reoptimize partition. No optimal-validation, novel-optimizer or superiority-over-reference-only claim is supported.

Derating preserves its original implementation: downward grid snapping followed by candidate tie-break. Nominal26 defined reductions range21.20%–79.87%, median46.53%;8/28 nominal selections change partition after snapping. Both−10% has28 defined reductions, range21.20%–78.98%, median26.09%. Two nominal abstentions have undefined realized reduction. Do not describe this policy as necessarily keeping the original selected partition.

## Provenance and remaining limits

Raw JB1 restores0/12 published endpoints; legacy progress restores12/12. Neither identifies the unavailable CA-final source or reruns its missing40-test/140-row historical bundle. Historical exploratory numerical recovery is separate from current baseline identity. Original CA repositories and supplied reviewer material remain read-only and excluded from journal commits.

Five mechanism traces are explanatory post hoc cases, not random samples or a complete causal decomposition. The workload/link/duration design is incomplete. Sequential planning ratios1328.6 and1389.1 refer only to two declared host measurements. Novelty, real hardware applicability and venue acceptance are not established by this freeze.

**No further experiments needed** for the stated bounded empirical contribution. Broader future claims would require new evidence; they are outside this stage.
