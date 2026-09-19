> **Current rebuild branch:** `aiccc-journal-rebuild`. J0 freezes the AICCC accounting-only event-driven evaluator as the only journal mother evaluator. J1 adds standard first-output TTFT and request-average post-first TPOT only as an accounting/ledger overlay on that frozen progress engine. The bounded 42-point cache-only J1 pilot passed with 0 false acceptances and 0 false rejections against the strict standard-metric reference, but it is not final journal validation. `JB-Avg-v1` / Stage 6B remain historical. See `docs/AICCC_JOURNAL_CONTRACT.md`, `docs/J1_VALIDATION_REPORT.md`, and `CURRENT_STATUS.md`.

# Journal research on SLA-aware LLM pipeline planning

**Stage3 evidence frozen (2026-09-17):** [Writing handoff](STAGE3_EVIDENCE_REPORT.md) and [formal evidence report](FORMAL_EVIDENCE_REPORT.md). Legacy sensitivity reuses1634 reference records for3268 judgments; no new reference run. Main line: Yes, but modified. Raw4 strict/2 tie-break mismatches become legacy3/1; decision and operating-point losses are separated. Mitigation is conditional replay on a reference-informed frozen grid.31 tests pass; no further experiments needed for the stated scope.

Reproducible diagnosis of an inexpensive evaluator against a pinned HELIX reference simulator, followed by evidence-based journal direction selection. No GPU cluster is required.

Selected direction: **Reference-Grounded Reliability Assessment for SLA-Aware Capacity and Partition Planning**. Read [JOURNAL_DIRECTION_REPORT.md](JOURNAL_DIRECTION_REPORT.md) for the Chinese decision report, [CURRENT_STATUS.md](CURRENT_STATUS.md) for execution state, and [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md) for evidence. Source/version and metric audits are in `docs/`.

## Reproduce

Use Python 3.12. From this repository:

```sh
python3 scripts/bootstrap.py
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/reproduce.py paper1
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/reproduce.py paper2
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/reproduce.py paper1_edges
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/reproduce.py paper2_revision
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/nominal_gap.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/partition_ranking.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/profile_mismatch.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/simple_guards.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/analyze.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/planning_pilot.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/figures.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
```

Dependencies are fetched into ignored `.deps/` at exact commits. The two sibling conference repositories are read-only. The bootstrap script does not change them. Existing `.deps` directories are retained; use a fresh clone for a fully clean bootstrap.

Results contain actual finite-grid simulator outputs, not real-GPU measurements. `results/raw_reference` stores compressed input manifests and full per-request metrics returned by the adapter; content hashes permit exact reuse. Evaluator scores, perturbed profiles, and reference verdicts are distinct. No confidence interval is inferred from a deterministic perturbation grid.

The supplied papers, private reviewer material, credentials, caches, and machine-specific paths are excluded from version control. Public code dependencies remain upstream; this repository contains new research wrappers and derived experimental results.

## Completed evidence

- `results/reproduction/`: recovered conference observations, environment, old-repository start/end states and validation.
- `results/diagnostic/nominal_summary.json`: ten A100 cases, 175 paired probes, mixed nominal disagreement.
- `results/diagnostic/partition_ranking/`: twenty candidate cases, 502 paired probes, refined and common-grid ranking views.
- `results/diagnostic/profile_mismatch/`: 7,282 evaluator-only stress rows, including nominal controls, zero run errors.
- `results/diagnostic/simple_guards/`: fixed margin, derating and finite-scenario controls.
- `results/diagnostic/planning_pilot/`: query-counted replay including strong uniform reference-only control; no allocation superiority claim.
- `results/figures/`: PNG/SVG scientific figures.

`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/verify_results.py` additionally checks this completed matrix and verifies the two sibling repositories against their recorded start states; it requires those sibling clones at the original commits. The ordinary bridge tests do not require sibling clones. Exploratory results do not substitute for the held-out journal evaluation described in the report.

## Stage 3 reproduction and writing inputs

With the pinned dependencies available, run `python scripts/stage3_evidence.py all`, `python scripts/stage3_report.py`, `python scripts/formal_verify.py`, and `python scripts/stage3_verify.py`. On Windows use `.venv/Scripts/python.exe`; on POSIX use `.venv/bin/python`. Existing legacy group outputs are verified and reused; no command above launches the reference simulator. See `docs/LEGACY_PROGRESS_SENSITIVITY.md`, `docs/DECISION_LOSS_DECOMPOSITION.md`, and `docs/MITIGATION_INTERPRETATION_AUDIT.md`. Stage 2 raw files and protocol remain immutable; figure/report presentation labels are updated separately.
