# Code reuse audit

## Immutable sources

| Repository | Initial checked-out HEAD | Initial git status --short |
|---|---|---|
| sla-aware-evaluator | `297280c000e45ba6a8fa79135e4bfc4a9e17cb99` | empty |
| SLA-Aware-Layer-Partitioning | `e92644c943369054b54361cdcdc54646d2bdc48f` | empty |

Both clones remain read-only after creation. All exports, dependency installation, bytecode, caches, and outputs are under JournalArticle. No checkout/reset/rebase/edit/commit/push is performed in either old repository. Branches were inspected using `git log`, `git show`, and `git archive`.

The main branches are not the complete final-paper artifacts. Public experiment branches must be pinned explicitly:

- Paper-1 reference and E31/E46 candidate: `1cd5c56365b084fb06e3ca14f67448ddbf45275a`, `origin/exp/e46-prefill-ttft-overhead-direct-run`. A later branch tip (`43c9c09`) records closure, not the paper's final accounting-only implementation. No accessible final-paper 40-test snapshot was identified.
- Paper-2 revisions: `2f876f0b889bb26d2c759b9b2d6eb3e7e97a9b4b`, `origin/reviewer-revision-experiments`, includes phases 14–16, 20 seeds, larger families, bandwidth sensitivity, and coarse-to-fine results.

## Paper-1 map (under src/sla_aware_mvp)

| Concern | Implementation and audit outcome |
|---|---|
| Entry point | `helix_demo.py`, later `prefill_debt_budget_ablation.py`, `e46_prefill_ttft_overhead_candidate.py` |
| Event loop | `evaluator.py:evaluate`; tied arrivals, fractional Decode progress, block/context epsilon, finite drain; recovered branch checks post-event resources |
| Domain/model | `domain.py`; 80 contiguous layers, stage/link route validation, separate SLA and config |
| Workload | `workload.py:build_helix_azure_conversation_workload`; restricted unpickler, 1200 count bins, global mean scaling, residual rounding, paired length draws |
| Profiles | `helix.py:HelixLayerProfile`; exact interpolation and ms-to-s; `HelixA100Llama2Profiler` sums stage layers |
| Singleton Decode | `exact_singleton_decode_demo.py:ExactHelixDecodeRuntimeProfiler`; factor two only for one active Decode |
| SLA/network | `evaluator.py:_account_resources`, `_network_bytes_by_link`; residual-time proportional commitments and sum across requests |
| Memory | `_static_memory_by_node` plus block-upper-bound KV; this recovered engine does not implement every activation-memory term described in the final paper |
| Capacity | `capacity.py`; sampled verification, refinement, right censoring; historical scripts also contain frontier helpers whose “upper bound” wording needs care |
| Decode blocking | `prefill_debt_budget_ablation.py:_budget_consistent_violation`; full compute+intrinsic Prefill debt charged at overlap; conservative and phase-insensitive |
| Intrinsic Prefill | E22 coefficient frozen at 59.37720874470879 us/token; E46 `PrefillTTFTOverheadProfiler` changes progress (trajectory-coupled), so it is not the final accounting-only method |
| HELIX adapter | `helix_fixed_reference.py`; fixed routing, upstream execution policy, event simulation, metric parser |
| Reference runners | `helix_fixed_reference_demo.py`, `helix_fixed_capacity_demo.py`, E31/E44/E46 drivers |
| Regression history | E31 multiworkload, phase jitter, request-size, TPOT, trajectory-alignment, counterexample scripts; `PROJECT_STATUS.md` contains E31–E46 findings |
| Tests/caches | 31 tests in exported branch; initial main has early MVP outputs. Most later reference outputs lived in CI artifacts/status reports, not a final paper result bundle |

Historical source already notes reference nonmonotonicity (E39), conservative phase exposure, and a size-shift counterexample (E44–46). These observations are prior project knowledge, not discoveries to claim as wholly new. New value must be a reproducible, systematic diagnostic and budgeted decision method, with new comparative evidence.

## Paper-2 map (under src/sla_partition_sensitivity)

| Concern | Implementation |
|---|---|
| Initial synthetic screen | `model.py`, `experiment.py`, phases 1–5 |
| Heterogeneous profiles | `helix_profile.py:derive_phase_speed_factors`; median A100/device ratios at five prompt and seven Decode sample sizes |
| Absolute compute model | `profiled_model.py`; analytical token/layer constants, context multiplier, concurrency penalties, phase-speed scaling |
| Partition | `phase6_profiled.py:shifted_partition`; alternating 10±shift |
| Workload | `phase11_trace_validation.py`; 120 s generated Azure windows, checksum-verified public distributions, seeds affect lengths |
| Capacity | `phase11_trace_validation.py:adaptive_capacity`; expand/halve then bisect; tolerance is 0.005 × max(high,1), effectively absolute 0.005 below intensity 1 |
| Compact score/search | phase 10 methods, phase 12 safe-edge surrogate, phase 13 direct capacity search |
| Wider families | phase 14 candidate radii and seed/bandwidth matrix; phase 15 directional expansion; phase 16 stride-two coarse-to-fine top-k |
| Frozen SLAs | Decode (TTFT 2, TPOT .2); Prefill (.28,1), seconds |
| Cached output | `results/phase13`, `results/phase14`, `results/phase16`; phase16 top1 corresponds to paper Algorithm 2 |

The absolute tolerance can create many tied capacities around 0.03 (roughly 10% brackets), so “exact best shift” can hide resolution effects. This is a diagnostic issue, not evidence that reported comparisons were fabricated.

## Reuse decision

Reuse pinned workload loaders, domain objects, event engine, HELIX adapter, profile tables, and original partition search for reproduction. New `src/research.py` provides:

- a transparent recovered accounting-only ledger on unchanged public progress;
- exact nominal machine-profile lookup for unified heterogeneous diagnostics;
- evaluator-only phase/device bias;
- name dispatch for HELIX group profiles;
- content-keyed reference caching with raw per-request/per-token metrics.

No large third-party tree is committed. `.deps` is ignored and `scripts/bootstrap.py` fetches exact public pins. Keep historical reproduction separate from unified diagnostics: constant 2 MB traffic and analytical absolute compute in paper 2 cannot be called an identical nominal HELIX model.

## Verification scope

The core paths, all major experiment phases, configs, stored summaries, and test interfaces were traced. This is a research audit, not a formal verification of every line or all upstream HELIX functionality. See `results/reproduction` and EXPERIMENT_LOG for actually executed checks.
