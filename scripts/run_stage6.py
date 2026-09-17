"""Bounded Stage 6 execution using immutable JB1 and memory-controlled HELIX."""
from stage6_common import *
from host_execution import spawned_call,available_memory_bytes
from memory_scheduler import MemoryAwareExecutor
from concurrent.futures import ProcessPoolExecutor,ThreadPoolExecutor,as_completed
from multiprocessing import get_context
import argparse,datetime

OLD_SLAS=['TTFT5.2_TPOT0.3','TTFT5.2_TPOT5','TTFT5.2_TPOT10']

def initial_group(g):
    previous=sorted((ROOT/'results/sla_sensitivity/points'/g['id']).glob('*.json.gz'))
    for source in previous:
        old=read(source);dest=point_path(g,old['shift'],old['intensity'])
        if dest.exists():continue
        p,w,row=point_base(g,old['shift'],old['intensity'])
        assert row['physical_fingerprint']==old['physical_fingerprint']
        raw=read(ROOT/old['reference_path'])
        ev={v:{sid:old['evaluator'][v][sid] for sid in OLD_SLAS} for v in P['semantics']}
        prof=CachedProfiles()
        for v,opts in P['semantics'].items():
            for sid,sla in LIMITS.items():
                if sid not in OLD_SLAS:ev[v][sid]=jb(p,w,sla,prof,fixed_in_progress=opts['fixed_in_progress'])
        row.update(origin='stage4_reuse',status=old['status'],attempts=[],reference_path=old['reference_path'],
          reference_cache_key=old['reference_cache_key'],reference=classify(raw),evaluator=ev,
          stage4_source=source.relative_to(ROOT).as_posix(),new_evaluator_calls=10,reused_evaluator_outputs=6)
        assert not monotonicity([row]);write_gz(dest,row)
    print('INITIAL_COMPLETE',g['workload'],len(previous),flush=True)

def initial_gate():
    oldsummary=read(ROOT/'results/sla_sensitivity/summary.json');labels=outputs=caps=decs=0
    for g in P['groups']:
        rows=[r for r in points(g) if r['origin']=='stage4_reuse']
        assert len(rows)==g['original_grid_size']*5
        for r in rows:
            old=read(ROOT/r['stage4_source'])
            for sid in OLD_SLAS:
                for k,v in old['reference'][sid].items():assert r['reference'][sid][k]==v,(g['id'],k)
                labels+=1
                for v in P['semantics']:
                    assert r['evaluator'][v][sid]==old['evaluator'][v][sid];outputs+=1;labels+=1
        assert not monotonicity(rows)
        for sid in OLD_SLAS:
            for v in P['semantics']:
                d,cs=decision_for(rows,sid,v)
                old=next(x for x in oldsummary['decisions'] if (x['group'],x['sla'],x['semantics'])==(g['id'],sid,v))
                for k,x in d.items():
                    if k.endswith('_scores'):x={str(s):a for s,a in x.items()}
                    assert old[k]==x,(g['id'],sid,v,k)
                decs+=1
                for s,c in cs.items():
                    old=next(x for x in oldsummary['capacity'] if (x['group'],x['sla'],x['semantics'],x['shift'])==(g['id'],sid,v,s))
                    assert old['reference']==c['reference'] and old['evaluator']==c[v];caps+=1
                old=next(x for x in oldsummary['judgment'] if (x['group'],x['sla'],x['semantics'])==(g['id'],sid,v))
                pairs=[(verdict(r,v,sid),verdict(r,'reference',sid)) for r in rows]
                for field,pair in [('both_safe',(True,True)),('both_unsafe',(False,False)),('optimistic_disagreement',(True,False)),('conservative_disagreement',(False,True))]:assert old[field]==pairs.count(pair)
    write_json(OUT/'initial_gate.json',{'passed':True,'label_comparisons':labels,'full_evaluator_outputs_reused_exactly':outputs,
      'capacity_reproduced':caps,'decisions_reproduced':decs,'old_judgments_reproduced':True,'initial_helix_runs':0,
      'new_evaluator_calls':20500,'new_slas':[.1,.15,.2,.25,.5]})
    print('INITIAL_GATE_PASS',labels,outputs,caps,decs,flush=True)

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
    row.update(origin='stage6_new',status='failed',attempts=[],reference={},evaluator=evaluate_all(p,w))
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
    for iteration in range(4):
        rows=points(g);grid=sorted({r['intensity'] for r in rows})
        if iteration<len(history['rounds']):plan=history['rounds'][iteration]
        else:
            intervals=transitions(rows);room=4-(len(grid)-len(g['original_grid']))
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
      stop_reason='no unresolved transition' if not unresolved else '4-intensity budget' if added==4 else 'four rounds' if len(history['rounds'])==4 else 'no new legal midpoint')
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
                  lambda x:write_json(OUT/'scheduler_snapshot.json',x)) as executor,ThreadPoolExecutor(max_workers=6) as coord:
                for f in as_completed([coord.submit(refine_group,g,executor) for g in P['groups']]):f.result()
    guard()

if __name__=='__main__':main()
