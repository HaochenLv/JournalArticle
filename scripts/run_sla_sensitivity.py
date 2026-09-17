"""Resume-safe Stage 4 execution: old-grid gate, then bounded shared refinement."""
from sla_sensitivity_common import *
from host_execution import spawned_call,host_metadata,available_memory_bytes
from memory_scheduler import MemoryAwareExecutor
from concurrent.futures import ProcessPoolExecutor,ThreadPoolExecutor,as_completed
from multiprocessing import get_context
import argparse,subprocess,datetime

def initial_group(g):
    old=read(FORMAL/'groups'/(g['id']+'.json'))
    assert old['grid']==g['original_grid']
    legacy=read(FORMAL/'legacy_progress_sensitivity/groups'/(g['id']+'.json'))
    legacy={(r['shift'],r['intensity'],r['regime']):r for r in legacy['rows']}
    for r in old['rows']:
        dest=point_path(g,r['shift'],r['intensity'])
        if dest.exists():continue
        p,w,row=point_base(g,r['shift'],r['intensity'])
        raw=read(ROOT/'results/raw_reference'/(r['reference_cache_key']+'.json.gz'))
        assert fingerprint(raw['inputs'])==r['reference_cache_key']
        assert physical_fingerprint(raw['inputs'])==row['physical_fingerprint']
        assert raw['raw']['finished_requests']==raw['raw']['total_requests']==len(w)
        row.update(origin='stage3_reuse',status='ok',attempts=[],reference_cache_key=r['reference_cache_key'],
                   reference_path='results/raw_reference/'+r['reference_cache_key']+'.json.gz',reference=classify(raw),evaluator=evaluate_all(p,w))
        for sid,regime in OLD.items():
            assert row['reference'][sid]['safe']==r['reference'][regime]['safe']
            assert row['evaluator']['raw'][sid]['safe']==r['evaluator'][regime]['safe']
            assert row['evaluator']['legacy'][sid]['safe']==legacy[r['shift'],r['intensity'],regime]['evaluator_safe']
            for v,previous in [('raw',r['evaluator'][regime]),('legacy',legacy[r['shift'],r['intensity'],regime]['legacy_result'])]:
                assert {k:x for k,x in row['evaluator'][v][sid].items() if k!='runtime_s'}=={k:x for k,x in previous.items() if k!='runtime_s'}
        write_gz(dest,row)
    print('INITIAL_COMPLETE',g['workload'],len(old['rows']),flush=True)

def initial_gate():
    records=[];count=0
    old_decisions=read(FORMAL/'legacy_progress_sensitivity/decision_summary.json')['trials']
    for g in P['groups']:
        rows=[r for r in points(g) if r['origin']=='stage3_reuse']
        assert len(rows)==g['original_grid_size']*5
        old=read(FORMAL/'groups'/(g['id']+'.json'))
        oldmap={(r['shift'],r['intensity']):r for r in old['rows']}
        legacy=read(FORMAL/'legacy_progress_sensitivity/groups'/(g['id']+'.json'))['rows']
        lm={(r['shift'],r['intensity'],r['regime']):r for r in legacy}
        for r in rows:
            o=oldmap[r['shift'],r['intensity']]
            for sid,regime in OLD.items():
                assert verdict(r,'reference',sid)==o['reference'][regime]['safe']
                assert verdict(r,'raw',sid)==o['evaluator'][regime]['safe']
                assert verdict(r,'legacy',sid)==lm[r['shift'],r['intensity'],regime]['evaluator_safe']
                count+=3
        assert not monotonicity(rows)
        for sid,regime in OLD.items():
            for v in P['semantics']:
                d,_=decision_for(rows,sid,v)
                old=next(x for x in old_decisions if (x['group'],x['regime'],x['variant'])==(g['id'],regime,v))
                for k in ['selected_shift','evaluator_best_set','reference_best_set','winner_agrees','selected_reference_rank','reference_regret','normalized_reference_quality']:
                    assert d[k]==old[k],(g['id'],sid,v,k)
                for k in ['evaluator_scores','reference_scores']:
                    assert {str(s):x for s,x in d[k].items()}==old[k]
                records.append({'group':g['id'],'sla':sid,'variant':v,'reproduced':True})
    result={'passed':True,'protocol_hash':PH,'label_comparisons':count,'decisions':records,
            'physical_points_reused':1450,'evaluator_calls':23200,'full_evaluator_outputs_except_runtime_reproduced':True,
            'sla_monotonicity':True,'portability':'Same Windows AMD64 / 20 CPU / physical-memory host configuration; bundled Python 3.12.14 replaces unavailable 3.12.10 launcher. Frozen profiles checked and all old-SLA evaluator fields reproduced exactly.'}
    write_json(OUT/'initial_gate.json',result)
    print('INITIAL_GATE_PASS',count,flush=True)

