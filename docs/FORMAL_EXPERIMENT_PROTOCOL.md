# Formal protocol FI-JB1-v1 — frozen before held-out outcomes

Research question is fixed: judgement reliability → sampled capacity error → decision transfer → controlled profile mismatch. This is a simulator-relative assessment, not a new optimizer.

## Baseline gate and separation

Use JB1 (`src/journal_baseline.py`), whose exact SHA256 is frozen in `config/formal_protocol.json`. BASELINE_IMPLEMENTATION_AUDIT documents the missing final source and the published-edge conflict. Stage1 results stay exploratory; neither their labels nor their candidate-specific grids are primary journal evidence. All formal evaluator verdicts are recomputed.

Exploration includes stage1 seeds0/7/19, all recovered paper seeds0/1/2/3/7/19, and the paper2 seed0–19 replay. Held-out seeds101–106 and six distinct arrival windows below are generated before any reference outcome. Selection is not based on resulting model errors.

## Bounded workload and topology matrix

Six workloads: (seed,3-second-bin offset,duration): (101,60,30), (102,300,120), (103,500,30), (104,700,120), (105,900,30), (106,1100,120). Use the pinned Azure-derived paired length/count pipeline. Global count scaling target=.5 requests/s, reduced from the exploratory1.5 to bound CPU simulation cost while retaining longer120s traces. No per-window renormalization, output truncation, or prompt clipping. Publish actual request count, input/output statistics, fraction of prompts≥1500 tokens, count-bin CV and interarrival CV; do not attach unsupported “smooth/bursty/long-heavy” labels.

Primary heterogeneous matrix: all six workloads ×two SLA regimes ×five shifts =60 configurations. Alternating L4x2/T4x4 device groups; same80 layers and inherited40GB per-stage controlled limit. Workloads101/104/105 use fast1.25GB/s;102/103/106 use slow312.5MB/s. Both durations occur under both links. This is an incomplete design, not a fully crossed factorial; do not interpret marginal link/duration differences causally. The assignment was corrected before any held-out reference outcome and before the freeze commit to avoid perfect duration/link confounding. Two anchor workloads101/102 additionally run shift0 on the opposite link under both SLAs (four configurations), providing a limited within-workload link control. No broad independent bandwidth/duration-effect claim is allowed.

Heterogeneous SLAs: TTFT5.2s, TPOT.30s (Decode-tight); TTFT5.2s, TPOT10s (Prefill-oriented). The larger TTFT than stage1 accommodates long prompts plus slow-link serialization, fixed before outcomes. Report actual first limiting metrics rather than assume labels imply the observed mechanism.

A100 uniform controls: six workloads ×two SLAs =12 configurations, using each workload's primary link. SLAs (2s,.15s) and (2s,1s). The latter is called relaxed-Decode, not automatically Prefill-tight. Total76 configuration/regime rows;14 physical workload/topology groups (6 heterogeneous main,6 A100,2 opposite-link anchors). Workload, pipeline, profile and code fingerprints are stored. No new model or candidate family is added.

## Shared-grid rule for RQ1–RQ3

Each physical group uses a single load grid for **all its candidates, both SLAs, and both E/R models**. Start with [.001,.004,.016,.064,.256,1.024,4.096,16.384,65.536]. If a lowest endpoint is unsafe, add common lower probes down to.0000625; this tests sparse arrival behavior without labeling intrinsic infeasibility as a missing run. If any highest endpoint is safe, double the common upper endpoint, at most262.144. Endpoint rules inspect both models/regimes and never stop merely at the evaluator boundary.

For each refinement round, take the union of every adjacent verdict-change interval for any candidate, regime or model. Where upper/lower−1>.025, add the geometric midpoint to **every** candidate/regime. Up to six rounds and128 common loads. If the cap would be exceeded, add the largest log-width intervals first, breaking ties by lower endpoint; candidates still receive exactly the same selected loads. Record unresolved resolution explicitly. Never refine only the winner or only one candidate. This is a frozen adaptive design; point counts are not independent random samples.

