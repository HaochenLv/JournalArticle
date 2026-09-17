# Journal outline selected after baseline falsification

Working title: **Reference-Grounded Reliability Assessment for SLA-Aware Capacity and Partition Planning**.

## Central question

When does an inexpensive evaluator's safety verdict or capacity estimate disagree with a pinned reference simulator, and when does that disagreement actually change a partition decision?

The primary contribution is a reproducible, matched-input empirical reliability study and a practical validation protocol. It is not a new robust optimizer or a claim that an advanced reference allocation policy has been established.

## Structure

1. Motivation and explicit relationship to the two conferences.
2. Input/metric contract: workload, absolute profiles, topology, units, aligned/native TTFT, maximum per-token TPOT, finite-trace intensity, simulator limitations.
3. Recovered artifact and reproduced conference observations; transparent missing-final-source limitation.
4. Nominal paired diagnosis, reference-side range extension, optimistic/conservative disagreement, sampled nonmonotonicity and first violations.
5. Evaluator-only phase/device stress: incremental effects beyond nominal mismatch; keep intrinsic overhead/reference fixed.
6. Capacity error versus decision error: five-candidate reference rankings, ties, resolution, winner stability, and bias-induced changes.
7. Simple mitigations and their limits: fixed margins/derating, finite scenarios, direct point validation, and query-budget controls. Report failed superiority hypotheses.
8. Held-out evidence, runtime, limitations, and usable recommendations.

## Minimum new contribution

- A common absolute-profile evaluator/reference contract, distinct from the analytical conference partition model.
- A paired benchmark including reference-unsafe probes, raw per-token evidence, and both directions of disagreement.
- A study separating absolute capacity reliability from partition decision reliability under nominal and structured mismatched profiles.
- A reproducible validation protocol and fair mitigation cost/quality comparison, including negative results.

The event engine, progress/accounting principle, intrinsic correction, shift family, and evaluator-guided/coarse-to-fine search remain prior contributions. Public historical notes already mention nonmonotonicity; its mere rediscovery is not journal novelty.

## Rejected primary method claim

The initial evaluator-seeded method reaches the 19-load-grid reference optimum in four heterogeneous trials with ten calls. However, reference-only bisection on the uniform partition reaches the SAME grid optimum in all four trials with five calls. Best-first also ties equal allocation. The coarse grid hides smaller candidate differences. These results do not support an allocation-method superiority claim; a budgeted planning method is only a backup pending denser, held-out comparisons.

## Submission gate

Freeze the protocol and reproduce the observed reliability patterns on additional seeds, longer traces, another source window, and a link variation. Confirm the recovered implementation's alignment with the final artifact if it becomes available. If only isolated artifacts remain, narrow the conclusions rather than claim general reliability. Venue novelty and acceptance remain unproven; no GPU deployment guarantee is claimed.
