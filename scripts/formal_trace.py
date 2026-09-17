"""Read-only runtime instrumentation of pinned HELIX; full metric equality gate."""
from pathlib import Path
import sys,json,gzip,argparse,collections,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from formal_core import *

def run(group_id,shift,intensity,regime,pp=1.,dd=1.,name=None):
 check_pins();g=next(g for g in groups() if g['id']==group_id)
 state=json.loads((FORMAL/'groups'/(group_id+'.json')).read_text())
 row=next(r for r in state['rows'] if r['shift']==shift and r['intensity']==intensity)
 assert row['status']=='ok'
 wd,base=load_workload(g['workload']);w=scale_workload(base,intensity)
 p=pipeline(g['link'],shift,g['kind']=='heterogeneous');sla=slas(g)[regime]
 with gzip.open(ROOT/'results/raw_reference'/(row['reference_cache_key']+'.json.gz'),'rt') as f:original=json.load(f)
 e=jb(p,w,sla,CachedProfiles(pp,dd),trace=True,drain=True)
 captured={};batches=[];queries={};runtime=ref._load_helix_runtime(HELIX)
 old_build=ref._build_helix_simulator;old_extract=ref.extract_helix_query_metrics;old_start=runtime.ClusterSimulator.handle_start_execution
 def build(**kwargs):
  sim,mini,mapping=old_build(**kwargs);captured.update(sim=sim,base_time=sim.current_time,node_mapping=mapping);return sim,mini,mapping
 def start(sim,event):
  result=old_start(sim,event)
  if result[0]!=-1:
   node=event.args['node'];batch=node.current_inference_batch
   batches.append({'start_s':sim.current_time-captured['base_time'],'end_s':result[2]-captured['base_time'],'node':node.node_uid,'layer':node.get_current_inference_layer(),'requests':[r.request_uid for r in batch.requests],'phases':[r.phase.name for r in batch.requests]})
  return result
 def extract(*,request_id,query,overhead_s=0.):
  origin=captured['base_time'];sim=captured['sim'];hist=[]
  for item in query.inference_history:
   request=sim.finished_requests[item.request_uid][1]
   hist.append({'uid':item.request_uid,'phase':item.request_phase.name,'start_s':item.start_time-origin,'end_s':item.end_time-origin,'duration_s':item.end_time-item.start_time,'tokens':item.token_seq_length,'prev_tokens':item.prev_num_tokens,'locations':[(loc,t-origin) for loc,t in request.location_history]})
  queries[request_id]={'arrival_s':query.creation_time-origin,'iterations':hist}
  return old_extract(request_id=request_id,query=query,overhead_s=overhead_s)
 ref._build_helix_simulator=build;ref.extract_helix_query_metrics=extract;runtime.ClusterSimulator.handle_start_execution=start
 begin=time.perf_counter()
 try:r=ref.evaluate_helix_fixed_reference(pipeline=p,workload=w,sla=sla,helix_root=HELIX)
 finally:ref._build_helix_simulator=old_build;ref.extract_helix_query_metrics=old_extract;runtime.ClusterSimulator.handle_start_execution=old_start
 raw=json.loads(json.dumps(asdict(r)))
 assert raw['query_metrics']==original['raw']['query_metrics'],'Instrumentation changed metrics'
 assert raw['finished_requests']==raw['total_requests']==len(w)
 # Thresholds can differ from the cached record; physical histories must not.
 assert raw['final_time_s']==original['raw']['final_time_s']
 violations=[]
 for rid,q in queries.items():
  for j,it in enumerate(q['iterations']):
   value=it['duration_s']+sla.fixed_overhead_s+sla.queue_overhead_s;limit=sla.ttft_s if j==0 else sla.tpot_s
   if value>limit:violations.append({'request_id':rid,'iteration':j,'phase':it['phase'],'observed_s':value,'limit_s':limit,'physical_end_s':it['end_s'],'uid':it['uid']})
 violations.sort(key=lambda x:(x['physical_end_s'],x['request_id'],x['iteration']))
 target_ids=set()
 if e['first_violation'] and 'request_id' in e['first_violation']:target_ids.add(e['first_violation']['request_id'])
 if violations:target_ids.add(violations[0]['request_id'])
 target_ids.add(max(raw['query_metrics'],key=lambda rid:raw['query_metrics'][rid]['max_tpot_s']))
 target_ids.add(max(raw['query_metrics'],key=lambda rid:raw['query_metrics'][rid]['aligned_ttft_s']))
 # Keep Prefill, worst Decode, and reference-first-violation iterations in detail.
 selected_uids=set()
 for rid in target_ids:
  its=queries[rid]['iterations'];selected_uids.add(its[0]['uid']);selected_uids.add(max(its[1:],key=lambda it:it['duration_s'])['uid'])
 if violations:selected_uids.add(violations[0]['uid'])
 chosen_batches=[b for b in batches if selected_uids.intersection(b['requests'])]
 concurrency=[]
 for snap in e['trace']:
  t=snap['time_s'];npre=sum(q['iterations'][0]['start_s']<=t<q['iterations'][0]['end_s'] for q in queries.values());ndec=sum(q['iterations'][0]['end_s']<=t<q['iterations'][-1]['end_s'] for q in queries.values())
  concurrency.append({'time_s':t,'side':snap['side'],'evaluator_prefill':snap['num_prefill'],'evaluator_decode':snap['num_decode'],'reference_prefill':npre,'reference_decode':ndec})
 details={'protocol_hash':PROTOCOL_HASH,'group':g,'shift':shift,'intensity':intensity,'regime':regime,'p_scale':pp,'d_scale':dd,'reference_cache_key':row['reference_cache_key'],'metrics_exactly_equal':True,'instrumented_runtime_s':time.perf_counter()-begin,'workload':[asdict(x) for x in w],'evaluator':e,'reference_metrics':raw['query_metrics'],'reference_violations_in_physical_finish_order':violations,'reference_queries':queries,'target_request_ids':sorted(target_ids),'selected_iteration_uids':sorted(selected_uids),'selected_execution_batches':chosen_batches,'concurrency_at_evaluator_checks':concurrency,'reference_node_mapping':captured['node_mapping'],'note':'Reference concurrency is query phase occupancy, not simultaneous GPU execution. Batch durations are shared service, not additive marginal request cost. Fixed overhead is ledger-only and is excluded from physical timestamps.'}
 folder=FORMAL/'mechanisms';folder.mkdir(parents=True,exist_ok=True);dest=folder/((name or group_id+'-'+regime+'-s'+str(shift)+'-'+str(intensity))+'.json.gz')
 with gzip.open(dest,'wt') as f:json.dump(details,f,separators=(',',':'))
 print(json.dumps({'path':str(dest.relative_to(ROOT)),'E':e['safe'],'R':not violations,'first_E':e['first_violation'],'first_R':violations[:1],'equal_metrics':True,'target_ids':sorted(target_ids),'batches':len(chosen_batches)}),flush=True)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--group',required=True);ap.add_argument('--shift',type=int,default=0);ap.add_argument('--intensity',type=float,required=True);ap.add_argument('--regime',required=True);ap.add_argument('--p-scale',type=float,default=1.);ap.add_argument('--d-scale',type=float,default=1.);ap.add_argument('--name');a=ap.parse_args();run(a.group,a.shift,a.intensity,a.regime,a.p_scale,a.d_scale,a.name)
