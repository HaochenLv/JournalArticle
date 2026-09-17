"""Stage 3: evaluator-only sensitivity and saved-data deployment audits.

Never launches a reference simulation, changes the grid, or writes Stage 2 raw
data. The existing frozen JB1 flag is isolated by a named control wrapper.
"""
from pathlib import Path
import sys, json, hashlib, collections, statistics, argparse
sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'src'), str(Path(__file__).resolve().parent)]
from formal_core import *
from formal_analyze import flatten, matrix

OUT = FORMAL / 'legacy_progress_sensitivity'

def label(regime):
    return 'tight-TPOT' if regime == 'decode' else 'relaxed-TPOT (fixed TTFT)'

def legacy_progress(p, w, sla, prof):
    # The frozen flag adds fixed+queue to progress. Queue is exactly zero here,
    # so only the prescribed 5 ms fixed overhead differs from raw JB1.
    assert sla.queue_overhead_s == 0 and sla.fixed_overhead_s == .005
    return jb(p, w, sla, prof, fixed_in_progress=True)

def mismatch(d):
    if not d['evaluator_best_set']: return 'no-safe recommendation'
    if not d['reference_best_set']: return 'no-safe reference'
    if d['winner_agrees']: return 'agreement'
    return ('tie-break mismatch' if set(d['evaluator_best_set']) & set(d['reference_best_set'])
            else 'strict best-set mismatch')

def protected_manifest():
    paths = [ROOT/'src/journal_baseline.py', ROOT/'config/formal_protocol.json',
             ROOT/'docs/FORMAL_EXPERIMENT_PROTOCOL.md']
    for folder in ['groups','workloads','rq1_reliability','rq2_capacity',
                   'rq3_decision_transfer','rq4_profile_mismatch','mitigation','mechanisms','runtime']:
        paths.extend(p for p in (FORMAL/folder).rglob('*') if p.is_file())
    paths.extend((ROOT/'results/raw_reference').glob('*'))
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(set(paths)) if p.is_file()}

def snapshot():
    p = OUT/'source_manifest.json'
    current = protected_manifest()
    if p.exists(): assert json.loads(p.read_text()) == current, 'Frozen evidence changed'
    else: write_json(p, current)
    return current

