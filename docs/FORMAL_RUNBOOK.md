# Formal execution and review

Actual inspection history is in `MONITORING_LOG.md`, newest first, with machine-readable evidence under `results/formal/monitoring/`. On each real automatic wakeup run `scripts/formal_healthcheck.py --source scheduled`; user-triggered checks use `--source manual`. The read-only health check records counts, process identity/liveness, scheduler/log age, available memory and detected issues, and never starts/stops experiments. Do not backfill fictitious checks or use ACTIVE configuration as evidence that scheduled execution occurred. Review any reported issues using actual CPU/logs before intervening; a quiet5-minute interval alone does not imply failure.

Current desktop scheduling (supersedes the fixed4 adjustment below): `scripts/formal_run.py --workers 8 --memory-budget-gib 22 --memory-reserve-gib 6`. The user requested acceleration; this enables up to8 tasks with per-workload estimated peak reservations, a live physical/commit-headroom admission guard and rotation across physical groups. Actual concurrency varies with workload size and available memory. The estimator is512MiB +0.30MiB per output token, rounded up to256MiB; it is a scheduling estimate, not an OS memory limit. Inspect `.private/memory_scheduler.json` and the log locations in `results/formal/desktop_resume.json`. Do not start a second driver to fill idle slots. The30-minute heartbeat follows the same settings. See `desktop_scheduler_change.json` for the switch and preserved checkpoint counts.

Windows-native execution is validated as of2026-09-17. In PowerShell set `$env:PYTHONUTF8='1'` and `$env:PYTHONDONTWRITEBYTECODE='1'`, and substitute `.venv\Scripts\python.exe` for `.venv/bin/python`. Reference attempts use killable spawn children when SIGALRM is unavailable, retaining600s/one retry. The postprocessor uses Windows process handles for read-only liveness checks. Preserve LF bytes (`git config core.autocrlf false`) for frozen hashes. See `results/formal/desktop_host_check.json` for the exact14-request migration comparison. This host uses Python3.12.10; no simulation/evaluator semantics or frozen inputs were changed.

Execution-resource adjustment: on the current32GB Windows host use `scripts/formal_run.py --workers 4`. Eight concurrent long traces approached physical/commit memory exhaustion;4 was chosen after this measured resource check. Eight new completed points were retained across the adjustment. This changes scheduling only; retain the frozen protocol file,600s per attempt, retries and every shared-grid stage plan. See `results/formal/desktop_memory_restart.json`. Evaluator-only mismatch/mitigation may still use8 workers, followed by sequential reference timing.

Monitoring update: the desktop heartbeat now runs every5 minutes (superseding earlier30-minute references). Healthy checks should only inspect stage, process activity, queue, errors and saved progress; remain quiet and avoid repeated tests/analysis/commits. A5-minute gap in output is not a failure: attempts still allow600s and one retry. The chained postprocessor polls matrix exit every30 seconds independently.

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
