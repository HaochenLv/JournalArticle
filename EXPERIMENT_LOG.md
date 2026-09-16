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
