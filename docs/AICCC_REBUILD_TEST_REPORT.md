# AICCC rebuild basic validation

- Date: 2026-09-19 (Asia/Shanghai).
- Result: **BASIC_TESTS_PASS**.
- Branch: `aiccc-journal-rebuild`.
- Starting HEAD: `f8ca85819af408957aa1c7e7bd037785f2452b4f` (matches the handoff).
- Ending HEAD: the delivery commit containing this report; resolve its exact hash with `git log -1 --format=%H -- docs/AICCC_REBUILD_TEST_REPORT.md`. The tested source remains identical to the starting HEAD. A literal self-containing commit hash cannot be embedded in its own content.
- Intake: checkout initially on `main` at `bfb4e002be2a079fc6dade5cf1d07d9c00b71bb0`, clean. Fetched origin, switched to the target branch, and pulled with `--ff-only`; already up to date. No edits or commits on main, no merge/rebase.
- Python: existing `.venv/Scripts/python.exe`, Python 3.12.10. `python` is not on PATH. The venv launcher required execution outside the restricted sandbox; no environment was recreated.
- Dependencies: `pip check` reported no broken requirements; installed `networkx==3.2.1` and `matplotlib==3.8.4` match `requirements.txt`. Existing `.deps/evaluator`, `.deps/partition`, and `.deps/helix` were used. No dependency installation or upgrade.

## Commands and results

PowerShell, from the repository root:

```powershell
git status --short
git branch --show-current
git log -5 --oneline
git fetch origin
git switch aiccc-journal-rebuild
git pull --ff-only origin aiccc-journal-rebuild
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pip show networkx matplotlib
.\.venv\Scripts\python.exe -m unittest tests.test_aiccc_math -v
.\.venv\Scripts\python.exe -m unittest tests.test_aiccc_evaluator -v
.\.venv\Scripts\python.exe -m unittest tests.test_journal_baseline -v
```

| Test invocation | Passed | Failed/errors | Runtime |
| --- | ---: | ---: | ---: |
| AICCC math | 5 | 0 | <0.001 s |
| AICCC evaluator | 6 | 0 | 0.007 s |
| Adjacent historical JB1 | 10 | 0 | 0.007 s |
| Bounded repository suite below (includes the above) | 84 | 0 | 9.213 s |

The repository suite ran 84 distinct tests, with zero unittest skips. The earlier 21 tests were rerun as part of these 84, not additional distinct coverage.

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_aiccc_math tests.test_aiccc_evaluator tests.test_journal_baseline tests.test_formal tests.test_host_execution tests.test_jb1_plus tests.test_jb_avg_v1 tests.test_memory_scheduler tests.test_sla_sensitivity tests.test_stage3 tests.test_stage6 tests.test_standard_metrics_v1 tests.test_research.ResearchTests.test_nominal_a100_profile_matches_pinned_profiler tests.test_research.ResearchTests.test_accounting_correction_and_bias_hold_trajectory_contract tests.test_research.ResearchTests.test_nominal_seed7_paper_transition tests.test_research.ResearchTests.test_nonmonotone_grid_does_not_claim_a_single_boundary tests.test_research.ResearchTests.test_paper2_reproduction_matches_frozen_rows tests.test_research.ResearchTests.test_planners_return_only_queried_safe_points_within_budget -v
```

Unrestricted `python -m unittest discover -s tests -v` was deliberately not run: inspection found two tests that traverse every saved `results/raw_reference/*.json.gz` record, prohibited by this handoff's historical-scan boundary. Only these two tests were omitted from the bounded suite:

- `tests.test_research.ResearchTests.test_reference_cache_input_hash_and_complete_requests`
- `tests.test_research.ResearchTests.test_threshold_reuse_matches_independent_complete_simulations`

Historical helper tests, including `test_stage6`, use their existing small fixtures and imports; no Stage 6 runner or analysis entry point was invoked. Their passing results are compatibility checks, not AICCC scientific evidence.

## Semantic invariants verified

- Residual budget subtracts compute and accounting charges from SLA.
- Path weights and allocated times conserve residual time; required bandwidth matches both `S_e / delta_e` and the frozen algebraic form `B_e * sum_j(S_j/B_j) / Delta`.
- Relative capacity is equal across the request path; shared-link commitments add.
- Zero residual raises `ResidualBudgetExhausted` instead of producing an allocation.
- Fixed overhead and SLA changes preserve the diagnostic drain trajectory hash; intrinsic accounting also preserves it.
- The 2051-token counterexample remains baseline safe / intrinsic-accounting unsafe, with identical trajectory hashes and frozen TTFT accounting values `1.8940402816` and `2.0158229367353977` seconds.
- Trace ledgers expose residual time and per-link allocations/commitments; path allocations sum to the residual.
- A single first violation is unsafe, without an attainment threshold.

## Post-hardening J0 validation

After the basic validation above, seven direct event/resource regressions were added to the rebuilt evaluator and the Decode block size was made an explicit runtime parameter. The last source/test hardening commit is `0d3e4b1a61cfd5ce48bf068dff12fd1481a47b2e`.

The hardened core was then executed through the repository's Windows self-hosted GitHub Actions path:

- Workflow: `AICCC Self-Hosted Tests`.
- Run: `35412992314`, attempt 2.
- Tested branch head: `b411bfcb29c08b71816b7570cb0e28b449108850`.
- Runner: `journal-win`.
- Python: 3.12.10.
- AICCC math: **5/5 passed**.
- AICCC evaluator: **13/13 passed**.
- Failed/errors: **0**.
- The run intentionally executed only the active AICCC core checks.

The seven added evaluator regressions cover tied-arrival commutativity, preservation of fractional Decode progress across unrelated arrivals, parameterized Decode block-boundary context/KV consistency, retention of simultaneous violations, immediate prompt-KV/activation reservation at arrival, explicit event-limit failure, and aggregate overload on a shared physical link. Block-sensitive tests use a non-default block size to verify that 16 is a compatibility default rather than a mathematical constant.

This self-hosted run did **not** execute HELIX, a formal validation matrix, a capacity sweep, Stage 6B experiments, profile-noise experiments, or manuscript experiments. Dependency bootstrap may fetch the pinned HELIX source tree, but no HELIX simulation was launched.

This checkpoint closes J0. Any future journal TTFT/TPOT work must be additive ledger-policy work above the frozen mother evaluator and must not silently alter the profiling-driven progress model or strict feasibility semantics. See `docs/J0_AICCC_CORE_FREEZE.md`.

## Changes, limitations, and handoff

- Files modified: this report and a short addition in the top AICCC section of `CURRENT_STATUS.md`. Historical status content is preserved.
- No implementation defect was exposed by the executed tests, so no source, test, mathematical contract, profile, or experimental artifact was changed.
- No blocker for basic validation. The two historical-cache tests remain unrun; this is not a claim that unrestricted full discovery passed.
- Decode blocking remains `active-prefill-full-service-recovered-assumption`, without a new theoretical claim.
- No HELIX execution was run, and **no HELIX formal experiment was run**.
- **No journal semantic extension was implemented**.
- **No Stage 6B evidence was reused as AICCC evidence**.
- No capacity matrix, profile stress, formal experiment, manuscript work, automation, process resumption, or PR merge was performed.

AICCC mother evaluator foundation is ready for the next semantic-extension stage.

The next stage may study journal TTFT / TPOT ledger semantic extensions while preserving the evaluator type. It was not started in this session.
