# Experiment log

## 2026-09-17 — Source and environment

Fetched the two conference repositories without changing their main checkouts. Initial commits and clean states are recorded in docs/CODE_REUSE_AUDIT.md. Retrieved exact public experiment-branch snapshots into ignored `.deps`. HELIX pinned at 8639497. Python 3.12.14, arm64 host, CPU simulation; dependencies in requirements.txt.

## R1 — Minimal paper-1 recovery

Question: do public progress/reference paths reproduce the paper's essential numerical observations?

Command: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/reproduce.py paper1`.

Result: isolated 2051-token request: uncorrected ledger 1.8940402816 s and SAFE; accounting-only ledger 2.0158229367 s and UNSAFE; HELIX aligned TTFT 2.0151050770 s and UNSAFE. Original/corrected progress hashes agree. Output length 1 is used for the isolated Prefill check; the old held-out request had 143 output tokens, which does not change its Prefill latency. At seed 7, 17 requests, lambda .01 both safe; .0131 evaluator/reference both safe; .0132 evaluator unsafe by Decode blocking debt, reference safe with max TPOT .117426 s. Matches the supplied sampled transition.

Files: results/reproduction/paper1.json and content-keyed raw reference runs. This is numerical recovery of specified observations, not a full final-artifact reproduction.

## R2 — Paper-2 exact public implementation

Command: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/reproduce.py paper2`.

One 120 s seed-7 window, 133 requests, five shifts, two original SLA regimes. Decode largest sampled safe .03125 with ties -2,-1,0; local search chooses 0. Prefill best -1 at .535156 vs uniform .523438. All ten candidate/method rows match the cached phase13 seed-7 rows. Frozen workload checksums verified. Results in results/reproduction/paper2_seed7.

## Engineering notes

An initial script-write command used an extra repository directory prefix and was corrected before experiments. A stdin-based multiprocessing launcher failed under macOS spawn; replaced with a guarded script entry point. Neither failure changed input repositories or experimental semantics. Failed setup logs remain private, outside published results.

## D1 — Nominal paired grids (running)

Six cases: seeds 0/7; slow and fast Decode-constrained pipelines (2 s/.15 s); slow Prefill-sensitive pipelines (2 s/1 s). The same 30 s generated window and nominal A100 tables are supplied to both models. Fixed grid .006–1.28, followed by two local midpoint rounds wherever **either** model changes verdict. Retain every probe and report safe islands; do not force binary-search monotonicity. Raw reference metrics are saved incrementally.

## V1 — Validation suites

Public evaluator-branch suite: 31/31 tests pass. Public partition revision suite: 42/42 tests pass. The first partition invocation used the journal working directory and failed relative config paths; rerunning from the **exported** snapshot's directory resolves this without modifying the old repository. New bridge suite: 6/6 tests pass (profile equality, accounting trajectory invariant, reported seed-7 edge, nonmonotonicity guard, cache fingerprints/completion/verdict recomputation, exact paper-2 stored rows).

Additional nominal cases are predeclared to separate limiting phases: seed19 original Decode regimes on both placements, plus seeds0/7 with TTFT 1.8 s and TPOT 10 s. The earlier TPOT 1 s cases retain their historical `prefill` filename but are actually **relaxed-Decode** diagnostics when the reference violation is TPOT; do not relabel their failures as TTFT failures.

## D2 — Matched-profile partition diagnostic (running)

Question: does capacity ranking transfer to the reference when workload, partition, network, and **absolute** device profiles agree? Five shifts [-2,-1,0,1,2], alternating L4x2/T4x4, fast links, 30 s windows. Nominal isolated seed-7 maximum Prefill plus intrinsic charge is 3.68–3.79 s and singleton Decode .2112–.2368 s, so the conference's analytical-model .28 s TTFT cannot be reused meaningfully. New diagnostic SLAs are (4.2 s,.30 s) and (4.2 s,10 s), selected before ranking results. These are controlled simulator tests, not a reproduction of the conference's absolute capacities. The first group-profile reference smoke runs successfully. Cost about 16 s per 17-request simulation under concurrent diagnostic load.

