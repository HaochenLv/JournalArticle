# Stage 6A — JB-Avg-v1 implementation and deterministic validation

**READY_FOR_FORMAL_VALIDATION.** The frozen serial virtual-round model is implemented in a new, independent core. All 29 new deterministic tests and all 75 repository tests pass. All 3,184 unique physical executions in the existing cache are recoverable. No new HELIX execution, formal evaluator matrix, refinement, ranking experiment, SLA sweep, profile stress or manuscript was run or written in Stage 6A. Readiness authorizes no automatic next-stage execution: this stage stops after Git delivery.

Source HEAD at intake: `881f5cbe159dc712178ec413378a3c616a6e739e`; branch `main`. The tracked tree was clean. The untracked, paused Stage 6 metric-SLA protocol/scripts/results already existed at intake and are preserved byte-for-byte in this milestone. They are incomplete historical work, not Stage 6A experiments or validated final results. The 2,065 saved Stage 6 point records include 2,050 reused points and 15 previously completed new references. Five interrupted reference-attempt journal entries retain their original `running` text; they are historical interruption records, not live jobs or unsafe outcomes. No prior Stage 6 process was running at intake and none was resumed.

## 1. Frozen model and implementation

The new [design contract](../config/jb_avg_v1_design.json) and [core](../src/jb_avg_v1.py) implement **simulate first, classify later**. `simulate(pipeline, workload, profiles, ...)` has no SLA/target argument. It returns first/last endpoints, a full event-batch trajectory and its hash, resource status and diagnostics. [The classifier](../src/standard_metrics_v1.py) is a pure postprocessor and does not modify simulation output.

For active Prefill cohort P and FIRST_DECODE/DECODE cohort D, the core forms Q_P from full input lengths and N_D from the Decode count. Every stage pays `layers × (P_h(Q_P) + D_tilde_h(N_D))` once per virtual round. D(0)=0; D(1) uses the pinned interpolation followed by the singleton ×2 rule. All integer in-domain lookups of the nominal A100/L4x2/T4x4 profile tables were compared against the pinned lookup implementation as a read-only profile-integrity test; this is not an A100 or second-pattern experiment.

Network bytes equal the sum of actual boundary transfers: one prompt activation per input token and one Decode activation per active Decode request. Multiple boundaries using the same physical link legitimately add messages. Serialization is bytes/effective bandwidth. `T_round = sum(stage compute) + sum(link serialization)` and `mu = 1/T_round`; the same mu advances normalized Prefill work and Decode token units. There is no additional contention factor, common gamma, overlap, NIC penalty, per-layer FIFO or detailed scheduler. Diagnostic shares sum back to the stage batch charge and cannot influence timing.

Only Arrival, PrefillDone, FirstToken, DecodeBlockUpdate and Finish events are used. At a timestamp, all due transitions/completions and arrivals are applied atomically before checking the resulting resource state and recomputing rates. Fractional progress survives intervening arrivals. PrefillDone sets FIRST_DECODE, never t_first. g=1 records FirstToken; g=m records Finish. For m=1 both occur together. q=16 controls memory/context boundaries, not TPOT granularity. q=8 and q=16 produce identical isolated first/last endpoints in the deterministic test.

Memory retains weights, assigned-node workspace/reserve, KV and per-stage activation buffers. Prefill context is input length; Decode context is input plus the next conservative block upper bound, capped at output length. Memory is a hard feasibility gate, not a service slowdown. A block transition may therefore cause resource infeasibility without being a latency miss. Zero bandwidth with positive traffic also produces `hard_resource_infeasible`. Profile domain overflow produces `unsupported_profile_domain`, with no safe/unsafe label. Incomplete execution cannot be classified as a latency failure.

No H correction or fixed/queue accounting overhead is used in new virtual execution. Both frozen JB1 source files, all original profiles, the adapter, HELIX sources and Stage 2–5 artifacts remain unchanged. The protected manifest verifies **11,859 pre-existing files**, including paused Stage 6 artifacts.

## 2. Metric contract and classifier

HELIX Initialization is Prefill; each Increment is one output token. Accordingly:

- standard TTFT = first Increment completion − arrival;
- request-average TPOT = (last Increment completion − first Increment completion)/(m−1), for m>1;
- m=1 has TPOT=None and checks TTFT only;
- joint pass requires that the same request passes both applicable limits;
- the workload target is at least ceil(0.90×N) joint passes.

