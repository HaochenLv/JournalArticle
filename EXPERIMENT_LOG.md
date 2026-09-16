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
