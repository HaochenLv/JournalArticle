# Baseline implementation gate — stage 2

## Decision and identity

The formal journal baseline is **JB1**, `src/journal_baseline.py`, an explicitly recovered implementation. It is **not** claimed to be the CA final implementation. The stage-1 wrapper in `src/research.py` remains unchanged for historical reproduction. New formal drivers must import JB1 explicitly and record its source hash.

The gate is a specification/provenance decision, not a claim that the missing artifact has been found. No held-out result was used to tune JB1. A significant manuscript-versus-public-code conflict is retained rather than fitted away.

## Source search

Fresh mirror clones were created inside ignored journal dependencies; the original two checkouts were never fetched into or modified. Searches covered branch/tag/PR refs, all reachable commit messages and Python/Markdown changes, moved/deleted paths, experiment modules, workflows and stored output paths. The initial fresh evaluator history contained329 commits,197 refs including50 fetched PR heads, and no tags; the partition history contained105 commits and no tags. Additional commits referenced only by Actions metadata were also investigated; final inventory is in `results/baseline_gate/source_inventory.json`.

The GitHub Actions inventory contains1,365 artifact metadata entries from128 commit SHAs. No artifact name identifies a final accounting-only/40-test bundle. Representative archive download attempts could not deliver locally readable ZIPs (403 from the connector's returned file URL;401 on the authenticated API download redirect). Therefore this audit does **not** claim to have inspected every archive's contents, nor prove that no private/unreachable copy exists. The latest visible E46 candidate is trajectory-coupled, not accounting-only.

## Semantic contract

| Item | JB1 behavior | Evidence / remaining ambiguity |
|---|---|---|
| Progress/accounting | Profile-only Prefill and Decode progress; intrinsic/fixed/queue costs affect ledger only | Paper Eqs16/18–21; no timing location invented for overhead |
| Fixed overhead |5ms in TTFT/TPOT ledger; excluded from progress | Deliberately differs from public E31 and stage1 recovery |
| Intrinsic Prefill | Frozen59.37720874470879 microseconds/input token, only Prefill accounting | Same public calibrated coefficient; no held-out refitting |
| Decode blocking | Sum full stored Prefill compute plus intrinsic charge for currently active Prefills | Public E31 rule retained. Paper names a blocking debt but does not uniquely define its recurrence; cannot certify identity to missing final source |
| Pre-event check | Advance fractional Decode work using preceding state, check before removals/transitions/arrivals | The pre-check uses the preceding block's upper context at an exact crossing (left-limit convention) |
| Post-event check | Apply tied finishes/block updates/P→D/arrivals as one epoch; compute arrival profiles from complete tied batch, then check | Stable ID ordering; no sequential tied-arrival profiling |
| Block semantics |16-token blocks, preserved fractional progress; same explicit block state for Decode profile and KV context | Context is prompt plus upper output count of current block, capped at output length |
| Constraints | Retain all SLA/network/memory failures at the earliest failing check | Normal run stops at earliest pre- or post-check; diagnostic drain mode continues while preserving first failures |
| Memory | Per-node weight+workspace+reserve, prompt KV at arrival, block-upper Decode KV, activation buffer | Paper does not give a unique activation-buffer formula. JB1 declares one buffer per active request per resident stage: prompt tokens in Prefill, one token in Decode; no universal memory-accuracy claim |
| Network | Per-request residual split proportional to serialization cost; sum commitments on actual traversed links | Supports unequal capacities and physical shared links; unused links receive zero |
| Sampled capacity | Both models use identical ordered probes; preserve reversals, censoring and nearest observed unsafe | No continuous safe-prefix theorem |
| Drain/timeout | Safe runs drain; rejected runs may stop early. Debug mode drains for trajectory analysis; event-limit breach is an error | Reference always must fully drain |

The baseline is credible as this **explicitly specified journal model**. It is not evidence that the unavailable final CA source has identical behavior. The paper's underspecified blocking/activation choices are stated recovery assumptions and require sensitivity/limitation discussion.

## Recovered results and the conflict

The isolated2051-input/143-output request gives baseline TTFT ledger1.8940402816s, corrected ledger2.0158229367354s; verdict changes safe→unsafe. The corrected/uncorrected raw-compute trajectories are identical. The pinned reference's aligned TTFT remains2.0151050770s (output length affects later Decode, not this Prefill latency).

All24 trajectory comparisons (six seeds ×two placements ×two published endpoint intensities) preserve the accounting-only invariant. The full published grid .006–.022 in .0001 increments is evaluated for both variants in all12 configurations (3,864 evaluator calls); results are saved, not inferred from endpoint checks.

**JB1 matches0/12 published endpoint pairs.** Each published unsafe endpoint is safe with raw-compute progress. Re-enabling only fixed overhead in progress restores12/12 endpoint pairs. This is a controlled implementation-semantic ablation, not failed numerical tuning.

| Seed | Published largest safe | JB1 largest safe on same grid (both placements) |
|---|---:|---:|
|0|.0150|.0156|
|1|.0159|.0166|
|2|.0102|.0107|
|3|.0152|.0159|
|7|.0131|.0137|
|19|.0152|.0159|

Thus stage1's exact numerical endpoint recovery depended on legacy progress semantics. Formal evidence must be regenerated with JB1 and must not silently reuse stage1 evaluator verdicts. This also limits how the journal can describe itself as an extension of the final CA artifact.

## Tests and unavailable results

Ten new semantic tests cover raw-progress timing, accounting-only trajectory equality, tied-arrival commutativity, fractional progress, pre/post block contexts, prompt KV/activation reservation, simultaneous constraints, proportional commitments, finite drain and event-limit errors. Together with eight existing bridge tests,18 tests pass. Source/version and result hashes are stored with the gate output.

The original final40-test suite and the exact140-row regression manifest (136 previously both-safe;116 unique both-safe) have not been recovered. They are **not** claimed as rerun. New tests/invariant checks do not substitute for those historical denominators. The final source/manifest remains an artifact limitation, not an excuse to mutate the old repositories or conceal the different sampled transitions.

## Gate outcome

Proceed with formal experiments on JB1 under its stated assumptions, after protocol freeze. Keep legacy fixed-progress behavior as an implementation-sensitivity control. Claims concern JB1 versus the pinned HELIX reference simulator, never “the exact final CA implementation.” If a final artifact becomes available later, compare it separately and version the protocol; do not overwrite JB1 results.

## Stage 3 held-out control completed

The frozen baseline is unchanged. A separate legacy-progress control evaluates all3268 nominal paired points against the existing1634 physical reference records, with no reference rerun. Only5ms fixed overhead enters progress (queue=0 asserted). Tight winner agreement remains6/6; relaxed0/6→2/6. Raw4 strict+2 tie-break mismatches become legacy3 strict+1 tie-break;53 safe labels become unsafe. This demonstrates partial implementation-semantic sensitivity and does not identify either variant as the missing CA final code. See LEGACY_PROGRESS_SENSITIVITY.md and the Stage 3 report. Historical source searches remain closed.