Equality at a threshold passes. N=10 requires 9 passes; N=11 requires 10. The disjoint-success test, where TTFT and TPOT each pass 9/10 but their intersection is only 8/10, correctly fails. Resource failures return safe=False with latency counts/attainment undefined. Unsupported, incomplete and empty workloads return safe=None. The empty-workload convention avoids fabricating service evidence; it is not exercised by the existing reference cache.

The model fully drains supported, resource-feasible workloads regardless of any later SLA classification. Strict and permissive thresholds leave all output data, event times and the trajectory hash unchanged. These are simulator-side predictions, not client measurements or measured GPU serving performance.

## 3. Read-only cache migration

[Migration implementation](../scripts/migrate_standard_metrics.py) scans compressed records under results and writes only the independent `results/standard_metrics_v1` directory. Each record supplies its own `inputs.sla.fixed_overhead_s` and `queue_overhead_s`; neither is defaulted. Current cache records all happen to specify h=0.005 s, while tests additionally cover h=0, 0.02 and 0.15 s. Missing metadata is unsupported, not guessed.

Recovery subtracts that record's h from saved true_first_token_ttft_s. For average TPOT it subtracts h from **only the post-first Increment durations** and averages those m−1 values. The first Increment duration is excluded because it is already part of TTFT. Reconstructed final completion is `arrival + TTFT + sum(post-first raw durations)`.

Physical deduplication removes SLA/accounting metadata from the canonical execution input and retains all other input fields, including pipeline, workload, source commits and dispatch extension. Every alias is independently audited; recovered metrics must agree before aliases merge. Thus multiple threshold labels do not become multiple physical executions. A conflicting physical group would be excluded and recorded, even if its individual records separately passed.

| Audit quantity | Result |
|---|---:|
| Compressed files scanned | 10,249 |
| Non-reference files skipped | 6,821 |
| Reference records audited | 3,428 |
| Unique physical executions | 3,184 |
| Recoverable physical executions | 3,184 / 3,184 (100%) |
| Recoverable source records | 3,428 / 3,428 (100%) |
| Pre-Stage-6 physical executions | 3,169 |
| Included prior paused Stage 6 executions | 15 |
| Known Stage 4 + Stage 5 heterogeneous inventory | 2,550, read only |
| Deduplicated request rows | 101,817 |
| Single-output requests | 1; average TPOT=None |
| Missing metrics / overhead metadata | 0 / 0 |
| Output/list-length / request-count mismatches | 0 / 0 |
| Full-drain failures / max-list mismatches | 0 / 0 |
| Final-completion failures / duplicate conflicts | 0 / 0 |
| Failed or unsupported migrations | 0 |

The 3,169 pre-Stage-6 points include earlier diagnostic/pilot records as well as Stage 2–5 evidence; they are not 3,169 newly held-out workloads. The 2,550-point inventory is just a read-only membership count: no evaluator matrix was executed. The extra 15 were completed before this task and are explicitly separated.

Every request has exactly output_tokens saved Increment durations and every audited reference fully drained. The largest reconstructed-final-time error is **9.094947017729282e−13 s**; the largest saved first-Increment/Prefill identity error is **3.552713678800501e−15 s**. The largest difference between mean(post-first durations) and the equivalent endpoint formula is **4.135580766728708e−14 s**. The audit uses absolute tolerance 1e−7 s and relative tolerance 1e−10 for final endpoints/duplicate comparisons. No metric reconstruction problem was detected. **No old cache record required exclusion.**

This verifies consistency of available compact data and the pinned lifecycle/extraction source. Complete original token timestamp histories are not stored, so the audit is not an independent client-side timing measurement. Final completion agreement is an additional endpoint check, not evidence of real deployment accuracy.

[cache_manifest.json](../results/standard_metrics_v1/cache_manifest.json) maps every source and SHA256 to its physical point; [cache_audit.json](../results/standard_metrics_v1/cache_audit.json) records counts and errors. [request_metrics.csv](../results/standard_metrics_v1/request_metrics.csv) has one row per unique physical execution/request, with full-precision TTFT and average TPOT; physical_point_id joins the manifest. An empty average_tpot_s cell means None, not zero. Missing, corrupted, undrained, inconsistent or conflicting future records are explicitly retained as unsupported/migration_failed and never trigger HELIX.

## 4. Deterministic validation

