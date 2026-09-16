# Journal research on SLA-aware LLM pipeline planning

Reproducible diagnosis of an inexpensive evaluator against a pinned HELIX reference simulator, followed by evidence-based journal direction selection. No GPU cluster is required.

Read `JOURNAL_DIRECTION_REPORT.md` for the decision, `CURRENT_STATUS.md` for execution state, and `EXPERIMENT_LOG.md` for evidence. Source/version and metric audits are in `docs/`.

## Reproduce

Use Python 3.12. From this repository:

```sh
python3 scripts/bootstrap.py
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/reproduce.py paper1
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/reproduce.py paper2
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/nominal_gap.py
```

Dependencies are fetched into ignored `.deps/` at exact commits. The two sibling conference repositories are read-only. The bootstrap script does not change them. Existing `.deps` directories are retained; use a fresh clone for a fully clean bootstrap.

Results contain actual finite-grid simulator outputs, not real-GPU measurements. `results/raw_reference` stores compressed input manifests and full per-request metrics returned by the adapter; content hashes permit exact reuse. Evaluator scores, perturbed profiles, and reference verdicts are distinct. No confidence interval is inferred from a deterministic perturbation grid.

The supplied papers, private reviewer material, credentials, caches, and machine-specific paths are excluded from version control. Public code dependencies remain upstream; this repository contains new research wrappers and derived experimental results.
