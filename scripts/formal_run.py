"""Shared adaptive grids, resumable paired runs, explicit failures; FI-JB1-v1."""
from pathlib import Path
import sys,json,math,time,signal,gzip,argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from formal_core import *
from host_execution import spawned_call,host_metadata

def execute_point(group,shift,value):
 wd,base=load_workload(group['workload']);limits=slas(group)
 p=pipeline(group['link'],shift,group['kind']=='heterogeneous');prof=CachedProfiles()
 def alarm(signum,frame):raise TimeoutError('formal reference wall timeout')
 if hasattr(signal,'SIGALRM'):signal.signal(signal.SIGALRM,alarm)
 value=round(value,10)
 w=scale_workload(base,value)
 row={'shift':shift,'intensity':value,'partition_fingerprint':fingerprint(asdict(p)),'scaled_workload_fingerprint':fingerprint([asdict(x) for x in w]),'evaluator':{},'reference':{},'status':'ok','attempts':[],'execution_host':host_metadata()}
 for regime,sla in limits.items():
  try:row['evaluator'][regime]=jb(p,w,sla,prof)
  except Exception as e:row['status']='error';row['attempts'].append({'part':'evaluator','regime':regime,'error':type(e).__name__+': '+str(e).replace(str(ROOT),'<journal>')})
 before={x.name[:-8] for x in (ROOT/'results/raw_reference').glob('*.json.gz')}
 for attempt in range(2):
  start=time.perf_counter()
  try:
   if hasattr(signal,'SIGALRM'):
    signal.alarm(CONFIG['timeout_s']);summary=reference(p,w,next(iter(limits.values())));signal.alarm(0)
   else:summary=spawned_call(reference,(p,w,next(iter(limits.values()))),CONFIG['timeout_s'])
   with gzip.open(ROOT/'results/raw_reference'/(summary['cache_key']+'.json.gz'),'rt') as f:raw=json.load(f)
   assert raw['raw']['finished_requests']==raw['raw']['total_requests']==len(w)
   row['reference']={regime:reference_details(raw,sla) for regime,sla in limits.items()}
   row['reference_cache_key']=summary['cache_key'];row['reference_was_cached']=summary['cache_key'] in before or 'derived_from' in raw
   handoff=FORMAL/'machine_handoff.json'
   inherited=set(json.loads(handoff.read_text())['cache_keys_present_before_transfer']) if handoff.exists() else set()
   row['reference_runtime_origin']='laptop_pretransfer' if summary['cache_key'] in inherited or raw.get('derived_from') in inherited else 'current_host'
   row['reference_physical_runtime_s']=summary['runtime_s'];row['reference_access_wall_s']=time.perf_counter()-start
   row['attempts'].append({'part':'reference','attempt':attempt+1,'status':'ok','wall_s':row['reference_access_wall_s']});break
  except Exception as e:
   if hasattr(signal,'SIGALRM'):signal.alarm(0)
   row['attempts'].append({'part':'reference','attempt':attempt+1,'status':'error','wall_s':time.perf_counter()-start,'error':type(e).__name__+': '+str(e).replace(str(ROOT),'<journal>')})
 if not row['reference']:row['status']='error'
 return row

