# Stage 6B formal evidence report

Protocol FI-JBAVG-S6B-v1. Completed under implementation `eb614e16c9ad3eba44068d58e51b49eabcbdfe14`. G0 is primary accuracy/judgment evidence; G1 is boundary-enriched sensitivity evidence. HELIX is a pinned simulator reference, not measured GPU or client truth.

## RQ1 — Request-level numerical accuracy

| Metric | Median signed error (s) | Median absolute error (s) | P90 absolute error (s) | Paired points |
|---|---:|---:|---:|---:|
| TTFT | -0.012211675858907256 | 0.0712052790895541 | 2.9211954348625113 | 1265 |
| TPOT | -5.89936192308127e-05 | 5.902721874084804e-05 | 0.041174705231194764 | 1265 |

These are empirical inverse-CDF quantiles under equal workload → candidate → valid point → applicable request weighting. TPOT seconds can be multiplied by 1000 for milliseconds. The per-workload, relative, SLA-budget-normalized and service-relevant results are in `metrics/request_accuracy.csv`; raw paired and unpaired request rows are in `metrics/request_pairs.csv`. Request-pooled summaries are supplemental and separately labeled. m=1 TPOT stays null. No significance tests, bootstrap or workload confidence intervals were used.

G0 evaluator statuses: {'complete': 1265, 'unsupported_profile_domain': 1285}. Paired execution coverage: 1265/2550. These counts include unfavorable and unsupported results; partial request completions never enter primary latency errors.

## RQ2 — Joint judgment and sampled capacity

G0 descriptive six-SLA counts: {'BU': 4619, 'BS': 2688, 'C': 264, 'unknown': 7710, 'O': 19}. The six SLA conditions reuse the same physical trajectories and are not independent replicates. `metrics/judgment_summary.csv` gives BS/BU/O/C, raw numerators/denominators, O/(BS+O), C/(BS+C), O/(BU+O), approval and decision coverage, macro versus pooled rates, latency-only and near-boundary subsets.

Capacity absolute relative error median/P90: G0 0.96875 / 0.998046875; G1 0.96875 / 0.9972378641357421. These descriptive candidate/SLA row summaries accompany all per-workload rows and capacity bounds; zero reference capacity and unidentified capacity have no exact relative error.

G0 no-safe/right-censored/unknown/nonmonotone sequences: 165 / 17 / 270 / 10. G1: 165 / 17 / 270 / 10. Sequence counts include both models and six correlated SLA classifications. G1 unresolved transition brackets: 296; quota and stopping reasons are retained in `checks/stop_summary.json` and full sequences.

A sampled maximum is a finite-grid quantity. Right-censoring does not invalidate that maximum, but equal top-end capacities do not establish agreement on continuous capacity. Unknown bounds are not confidence intervals. No monotonicity or continuous safe interval is assumed.

## RQ3 — Bounded applicability and runtime

All 60 cells are reported: {'fail': 59, 'not-assessable': 1}; 0 pass. The screen thresholds (10% P90 latency-budget error, 20% capacity/loss, zero observed optimistic approval, 10× matched runtime) are preregistered engineering tolerances, not literature standards. A failed cell alone does not establish universal worthlessness.

Matched full-drain runtime pairs: 295. Matched ratios describe a boundary-selected subset, with one R execution versus five E measurements, and different wrapper scopes.

Evaluator per-point median runtime strata: `{"complete": {"median": 0.041718000000400934, "P95": 0.28412090000347234, "min": 0.0031582000010530464, "max": 0.6620058999978937, "count": 1560, "na_reason": null}, "unsupported_profile_domain": {"median": 0.0011355999959050678, "P95": 0.005532399998628534, "min": 0.0006922000029589981, "max": 0.02236599999741884, "count": 1290, "na_reason": null}}`. All scheduled E inputs receive one warmup and five measurements; technical attempts are retained. Cache read/decompression/recovery/classification is separately measured and never called HELIX execution time. Timing repeats describe this host, not independent workloads.