## R3 — Additional provenance checks

All 12 published evaluator transition endpoint pairs (six seeds × two placements) match the recovered implementation. The paper-2 revision's 20-seed, nine-shift top1 coarse-to-fine outcomes also reproduce: Decode 20/20 exact and near; Prefill 16/20 exact and 19/20 near. This checks the final reported search suite rather than relying only on the older phase13 snapshot.

## D3 — Preliminary guard result and branch stop

On the first completed six nominal cases (98 paired probes), four-scenario checking has the same accepted/reference-safe counts and optimistic counts as fixed 25% compute inflation: at nominal inputs 0 optimistic and 17 accepted/reference-safe points; with both profiles underestimated by 10%, 8 optimistic and 24 accepted/reference-safe points. Therefore **stop developing a more complicated scenario method** on the basis of these data. Both are conservative at nominal input and neither resolves structural mismatch under all stresses. Final aggregate is regenerated after the full declared matrix, so do not combine this interim denominator with the final one.

## D4 — Nonmonotone and conservative reference behavior

Seed19, slow links, original 2 s/.15 s SLA: reference unsafe at .01625, safe at .0175, unsafe at .01875. No single reference transition is valid. Fast links remain reference-safe at .04, while the published evaluator transition is .0152–.0153. Safe-point recovery is meaningful; an inferred safe **prefix** is not certified.

## Engineering — Threshold-only reference reuse

The simulator never reads TTFT/TPOT thresholds until all requests finish. Seventy-nine independently simulated pairs with identical physical inputs and different thresholds had **exactly identical per-token metrics**. A new cache layer therefore reuses complete physical outcomes across threshold-only changes and reapplies the pinned adapter's classification/first-violation logic. Fixed/queue overhead remains part of the physical key because cached metrics include it. Eight bridge tests pass, including recomputation against independent prior runs. Records mark `derived_from`; planning comparisons count unique physical queries within each fixed-SLA trial, and inherited runtime is explicitly a replay cost estimate. In-progress drivers were restarted from saved caches to avoid redundant simulations; no conference repository or HELIX simulator source was changed.

## D5 — Reference-call pilot

An offline query-counted pilot compares evaluator only, reference exhaustive on a fixed coarse grid, a fixed reference grid, evaluator-seeded equal allocation, and evaluator-seeded best-first allocation. It returns only directly queried reference-safe operating points, with abstention if none is found. Returning validated points is a construction rule, not a probabilistic guarantee. On initial completed cases, best-first does not beat simpler equal allocation, so no advanced allocation claim is justified. Finer-grid and held-out validation remain necessary before publishing method superiority.

## D1 completed — Nominal sign and reference boundaries

All ten nominal A100 cases now include reference-unsafe probes. Original Decode SLAs show both matching and conservative classifications; relaxed-Decode TPOT=1 s shows nominal optimism (seed0 evaluator safe maximum .8 versus observed reference-safe .0325; seed7 .04 versus .0132). TTFT-sensitive (1.8 s,10 s) cases show substantial conservatism: seed0 evaluator safe maximum 3.2 versus reference 40.96, next unsafe 51.2; seed7 1.28 versus 12.8, next unsafe 15.36. These are intensities of **17-request finite traces**, not sustained production rates. Larger intensity compresses a finite arrival window. Seed19 slow's nonmonotone sequence prevents reporting a single reference edge.

The initial range was explicitly extended after reference right censoring, first to 10.24 and then until unsafe (maximum tested 81.92). No profile was changed in D1. All rows, first disagreements, next unsafe probes where valid, TTFT/TPOT metrics, and native-definition sensitivity counts are in nominal_summary.json/csv. This supports a mixed nominal reliability conclusion for the recovered implementation; it is not an accusation that an unavailable final implementation has identical behavior.

## D2/D6 completed — Final matched-profile and stress matrix