Always retain full sequences, unsafe→safe reversals, all-unsafe cases and right censoring. Report largest observed safe and nearest observed unsafe above it. A single transition bracket requires sampled monotonicity and both sides; it is not a continuous capacity bound. RQ2 signed gap is Emax−Rmax and relative gap=(Emax−Rmax)/Rmax; also retain flags and sequences. If one model has no safe probe or right censoring, numerical differences are descriptive only and cannot be treated as precise capacity error.

## RQ1 outputs

Per paired point: case/workload/partition/SLA/link/intensity; E/R verdict; first E violations including side/time/concurrency; R maxima for aligned/native TTFT and per-iteration TPOT; fraction of requests violating either SLA; maximum normalized excess and separate TTFT/TPOT excess; complete drain/error status; code/workload/partition/profile fingerprints; E/R runtime and cache key. Confusion totals include all successfully paired points; failed/missing/timeout counts are separate denominators. Export raw.csv, summary.csv and summary.json in rq1_reliability.

## RQ3 decision metrics

Use the complete shared refined grid, five candidates only. Tie-break by smallest absolute shift then negative shift. Reference-best means best in this exact tested set/grid. Report selected shift, best sets, tied ranks (competition rank), normalized quality, intensity regret, best-to-runner-up gap, Spearman correlation with average tied ranks (undefined if constant), and whether nominal E selects a reference-best member. No-safe-output cases abstain; all-zero scores are not credited as successful selection. Failed or unresolved cases remain visible.

## RQ4 and mitigation

Freeze nominal reference histories. Evaluate Prefill/Decode/Both underestimation of5/10/20%, plus L4x2-only10% on heterogeneous groups. Recompute confusion/capacity/ranking using the same nominal shared grid; mark stress boundaries censored/unresolved rather than extending only favorable variants. No Monte Carlo/noise-distribution inference.

Practical strategies: E-only; fixed25% compute inflation;20% uniform capacity derating (floor to a tested load, then report its verdict); four scenarios (nominal,P×1.25,D×1.25,Both×1.25); selected-point reference validation; selected-partition boundary validation with at most five queried points. Run nominal and Both−10% supplies. Selected-point validation abstains on failure. Boundary validation starts at the chosen point and tests adjacent common-grid points according to a fixed down-on-failure/up-on-success rule, returns only a queried safe point. No algorithmic novelty is claimed. Count E/R calls, unique physical reference queries, usable validated intensity, regret, errors and abstention; do not call rejecting everything effective mitigation.

## Runtime, mechanism and quality gates

Reference simulation may run in eight CPU workers; runtime fields from these runs are observed component costs, not controlled sequential speed ratios. After the matrix, run a small sequential warm-up/repetition timing check on predeclared short/long workloads101/102, shift0 and a selected valid grid point, with10 E and3 fresh reference repetitions. Report medians and hardware/conditions. Total campaign elapsed time and summed physical simulation time are distinct.

Mechanism selection is outcome-based and explicitly explanatory: at least one O,one C,a large capacity-gap stable-winner case, and a decision reversal if present. Rerun selected pairs with detailed E ledgers and actual HELIX request/iteration timestamps. Do not infer exact causal timing from the old adapter's approximate first-violation ordering. Use limited implementation ablations where attribution is possible; otherwise state uncertainty.

Quality checks: exact grids across candidates; fingerprints; duplicate keys; full reference drain; immutable reference under stress; error/timeout/missing counts; censoring; nonmonotonicity; ties; unit conversions; total denominators.600s per simulator attempt; one identical retry allowed after a failure, with both attempts logged. Unresolved failures are not unsafe labels. Any change to this protocol after outcomes requires an explicit amendment/version and cannot silently overwrite prior evidence.