`applicability/evidence_cells.csv` lists every failed/NA dimension. Fixed G0-based low/middle/high log-intensity bands are descriptive; they do not define another pass screen. w203 (N=5) cannot satisfy the N≥10 screen and is still fully reported.

## RQ4 — Controlled ranking and original operating points

G0 ranking: {'undefined': 57, 'overlap_nonidentical': 1, 'exact_set_agreement': 2}; safe/unsafe/abstained/unknown original recommendations: 29 / 1 / 30 / 0. G1 ranking: {'undefined': 57, 'overlap_nonidentical': 1, 'exact_set_agreement': 2}; corresponding recommendations: 27 / 3 / 30 / 0.

This is a controlled five-candidate ranking probe. Fixed tie-break is 0, −1, +1, −2, +2. E recommendations are selected solely from E confirmed-safe pairs; original G0 recommendations remain intact and are never replaced by reference-informed fallback. Tables retain attainment, J/K/N, TTFT/TPOT/both/joint failure counts, shortfall, excess failures, arithmetic loss, safe usable intensity/loss and candidate/load decomposition. A single latency violation does not imply unsafe: only the 90% joint target defines the decision.

## Positive, negative and insufficient evidence

Positive observations: 2688 G0 both-safe classified conditions and 29 reference-safe original G0 recommendations; these are local observations, not a general reliability claim. Negative observations include 19 optimistic and 264 conservative conditions, 1 unsafe G0 recommendations, and the separately listed unsupported/no-safe/censored cases. Unknown coverage and unresolved brackets remain explicit.

Permitted interpretation: **B; D (full-grid capacities and rankings partly unidentified because of domain coverage); C (in specified cells failing accuracy or original-recommendation tolerances)**. A/B/C can differ across cells. Correlated diagnostics do not establish a mechanism's causal contribution without an ablation. This one approximation/reference comparison cannot establish that every accurate lightweight model must reproduce HELIX complexity.

## Provenance, budget and limitations

G0 physical count 2550; G1 2850. New HELIX unique inputs/attempts: 300 / 300; selected common intensities: 60; E unique inputs/invocations: 2850 / 17100. Quality checks: passed; 41 targeted tests. Full budget ledger includes failures and cache hits.

The historical G0 grid is outcome-adaptive from earlier metrics; the G1 grid is E/R transition-informed. Neither is a blind online search or external workload generalization test. h and w are fixed historical workloads, with w described as additional historical workloads, not untouched held-out. Existing compact cache records lack full original timestamp histories; saved endpoint identities and pinned lifecycle source support the recovery, not independent client measurements. No model edits, new baseline, ablation, SLA, hardware, workload, Stage 6C or manuscript were added.

## Per-workload primary variation

| Workload | TTFT median signed (s) | TTFT median absolute (s) | TTFT P90 absolute (s) | TPOT median signed (ms) | TPOT median absolute (ms) | TPOT P90 absolute (ms) |
|---|---:|---:|---:|---:|---:|---:|
| h101 | -0.023302473 | 0.061471335 | 0.22604803 | -0.058993602 | 0.058993603 | 18.467784 |
| h102 | -0.02384699 | 0.061034129 | 0.2268935 | -0.059027216 | 0.059027217 | 25.138128 |
| h103 | -0.0087950534 | 0.0937352 | 13.385337 | -0.059027204 | 0.059027219 | 91.568993 |
| h104 | -0.014335446 | 0.066013842 | 0.25649884 | -0.058993631 | 0.058993634 | 48.420626 |
| h105 | -0.022063608 | 0.061353347 | 0.22135218 | -0.058993602 | 0.058993603 | 22.395396 |
| h106 | 0.1594096 | 0.15958872 | 0.23143463 | -0.059027204 | 6.0910658 | 49.900163 |
| w201 | 0.15304284 | 0.15304284 | 3.338341 | -0.058993603 | 0.8269394 | 37.793793 |
| w202 | -0.012572794 | 0.11055795 | 0.30059033 | -0.059027205 | 0.30797438 | 39.964708 |
| w203 | 0.72520879 | 0.72520879 | 6.307101 | 2.4134493 | 2.498236 | 10.076995 |
| w204 | -0.00070792326 | 0.074744895 | 1.8627456 | -0.058993616 | 0.058993637 | 59.135232 |