Twenty heterogeneous candidate cases completed on the shared 19-load base grid plus four local refinement rounds: 502 paired probes, all cases include reference-unsafe points, no right censoring. Nominal counts are 0 optimistic / 68 conservative. In each of four seed/regime trials, the nominal evaluator-selected candidate is reference-best in the refined sampled set. Prefill scores differ substantially despite winner agreement: seed0 shift1 E=2.755, R=12.76; seed7 shift1 E=1.2325, R=4.205.

`profile_mismatch.py` completed 7,282 rows: 175 A100 points ×10 variants, 502 heterogeneous points ×11 variants, and ten isolated controls. Zero exceptions/event-budget failures. A100 optimistic counts: nominal13, Prefill −20%20, Decode −20%26, Both −20%31. Reference cache keys are invariant across each case/load's variants. The 20,000-event resource guard never activates on the published matrix; an exception is recorded separately, never classified as unsafe.

On candidate-specific refinement grids, six of40 nonnominal trial/variant choices differ from nominal and have lower sampled reference quality: seed0 Prefill changes to shift2 under Prefill/Both −10%/−20% (90.91%); seed7 Decode changes to shift0 under Decode/Both −20% (96.43%). This is a resolution-sensitive screen, not a stable ranking-error estimate. The identical common19 grid yields reference-best choices for all44 combinations including nominal, because ties conceal smaller differences. Both views are saved. A common finer grid is required before publishing reversal claims.

## D3 completed — Simple guards

All175 nominal A100 probes: fixed25% compute inflation and finite-four-scenario checking both yield O=0, accepted/reference-safe=32 under nominal profiles; under Both −10%, both yield O=8, accepted/reference-safe=54. No scenario-method benefit appears. Fixed10% compute margin gives O=8/15 and validated accepted58/73 for nominal/biased input respectively; 10% capacity derating gives O=11/13 and validated accepted58/60. These are discrete point counts; per-case validated-load ratios are separately saved. Stop scenario optimization.

## D5 completed — Strong baseline falsifies initial primary direction

Common-grid query-counted replay includes fixed sampling, reference-only adaptive, reference-only bisection across candidates, reference-only bisection concentrated on uniform, E-seeded equal allocation, best-first, E-only and exhaustive. Heterogeneous exhaustive=5×19=95 calls per trial. E-seeded equal allocation reaches all four coarse-grid optima with10 reference calls, best-first ties it. However **uniform reference-only bisection reaches all four with5 calls**, without95 evaluator scores. At B=5 E-seeded quality ratios are [1,.25,1,.5] for seed0 Decode/Prefill and seed7 Decode/Prefill. This control invalidates a claimed new allocation advantage on present evidence. It does not prove uniform partition optimal on the finer sampled sets.

Decision: change the preferred direction from provisional budgeted planning to **reference-grounded capacity/decision reliability assessment**. Budgeted planning is the sole conditional backup, only if stronger held-out/common-fine-grid comparisons support it. No new complex method is added to evade the negative result.

## Final verification and scope

All30 diagnostic cases,677 paired probes,7,282 stress rows,304 policy/baseline replay rows,678 raw reference records are checked by `verify_results.py`. Eight bridge tests pass after the final policy additions, including raw verdict recomputation and exact threshold-only reuse. Three PNG/SVG figures were rendered and visually inspected. Both old repositories remain at their initial HEAD with empty status; `repository_state_end.json` equals the start record. Earlier headings marked running/preliminary are retained as dated experiment history; this completion record and CURRENT_STATUS supersede them.

The final paper-1 source/40-test bundle remains unavailable publicly. No final-artifact regression total is claimed to have been rerun. All new conclusions are explicitly tied to the recovered implementation and pinned reference. Held-out tests, finer common grids and controlled sequential timing are planned publication work.

## Stage2 baseline gate — manuscript/source conflict

