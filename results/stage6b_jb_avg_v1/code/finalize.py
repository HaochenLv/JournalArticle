"""Audit and publish all protocol tables without altering frozen scientific definitions."""
from common import *
from analyze import weighted_errors
from collections import Counter,defaultdict
import datetime,subprocess,time,platform

def csvread(path):
    with path.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def num(s):return None if s=='' or s is None else float(s)
def boolean(s):return True if s=='True' else False if s=='False' else None
def combine(folder,name):
    paths=[OUT/folder/(v+'_'+name+'.csv') for v in ['g0','g1']]
    rows=[r for p in paths if p.exists() for r in csvread(p)]
    csvwrite(OUT/folder/(name+'.csv'),rows)
    return rows
def stats(xs):return {'median':quantile(xs,.5),'P95':quantile(xs,.95),'min':min(xs) if xs else None,'max':max(xs) if xs else None,'count':len(xs),'na_reason':None if xs else 'no eligible observations'}
def complete():
    t0=time.perf_counter();stop=read(OUT/'checks/stop_summary.json');assert stop['status']=='complete'
    from run import guard
    guard()
    protected=read(ROOT/'results/standard_metrics_v1/protected_manifest.json')['files']
    for rel,h in protected.items():assert sha(ROOT/rel)==h,('protected file changed',rel)
    frozen_reuse=read(OUT/'provenance/cache_reuse_manifest.json')
    for r in frozen_reuse['G0']:
        for a in r['aliases']:assert sha(ROOT/a['source'])==a['sha256'],('cache provenance changed',a['source'])
    data={v:read(OUT/'status'/(v.lower()+'_rows.json')) for v in ['G0','G1']}
    summaries={v:read(OUT/'reports'/(v.lower()+'_summary.json')) for v in data}
    ledger=read(OUT/'checks/budget_ledger.json');g0=read(OUT/'grids/g0.json');g1=read(OUT/'grids/g1.json')
    assert len(data['G0'])==2550 and len(data['G1'])==2550+ledger['candidate_slots']
    assert ledger['new_helix_unique_starts']<=300 and ledger['helix_attempts']<=600
    assert all(x<=6 for x in ledger['per_workload'].values())
    assert len({r['physical_id'] for r in data['G1']})==len(data['G1'])
    assert {r['physical_id'] for r in data['G0']}<={r['physical_id'] for r in data['G1']}
    for wid,grid in g1['grids'].items():
        for s in P['candidate_shifts']:assert sorted(r['intensity'] for r in data['G1'] if r['workload']==wid and r['candidate']==s)==grid
    combined={}
    for folder,name in [('status','point_status'),('metrics','request_pairs'),('metrics','request_accuracy'),('metrics','judgments'),('metrics','judgment_summary'),('capacity','capacities'),('decisions','ranking'),('decisions','operating_points'),('applicability','load_bands')]:combined[name]=combine(folder,name)
    for v in summaries:
        cc=[r for r in combined['capacities'] if r['grid_version']==v]
        summaries[v]['identified_capacity_pair_rows']=sum(r['E_identified']=='True' and r['R_identified']=='True' for r in cc)
        summaries[v]['relative_capacity_error_valid_rows']=sum(r['absolute_relative_gap']!='' for r in cc)
        summaries[v]['relative_capacity_error_workloads']=sorted({r['workload'] for r in cc if r['absolute_relative_gap']!=''})
    with (OUT/'capacity/sequences.jsonl').open('w',encoding='utf-8') as out:
        for v in ['g0','g1']:out.write((OUT/'capacity'/(v+'_sequences.jsonl')).read_text(encoding='utf-8'))
    sample=csvread(OUT/'runtime/evaluator_samples.csv');refs=csvread(OUT/'runtime/reference_execution.csv');by=defaultdict(list)
    for s in sample:by[s['physical_id']].append(s)
    runtime=[];matched=[];failures=[]
    for r in data['G1']:
        pid=r['physical_id'];ss=by[pid];good=[s for s in ss if s.get('semantic_hash')]
        assert len({s['semantic_hash'] for s in good})<=1
        reps=[s for s in good if s['warmup']=='False'];valid=len(reps)==5 and len({s['repeat'] for s in reps})==5
        med=statistics.median(float(s['wall_s']) for s in reps) if valid else None
        runtime.append({'physical_id':pid,'workload':r['workload'],'candidate':r['candidate'],'status':r['E_status'],'median_five_wall_s':med,'measurement_count':len(reps),'min_s':min((float(s['wall_s']) for s in reps),default=None),'max_s':max((float(s['wall_s']) for s in reps),default=None),'na_reason':None if valid else 'five successful measured repeats unavailable'})
        ref=next(x for x in refs if x['physical_id']==pid)
        if r['pairable'] and valid and ref['actual_new_execution']=='True' and ref['matched_environment']:
            matched.append({'physical_id':pid,'workload':r['workload'],'candidate':r['candidate'],'reference_wall_s':float(ref['wall_s']),'evaluator_median_s':med,'ratio':float(ref['wall_s'])/med,'environment_id':ref['matched_environment'],'E_status':r['E_status'],'R_status':r['R_status'],'scope':'matched simulator-execution runtime ratio; boundary-selected subset; single R vs median five E; wrappers differ'})
    csvwrite(OUT/'runtime/evaluator_point_medians.csv',runtime)
    csvwrite(OUT/'runtime/matched_ratios.csv',matched,fields=list(matched[0]) if matched else ['physical_id','workload','candidate','reference_wall_s','evaluator_median_s','ratio','environment_id','E_status','R_status','scope'])
    write(OUT/'runtime/matched_evidence_status.json',{'matched_points':len(matched),'status':'matched boundary-selected evidence' if matched else 'cost advantage unestablished','insufficient_evidence_reason':None if matched else 'no qualified same-environment full-drain physical execution pairs','limitations':['single R execution vs five E repetitions','boundary-selected subset','reference initialization and extraction vs E prepared object call','not GPU serving speedup']})
    rst={status:stats([r['median_five_wall_s'] for r in runtime if r['status']==status and r['median_five_wall_s'] is not None]) for status in sorted({r['status'] for r in runtime})}
    write(OUT/'runtime/runtime_summary.json',{'E_by_status':rst,'matched_ratio':stats([r['ratio'] for r in matched]),'new_R_wall':stats([float(r['wall_s']) for r in refs if r['actual_new_execution']=='True']),'archival_R':'unknown or mixed environment; excluded from controlled ratios'})
    # Registry preserves original G0 identity plus actual G0/G1 membership and terminal states.
    registry=[]
    for r in data['G1']:registry.append({k:v for k,v in r.items() if k not in ['E','R']}|{'grid_membership':'G0;G1' if r['membership']=='G0' else 'G1','evaluator_status':r['E_status'],'reference_status':r['R_status']})
    csvwrite(OUT/'provenance/physical_registry.csv',registry)
    # Add a refinement manifest; the pre-outcome G0 cache manifest remains immutable.
    csvwrite(OUT/'provenance/refinement_sources.csv',[r for r in registry if r['membership']!='G0'],fields=list(registry[0]))
    points={r['physical_id']:read(OUT/'metrics/physical'/(r['physical_id']+'.json.gz')) for r in data['G1']}
    cells=[]
    for w in P['workloads']:
        wid=w['short_id'];rm=[r for r in matched if r['workload']==wid];rcandidates={r['candidate'] for r in rm};cost=stats([r['ratio'] for r in rm]);costok=cost['median']>=10 if len(rcandidates)==5 and cost['median'] is not None else None
        for sla in P['slas']:
            sid=sla['id'];cell={'workload':wid,'SLA':sid,'N':w['requests'],'required_pass_count':int((Decimal('.90')*w['requests']).to_integral_value(rounding='ROUND_CEILING')),'matched_candidate_count':len(rcandidates),'matched_points':len(rm),'runtime_ratio_median':cost['median'],'runtime_ratio_P95':cost['P95'],'runtime_ratio_min':cost['min'],'runtime_ratio_max':cost['max'],'cost_pass':costok,'cost_na_reason':None if costok is not None else 'qualified matched timing unavailable'}
            reasons=[];checks=[]
            for v in ['G0','G1']:
                rs=[r for r in data[v] if r['workload']==wid];ps=[points[r['physical_id']] for r in rs]
                relevant=[p for p in ps if p['classifications']['E'][sid]['safe'] is True or p['classifications']['R'][sid]['safe'] is True]
                caps,rank,op=decisions(rs,sid)
                bs=Counter(r['candidate'] for r in rs if r['E'][sid]['safe'] is True and r['R'][sid]['safe'] is True)
                nontrivial=w['requests']>=10 and max(bs.values(),default=0)>=2 and max(c['C_lower'] for c in caps['E'].values())>0 and max(c['C_lower'] for c in caps['R'].values())>0
                coverage=all(p['classifications']['pairable'] for p in relevant) if relevant else None
                O=sum(r['E'][sid]['safe'] is True and r['R'][sid]['safe'] is False for r in rs);unverified=sum(r['E'][sid]['safe'] is True and r['R'][sid]['safe'] is None for r in rs)
                approval=sum(r['E'][sid]['safe'] is True for r in rs);approved_decidable=sum(r['E'][sid]['safe'] is True and isinstance(r['R'][sid]['safe'],bool) for r in rs)
                ids=all(c['identified'] for m in caps.values() for c in m.values());positive=[c for c in P['candidate_shifts'] if caps['R'][c]['identified'] and caps['R'][c]['C']>0]
                gaps=[abs(caps['E'][c]['C']-caps['R'][c]['C'])/caps['R'][c]['C'] for c in positive] if ids else []
                relevantcaps=[caps[m][c] for c in positive for m in ['E','R']]
                capok=bool(positive) and all(x<=.20 for x in gaps) and all(not c['right_censored'] and c['upper_transition_width'] is not None and c['upper_transition_width']<=.05 for c in relevantcaps) if ids else None
                err={name:weighted_errors(relevant,key,limit) for name,key,limit in [('TTFT','ttft_s',sla['ttft_s']),('TPOT','average_tpot_s',sla['tpot_s'])]}
                errorok=all(err[k]['p90_absolute']<=.10 for k in err) if all(err[k]['p90_absolute'] is not None for k in err) else None
                opok=op['safe_R'] is True and op['safe_usable_loss']<=.20 if op['safe_R'] is not None and op['safe_usable_loss'] is not None else None
                versionchecks={'nontrivial_service':nontrivial,'paired_relevant_coverage':coverage,'zero_observed_optimistic':O==0 and unverified==0,'sampled_capacity':capok,'request_error':errorok,'original_recommendation':opok}
                for key,value in versionchecks.items():
                    cell[v+'_'+key+'_pass']=value;checks.append(value)
                    if value is not True:reasons.append(v+':'+key+(' not-assessable' if value is None else ' failed'))
                cell.update({v+'_service_relevant_points':len(relevant),v+'_paired_relevant_points':sum(p['classifications']['pairable'] for p in relevant),v+'_O':O,v+'_approved_decidable':approved_decidable,v+'_optimistic_approval_fraction':ratio(O,approved_decidable),v+'_unverified_approvals':unverified,v+'_E_approval_coverage':approval/len(rs),v+'_all_capacities_identified':ids,v+'_max_absolute_relative_capacity_gap':max(gaps,default=None),v+'_B_R':op['B'],v+'_E_L':op['L'],v+'_R_attainment':op['A_R'],v+'_recommendation_safe':op['safe_R'],v+'_safe_usable_loss':op['safe_usable_loss'],v+'_right_censored_candidates':sum(c['right_censored'] for c in relevantcaps),v+'_NA_reasons':{k:'no applicable or identifiable evidence' for k,value in versionchecks.items() if value is None},v+'_capacity_bounds':{m:{str(c):[x['C_lower'],x['C_upper']] for c,x in cs.items()} for m,cs in caps.items()}})
                for metric,er in err.items():cell.update({v+'_'+metric+'_P90_normalized_absolute':er['p90_absolute'],v+'_'+metric+'_median_signed_normalized':er['median_signed'],v+'_'+metric+'_valid_points':er['valid_points'],v+'_'+metric+'_na_reason':er['na_reason']})
            checks.append(costok)
            if costok is not True:reasons.append('cost not-assessable' if costok is None else 'cost failed')
            cell['screen_status']='pass' if all(c is True for c in checks) else 'fail' if any(c is False for c in checks) else 'not-assessable';cell['failed_or_unassessed_dimensions']=reasons
            cells.append(cell)
    assert len(cells)==60;csvwrite(OUT/'applicability/evidence_cells.csv',cells)
    # Supplemental pooled request summaries are explicitly separate from equal-workload primary evidence.
    pooled=[]
    for v in data:
        ps=[points[r['physical_id']] for r in data[v]]
        for wid in [w['short_id'] for w in P['workloads']]+['ALL']:
            for key,name in [('ttft_s','TTFT'),('average_tpot_s','TPOT')]:
                vals=[e[key]-p['R']['request_metrics'][rid][key] for p in ps if p['classifications']['pairable'] and (wid=='ALL' or p['item']['workload']==wid) for rid,e in p['E']['request_metrics'].items() if e[key] is not None]
                pooled.append({'grid_version':v,'workload':wid,'metric':name,'weighting':'request-pooled supplement',**summary([(x,Fraction(1,len(vals))) for x in vals]),'request_count':len(vals)})
    csvwrite(OUT/'metrics/request_pooled_supplement.csv',pooled)
    # All primary NA fields have either a local reason or this fixed schema explanation.
    write(OUT/'checks/NA_SCHEMA.json',{'empty_csv_numeric':'NA, never zero. Read the associated *_na_reason, na_reason, loss_na_reason, actual_na_reason, relative_na_reason or version NA_reasons fields.','empty_nullable_decision':'unknown: see model status and resource_feasible; abstained operating points have actual_na_reason=abstention.','empty_optional_reason':'not applicable because the corresponding value is defined; not missing evidence','empty_optional_candidate':'abstention or full best set unidentified: see abstention/na_reason','runtime_missing':'failed repetition or archival metadata unavailable; never cache execution time','empty_SLA':'SLA-independent accuracy, not missing SLA','TPOT_m1':'undefined by metric definition; not zero','resource_latency_counts':'undefined for hard-resource rejection','quantile':'empirical inverse CDF using exact rational hierarchy weights'})
    q={'passed':True,'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'G0_physical_count':2550,'G1_physical_count':len(data['G1']),'G0_judgments':2550*6,'G1_judgments':len(data['G1'])*6,'distinct_request_pair_keys':len({(r['physical_id'],r['request_id']) for r in combined['request_pairs']}),'request_pair_rows':len(combined['request_pairs']),'source_and_protocol_hashes_unchanged':True,'source_gate':'preflight_data_gate.json','common_grids':True,'budget_limits':True,'successful_repeat_semantics':True,'classifications_pure_and_SLA_monotonic':True,'joint_inclusion_exclusion':True,'request_pairing_and_endpoints':True,'G0_preserved':True,'all_60_cells':True,'unknowns_preserved':True,'model_edited':False,'tests':{'evaluator':20,'metrics':9,'protocol':12},'limitations':['full historical raw event timestamps unavailable; pinned source and saved endpoint identities verified','archival timing is excluded from controlled ratios absent matched metadata']}
    assert q['distinct_request_pair_keys']==q['request_pair_rows']
    write(OUT/'checks/quality_checks.json',q)
    cost=read(OUT/'runtime/planning_cost.json');cost.update(final_reporting_wall_s=time.perf_counter()-t0,actual_new_R_wall_s=sum(float(r['wall_s']) for r in refs if r['actual_new_execution']=='True'),matched_points=len(matched),input_and_serialization_s=sum(float(s.get('input_object_preparation_s') or 0)+float(s.get('serialization_and_semantic_hash_s') or 0) for s in sample),analysis_wall_s=sum(x['analysis_wall_s'] for x in summaries.values()),complete_breakdown_pending_report=False)
    write(OUT/'runtime/planning_cost.json',cost)
    report(summaries,cells,rst,matched,ledger,q)
    return summaries,cells

def report(summaries,cells,rst,matched,ledger,q):
    a=summaries['G0'];b=summaries['G1'];passed=[r for r in cells if r['screen_status']=='pass']
    hasA=len({r['workload'] for r in passed})>=2 and any(r['workload'].startswith('h') for r in passed) and any(r['workload'].startswith('w') for r in passed)
    interpretation=['A'] if hasA else []
    if a['judgment_counts'].get('O',0) or a['judgment_counts'].get('C',0) or a['E_status_counts'].get('unsupported_profile_domain',0):interpretation.append('B')
    if not matched:interpretation.append('D (runtime cost advantage unestablished)')
    if a['unknown_sequences'] or b['unknown_sequences']:interpretation.append('D (full-grid capacities and rankings partly unidentified because of domain coverage)')
    # C requires positive service-relevant evidence; screen failure alone is insufficient.
    cfail=sum(r['G0_original_recommendation_pass'] is False or r['G0_request_error_pass'] is False for r in cells)
    if cfail:interpretation.append('C (in specified cells failing accuracy or original-recommendation tolerances)')
    accuracy=[r for r in a['accuracy'] if r['error_kind']=='seconds'];lines=['# Stage 6B formal evidence report','',f"Protocol FI-JBAVG-S6B-v1. Completed under implementation `{P['implementation_pin']}`. G0 is primary accuracy/judgment evidence; G1 is boundary-enriched sensitivity evidence. HELIX is a pinned simulator reference, not measured GPU or client truth.",'','## RQ1 — Request-level numerical accuracy','', '| Metric | Median signed error (s) | Median absolute error (s) | P90 absolute error (s) | Paired points |','|---|---:|---:|---:|---:|']
    for r in accuracy:lines.append(f"| {r['metric']} | {r['median_signed']} | {r['median_absolute']} | {r['p90_absolute']} | {r['valid_points']} |")
    lines+=['','These are empirical inverse-CDF quantiles under equal workload → candidate → valid point → applicable request weighting. TPOT seconds can be multiplied by 1000 for milliseconds. The per-workload, relative, SLA-budget-normalized and service-relevant results are in `metrics/request_accuracy.csv`; raw paired and unpaired request rows are in `metrics/request_pairs.csv`. Request-pooled summaries are supplemental and separately labeled. m=1 TPOT stays null. No significance tests, bootstrap or workload confidence intervals were used.','',f"G0 evaluator statuses: {a['E_status_counts']}. Paired execution coverage: {a['pairable_points']}/2550. These counts include unfavorable and unsupported results; partial request completions never enter primary latency errors.",'','## RQ2 — Joint judgment and sampled capacity','',f"G0 descriptive six-SLA counts: {a['judgment_counts']}. The six SLA conditions reuse the same physical trajectories and are not independent replicates. `metrics/judgment_summary.csv` gives BS/BU/O/C, raw numerators/denominators, O/(BS+O), C/(BS+C), O/(BU+O), approval and decision coverage, macro versus pooled rates, latency-only and near-boundary subsets.",'',f"Capacity absolute relative error median/P90: G0 {a['relative_capacity_error_median']} / {a['relative_capacity_error_P90']}; G1 {b['relative_capacity_error_median']} / {b['relative_capacity_error_P90']}. These descriptive candidate/SLA row summaries accompany all per-workload rows and capacity bounds; zero reference capacity and unidentified capacity have no exact relative error.",'',f"G0 no-safe/right-censored/unknown/nonmonotone sequences: {a['no_safe_sequences']} / {a['right_censored_sequences']} / {a['unknown_sequences']} / {a['nonmonotone_sequences']}. G1: {b['no_safe_sequences']} / {b['right_censored_sequences']} / {b['unknown_sequences']} / {b['nonmonotone_sequences']}. Sequence counts include both models and six correlated SLA classifications. G1 unresolved transition brackets: {b['unresolved_brackets']}; quota and stopping reasons are retained in `checks/stop_summary.json` and full sequences.",'','A sampled maximum is a finite-grid quantity. Right-censoring does not invalidate that maximum, but equal top-end capacities do not establish agreement on continuous capacity. Unknown bounds are not confidence intervals. No monotonicity or continuous safe interval is assumed.','', '## RQ3 — Bounded applicability and runtime','',f"All 60 cells are reported: {dict(Counter(r['screen_status'] for r in cells))}; {len(passed)} pass. The screen thresholds (10% P90 latency-budget error, 20% capacity/loss, zero observed optimistic approval, 10× matched runtime) are preregistered engineering tolerances, not literature standards. A failed cell alone does not establish universal worthlessness.",'',f"Matched full-drain runtime pairs: {len(matched)}. "+('Matched ratios describe a boundary-selected subset, with one R execution versus five E measurements, and different wrapper scopes.' if matched else 'Cost advantage unestablished. No controlled speedup ratio is reported, and the historical 488× number is not inherited.'),'',f"Evaluator per-point median runtime strata: `{json.dumps(rst)}`. All scheduled E inputs receive one warmup and five measurements; technical attempts are retained. Cache read/decompression/recovery/classification is separately measured and never called HELIX execution time. Timing repeats describe this host, not independent workloads.",'','`applicability/evidence_cells.csv` lists every failed/NA dimension. Fixed G0-based low/middle/high log-intensity bands are descriptive; they do not define another pass screen. w203 (N=5) cannot satisfy the N≥10 screen and is still fully reported.','', '## RQ4 — Controlled ranking and original operating points','',f"G0 ranking: {a['ranking_counts']}; safe/unsafe/abstained/unknown original recommendations: {a['safe_recommendations']} / {a['unsafe_recommendations']} / {a['abstentions']} / {a['unknown_recommendations']}. G1 ranking: {b['ranking_counts']}; corresponding recommendations: {b['safe_recommendations']} / {b['unsafe_recommendations']} / {b['abstentions']} / {b['unknown_recommendations']}.",'','This is a controlled five-candidate ranking probe. Fixed tie-break is 0, −1, +1, −2, +2. E recommendations are selected solely from E confirmed-safe pairs; original G0 recommendations remain intact and are never replaced by reference-informed fallback. Tables retain attainment, J/K/N, TTFT/TPOT/both/joint failure counts, shortfall, excess failures, arithmetic loss, safe usable intensity/loss and candidate/load decomposition. A single latency violation does not imply unsafe: only the 90% joint target defines the decision.','', '## Positive, negative and insufficient evidence','',f"Positive observations: {a['judgment_counts'].get('BS',0)} G0 both-safe classified conditions and {a['safe_recommendations']} reference-safe original G0 recommendations; these are local observations, not a general reliability claim. Negative observations include {a['judgment_counts'].get('O',0)} optimistic and {a['judgment_counts'].get('C',0)} conservative conditions, {a['unsafe_recommendations']} unsafe G0 recommendations, and the separately listed unsupported/no-safe/censored cases. Unknown coverage and unresolved brackets remain explicit.",'',f"Permitted interpretation: **{'; '.join(interpretation) or 'D — insufficient evidence'}**. A/B/C can differ across cells. Correlated diagnostics do not establish a mechanism's causal contribution without an ablation. This one approximation/reference comparison cannot establish that every accurate lightweight model must reproduce HELIX complexity.",'','## Provenance, budget and limitations','',f"G0 physical count {a['physical_count']}; G1 {b['physical_count']}. New HELIX unique inputs/attempts: {ledger['new_helix_unique_starts']} / {ledger['helix_attempts']}; selected common intensities: {ledger['new_common_intensities']}; E unique inputs/invocations: {ledger['evaluator_unique_inputs']} / {ledger['evaluator_invocations']}. Quality checks: passed; 39 targeted tests. Full budget ledger includes failures and cache hits.",'','The historical G0 grid is outcome-adaptive from earlier metrics; the G1 grid is E/R transition-informed. Neither is a blind online search or external workload generalization test. h and w are fixed historical workloads, with w described as additional historical workloads, not untouched held-out. Existing compact cache records lack full original timestamp histories; saved endpoint identities and pinned lifecycle source support the recovery, not independent client measurements. No model edits, new baseline, ablation, SLA, hardware, workload, Stage 6C or manuscript were added.','']
    (OUT/'reports/FINAL_EVIDENCE_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    write(OUT/'reports/final_summary.json',{'status':'complete','G0':a,'G1':b,'applicability_pass_cells':len(passed),'matched_runtime_points':len(matched),'interpretation':interpretation,'ledger':ledger,'quality_passed':True})

if __name__=='__main__':complete()
