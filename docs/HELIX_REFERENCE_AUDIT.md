# HELIX reference audit

## Verdict

The path used here is the **HELIX reference simulator**, a Python discrete-event simulation. No real GPU execution, model weights, CUDA kernels, RPC workers, or serving cluster is started. Upstream contains both a simulator and a prototype; their coexistence must not be confused with which path this experiment invokes. [Official HELIX repository](https://github.com/Thesys-lab/Helix-ASPLOS25).

Pinned upstream: `8639497a4aaf1eb3b7594614cb0bbd376c1342b3`.
Adapter source: evaluator branch snapshot `1cd5c56365b084fb06e3ca14f67448ddbf45275a`.

## Executed chain

1. `scripts/reproduce.py` / diagnostic drivers construct a finite `RequestSpec` tuple and fixed `Pipeline`.
2. `src/research.py:reference` creates a content-keyed cache record and calls `evaluate_helix_fixed_reference`.
3. The adapter imports `simulator.event_simulator.cluster_simulator.ClusterSimulator` and creates `ModelName.LLaMa70B`.
4. `_build_helix_simulator` creates nodes and seven internal links, initializes model metadata, and processes model-load **events** (disk rate 1e15 bytes/s). Source/sink links use very high bandwidth and zero propagation delay. Model loading precedes all request arrivals and is excluded from latency.
5. `_issue_fixed_query` mirrors HELIX's QueryManager with an externally specified mini-pipeline. The stage route is fixed; no HELIX placement/max-flow optimization or Gurobi solve occurs.
6. `FixedPipelineScheduler.schedule_execution` delegates to upstream `execution_policy`, a FIFO traversal subject to per-machine prompt and Decode batch limits. Network transmission uses HELIX bandwidth state with at most one newly scheduled request per outbound link in a scheduler invocation.
7. `simulate_next_event` drains all finite queries. CPU-buffer overhead, per-layer lookup/interpolation, batching, resource state, and link events occur in the simulator.
8. `query.inference_history` is parsed into per-request Prefill and Decode timing. All queries must finish. An exception, exceeded event limit, or undrained workload is a run error, never silently a safe result.
9. Safety is the conjunction of per-request aligned TTFT and every Decode-iteration latency meeting their thresholds. Raw histories as exposed by the adapter are compressed in `results/raw_reference/*.json.gz`; summaries retain maxima and first violation type.

## Definitions and units

| Quantity | Implemented definition |
|---|---|
| Aligned TTFT | Prefill end minus query creation, plus fixed and configured queue overhead |
| Native first-token TTFT | First Decode iteration end minus query creation, plus the same overhead |
| TPOT | Each Decode iteration's end minus start, plus the same overhead; safe requires **all**, not average or p95, to pass |
| Fixed overhead | 5 ms charged once to aligned TTFT and once to every TPOT check; postprocessed in reference, also present in recovered evaluator progress |
| Intrinsic Prefill | HELIX compute-node CPU-buffer concat/transfer model at the first layer of each stage; not a measured new hardware observation |
| Profile units | CSV milliseconds per layer -> seconds; linear interpolation within table domain |
| Network | Internal bytes/s; model activation 8192 × 2 = 16384 bytes per token, Prefill times input length, Decode one token; seven internal hops |
| Time origin | Requests start after simulated model loading; latencies subtract query creation, so load-time offset cancels |

`compute_node.py:get_inference_statistics` adds `tokens * activation_size / (4*gbps)` and `/ (5*gbps)` to the first layer in each stage and clears the CPU buffer. In this pinned artifact the named `gbps` constant is 1e9 in the simulator's internal convention. The resulting eight-stage coefficient is 58.9824 microseconds/token. This is source-modeled overhead, not an observed CPU/GPU measurement. The paper's independently calibrated 59.37720874470879 microseconds/token remains frozen; the source coefficient is used only for diagnosis.

`event_simulator/model.py:get_inference_statistics` doubles interpolated Decode time for exactly one Decode token. The evaluator wrapper mirrors this singleton special case. Aggregate active Decode count is still not guaranteed to equal a particular stage's actual batch, a structural mismatch that remains after sharing tables.

## Shared inputs and limitations

For paper-1 reproduction and unified diagnostics, evaluator and reference use the exact same nominal machine-specific CSV tables, finite workload, partition, SLA, activation definition, and internal link capacities. Sharing profiles makes this a relative consistency study, not independent hardware validation. Controlled mismatch changes only evaluator multipliers and leaves the reference and its cache keys unchanged.

The evaluator reserves static weight/KV resources with simplified accounting; HELIX uses its own model metadata, KV blocks and batching constraints. Identical numerical memory limits do not make these implementations identical. Current diagnostic cases should be reported by first limiting mechanism; absence of memory violations does not validate memory behavior generally.

The heterogeneous extension adds only `L4x2`/`T4x4` name dispatch to the public adapter and uses upstream group profiles/limits. Such stages represent device groups, not eight individual GPUs. The controlled 40 GB per-stage limit is inherited from the conference experiment, not asserted as the physical capacity of every group.

The public recovered evaluator advances with profiled compute **plus configured 5 ms overhead**, checks post-event state, and uses a postprocessed Prefill blocking ledger. This differs in detail from the final manuscript's raw-compute equations and pre/post checks. We preserve the historical engine and label it recovered; we do not silently claim an exact final-source reproduction.

The adapter's `first_violation` ordering approximates token finish order by cumulative postprocessed latencies, including repeatedly charged fixed overhead. This does not change per-token safe/unsafe verdicts or maxima, but its reported first violating request/time is not a precise physical chronology. The journal should retain actual iteration timestamps before making timing-order claims.

## Wording correction for new work

Use “under the pinned HELIX reference simulator and tested configurations.” The older manuscript's “execution reference”, “runtime residual”, and “488×” can be misunderstood as real-GPU evidence. Their numerical results are simulator-relative. Do not modify the old manuscript; use explicit terminology and definitions in the journal.