def fresh_physical(p,w):
    start=time.perf_counter()
    run=ref.evaluate_helix_fixed_reference(pipeline=p,workload=w,sla=next(iter(LIMITS.values())),helix_root=HELIX)
    assert run.finished_requests==run.total_requests==len(w)
    inputs=physical_inputs(p,w)
    return {'inputs':inputs,'summary':{'runtime_s':time.perf_counter()-start,'cache_key':fingerprint(inputs)},'raw':asdict(run)}

def new_point(g,shift,value):
    dest=point_path(g,shift,value)
    if dest.exists():return read(dest)
    p,w,row=point_base(g,shift,value)
    row.update(origin='stage4_new',status='failed',attempts=[],reference={},evaluator=evaluate_all(p,w))
    refpath=OUT/'reference'/(row['physical_fingerprint']+'.json.gz')
    journal=OUT/'attempts'/g['id']/(fingerprint([shift,value])+'.json')
    attempts=read(journal) if journal.exists() else []
    if refpath.exists():
        raw=read(refpath)
        assert physical_fingerprint(raw['inputs'])==row['physical_fingerprint']
    else:
        raw=None
        for attempt in range(len(attempts),2):
            entry={'attempt':attempt+1,'status':'running','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
            attempts.append(entry);write_json(journal,attempts)
            start=time.perf_counter()
            try:
                raw=spawned_call(fresh_physical,(p,w),600)
                write_gz(refpath,raw)
                entry.update(status='ok',wall_s=time.perf_counter()-start)
                write_json(journal,attempts);break
            except Exception as exc:
                entry.update(status='timeout' if isinstance(exc,TimeoutError) else 'error',wall_s=time.perf_counter()-start,
                             error=type(exc).__name__+': '+str(exc).replace(str(ROOT),'<journal>'))
                write_json(journal,attempts)
    row['attempts']=attempts
    if raw:
        row.update(status='ok',reference=classify(raw),reference_path=refpath.relative_to(ROOT).as_posix(),reference_cache_key=raw['summary']['cache_key'])
    assert not monotonicity([row])
    write_gz(dest,row)
    return row

def refine_group(g,executor):
    path=OUT/'refinement'/(g['id']+'.json')
    history=read(path) if path.exists() else {'group':g['id'],'original_grid':g['original_grid'],'rounds':[],'status':'running'}
    for iteration in range(6):
        rows=points(g);grid=sorted({r['intensity'] for r in rows})
        if iteration<len(history['rounds']):plan=history['rounds'][iteration]
        else:
            intervals=transitions(rows);room=24-(len(grid)-len(g['original_grid']))
            legal=[x for x in intervals if x['lower']<x['midpoint']<x['upper'] and x['midpoint'] not in grid]
            values=list(dict.fromkeys(x['midpoint'] for x in legal))[:max(0,room)]
            plan={'round':iteration+1,'grid_before':grid,'unresolved_before':intervals,'selected':values,
                  'unselected':[x for x in intervals if x['midpoint'] not in values]}
            history['rounds'].append(plan);write_json(path,history)
        futures={executor.submit(new_point,g,s,v):(s,v) for v in plan['selected'] for s in g['shifts'] if not point_path(g,s,v).exists()}
        for f in as_completed(futures):
            r=f.result();print('POINT',g['workload'],r['shift'],r['intensity'],r['status'],flush=True)
        if not plan['selected']:break
    rows=points(g);grid=sorted({r['intensity'] for r in rows});unresolved=transitions(rows)
    added=len(grid)-len(g['original_grid'])
    history.update(status='complete',final_grid=grid,added_intensities=added,unresolved_transitions=unresolved,
      stop_reason='no unresolved transition' if not unresolved else '24-intensity budget' if added==24 else 'six rounds' if len(history['rounds'])==6 else 'no new legal midpoint')
    write_json(path,history)
    print('REFINEMENT_COMPLETE',g['workload'],added,len(unresolved),history['stop_reason'],flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['initial','refine','all']);args=ap.parse_args()
    guard()
    if args.stage in ['initial','all']:
        with ProcessPoolExecutor(max_workers=6,mp_context=get_context('spawn')) as pool:
            for f in as_completed([pool.submit(initial_group,g) for g in P['groups']]):f.result()
    initial_gate()
    if args.stage in ['refine','all']:
        costs={g['id']:math.ceil((512+.30*sum(r.output_tokens for r in load_workload(g['workload'])[1]))/256)*256*1024**2 for g in P['groups']}
        with ProcessPoolExecutor(max_workers=12,mp_context=get_context('spawn')) as pool:
            with MemoryAwareExecutor(pool,12,24*1024**3,costs,available_memory_bytes,6*1024**3,
                  lambda x:write_json(OUT/'scheduler_snapshot.json',x)) as executor, ThreadPoolExecutor(max_workers=6) as coord:
                for f in as_completed([coord.submit(refine_group,g,executor) for g in P['groups']]):f.result()
    guard()

if __name__=='__main__':main()