Created independent fresh mirrors under ignored dependencies and inspected reachable history, PR refs, deleted/moved files and Actions artifact metadata. Built JB1 from the manuscript's raw-compute progress and pre/post-check contract, retaining declared public blocking and activation-memory recovery assumptions. The2051-token ledger observation and24 accounting-only trajectory pairs reproduce. The published edge pairs do NOT reproduce under raw-compute progress (0/12); adding only the legacy5ms overhead back to progress restores12/12. Full3,864-point evaluator grid replay is retained. Ten semantic tests plus eight bridge tests pass. No formal sweep starts before this distinction and the protocol are frozen.

## Stage2 protocol frozen

FI-JB1-v1 is frozen before held-out reference outcomes. Six new seed/window pairs,30/120s traces, global source-count scaling target.5, five-shift heterogeneous comparisons, A100 controls and two opposite-link uniform anchors give76 configuration/regime combinations. Common grid refinement uses union transitions across all candidates and both SLAs, targeting2.5% relative brackets with finite caps.22 pre-run tests pass. Per user steering, historical archaeology is closed; missing historical artifacts are documented limitations and do not block new evidence.

## Stage2 execution and first mechanism check — running

Changed CPU scheduling from one process per physical group to eight shared point workers. Existing points and per-stage frozen plans are resumed unchanged. Eight potentially interrupted probes are recorded in `results/formal/execution_restart.json` and must appear in the final completeness audit. This is an execution-only change, not a changed grid, workload, SLA or reference model. Long reference traces remain fully drained.

Prepared RQ1–RQ4 analysis, six simple mitigation replays, event tracing, quality checks and post-matrix sequential timing. All22 tests still pass. A storage-only reference experiment matched two complete metric sets, but showed no established speed benefit under uncontrolled contention; it is not used by the formal runner.

First explanatory trace: h105/A100/fast/intensity4.096/relaxed-Decode. JB1 rejects from full active-Prefill blocking debt1.547523s; the reference's maximum TPOT is.945950s against1s. Full instrumented metrics exactly equal the original reference record. The comparison and local arithmetic, with attribution limits, are in MECHANISM_ANALYSIS. No aggregate reliability or decision-transfer conclusion is drawn from incomplete groups.

## User-requested pause for desktop transfer

Stopped the laptop's matrix coordinator, eight workers and waiting postprocessor; the temporary idle-sleep assertion exited with the postprocessor. Paused the thread's automatic follow-up.195 physical reference runs /390 paired SLA points are saved;0 recorded failed points. Unfinished planned probes remain explicit and have no assigned outcome. `machine_handoff.json` records all pre-transfer cache keys and the laptop environment, so mixed-machine runtime provenance remains recoverable. Added `HANDOFF_TO_DESKTOP.md` with environment setup, resume instructions and the remaining research deliverables. Made process startup explicitly spawn on all platforms and made runtime hardware metadata portable to Linux; neither change modifies baseline semantics. No new research computation was started after the pause request.

## 2026-09-17 — Desktop intake verified; Linux environment pending

Cloned handoff commit97c38c6 on the Windows destination and fully read the handoff, status, formal protocol and runbook. WSL reports that the Windows Subsystem for Linux is not installed (exit50), including outside the sandbox. Requested confirmation for installing the required system components; no Windows-native runner was started.

The initial Windows Git checkout converted text to CRLF, changing the frozen baseline's byte hash. Set repository-local `core.autocrlf=false` and restored only pristine files whose bytes differed solely by line endings to the exact Git archive bytes. JB1 again hashes to the frozen4f186748f3fb5940179e833ffe68cf463bb8b9d1dbbd16926490062065669b15; no baseline source, workload, protocol or saved result changed.

Standard-library data inspection verified all6 workload fingerprints, all874 pre-transfer cache input hashes and complete drains,14 group protocol/profile/workload fingerprints, unique saved point identities, and exact unfinished stage plans. Recomputed reference verdicts and TTFT/TPOT maxima from saved per-request metrics for all390 SLA pairs belonging to195 physical points;0 failed points. This is archive integrity verification, not a fresh simulation or cross-machine numerical-equality experiment. Record: `results/formal/desktop_intake.json`. Linux dependencies/tests, the short fresh reference comparison, eight-worker continuation and all post-matrix research deliverables remain pending. No desktop runtime measurements exist yet.

