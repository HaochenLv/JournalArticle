# J1 — Standard TTFT / request-average TPOT implementation and pilot audit

Date: 2026-09-19 (Asia/Shanghai)

Status: **BOUNDED_VALIDATION_PASS; not final journal validation**

## 1. Scope and source boundary

The frozen J0 AICCC evaluator remains the only mother evaluator. Published AICCC semantics use profiling-driven request progress, phase-local SLA residual budgets, and the residual-time -> omega -> delta -> required-bandwidth chain. J1 does not rewrite that evaluator. It adds a second, accounting-only ledger pass whose semantic horizons are standard first-output TTFT and request-average post-first TPOT.

The standard request-horizon formulas in J1 are therefore a journal-extension design, not equations silently attributed to the conference paper.

## 2. Implemented design

Implementation file: `src/aiccc_j1_evaluator.py` (blob `30cd80e8cd276d5756903172ac88e02bfe97d4a3`).

J1 uses two passes:

1. J0 is run with full drain and trace. Profiling alone determines Prefill-to-Decode timing and continuous Decode progress.
2. J1 overlays request-level SLA ledgers on the immutable J0 trajectory. The first Decode-token completion is reconstructed by interpolation inside the relevant J0 interval and is used only as a ledger boundary.

For TTFT, J1 charges the profile-driven arrival-to-first-Decode-token interval, intrinsic Prefill accounting, recovered blocking integrated over Decode progress [0,1], and one fixed/queue charge. Prompt activation traffic plus one Decode-token activation transfer is converted through the unchanged AICCC network kernel.

For output length m>1, average TPOT uses the profile-driven first-token-to-finish interval, recovered blocking integrated over Decode progress [1,m], and (m-1) fixed/queue charges. The network horizon contains (m-1) Decode-token activation transfers. A one-output request has no average-TPOT ledger.

Safety remains strict. Any applicable non-positive residual budget, aggregate physical-link overload, or memory violation makes the workload unsafe. There is no 90% workload-attainment rule and no network serialization is inserted into the progress clock.

## 3. Deterministic validation

GitHub Actions run `35415896706` completed successfully on the Windows self-hosted runner with Python 3.12.10:

| Suite | Result |
| --- | ---: |
| Frozen J0 math | 5/5 |
| Frozen J0 evaluator | 13/13 |
| J1 standard-ledger guards | 9/9 |

The J1 tests cover first-token reconstruction, fixed-overhead placement, exclusion of the first output from average TPOT, m=1 behavior, exact J0 trajectory-hash/final-time parity, Decode block-size independence of first-token semantics under a constant profile, a case where request-average TPOT passes while old phase-local per-token TPOT rejects, integrated recovered blocking, strict safety, and shared-link aggregation.

An independent blob comparison after J1 implementation confirmed that `src/aiccc_math.py`, `src/aiccc_evaluator.py`, the J0 math/evaluator tests, and `config/aiccc_journal_contract_v1.json` are byte-identical to the J0 freeze checkpoint `4630ef7113d425d1af572263e6df0be1c6cc6e60`.

## 4. Pilot protocol and protocol amendment

The pilot is intentionally cache-only. It never invokes the HELIX reference runner.

The first planned 72-point cache-only run (`35415910577`) aborted before producing scientific output because several requested seed/intensity combinations had no cached physical reference. No HELIX job was launched and no result file was produced.

Protocol revision 2 was made before successful outcome inspection. It restricts the pilot to the pre-existing `nominal_gap.py` seed/placement/intensity family: seeds 0, 7, and 19; slow and fast placements; intensities 0.006, 0.010, 0.0131, 0.0132, 0.015, 0.020, and 0.025. This gives 42 physical cases. The amendment is cache-availability driven, not outcome selected.

Each workload contains 17 requests. The SLA is TTFT 2.0 s, TPOT 0.150 s, fixed overhead 5 ms, queue overhead 0. The reference reconstructs standard first-output TTFT and request-average post-first TPOT from existing pinned HELIX records, then applies the same explicit fixed/queue ledger charge used by J1. It does not add the evaluator's intrinsic-H or recovered-blocking approximations to the execution reference.

## 5. Pilot result

Successful run: `35415993230`, head `f4f428a14d7cf7117368146ecacd079327dc43de`. The uploaded artifact was `j1-pilot-v1`, artifact ID `10575582812`, digest `sha256:132d65a273ae23ecafc92d63af0a4861f22a7410a053d2937a94e3df2538ec49`.

The raw-reference cache contained 2,313 files and 2,069 unique physical identities; 244 files were aliases and no malformed records were observed. All 42 revised target points were found. The raw-reference filename fingerprint was identical before and after the run, and the script reports `new_helix_runs = 0`.

| Verdict comparison against strict standard reference | Safe / safe | False acceptance | False rejection | Unsafe / unsafe | Agreement |
| --- | ---: | ---: | ---: | ---: | ---: |
| J1 standard ledger | 35 | **0** | **0** | 7 | **42/42 (100%)** |
| J0 phase-local verdict | 23 | 5 | 12 | 2 | 25/42 (59.52%) |

The seven reference-unsafe cases are all seed 19 on the slow placement, across all seven tested intensities. In every one, exactly one of 17 requests violates standard TTFT and no request violates average TPOT. J1 also rejects all seven. Its first limiting constraint is physical link `slow-0`: required bandwidth is about 313.694 MB/s against 312.500 MB/s capacity (peak utilization 1.003822). For this cluster the maximum J1 standard-TTFT diagnostic is about 2.002682 s and the execution-reference maximum is about 2.002069 s.

Across all 42 points, J1 minus reference maximum standard TTFT ranges from +0.411 ms to +0.677 ms. For maximum average TPOT, the range is approximately -0.059 ms to +8.676 ms. The small negative endpoint matters: this pilot does **not** establish that J1 is a numerical upper bound for every latency metric, even though no false acceptance occurred on this grid.

The median J1 evaluator runtime was about 30.67 ms per workload on the self-hosted Windows runner. This is an implementation-cost diagnostic only, not a controlled speedup comparison against HELIX.

## 6. Audit conclusion

The implementation passes its deterministic semantic invariants and exactly preserves the frozen J0 progress engine. On the bounded pre-existing 42-case cache grid, J1 removes both types of disagreement seen when the old phase-local J0 verdict is compared with standard request-level metrics: five observed false acceptances and twelve observed false rejections become zero and zero.

This result is encouraging but intentionally narrow. The 42 cases cover only three workload seeds, two placements, one 17-request workload length, one SLA tuple, and existing cached executions. They are not an independent held-out validation set, do not test profile perturbation, and do not establish universal conservatism or production safety. The slight negative average-TPOT metric gap is retained rather than hidden.

J1 is therefore accepted as the current **standard-ledger implementation for the next validation stage**, while final journal claims remain blocked on broader reference validation, explicit false-acceptance analysis beyond this grid, and profile-noise sensitivity.

Machine-readable summary: `results/j1/pilot_v1_summary.json`.
Design contract: `config/j1_standard_ledger_v1.json` and `docs/J1_STANDARD_LEDGER_DESIGN.md`.
