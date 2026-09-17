# Mechanism analysis — completed stage2 review

The full1634-point matrix and postprocessing are complete. Five saved instrumented traces cover an optimistic point, the inherited conservative point, a large-gap/correct-winner stress case, and both candidates in a nominal reversal. Every trace matches the cached per-query metrics exactly; newly executed traces also assert equal final simulation time. Selection rules are recorded in `results/formal/research_review.json`; compact measurements are in `results/formal/mechanisms/summary.json`. Selection is explanatory and does not provide a prevalence estimate.

For each selected point, retain the actual request arrivals and HELIX Prefill/Decode iteration timestamps. Instrumentation may retain per-node execution-batch and request-location timestamps without changing scheduling. Compare those with JB1 pre/post-event ledgers, active Prefill/Decode counts, fractional progress, blocking charge, residual SLA budgets, and link commitments. Align virtual time origins explicitly; do not use the compact adapter's approximate first-violation ordering for causal chronology.

The current baseline gate has already isolated one reproducible implementation mechanism: adding5ms fixed overhead to progress changes overlap trajectories and restores all12 published endpoint pairs, whereas keeping overhead only in the ledger shifts those edges. This was the baseline-semantic audit. Stage 3 now adds the full held-out evaluator-only sensitivity in LEGACY_PROGRESS_SENSITIVITY.md, without any new reference run.

Possible explanations such as overcharging full active Prefill service or aggregate-vs-stage-local batching will be called mechanisms only to the extent supported by traces and limited ablations. Otherwise the report will state that causation remains uncertain. No unsupported hardware/runtime explanation will be introduced.

## Observed conservative mechanism: full active-Prefill charge

Explanatory case selected while the matrix was running: held-out h105, A100, fast links, intensity4.096, TTFT2s/TPOT1s. This was an early observed short-trace conservative disagreement, not a random sample. The instrumented rerun exactly matches **all** original per-query TTFT/TPOT metrics and final simulation time. Evidence: `results/formal/mechanisms/conservative_h105_a100.json.gz`; instrumentation: `scripts/formal_trace.py`.

At physical time2.46484375s, request azure-00003 arrives. Both models then have two Prefill and two Decode queries. JB1 charges each Decode query the two full Prefill compute times, .76032+.64832s, plus .1388832913s intrinsic charge. The resulting1.5475232913s blocking charge plus .112s Decode compute and .005s fixed overhead gives1.6645232913s against a1s TPOT limit; residual budget is−.6645232913s. This is sufficient to explain JB1's rejection at that epoch. Without the blocking component, this particular ledger would be below1s; that local arithmetic is not a claim that every later ledger would pass.

The reference fully drains14 queries: maximum aligned TTFT=.9632468762s, maximum TPOT=.9459497200s. For the first rejected query azure-00000, its worst Decode iteration physically spans1.9080729312–2.8267538072s, including the evaluator's failing epoch. Its actual iteration duration is.9186808760s; adding the5ms ledger overhead yields.9236808760s. Its80 per-layer execution intervals sum to.1121179648s and none shares an execution batch with a Prefill request. The remaining.8065629112s includes queuing and transmission, which this aggregate does not separate. Actual stage-local overlap therefore does not incur the full1.5475s charge imposed on this Decode ledger.

The two models agree on query-phase concurrency at the failing post-event epoch, so this example does not need a concurrency-count error to explain rejection. The full-service blocking rule, rather than a measured residual waiting time, is the identifiable conservative component here. We do not infer that removing this charge is generally safe or recommend changing the frozen baseline. This inherited trace was reused without another simulation.

## Optimistic error: completion-time drift removes real overlap

At h103/A100/slow, intensity0.016 and TPOT0.15s, JB1 accepts with maximum accounted TPOT0.117367s. Reference TPOT reaches1.103934s for azure-00013, iteration548, ending1721.391211s. Its physical duration is1.098934s plus the0.005s ledger overhead. All15 requests drain; TTFT remains within2s.