## 2026-09-17 — Native Windows compatibility and exact migration comparison

At user direction, investigated native Python instead of installing WSL. Installed pinned public snapshots and requirements in repository-local ignored directories. Fixed HELIX clone line-ending configuration. Added an execution-only spawn-child deadline for Windows (600s and one identical retry unchanged), safe Windows process-handle liveness checks for the postprocessor, Windows physical-memory metadata, and machine-origin labels on new rows/analysis exports. POSIX SIGALRM execution remains available. Extended public preflight to reject personal Windows paths. Frozen JB1 and FI-JB1-v1 inputs are unchanged.

All25 tests pass (22 existing plus3 execution portability tests). Windows AMD64/Python3.12.10,20 logical CPUs and34164097024 bytes physical memory. The fresh h105/A100/fast/shift0/intensity4.096 reference fully drains14 requests in18.1346s including spawn overhead. All per-query metrics and final simulation time equal the original macOS/Python3.12.14 cache exactly. Both SLA reference summaries and evaluator outputs, excluding runtime fields, also equal saved values. The cache is byte-identical afterwards. Decode verdicts E=false/R=false; relaxed-Decode E=false/R=true. This is the single required migration check, not a historical campaign rerun or a sequential speedup benchmark. Evidence: `results/formal/desktop_host_check.json`; reproducible check: `scripts/formal_host_check.py`. WSL is no longer a prerequisite for this runner.

## Desktop continuation — execution-resource adjustment

Started the shared queue and chained postprocessor on native Windows. Eight concurrent long traces approached the32GB host's memory limit (414580KiB free physical and1066892KiB free virtual/commit space at inspection). The first8 new reference points completed successfully and were saved. Terminated the verified matrix tree and waiting postprocessor before resource exhaustion, retained all caches and stage plans, and resumed with `--workers 4`. This explicitly documented execution-resource adjustment leaves all scientific inputs, timeout/retry rules and grid refinement unchanged; it is not a new experimental protocol. Unrecorded interrupted probes receive no verdict and may be recomputed. Original195 rows are exactly equal to the handoff commit;203 physical points/406 SLA pairs are saved with0 failures at restart. New PIDs and timestamps are recorded in `results/formal/desktop_resume.json`; memory observation in `desktop_memory_restart.json`. Postprocessing will start only after all groups complete; formal sequential timing remains after all parallel reference work.

Requested a30-minute Codex follow-up for remaining research review/reporting, but automatic approval review rejected creating persistent automation without explicit user confirmation. Confirmation is pending; no periodic task was created. The already-authorized matrix and chained numeric postprocessor remain active. Completion of those numeric steps will still require the mechanism review and14-section evidence report.

## Desktop automatic continuation authorized

The user explicitly approved automatic continuation after the earlier approval-review rejection. Created the active30-minute heartbeat `JournalArticle 主机第二阶段续跑` (id `journalarticle`) on the current desktop task. It must reuse existing drivers and caches, keep reference concurrency at4 on this32GB host, retain failures and incomplete plans, complete the numeric workflow and research review/14-section report, run public preflight before milestone commits/pushes, and pause after completion. No laptop task was resumed and no duplicate matrix was launched. Process/record inspection shows373 saved physical points/746 SLA pairs,0 recorded failures; all14 groups still need completion of their common-grid refinement. Both matrix and waiting postprocessor are alive. No completed point was requested again.

## User-requested acceleration — memory-aware concurrency

The user explicitly requested higher parallelism after observing20% total CPU utilization. Live sampling confirmed four reference children each used roughly one logical core on the20-logical-core host. Replaced fixed4 dispatch with a maximum8-process pool governed by a22GiB estimated memory budget and a6GiB live physical/commit-headroom admission guard. Cost is512MiB base +0.30MiB per frozen workload output token, rounded up to256MiB. Reservations account for future event-archive growth rather than only current RSS. A group-rotating queue can admit short jobs while a large queued job does not fit. These estimates are execution heuristics and must be monitored; no hard memory-bound or controlled speedup claim is made. The simulator/storage/model implementation is unchanged, including disabled optional compact storage. All28 tests pass, adding budget/fairness, low-headroom recovery and exception-release tests.

