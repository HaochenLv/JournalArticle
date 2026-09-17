# Formal execution and review

The baseline and protocol are frozen. Do not resume historical-source archaeology. All commands run from JournalArticle with Python3.12 and pinned dependencies installed by `scripts/bootstrap.py`. Keep the original conference repositories read-only.

## Existing campaign

Before starting a process, inspect whether `scripts/formal_run.py` or `scripts/formal_followthrough.py` is already running. Do not run duplicate drivers. The active driver uses eight shared point workers; each group has one coordinator writing atomic snapshots. Completed rows and saved stage plans are resumed from `results/formal/groups`. An interrupted probe has no verdict until successfully recorded. The initial scheduling restart is listed in `results/formal/execution_restart.json`.

`scripts/formal_followthrough.py --wait-pid <matrix-driver-pid>` waits for that process to exit, requires all groups to be complete, then executes the analysis, stress, mitigation, verification, figures and sequential timing commands below. Its status is saved in `results/formal/execution_workflow.json`; detailed local execution logs are ignored under `.private`. The status `computed_pending_research_review` means numeric processing is finished, not that the research report is complete. Matrix start predates this workflow's start timestamp, so their elapsed times must not be conflated.

## Resume / reproduce

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/formal_run.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/formal_analyze.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/formal_mismatch.py --workers 8
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/formal_mitigation.py --workers 8
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/formal_verify.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/formal_figures.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/formal_timing.py
```

The first command must finish before the following ones are used as complete evidence. The analysis/stress/mitigation scripts accept `--partial` for explicitly incomplete diagnostics; these are not a substitute for the final matrix. Sequential timing must run after parallel reference jobs stop. Failed rows are preserved and never silently removed or reclassified; any recovery procedure must retain their attempt records.

Optional explanatory tracing reruns the same physical input with read-only runtime instrumentation. Every per-query metric and final simulation time must exactly match the cached nominal reference. The first conservative example is:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/formal_trace.py --group h105-o900-d30-a100-fast --intensity 4.096 --regime relaxed_decode --name conservative_h105_a100
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/formal_trace_figure.py conservative_h105_a100
```

The optional `reference_storage.py` diagnostic is **not enabled** in formal execution. Its two metric-equality checks do not establish a speed benefit under controlled conditions.

## Research review still required

Review full sequences, all-unsafe configurations, censoring, error logs, common-grid equality, tie handling and stress boundary resolution. Report tested point denominators without interpreting the adaptive grid as a random population sample. Complete optimistic, large-gap/stable-choice and reversal explanations only where observed; distinguish exact rejection arithmetic from causal attribution. Visually inspect figures. Create the14-section Chinese FORMAL_EVIDENCE_REPORT requested in the task, update the status/log/claim documents, run the public preflight, commit/push, and verify original repository HEAD/status. No new optimizer or expanded research direction is authorized by this runbook.