Capacity macro summaries use equal valid candidate then equal workload weighting, separately for each SLA, in `capacity/capacity_macro_summary.csv`. Ranking defined denominators and uncensored strata are in `decisions/ranking_summary.csv`. Operating loss distributions are in `decisions/operating_summary.csv`. Physical-point-pooled and request-pooled accuracy remain supplemental.

G0 exact capacity comparisons: 30/300 rows; relative capacity error is defined in 15/300 rows, from workloads ['w203']. The displayed error median/P90 describes only these identifiable positive-reference-capacity rows, not the unidentified remainder.

G1 exact capacity comparisons: 30/300 rows; relative capacity error is defined in 15/300 rows, from workloads ['w203']. The displayed error median/P90 describes only these identifiable positive-reference-capacity rows, not the unidentified remainder.

## Audited execution cost and concrete unsafe recommendations

Matched R/E wall-time ratio over 295 qualified complete pairs: median 535.115, P95 738.931, range 70.5587–840.668. Every workload has timing evidence for all five candidates. These are simulator-call cost ratios, not GPU serving speedups. R includes initialization/extraction and dataclass materialization; E starts from prepared objects. Historical R timing is excluded. Five new E unsupported points are excluded from the matched full-drain ratio, not reported as fast successful predictions.

Actual campaign wall time: 9843.865s. Actual new R attempts: 7884.189s total. E benchmark calls: 620.324s total; one primary E call per input: 102.996s. Actual cached-reference processing: 18.689s; all E/R classification: 1.666s. The classifier time overlaps the cache-processing aggregate and must not be added twice. See `runtime/planning_cost.json` for preparation, serialization, profile loading, postprocessing and NA components. Exact repeat-free end-to-end planning cost and historical rebuild cost remain unavailable; no extrapolation is used. Peak memory is the persistent process lifetime high-water mark, not isolated model allocation.

| Grid | Workload | SLA | E candidate | Recommended intensity L | R J / K / N | R attainment | Safe usable loss |
|---|---|---|---:|---:|---|---:|---:|
| G0 | h106 | S5 | -2 | 0.2248002765 | 44 / 45 / 49 | 0.897959184 | 1.0 |
| G1 | h102 | S5 | 0 | 0.181019336 | 34 / 49 / 54 | 0.629629630 | 1.0 |
| G1 | h104 | S5 | 0 | 0.128 | 60 / 73 / 81 | 0.740740741 | 1.0 |
| G1 | h106 | S5 | -2 | 0.2248002765 | 44 / 45 / 49 | 0.897959184 | 1.0 |

All ten workloads stopped because each exhausted its six-intensity quota. Remaining eligible transitions are retained, without extra execution. No timeout, technical failure, retry, cache alias conflict or protocol deviation occurred. G0 and its original recommendations remain unchanged.

Independent audit passed 174948 checks, including per-point classification and provenance, endpoint formulas, successful repeat equality, exact capacity bounds, E-only recommendation, loss, best sets, deterministic refinement replay and dependency hashes. The 41 targeted tests passed. All required files and four PNG/SVG figure pairs are present; visual review passed.

Screen disposition: 59 failed cells and one not-assessable cell (h103/S4, due to unidentified sampled capacities). No cell passed; the prerequisites for interpretation A are therefore absent. The B/C conclusions are conditional on the observed failure dimensions, while D applies to the unidentified capacity/ranking evidence.