**29 new tests passed; 0 failures, 0 errors. All 75 repository tests passed.** The regression suite includes existing immutable-model tests; it does not conduct a JB1+ experiment or call HELIX. New tests are entirely hand-checkable fixtures and read-only profile comparisons.

| Frozen cases | Verified behavior |
|---|---|
| A / B / C | m=1 has first=last and TPOT=None; m=2 excludes the first Increment; isolated execution has exact analytical endpoints |
| D / E / F | D(2) once; P(L)+D(1) on one mixed compute resource; P(L1+L2) once, including nonlinear lookup |
| G / H | Half bandwidth changes only serialization; fractional Prefill and Decode progress survive an arrival |
| I / J | Classifier cannot change trajectory; q does not change isolated first-token timing |
| K / L | Conservative KV context and block-boundary memory gate; simultaneous Finish/FirstToken/Arrival is atomic and input ordering commutes |
| M / N / O | Profile maximum supported, max+1 unsupported; ceil(90%×N); disjoint success trap |
| P | Diagnostic compute-share conservation and identical trajectory with shares on/off |
| Additional | Record-specific overhead, corrupt/missing-cache handling, physical deduplication, same physical link used by multiple boundaries, memory components, resource-vs-latency status, q=1 event tie |

Artifacts: [deterministic test results](../results/standard_metrics_v1/deterministic_tests.json), [full regression output](../results/standard_metrics_v1/regression_tests.txt), [validation checks](../results/standard_metrics_v1/validation_checks.json). CSV row counts, unique physical/request keys, nonnegative finite metrics and m=1 null handling were independently checked. All protected source/cache bytes were rechecked after execution.

## 5. Runtime sanity and limitations

The two deterministic CPU workloads each use 5 warmups and 50 measured runs. The benchmark includes diagnostics, event records and trajectory hashing. All repeated runs retain identical trajectory hashes.

| Workload | Requests / output tokens | Event batches | Median | p95 |
|---|---:|---:|---:|---:|
| Single isolated | 1 / 33 | 6 | 0.0801 ms | 0.2136 ms |
| Staggered small cohort | 8 / 264 | 48 | 2.0481 ms | 2.3303 ms |

Environment: Windows AMD64, Python 3.12.14. Full samples are in [runtime_sanity.json](../results/standard_metrics_v1/runtime_sanity.json). JB-Avg-v1 is lightweight on these small fixtures. This does **not** establish full-matrix runtime, a formal speed/cost advantage, GPU throughput or any inherited 488× speedup.

No internally inconsistent implementation requirement was found. Documented edge conventions—empty-workload unknown, bounded event-limit unknown, unsupported zero/nonfinite service cost and numerical tie tolerance—do not alter the frozen service law. The design remains an approximation: full active input counts drive mixed batch cost even after fractional Prefill progress, compute/network costs compose serially, and conservative block contexts can affect hard memory feasibility. None of these conventions imply equivalence to detailed HELIX scheduling. Profile-domain rejection is expected when cohorts exceed table coverage; it must remain a separate outcome in any later study.

## 6. Decision and stopping point

**READY_FOR_FORMAL_VALIDATION** means the implementation and cache layer are ready to be subjected to a separately authorized formal validation protocol. It does not mean the new model has demonstrated reliability, candidate ranking quality, capacity accuracy or real deployment safety. Stage 6A supplies no such formal evidence. No further experiment starts in this task.

Historical JB1/JB1+ metrics and results remain historical. The new primary semantics are standard TTFT + request-average TPOT + 90% joint attainment; maximum accounted Decode-iteration latency is not silently relabeled as average TPOT. The withdrawn, never-public AICCC manuscript is not prior publication and was not searched. The accepted prior work is *Evaluator-Guided SLA-Aware Layer Partitioning for Heterogeneous LLM Pipelines*; evaluator-induced capacity, predefined allocation families, evaluator-guided comparison and coarse-to-fine search are not claimed as new contributions.

Reproduction entry points (no HELIX execution): `python -m unittest discover -s tests -v`, `python scripts/migrate_standard_metrics.py`, `python scripts/validate_jb_avg_v1.py`. Use the repository's available Python 3.12 environment and pinned dependencies. Git delivery preserves the pre-existing paused Stage 6 files, adds this implementation/validation package, updates status/log and leaves the remote main synchronized. Final commit identity and clean-tree confirmation are reported at delivery.