def run_group(group,executor):
 check_pins();dest=FORMAL/'groups'/(group['id']+'.json');dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists():
  state=json.loads(dest.read_text());assert state['protocol_hash']==PROTOCOL_HASH
  if state['status']=='complete':return {'group':group['id'],'status':'cached_complete','points':len(state['rows'])}
 else:state={'protocol_hash':PROTOCOL_HASH,'group':group,'status':'running','stages':{},'rows':[],'elapsed_s':0.}
 begin=time.perf_counter();prior_elapsed=state['elapsed_s'];wd,base=load_workload(group['workload']);limits=slas(group)
 state['workload_fingerprint']=wd['workload_fingerprint'];state['profile_fingerprint']=CONFIG['profile_fingerprint'];state['baseline_sha256']=CONFIG['baseline_sha256']
 rows={(r['shift'],r['intensity']):r for r in state['rows']};ps={s:pipeline(group['link'],s,group['kind']=='heterogeneous') for s in group['shifts']};prof=CachedProfiles()
 def save():
  state['rows']=sorted(rows.values(),key=lambda r:(r['intensity'],r['shift']));state['elapsed_s']=prior_elapsed+time.perf_counter()-begin;write_json(dest,state)
 def stage(name,values):
  if name not in state['stages']:state['stages'][name]=sorted(set(round(v,10) for v in values));save()
  from concurrent.futures import as_completed
  futures={executor.submit(execute_point,group,shift,v):(shift,v) for v in state['stages'][name] for shift in group['shifts'] if (shift,v) not in rows}
  for f in as_completed(futures):
   shift,v=futures[f];row=f.result();rows[shift,v]=row;save()
   print(json.dumps({'group':group['id'],'shift':shift,'load':v,'status':row['status'],'E':{k:x['safe'] for k,x in row['evaluator'].items()},'R':{k:x['safe'] for k,x in row['reference'].items()}}),flush=True)
 def any_endpoint(value,safe):
  return any(v['safe']==safe for s in group['shifts'] for model in ['evaluator','reference'] for v in rows[s,value][model].values())
 stage('initial',CONFIG['initial_grid'])
 low=min(CONFIG['initial_grid']);j=0
 while low>CONFIG['minimum_probe'] and any_endpoint(low,False):
  low=round(max(CONFIG['minimum_probe'],low/4),10);stage('lower-'+str(j),[low]);j+=1
 high=max(CONFIG['initial_grid']);j=0
 while high<CONFIG['maximum_probe'] and any_endpoint(high,True):
  high=round(min(CONFIG['maximum_probe'],high*2),10);stage('upper-'+str(j),[high]);j+=1
 for iteration in range(CONFIG['max_refinement_rounds']):
  name='refinement-'+str(iteration)
  if name in state['stages']:stage(name,[]);continue
  grid=sorted({v for s,v in rows});intervals=[]
  for a,b in zip(grid,grid[1:]):
   if b/a-1<=CONFIG['relative_transition_resolution']:continue
   changed=any(rows[s,a][model].get(regime,{}).get('safe')!=rows[s,b][model].get(regime,{}).get('safe') for s in group['shifts'] for model in ['evaluator','reference'] for regime in limits if rows[s,a]['status']=='ok' and rows[s,b]['status']=='ok')
   if changed:intervals.append((a,b))
  intervals.sort(key=lambda ab:(-math.log(ab[1]/ab[0]),ab[0]));room=max(0,CONFIG['max_common_grid_points']-len(grid))
  values=[math.sqrt(a*b) for a,b in intervals[:room]];stage(name,values)
  if not values:break
 state['grid']=sorted({v for s,v in rows});state['status']='complete';state['failed_points']=sum(r['status']!='ok' for r in rows.values());save()
 return {'group':group['id'],'status':'complete','points':len(rows),'loads':len(state['grid']),'failures':state['failed_points'],'elapsed_s':state['elapsed_s']}

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--group');ap.add_argument('--workers',type=int,default=CONFIG['workers']);args=ap.parse_args()
 selected=[g for g in groups() if args.group is None or g['id']==args.group]
 if args.group and not selected:raise SystemExit('unknown group')
 selected.sort(key=lambda g:load_workload(g['workload'])[0]['features']['request_count']*len(g['shifts']),reverse=True)
 from concurrent.futures import ProcessPoolExecutor,ThreadPoolExecutor,as_completed
 from multiprocessing import get_context
 # Explicit spawn also avoids forking a multithreaded coordinator on Linux.
 with ProcessPoolExecutor(max_workers=args.workers,initializer=check_pins,mp_context=get_context('spawn')) as pool, ThreadPoolExecutor(max_workers=len(selected)) as coordinators:
  futures={coordinators.submit(run_group,g,pool):g['id'] for g in selected}
  for f in as_completed(futures):
   try:print('GROUP_COMPLETE',json.dumps(f.result()),flush=True)
   except Exception as e:print('GROUP_ERROR',futures[f],repr(e),flush=True);raise
