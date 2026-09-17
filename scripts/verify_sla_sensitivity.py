"""Independent integrity checks against immutable source records and saved runs."""
from sla_sensitivity_common import *
from run_sla_sensitivity import initial_gate
import csv,subprocess

def main():
    guard();initial_gate();data=read(OUT/'summary.json');execution=read(OUT/'execution_summary.json')
    scheduler=read(OUT/'scheduler_snapshot.json')
    assert scheduler['max_workers']==12 and scheduler['budget_bytes']==24*1024**3 and scheduler['reserve_bytes']==6*1024**3
    assert scheduler['peak_active']<=12 and scheduler['peak_reserved_bytes']<=24*1024**3
    assert scheduler['active']==scheduler['pending']==0
    dependency=read(FORMAL/'quality_checks.json')['dependency_source_integrity']
    assert subprocess.check_output(['git','-C',str(HELIX),'rev-parse','HEAD'],text=True).strip()==CONFIG['helix_commit']
    assert not subprocess.check_output(['git','-C',str(HELIX),'status','--porcelain'],text=True).strip()
    for name,sha in dependency['adapter_files_equal_git_objects'].items():
        assert hashlib.sha256((ROOT/'.deps/evaluator'/name).read_bytes()).hexdigest()==sha
    allrows=[];pointkeys=set();physicalkeys=set();attempts=[];gridchecks=[];refchecks=0
    for g in P['groups']:
        wd,base=load_workload(g['workload'])
        assert fingerprint([asdict(r) for r in base])==wd['workload_fingerprint']==g['workload_fingerprint']
        rows=points(g);allrows.extend(rows);grid=sorted({r['intensity'] for r in rows})
        assert set(g['original_grid'])<=set(grid)
        assert min(grid)==min(g['original_grid']) and max(grid)==max(g['original_grid'])
        assert len(grid)-len(g['original_grid'])<=24
        assert not monotonicity(rows)
        for s in g['shifts']:
            assert sorted(r['intensity'] for r in rows if r['shift']==s)==grid
        h=read(OUT/'refinement'/(g['id']+'.json'))
        assert h['final_grid']==grid and h['status']=='complete' and len(h['rounds'])<=6
        assert h['unresolved_transitions']==transitions(rows)
        reconstructed=list(g['original_grid'])
        for rnd in h['rounds']:
            assert rnd['grid_before']==sorted(reconstructed)
            subset=[r for r in rows if r['intensity'] in reconstructed]
            intervals=transitions(subset);assert intervals==rnd['unresolved_before']
            legal=[x for x in intervals if x['lower']<x['midpoint']<x['upper'] and x['midpoint'] not in reconstructed]
            expected=list(dict.fromkeys(x['midpoint'] for x in legal))[:24-(len(reconstructed)-len(g['original_grid']))]
            assert rnd['selected']==expected
            assert rnd['unselected']==[x for x in intervals if x['midpoint'] not in expected]
            reconstructed.extend(expected)
        assert sorted(reconstructed)==grid
        gridchecks.append({'workload':g['workload'],'points':len(rows),'grid_size':len(grid),'shared':True,'refinement_replayed':True})
        for r in rows:
            key=(g['id'],r['shift'],r['intensity']);assert key not in pointkeys;pointkeys.add(key)
            assert r['physical_fingerprint'] not in physicalkeys;physicalkeys.add(r['physical_fingerprint'])
            p,w,expected=point_base(g,r['shift'],r['intensity'])
            for k,v in expected.items():assert r[k]==v,(key,k)
            assert len(r['attempts'])<=2
            attempts.extend(r['attempts'])
            if r['origin']=='stage4_new':
                journal=OUT/'attempts'/g['id']/(fingerprint([r['shift'],r['intensity']])+'.json')
                assert read(journal)==r['attempts']
                assert r['attempts'] and all(a['status'] in ['ok','error','timeout'] for a in r['attempts'])
                if len(r['attempts'])==2:assert r['attempts'][0]['status']!='ok'
            else:assert r['origin']=='stage3_reuse' and not r['attempts']
            assert set(r['evaluator'])==set(P['semantics'])
            for v in P['semantics']:
                assert set(r['evaluator'][v])==set(LIMITS)
                for e in r['evaluator'][v].values():
                    assert isinstance(e['safe'],bool) and e['safe']==(not e['first_violations'])
                    assert not e['safe'] or e['drained']
                    assert e['first_violation']==(e['first_violations'][0] if e['first_violations'] else None)
            if r['status']=='ok':
                raw=read(ROOT/r['reference_path'])
                assert fingerprint(raw['inputs'])==r['reference_cache_key']
                assert physical_fingerprint(raw['inputs'])==r['physical_fingerprint']
                rr=raw['raw'];assert rr['finished_requests']==rr['total_requests']==len(w)
                assert set(rr['query_metrics'])=={x.id for x in w}
                for request in w:
                    m=rr['query_metrics'][request.id]
                    assert len(m['decode_tpot_s'])==request.output_tokens
                    assert m['max_tpot_s']==max(m['decode_tpot_s'])
                assert classify(raw)==r['reference'];refchecks+=8
            else:assert r['status']=='failed' and r['reference']=={}
    assert len(allrows)==execution['total_physical_points']
    assert sum(r['origin']=='stage3_reuse' for r in allrows)==1450
    added=[r for r in allrows if r['origin']=='stage4_new']
    assert len(added)==execution['new_unique_physical_points']<=720
    assert len(attempts)==execution['physical_attempts']
    assert sum(max(0,len(r['attempts'])-1) for r in added)==execution['retries']
    assert sum(a['status']=='timeout' for a in attempts)==execution['timeouts']
    assert sum(r['status']!='ok' for r in allrows)==execution['failed_points']==len(read(OUT/'failed_points.json'))
    assert len(list((OUT/'reference').glob('*.json.gz')))==execution['successful_new_physical_points']
    assert refchecks==execution['reference_sla_classifications']
    assert len(data['judgment'])==96 and len(data['capacity'])==480 and len(data['decisions'])==96
    indexed={(r['group'],r['shift'],r['intensity']):r for r in allrows}
    for c in data['capacity']:
        rs=[r for r in allrows if r['group']==c['group'] and r['shift']==c['shift']]
        for label,model in [('evaluator',c['semantics']),('reference','reference')]:assert c[label]==sampled(rs,model,c['sla'])
        a=c['evaluator']['largest_safe'];b=c['reference']['largest_safe']
        assert c['relative_signed_gap']==((a-b)/b if a is not None and b else None)
    for j in data['judgment']:
        paired=[(verdict(r,j['semantics'],j['sla']),verdict(r,'reference',j['sla'])) for r in allrows if r['group']==j['group'] and r['status']=='ok']
        for field,pair in [('both_safe',(True,True)),('both_unsafe',(False,False)),('optimistic_disagreement',(True,False)),('conservative_disagreement',(False,True))]:assert j[field]==paired.count(pair)
        assert j['paired_denominator']==len(paired)
    for d in data['decisions']:
        expected,_=decision_for([r for r in allrows if r['group']==d['group']],d['sla'],d['semantics'])
        for k,v in expected.items():
            if k.endswith('_scores'):v={str(s):x for s,x in v.items()}
            assert d[k]==v,(d['workload'],d['sla'],k)
        B=d['reference_best_capacity'];S=d['selected_partition_reference_capacity'];L=d['evaluator_recommended_intensity']
        if B and L is not None and S is not None:
            assert math.isclose(d['partition_selection_loss']+d['allocation_component'],d['operating_point_loss'],abs_tol=1e-12)
        if not B:
            assert all(d[k] is None for k in ['partition_selection_loss','operating_point_loss','allocation_component','safe_operating_point_loss'])
        if L is not None:
            point=indexed[d['group'],d['selected_shift'],L]
            assert d['exact_reference_safe']==verdict(point,'reference',d['sla'])
        if d['exact_reference_safe'] is False:assert d['safe_usable_load']==0 and (not B or d['safe_operating_point_loss']==1)
    assert len(data['initial_grid_decision_comparison'])==96
    for r in data['initial_grid_decision_comparison']:
        initial,_=decision_for([p for p in allrows if p['group']==r['group'] and p['origin']=='stage3_reuse'],r['sla'],r['semantics'])
        assert r['initial_selected']==initial['selected_shift'] and r['initial_type']==initial['mismatch_type']
        assert r['type_changed']==(r['initial_type']!=r['final_type'])
    expected_sizes={'raw':len(allrows)*16,'judgment':96,'capacity':480,'decisions':96,'operating_points':96}
    for name,n in expected_sizes.items():
        with (OUT/(name+'.csv')).open(encoding='utf-8',newline='') as f:
            records=list(csv.DictReader(f));assert len(records)==n
        if name=='raw':
            keys={(r['group'],int(r['shift']),float(r['intensity']),r['sla'],r['semantics']) for r in records}
            assert len(keys)==n
            for r in records:
                point=indexed[r['group'],int(r['shift']),float(r['intensity'])]
                assert r['evaluator_safe']==str(verdict(point,r['semantics'],r['sla']))
                assert r['reference_safe']==('' if verdict(point,'reference',r['sla']) is None else str(verdict(point,'reference',r['sla'])))
    result={'passed':True,'protocol_hash':PH,'protected_hashes_unchanged':len(read(OUT/'source_manifest.json')),
      'checks':{k:True for k in ['protocol_hash','workload_fingerprints','partition_fingerprints','profile_fingerprints','network_unchanged',
        'candidate_grids_equal','sla_monotonicity','original_stage3_labels_and_decisions','full_drain_and_per_token_completeness',
        'failure_retry_accounting','all_new_points_across_five_candidates','all_reference_metrics_across_eight_slas',
        'no_hidden_dropped_cases','ties_retained','no_safe_retained','nonmonotone_retained','unresolved_brackets_retained',
        'exact_recommendation_safety','loss_identity','refinement_priority_and_budget','frozen_dependency_sources','original_memory_scheduling_limits']},
      'grids':gridchecks,'physical_points':len(allrows),'new_physical_points':len(added),'paired_rows':execution['evaluator_judgments'],
      'capacity_rows':480,'decision_rows':96,
      'retained_flags':{m:{flag:sum(c[m][flag] for c in data['capacity']) for flag in ['no_safe','nonmonotone','right_censored','unresolved']} for m in ['evaluator','reference']},
      'reference_flag_count_note':'reference flags repeat once per evaluator semantic in the 480 capacity rows',
      'source_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'scripts').glob('*sla_sensitivity*.py')}}
    guard();write_json(OUT/'quality_checks.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':main()
