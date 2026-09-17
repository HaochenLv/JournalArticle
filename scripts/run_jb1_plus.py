"""One-shot evaluator correction: cache-only Phase A, bounded Phase B."""
from jb1_plus_common import *
from host_execution import spawned_call,available_memory_bytes
from memory_scheduler import MemoryAwareExecutor
from concurrent.futures import ProcessPoolExecutor,ThreadPoolExecutor,as_completed
from multiprocessing import get_context
import argparse,datetime

def phase_a_group(g):
 sources=sorted((ROOT/'results/sla_sensitivity/points'/g['id']).glob('*.json.gz'))
 for path in sources:
  old=read(path);s=old['shift'];v=old['intensity'];dest=point_path('a',g,s,v)
  if dest.exists():continue
  p=pipeline(g['link'],s,True);w=scale_workload(load_workload(g['workload'])[1],v)
  row={k:x for k,x in old.items() if k!='evaluator'}
  row.update(origin='phase_a_stage4_reuse',protocol_hash=PH,source_point=path.relative_to(ROOT).as_posix(),attempts=[],
   evaluator={'Raw-Full':old['evaluator']['raw'],'Legacy-Full':old['evaluator']['legacy'],**evaluate_all(p,w,limits('a'),['Raw-Remaining','Legacy-Remaining'])})
  write_gz(dest,row)
 print('PHASE_A_COMPLETE',g['workload'],len(sources),flush=True)

def a100_group(g):
 original=read(FORMAL/'groups'/(g['id']+'.json'))
 legacy=read(FORMAL/'legacy_progress_sensitivity/groups'/(g['id']+'.json'))['rows']
 lm={(r['shift'],r['intensity'],r['regime']):r['legacy_result'] for r in legacy}
 sl=slas(g)
 for old in original['rows']:
  s=old['shift'];v=old['intensity'];dest=point_path('controls',g,s,v)
  if dest.exists():continue
  p=pipeline(g['link'],s,False);w=scale_workload(load_workload(g['workload'])[1],v)
  row={'group':g['id'],'workload':g['workload'],'shift':s,'intensity':v,'origin':'a100_reuse','status':old['status'],'attempts':[],
   'reference_cache_key':old['reference_cache_key'],'reference_path':'results/raw_reference/'+old['reference_cache_key']+'.json.gz',
   'reference':old['reference'],'evaluator':{'Raw-Full':old['evaluator'],'Legacy-Full':{sid:lm[s,v,sid] for sid in sl},**evaluate_all(p,w,sl,['Raw-Remaining','Legacy-Remaining'])}}
  write_gz(dest,row)
 print('A100_COMPLETE',g['workload'],len(original['rows']),flush=True)

def fresh_physical(p,w):
 start=time.perf_counter();run=ref.evaluate_helix_fixed_reference(pipeline=p,workload=w,sla=next(iter(limits('b').values())),helix_root=HELIX)
 assert run.finished_requests==run.total_requests==len(w);inputs=physical_inputs(p,w)
 return {'inputs':inputs,'summary':{'runtime_s':time.perf_counter()-start,'cache_key':fingerprint(inputs)},'raw':asdict(run)}

def new_point(g,s,v):
 dest=point_path('b',g,s,v)
 if dest.exists():return read(dest)
 p,w,row=b_base(g,s,v);row.update(status='failed',attempts=[],reference={},evaluator=evaluate_all(p,w,limits('b')))
 path=OUT/'reference'/(row['physical_fingerprint']+'.json.gz');journal=OUT/'attempts'/g['id']/(fingerprint([s,v])+'.json')
 attempts=read(journal) if journal.exists() else [];raw=None
 if path.exists():raw=read(path);assert physical_fingerprint(raw['inputs'])==row['physical_fingerprint']
 else:
  for attempt in range(len(attempts),2):
   entry={'attempt':attempt+1,'status':'running','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};attempts.append(entry);write_json(journal,attempts);start=time.perf_counter()
   try:
    raw=spawned_call(fresh_physical,(p,w),600);write_gz(path,raw);entry.update(status='ok',wall_s=time.perf_counter()-start);write_json(journal,attempts);break
   except Exception as exc:
    entry.update(status='timeout' if isinstance(exc,TimeoutError) else 'error',wall_s=time.perf_counter()-start,error=type(exc).__name__+': '+str(exc).replace(str(ROOT),'<journal>'));write_json(journal,attempts)
 row['attempts']=attempts
 if raw:row.update(status='ok',reference=classify(raw,limits('b')),reference_path=path.relative_to(ROOT).as_posix(),reference_cache_key=raw['summary']['cache_key'])
 assert not monotonicity([row],limits('b'));write_gz(dest,row);return row

def b_group(g,executor):
 initial=P['phase_b']['initial_grid'];path=OUT/'refinement'/(g['id']+'.json')
 h=read(path) if path.exists() else {'group':g['id'],'initial_grid':initial,'rounds':[],'status':'running'}
 def execute(values):
  fs=[executor.submit(new_point,g,s,v) for v in values for s in g['shifts'] if not point_path('b',g,s,v).exists()]
  for f in as_completed(fs):
   r=f.result();print('POINT',g['workload'],r['shift'],r['intensity'],r['status'],flush=True)
 execute(initial)
 for iteration in range(4):
  rows=points('b',g);grid=sorted({r['intensity'] for r in rows})
  if iteration<len(h['rounds']):plan=h['rounds'][iteration]
  else:
   intervals=transitions(rows);room=16-(len(grid)-len(initial));legal=[x for x in intervals if x['lower']<x['midpoint']<x['upper'] and x['midpoint'] not in grid]
   values=list(dict.fromkeys(x['midpoint'] for x in legal))[:max(0,room)]
   plan={'round':iteration+1,'grid_before':grid,'unresolved_before':intervals,'selected':values,'unselected':[x for x in intervals if x['midpoint'] not in values]};h['rounds'].append(plan);write_json(path,h)
  execute(plan['selected'])
  if not plan['selected']:break
 rows=points('b',g);grid=sorted({r['intensity'] for r in rows});unresolved=transitions(rows);added=len(grid)-len(initial)
 h.update(status='complete',final_grid=grid,added_intensities=added,unresolved_transitions=unresolved,stop_reason='no unresolved transitions' if not unresolved else '16-intensity budget' if added==16 else 'four rounds' if len(h['rounds'])==4 else 'no legal midpoint')
 write_json(path,h);print('PHASE_B_COMPLETE',g['workload'],len(rows),len(unresolved),flush=True)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['a','b','all']);args=ap.parse_args();guard()
 if args.phase in ['a','all']:
  with ProcessPoolExecutor(max_workers=6,mp_context=get_context('spawn')) as pool:
   for f in as_completed([pool.submit(phase_a_group,g) for g in P['phase_a']['groups']]+[pool.submit(a100_group,g) for g in groups() if g['kind']=='a100']):f.result()
 if args.phase in ['b','all']:
  gs=b_groups();costs={g['id']:math.ceil((512+.30*sum(r.output_tokens for r in b_workload(g)[1]))/256)*256*1024**2 for g in gs}
  with ProcessPoolExecutor(max_workers=12,mp_context=get_context('spawn')) as pool:
   with MemoryAwareExecutor(pool,12,24*1024**3,costs,available_memory_bytes,6*1024**3,lambda x:write_json(OUT/'scheduler_snapshot.json',x)) as executor,ThreadPoolExecutor(max_workers=4) as coord:
    for f in as_completed([coord.submit(b_group,g,executor) for g in gs]):f.result()
 guard()

if __name__=='__main__':main()
