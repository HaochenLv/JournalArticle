# Journal writing inputs — Stage 3 frozen

Working title: **Reference-Grounded Reliability Assessment for SLA-Aware Capacity and Partition Planning**.

Read [STAGE3_EVIDENCE_REPORT.md](../STAGE3_EVIDENCE_REPORT.md) first. Evidence assessment: **Yes, but modified**. No further experiments needed for the bounded claims. This is an outline, not manuscript prose.

## Central question

When does a lightweight evaluator's judgement error remain numerical, and when does it change sampled capacity, partition selection or the actual recommended operating point? How do controlled profile mismatch and a small progress-semantic choice change that reliability?

## Evidence sequence

1. Input and metric contract: finite arrivals/token lengths, absolute profiles, fixed partition/network/memory, HELIX-relative TTFT/TPOT and common adaptive grids. State simulator and design limitations.
2. Provenance: recovered JB1 raw-progress is the experimental baseline; missing CA-final source is an explicit boundary. Legacy5ms control is a semantic sensitivity, not confirmed CA code.
3. Nominal judgement/capacity:3268 pairs/1634 physical runs, Raw23 optimistic/413 conservative; capacity median0 conceals signed extremes. Preserve8 no-safe and3 reference nonmonotone configurations.
4. Decision transfer: tight6/6 agree; relaxed4 strict best-set plus2 tie-break mismatches. Best sets, deterministic tie-break and sampled rank accompany winner counts.
5. Loss decomposition: partition loss versus actual operating-point loss, with exact recommendation safety. Highlight h106 unsafe output and legacy h105 correct winner with87.77% operating-point loss.
6. Implementation sensitivity: legacy changes53 labels, O17/C460, retains tight6/6 and improves relaxed0/6→2/6. Three strict and one tie-break remain; h102 worsens. Specific failures depend partly on semantics.
7. Controlled Raw profile mismatch:35,688 rows; stress can improve winner while worsening optimistic judgments. Keep3268 versus3008 device-specific denominators separate; no legacy stress extrapolation.
8. Mechanisms: full active-Prefill ledger charge, missed overlap from finish-time drift, local h101 threshold contrast. Large-gap/correct-winner case is explicitly stress; causal limits remain.
9. Practical engineering evidence: conditional reference-validation replay on a reference-informed preconstructed grid.20%-target derating has variable realized reduction and can change partition after snapping. No new optimizer or from-scratch five-call claim.
10. Limitations and reproducibility: fixed candidates, finite workloads, nonmonotone reference, control-grid resolution, simulator-only truth, missing artifact, post hoc traces and excluded grid-construction cost.

## Recommended figures and tables

- Four existing core figures01–04;03 marks strict versus tie-break;04 states conditional replay and grid snapping.
- Two existing mechanism timelines as one two-panel figure; h101 trace in supplement.
- One compact legacy decision table and a six-row relaxed loss table, both derived from Stage3 report; full24-row raw/control decomposition in supplement.
- Small existing sequential CPU planning-time table, without GPU or end-to-end policy speedup claims.

## Three strongest findings

1. Judgement, capacity and partition reliability are distinct and SLA-dependent.
2. Correct partition selection does not imply a safe or well-utilized recommended load; report both losses and point safety.
3. Profile and progress semantics alter downstream reliability; conditional validation has engineering value within its explicitly limited budget accounting.

## Prior-work and claim boundary

Event-driven evaluation, intrinsic Prefill accounting, the shift family and evaluator-guided search belong to prior CA contributions. The journal increment is the matched-input reference diagnosis, the error-to-decision/loss evidence chain, semantic sensitivity and audited validation limits. Historical failed optimizer superiority evidence stays negative; no new scheduler, optimizer, RL, global search or safety proof is proposed.

The writing task must honor [CLAIM_BOUNDARY.md](../docs/CLAIM_BOUNDARY.md). Do not draft a claim about the unavailable CA-final evaluator or label six raw mismatches as strict reversals. No full Introduction, Related Work, Abstract or Conclusion is created in this stage.
