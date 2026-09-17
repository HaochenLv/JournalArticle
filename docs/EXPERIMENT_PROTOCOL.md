# Diagnostic and publication protocol

## Frozen dimensions

- HELIX and conference pins: CODE_REUSE_AUDIT.md.
- Matched nominal profiles: exact absolute per-layer tables, no artificial perturbation.
- Finite Azure-derived requests: identical arrivals/lengths/IDs within a paired evaluator/reference call; intensity only rescales arrival gaps.
- A100 nominal cases: seeds 0,7,19; original Decode SLAs, relaxed Decode controls, and genuinely TTFT-limited controls.
- Heterogeneous ranking: seeds 0,7; five shifts; absolute L4x2/T4x4 tables; diagnostic SLAs (4.2 s,.3 s) and (4.2 s,10 s). These deliberately differ from the analytical conference model's .28 s Prefill threshold.
- Profile stresses: evaluator-only Prefill, Decode, or Both multipliers .95/.90/.80; plus L4x2-only .90. Intrinsic coefficient and reference remain unchanged. These are deterministic stresses, not inferred hardware noise.

## Sampling

The nominal broad grid is followed by two rounds of local midpoints wherever either model changes verdict. The candidate study uses four midpoint rounds. Reference-safe range endpoints trigger doubling until a reference-unsafe point appears or a stated finite cap is reached. Check the entire observed sequence; retain unsafe-to-safe reversals and censoring. “Next unsafe” is an observed probe, not a mathematical upper bound on continuous capacity.

The ranking grid was enlarged to a common 19-load schedule through 18.56 after initial exploratory runs found that the original 1.16 endpoint censored the TTFT-sensitive reference. The enlarged schedule is used for all five candidates before the final planning replay. It is an **exploratory common-grid diagnostic**, not a preregistered held-out evaluation. Local refinement adds candidate-specific points; report brackets and ties when describing rankings.

## Reference reuse

A logical verdict uses exact full-input keys. Threshold-only variants may reuse an identical physical simulator history and reapply thresholds; such records identify their source. Derivation was tested against independent simulations. An exception is not an unsafe/safe datapoint. All reference queries drain all finite requests.

Within a single planning trial (fixed SLA/workload), distinct candidate/load pairs require distinct physical simulations. Planning pilots expose a reference label only through a counted query callback; a precomputed exhaustive table is used by the evaluator of the policy, not its decision logic. The exhaustive table's cost is not included in the policy's online budget, but is counted as the exhaustive baseline.

## Comparisons and honest interpretation

Report both optimistic and conservative counts, with exact deterministic denominators. For each policy, report validated load, selected candidate, abstention, regret against the finite tested set, evaluator calls, reference calls, and runtime. Pilot runtime sums previously recorded components under concurrent background load; it is not a controlled sequential benchmark. Final paper runtime tests need warm-up and repeated sequential trials.

Compare reference-only adaptive sampling as well as a fixed reference schedule. Compare finite scenarios to fixed compute/SLA margins and capacity derating. Do not select a margin on test labels and then report the same labels as validation. In nightly exploration, report tuning/exploration status explicitly.

The current inexpensive evaluator oracle has no power to certify real deployments. Reference validation certifies only the queried point under the pinned simulator. Any claim about an entire safe prefix, continuous capacity, stationary throughput, hardware profiling distribution, or global partition optimum requires evidence not supplied here.

## Two-week held-out split

Use tonight's seeds 0,7,19 as exploratory. Freeze the method and all baselines before testing additional seeds/windows. Include the 120 s workload used by conference paper 2, a changed source-window offset, and at least one slower link setting. A minimal publication comparison can retain one model and one device pattern if these limits are explicit and the reliability/cost-quality results are sufficiently supported.

## Final direction gate outcome

The uniform-candidate reference-only bisection control matches the four common-grid optima in five queries; evaluator-seeded allocation needs ten. This falsifies a primary method-superiority interpretation of the initial pilot. The selected paper is a reliability/decision-transfer study. Budgeted planning is a conditional backup only. Common-grid ranking controls are published beside the candidate-specific refinements because six apparent stress-induced reversals are resolution-sensitive.