def sensitivity():
    check_pins(); before = snapshot(); allrows = []
    for g in groups():
        state = json.loads((FORMAL/'groups'/(g['id']+'.json')).read_text())
        assert state['status'] == 'complete' and state['protocol_hash'] == PROTOCOL_HASH
        dest = OUT/'groups'/(g['id']+'.json')
        if dest.exists():
            result = json.loads(dest.read_text())
            assert result['source_hash'] == fingerprint(state)
            allrows.extend(result['rows']); continue
        wd, w = load_workload(g['workload']); limits = slas(g); prof = CachedProfiles()
        assert fingerprint([asdict(x) for x in w]) == state['workload_fingerprint'] == wd['workload_fingerprint']
        ps = {s:pipeline(g['link'],s,g['kind']=='heterogeneous') for s in g['shifts']}
        for s in g['shifts']:
            assert sorted(r['intensity'] for r in state['rows'] if r['shift']==s) == state['grid']
        rows = []
        for r in flatten(state):
            assert r['status']=='ok'
            p = ps[r['shift']]; scaled = scale_workload(w,r['intensity'])
            assert fingerprint(asdict(p)) == r['partition_fingerprint']
            assert fingerprint([asdict(x) for x in scaled]) == r['scaled_workload_fingerprint']
            assert r['profile_fingerprint']==CONFIG['profile_fingerprint']
            # Recompute labels from stored request metrics, never from a new run.
            with gzip.open(ROOT/'results/raw_reference'/(r['reference_cache_key']+'.json.gz'),'rt') as f:
                refdata=json.load(f)
            assert fingerprint(refdata['inputs'])==r['reference_cache_key']
            assert fingerprint(refdata['inputs']['pipeline'])==r['partition_fingerprint']
            assert fingerprint(refdata['inputs']['workload'])==r['scaled_workload_fingerprint']
            assert reference_details(refdata,limits[r['regime']])['safe']==r['reference_safe']
            assert refdata['raw']['finished_requests']==refdata['raw']['total_requests']==len(w)
            e = legacy_progress(p,scaled,limits[r['regime']],prof)
            row = {k:r[k] for k in ['case_id','group','workload','role','kind','link','shift','regime','intensity','status','reference_safe','reference_cache_key','workload_fingerprint','scaled_workload_fingerprint','partition_fingerprint','profile_fingerprint']}
            row.update(point_id=fingerprint([r['group'],r['shift'],r['intensity'],r['regime']]),
                       sla_label=label(r['regime']),grid_fingerprint=fingerprint(state['grid']),
                       raw_safe=r['evaluator_safe'],evaluator_safe=e['safe'],
                       legacy_result=e,ttft_s=limits[r['regime']].ttft_s,tpot_s=limits[r['regime']].tpot_s)
            rows.append(row)
        write_json(dest,{'source_hash':fingerprint(state),'protocol_hash':PROTOCOL_HASH,'group':g,'rows':rows})
        allrows.extend(rows); print('LEGACY',g['id'],len(rows),flush=True)
    assert len(allrows)==3268 and len({r['point_id'] for r in allrows})==3268
    csv_write(OUT/'raw.csv',allrows)
    counts=[]
    for kind,regime in [('heterogeneous','decode'),('heterogeneous','prefill'),('a100','decode'),('a100','relaxed_decode')]:
        rs=[r for r in allrows if r['kind']==kind and r['regime']==regime]
        for variant,key in [('raw','raw_safe'),('legacy','evaluator_safe')]:
            counts.append({'kind':kind,'regime':regime,'sla_label':label(regime),'variant':variant,
                           **matrix([dict(r,evaluator_safe=r[key]) for r in rs]),
                           'changed_labels':sum(r['raw_safe']!=r['evaluator_safe'] for r in rs)})
    caps=[]; bycase=collections.defaultdict(list)
    for r in allrows: bycase[r['case_id']].append(r)
    original={r['case_id']:r for r in json.loads((FORMAL/'rq2_capacity/summary.json').read_text())['rows']}
    for case,rows in sorted(bycase.items()):
        c={k:rows[0][k] for k in ['case_id','group','workload','kind','regime','sla_label','shift','role']}
        c.update(raw=safe_summary(rows,'raw'),legacy=safe_summary(rows,'evaluator'),reference=safe_summary(rows,'reference'))
        assert c['raw']==original[case]['evaluator'] and c['reference']==original[case]['reference']
        for variant in ['raw','legacy']:
            a=c[variant]['largest_safe']; b=c['reference']['largest_safe']
            c[variant+'_relative_gap']=(a-b)/b if a is not None and b else None
        caps.append(c)
    trials=[]
    originals={(t['group'],t['regime']):t for t in json.loads((FORMAL/'rq3_decision_transfer/summary.json').read_text())['trials']}
    for g in groups():
        if len(g['shifts'])!=5: continue
        for regime in slas(g):
            cs=[c for c in caps if c['group']==g['id'] and c['regime']==regime]
            for variant in ['raw','legacy']:
                d=decision({c['shift']:c[variant]['largest_safe'] or 0. for c in cs},
                           {c['shift']:c['reference']['largest_safe'] or 0. for c in cs})
                if variant=='raw':
                    old=originals[g['id'],regime]
                    for key in ['selected_shift','evaluator_best_set','reference_best_set','reference_regret','normalized_reference_quality']: assert d[key]==old[key]
                trials.append({'group':g['id'],'workload':g['workload'],'regime':regime,'sla_label':label(regime),'variant':variant,
                               **d,'mismatch_type':mismatch(d),'partition_selection_loss':1-d['normalized_reference_quality'] if d['normalized_reference_quality'] is not None else None,
                               'reference_nonmonotone':any(c['reference']['nonmonotone'] for c in cs),
                               'evaluator_nonmonotone':any(c[variant]['nonmonotone'] for c in cs),
                               'evaluator_right_censored':any(c[variant]['right_censored'] for c in cs),
                               'no_safe_candidates':[c['shift'] for c in cs if c[variant]['all_unsafe']]})
    csv_write(OUT/'summary.csv',counts);write_json(OUT/'summary.json',{'protocol_hash':PROTOCOL_HASH,'counts':counts,'capacity':caps})
    csv_write(OUT/'capacity.csv',[{k:v for k,v in c.items() if k not in ['raw','legacy','reference']}|
        {v+'_'+k:x for v in ['raw','legacy','reference'] for k,x in c[v].items() if k not in ['sequence','transitions']} for c in caps])
    write_json(OUT/'decision_summary.json',{'trials':trials});csv_write(OUT/'decision_summary.csv',trials)
    assert protected_manifest()==before
    write_json(OUT/'integrity_checks.json',{'passed':True,'protocol_hash':PROTOCOL_HASH,'baseline_sha256':CONFIG['baseline_sha256'],
        'physical_reference_records_reused':1634,'new_reference_runs':0,'paired_judgments':len(allrows),'configuration_regimes':len(caps),
        'main_trials_per_variant':12,'unique_point_ids':len({r['point_id'] for r in allrows}),
        'protected_files_unchanged':len(before),'workload_partition_profile_grid_reference_labels_verified':True,
        'raw_capacity_and_decisions_exactly_reproduced_from_saved_labels':True,
        'only_changed_semantics':'5 ms fixed overhead enters progress; queue overhead is asserted zero',
        'source_manifest':'source_manifest.json','driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    print(json.dumps(counts,indent=2))

def decomposition():
    snapshot()
    caps=json.loads((OUT/'summary.json').read_text())['capacity']
    trials=json.loads((OUT/'decision_summary.json').read_text())['trials']
    rows=[]
    for t in trials:
        state=json.loads((FORMAL/'groups'/(t['group']+'.json')).read_text())
        s=t['selected_shift']; v=t['variant']; regime=t['regime']
        cs=[c for c in caps if c['group']==t['group'] and c['regime']==regime]
        chosen=next((c for c in cs if c['shift']==s),None)
        load=chosen[v]['largest_safe'] if chosen else None
        best=max(c['reference']['largest_safe'] or 0 for c in cs)
        selected_capacity=chosen['reference']['largest_safe'] if chosen else None
        exact=next((r['reference'][regime]['safe'] for r in state['rows'] if r['shift']==s and r['intensity']==load),None)
        util=load/best if load is not None and best else None
        usable=(load if exact else 0)/best if best else None
        row={**t,'best_set_overlap':sorted(set(t['evaluator_best_set']) & set(t['reference_best_set'])),
             'evaluator_recommended_intensity':load,'exact_recommendation_reference_safe':exact,
             'reference_capacity_selected_partition':selected_capacity,'reference_best_capacity':best,
             'partition_selection_regret':t['partition_selection_loss'],
             'partition_selection_regret_intensity':t['reference_regret'],
             'recommended_load_utilization':util,'operating_point_loss':1-util if util is not None else None,
             'safe_usable_quality':usable,'safe_operating_point_loss':1-usable if usable is not None else None,
             'within_selected_partition_operating_loss':(selected_capacity-load)/best if selected_capacity is not None and load is not None and best else None,
             'evaluator_tie':len(t['evaluator_best_set'])>1,'reference_tie':len(t['reference_best_set'])>1,
             'no_safe_recommendation':load is None,'reference_no_safe_candidates':[c['shift'] for c in cs if c['reference']['all_unsafe']]}
        if row['operating_point_loss'] is not None:
            assert math.isclose(row['partition_selection_regret']+row['within_selected_partition_operating_loss'],row['operating_point_loss'],abs_tol=1e-12)
        rows.append(row)
    policy_rows=[]
    for r in json.loads((FORMAL/'mitigation/results.json').read_text())['rows']:
        if r['candidate_count']!=5:continue
        cs=[c for c in caps if c['group']==r['group'] and c['regime']==r['regime']]
        c=next((c for c in cs if c['shift']==r['chosen_shift']),None)
        best=r['reference_oracle_intensity']; selected=c['reference']['largest_safe'] if c else None
        # A selected partition can itself have no sampled reference-safe point.
        selected_score=(selected or 0.) if c else None
        load=r['reported_intensity']; util=load/best if load is not None and best else None
        policy_rows.append({k:r[k] for k in ['group','regime','bias','policy','chosen_shift','reported_intensity','output_reference_safe','abstention']}|
            {'reference_capacity_selected_partition':selected,'reference_best_capacity':best,
             'partition_selection_loss':1-selected_score/best if selected_score is not None and best else None,
             'operating_point_loss':1-util if util is not None else None,
             'safe_operating_point_loss':1-r['normalized_usable_quality'] if r['normalized_usable_quality'] is not None else None,
             'reference_nonmonotone':any(c['reference']['nonmonotone'] for c in cs)})
    assert len(policy_rows)==144
    write_json(FORMAL/'decision_loss_decomposition.json',{'main_trials_per_variant':12,'rows':rows,'mitigation_main_rows':policy_rows,
       'definitions':{'partition_selection_loss':'1 - Rcapacity(selected) / Rbest',
       'operating_point_loss':'1 - recommended_load / Rbest; descriptive, does not certify safety',
       'safe_operating_point_loss':'1 - (recommended_load if exact reference-safe else 0) / Rbest',
       'additive_identity':'operating_point_loss = partition_selection_loss + (Rcapacity(selected)-recommended_load)/Rbest'}})
    csv_write(FORMAL/'decision_loss_decomposition.csv',rows)
    csv_write(FORMAL/'decision_loss_mitigation.csv',policy_rows)
    print('DECISION_LOSSES',json.dumps([{k:r[k] for k in ['workload','regime','variant','mismatch_type','partition_selection_regret','operating_point_loss','exact_recommendation_reference_safe']} for r in rows],indent=2))

def derating_audit():
    snapshot();data=json.loads((FORMAL/'mitigation/results.json').read_text())['rows'];rows=[]
    for r in data:
        if r['policy']!='capacity_derating_20pct':continue
        base=next(x for x in data if (x['group'],x['regime'],x['bias'],x['policy'])==(r['group'],r['regime'],r['bias'],'evaluator_only'))
        load=base['reported_intensity']; target=load*.8 if load is not None else None; out=r['reported_intensity']
        state=json.loads((FORMAL/'groups'/(r['group']+'.json')).read_text())
        expected=max((v for v in state['grid'] if target is not None and v<=target),default=None)
        assert expected==out
        rows.append({k:r[k] for k in ['group','regime','kind','role','bias','chosen_shift','output_reference_safe','abstention']}|
                    {'sla_label':label(r['regime']),'original_shift':base['chosen_shift'],'original_intensity':load,
                     'target_derating':.2,'target_intensity':target,'grid_snapped_output':out,
                     'realized_derating':1-out/load if load is not None and out is not None else None,
                     'shift_changed_after_snapping':base['chosen_shift']!=r['chosen_shift'],
                     'note':'global candidate tie-break is reapplied after per-candidate snapping'})
    assert len(rows)==56
    summary=[]
    for bias in [1.,.9]:
        rs=[r for r in rows if r['bias']==bias];values=[r['realized_derating'] for r in rs if r['realized_derating'] is not None]
        summary.append({'bias':bias,'cases':len(rs),'defined_realized_derating':len(values),'abstentions':sum(r['abstention'] for r in rs),
                        'min':min(values),'median':statistics.median(values),'max':max(values),
                        'shift_changes_after_snapping':sum(r['shift_changed_after_snapping'] for r in rs),
                        'unsafe_outputs':sum(r['output_reference_safe'] is False for r in rs)})
    csv_write(FORMAL/'mitigation_derating_audit.csv',rows)
    write_json(FORMAL/'mitigation_derating_audit/summary.json',{'label':'20%-target derating with grid snapping','summary':summary,'rows':rows,
         'reference_validation_scope':'conditional reference-validation replay on a frozen grid constructed using reference transition information; grid construction cost is excluded from query counts'})
    print('DERATING',json.dumps(summary,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['legacy','decomposition','derating','all']);args=parser.parse_args()
    if args.stage in ['legacy','all']:sensitivity()
    if args.stage in ['decomposition','all']:decomposition()
    if args.stage in ['derating','all']:derating_audit()