JB1 finishes request13 at1720.199600s, just before request14 arrives at1720.250000s. The reference finishes request13 at1721.840915s: request13 is still decoding when request14 enters Prefill. At the post-arrival check JB1 sees one Prefill and zero Decode; reference query occupancy is one of each. The reference violating iteration spans1720.292276–1721.391211s. Its80 layer execution intervals total0.112059s and none shares a batch with Prefill; the remaining0.986875s is time outside those execution intervals, not slower isolated Decode compute. Location history and phase occupancy support a missed-overlap explanation; the residual is not uniquely assigned to queueing versus transport.

An evaluator-only diagnostic ablation adds the fixed5ms overhead to progress, leaving the saved nominal labels untouched. It moves request13 completion to1722.964600s and restores Decode occupancy at request14 arrival; the evaluator becomes unsafe. However its first failure is an earlier request at751.5s. This demonstrates sensitivity to progress semantics, not an exact reconstruction of reference chronology or a validated correction. Evidence: `optimistic_h103_a100.json.gz`, `optimistic_progress_ablation.json`, and the optimistic timeline figure. The frozen baseline hash is unchanged.

## Large capacity error with the correct winner under stress

No Raw nominal main trial combines a large selected-capacity gap with a correct winner: the six correct Raw nominal tight-TPOT winners have matching selected sampled capacities. The original mechanism trace therefore uses an explanatory Raw stress case. Stage 3 separately finds correct nominal legacy winners with large operating-point losses (h104/h105); those are control-result observations, not these original Raw traces.

For h103/heterogeneous/relaxed-TPOT (fixed TTFT) with Both−10%, shift0 has Emax2.8963093757 versus Rmax9.7419846861 (−70.2698%), yet is reference-best. Both−5% also selects shift0, so the selected winner is stable across those two perturbations. Nominal profiles select shift2 and are wrong; stability is not claimed across nominal and stress.

At common load4.096, the stress trace rejects at3.575195s: the Decode ledger charges10.625292s of active-Prefill debt plus0.201600s compute and0.005s overhead, exceeding10s. The reference maxima are TTFT4.533201s and TPOT4.478798s, both safe. At that epoch JB1 counts5 Prefill/1 Decode while reference query occupancy is6 Prefill/0 Decode. Both excessive blocking accounting and phase timing differ here; this case does not isolate either as the sole cause. A large absolute error can coexist with a correct ordering among the tested candidates.

## Genuine nominal decision reversal

In h101/relaxed-TPOT (fixed TTFT), E selects shift2 (Emax4.096) over shift0 (Emax3.8382953147). The reference selects shift0 (Rmax13.1931367994); shift2 reaches10.3960654413 and ranks fourth, a21.201% sampled-capacity loss. This is a common-grid reversal, not an artifact of candidate-specific probe sets.

Paired traces at the same load4.096 reproduce the local preference: shift0 is E-unsafe/R-safe while shift2 is E-safe/R-safe. At4.662109s, shift0 has6 Prefill and4 Decode in both models. Its first failing ledger is9.822287s blocking plus0.232s compute plus0.005s overhead =10.059287s, marginally exceeding10s. Shift2's maximum accounted TPOT is9.953235s. Reference maxima at this load are only4.513336s and4.452622s. Thus a small shift-dependent accounting difference straddles E's threshold while both candidates remain reference-safe.

The shared grids establish the later capacity ranking; these two local traces explain the evaluator's premature distinction. They do not fully explain why shift0 has the larger reference frontier. No single queuing/batching cause for the entire reversal is claimed without a further causal intervention. The documented local mechanism and its boundary are sufficient for this empirical diagnosis.

## Stage 3 implementation sensitivity boundary

Full frozen-grid control: Raw O/C=23/413, legacy=17/460. Tight winner agreement remains6/6; relaxed improves0/6→2/6. Raw has4 strict best-set and2 tie-break mismatches; legacy retains3 strict (h101–h103) and1 tie-break (h106). h104/h105 improve, but h102 selected rank worsens2→4. The outcome is partially semantic-sensitive, not a universal repair. h101's strict mismatch survives the control; the local explanatory trace remains Raw evidence. Existing stress traces do not establish legacy stress behavior. All five traces are reused unchanged.
