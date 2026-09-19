# J0 — AICCC mother-evaluator core freeze

Date: 2026-09-19 (Asia/Shanghai)

Status: **FROZEN FOR JOURNAL EXTENSION**

## Frozen research object

The Future Internet journal line uses the rebuilt AICCC accounting-only, event-driven evaluator as its only mother evaluator. J0 freezes the following chain:

```text
profile-driven request progress
    -> SLA/accounting ledger
    -> residual network time
    -> per-link time allocation
    -> per-link required bandwidth commitment
    -> shared-link / memory / SLA feasibility
```

The frozen core does not advance request progress with network serialization and does not classify workload safety with a post-hoc 90% attainment rule.

## Frozen implementation checkpoint

- Branch: `aiccc-journal-rebuild`
- Branch origin: `main@bfb4e002be2a079fc6dade5cf1d07d9c00b71bb0`
- Last J0 core source/test hardening commit: `0d3e4b1a61cfd5ce48bf068dff12fd1481a47b2e`
- Tested branch head: `b411bfcb29c08b71816b7570cb0e28b449108850`
- CI-only commits after the core hardening do not change the evaluator mathematics or tests.

Key frozen files:

- `src/aiccc_math.py`
- `src/aiccc_evaluator.py`
- `tests/test_aiccc_math.py`
- `tests/test_aiccc_evaluator.py`
- `config/aiccc_journal_contract_v1.json`
- `docs/AICCC_JOURNAL_CONTRACT.md`

## Validation evidence

GitHub Actions self-hosted validation:

- Workflow: `AICCC Self-Hosted Tests`
- Run ID: `35412992314`
- Attempt: 2
- Runner: `journal-win`
- Python: 3.12.10
- AICCC math: **5/5 passed**
- AICCC evaluator: **13/13 passed**
- Failures/errors: **0**

The run was intentionally scoped to the active AICCC core. It did not run HELIX simulation, formal matrices, capacity sweeps, Stage 6B experiments, or journal semantic experiments.

## Invariants frozen at J0

1. Prefill and Decode progress are driven by profiling, not by the SLA threshold or accounting-only charges.
2. Residual SLA/network time is computed before network commitment.
3. Per-link allocation follows the frozen `omega -> delta -> b_req` chain.
4. Concurrent requests aggregate required bandwidth on shared physical links before comparison with link capacity.
5. Memory feasibility is checked alongside SLA/network feasibility.
6. Any checked constraint violation makes the workload unsafe; there is no attainment-threshold escape hatch.
7. Tied events are processed atomically and simultaneous first violations may all be retained.
8. Fractional Decode progress survives unrelated events.
9. `decode_block_size` is a runtime recomputation-granularity parameter. The default 16 is compatibility only, not a mathematical constant.
10. Decode blocking remains explicitly labeled `active-prefill-full-service-recovered-assumption`; it is not promoted to a theorem.

## Change-control rule after J0

J1 and later journal work should be additive. Standard-TTFT and request-average-TPOT semantics may change the **ledger horizon/accounting policy**, but they must still feed the frozen residual-time-to-bandwidth-commitment chain.

A proposed change to `src/aiccc_math.py` or to the progress/event semantics in `src/aiccc_evaluator.py` is therefore a **core change**, not an ordinary J1 extension. Such a change requires an explicit rationale, contract update, new regression coverage, and a new freeze checkpoint before it can be used as journal evidence.

Historical JB-Avg-v1 / Stage 6B code and results remain provenance only and are not J0 evidence.