Before switching, saved530 existing rows in a private snapshot. Shutdown retained531 rows, including one final completion. All snapshot rows and the original195 handoff rows are exactly equal after shutdown; only unrecorded in-flight attempts may be recomputed. Restarted one matrix and one waiting postprocessor with new PIDs; new command/logs recorded in `desktop_resume.json`, scheduling rationale and source hashes in `desktop_scheduler_change.json`. Updated the existing active30-minute heartbeat instead of creating another automation. Freeze hashes, common stage plans, timeout/retry rules and final sequential timing requirements remain unchanged.

## Follow-up interval reviewed and reduced to5 minutes

At user request, reviewed monitoring latency against live progress. At inspection,690 physical points were saved,0 failures,5 of14 groups complete.495 fresh desktop reference calls have access-wall median18.5702s,p90=48.2609s,max=110.9127s; these are descriptive execution-health statistics across the desktop campaign, not controlled speedup measurements. Recent output was9.4s old. Thirty minutes is unnecessarily slow for detecting a stopped process or picking up final research review while the new scheduler is being monitored. Updated the existing active heartbeat to5 minutes, preserving its research scope and quiet-on-no-action policy. Healthy checks are lightweight; no repeated tests/analysis/commit are required each time. Lack of output for5 minutes alone does not justify restarting: preserve600s attempts plus one retry and inspect actual process activity/stage. The existing postprocessor polls matrix exit every30 seconds, so numeric pipeline handoff never depended on heartbeat cadence. No experimental process or input was changed.

## User-visible evidence that a check actually ran

The user asked how to verify inspections. Recent visible task turns showed user-triggered checks and enabled scheduling, which is not proof of actual scheduled execution. Added `scripts/formal_healthcheck.py` to record actual read-only inspections in `MONITORING_LOG.md` and `results/formal/monitoring/checks.jsonl`/`latest.json`, explicitly distinguishing manual from scheduled triggers. The first real entry at14:28:04 Beijing is manual:860 saved physical points,1720 SLA pairs,0 failures,5/14 complete groups,8 active jobs; expected driver/postprocessor identities are alive and no issue was detected. The heartbeat prompt now requires creating a scheduled entry only when it actually wakes. No past execution history was invented, and no experiment was restarted or repeated to produce monitoring evidence.

## Desktop parallelism adjustment (2026-09-17)

User requested greater CPU/memory utilization. Raised the matrix admission ceiling from8 to12 and reservation budget from22 to24GiB, retaining6GiB live physical/commit headroom and unchanged workload cost estimates. Verified all1007 previously saved rows and saved stage plans exactly unchanged; reused caches and resumed only unfinished points. Execution-resource amendment only: frozen scientific inputs,600s deadline/one retry,8-worker postprocessing and sequential formal timing remain unchanged. Initial four host samples showed40-63% CPU,5-7 active jobs and7.54-14.76GiB free commit; long tasks still limited admission, so no claim of12 simultaneous jobs or measured speedup. Evidence: results/formal/desktop_parallel12_change.json. The5-minute heartbeat and current PID/log manifest were updated.

## Desktop matrix complete (2026-09-17)

All14 groups completed with1634 physical points/3268 SLA pairs and0 failed points. Exact preservation of195 inherited rows and common grids across all candidates was verified; frozen baseline SHA remains intact. RQ1 totals before comprehensive quality verification:953 both-safe,1879 both-unsafe,23 optimistic and413 conservative pairs. The postprocessor observed matrix exit at08:00:17 UTC and generated RQ1-RQ3 summaries; mismatch analysis continues. Mitigation, full quality checks, figures, sequential desktop timing, mechanisms and final report remain pending. Evidence: results/formal/desktop_matrix_complete.json.
