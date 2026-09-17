"""Isolated JB1+ one-shot remaining-Prefill blocking correction.

The frozen JB1 implementation stays unchanged. This copy changes only the
profiled compute part of active-Prefill debt when the explicit switch is on.
"""
from dataclasses import dataclass
import math,time
from research import Profiles,H,fingerprint
from sla_aware_mvp.domain import sorted_workload

VERSION='JB1-raw-progress-prepost-active-prefill-debt-stage-buffer'

@dataclass
class State:
 spec: object
 phase: str='prefill'
 progress: float=0.
 block: int=0
 prefill_compute: float=0.
 prefill_end: float=0.
 prefill_start_s: float=0.
 prefill_progress_duration_s: float=0.
 decode_compute: float=0.

def remaining_fraction(t, start, duration):
 if duration <= 0:return 0. if t >= start else 1.
 return 1. - min(1., max(0., (t-start)/duration))

def evaluate(pipeline,workload,sla,prof=None,*,intrinsic=True,trace=False,drain=False,
             fixed_in_progress=False,precheck=True,activation_buffers=True,max_events=100_000,
             remaining_prefill_blocking=False):
 """Preserve Raw/Legacy progress while optionally scaling Prefill compute debt.

 By default stop at the first violating check. `drain=True` is diagnostic and
 allows full trajectory comparisons without changing the first unsafe verdict.
 A stage holds one activation buffer per active request (prompt tokens during
 Prefill, one token during Decode); this is a declared recovery assumption.
 """
 started=time.perf_counter();pipeline.validate();requests=sorted_workload(workload);prof=prof or Profiles()
 active={};index=0;t=requests[0].arrival_time_s if requests else 0.;epoch=0;first=[];history=[];trajectory=[]
 peak_p=peak_d=0;peak_memory={n:0. for n in pipeline.nodes};peak_util=0.;max_ttft=max_tpot=0.
 layers=pipeline.layers_by_node();stages={n:sum(s.node_id==n for s in pipeline.stages) for n in pipeline.nodes}
 static={n:pipeline.model.weight_bytes*layers[n]/pipeline.model.num_layers+(node.workspace_bytes+node.memory_margin_bytes if layers[n] else 0) for n,node in pipeline.nodes.items()}
 demands={}
 for r in requests:
  for phase,tokens in [('prefill',r.input_tokens),('decode',1)]:
   d={k:0. for k in pipeline.links}
   for boundary in pipeline.boundaries:
    for k in boundary.route_link_ids:d[k]+=pipeline.model.activation_bytes_per_token*tokens
   demands[r.id,phase]=d
 def counts():return sum(x.phase=='prefill' for x in active.values()),sum(x.phase=='decode' for x in active.values())
 def context(x):return x.spec.input_tokens+(min((x.block+1)*16,x.spec.output_tokens) if x.phase=='decode' else 0)
 def check(side,events):
  nonlocal peak_p,peak_d,peak_util,max_ttft,max_tpot
  np,nd=counts();peak_p=max(peak_p,np);peak_d=max(peak_d,nd)
  # Only profiled compute is scaled. The intrinsic term is always full.
  debt=sum((remaining_fraction(t,x.prefill_start_s,x.prefill_progress_duration_s)*x.prefill_compute if remaining_prefill_blocking else x.prefill_compute)+H*x.spec.input_tokens for x in active.values() if x.phase=='prefill')
  links={k:0. for k in pipeline.links};memory=dict(static);viol=[];ledgers={}
  for rid,x in sorted(active.items()):
   compute=x.prefill_compute if x.phase=='prefill' else prof.decode_time_per_token(x.spec,context(x),pipeline,np,nd)
   charge=(H*x.spec.input_tokens if intrinsic else 0.) if x.phase=='prefill' else debt
   limit=sla.ttft_s if x.phase=='prefill' else sla.tpot_s
   required=compute+charge+sla.fixed_overhead_s+sla.queue_overhead_s;residual=limit-required
   demand=demands[rid,x.phase];serial=sum(v/pipeline.links[k].capacity_bytes_per_s if pipeline.links[k].capacity_bytes_per_s>0 else math.inf for k,v in demand.items() if v)
   predicted=required+serial
   if x.phase=='prefill':max_ttft=max(max_ttft,predicted)
   else:max_tpot=max(max_tpot,predicted)
   ledgers[rid]={'phase':x.phase,'compute_s':compute,'blocking_charge_s':charge if x.phase=='decode' else 0.,'intrinsic_s':charge if x.phase=='prefill' else 0.,'residual_s':residual,'serialization_s':serial,'context':context(x),'progress':x.progress,'block':x.block}
   if residual<=1e-9:viol.append({'kind':'sla_time','object':x.phase,'request_id':rid,'required':required,'limit':limit})
   elif serial:
    for k,v in demand.items():
     if v:links[k]+=pipeline.links[k].capacity_bytes_per_s*serial/residual if math.isfinite(serial) else math.inf
   for n in memory:
    memory[n]+=pipeline.model.kv_bytes_per_token_per_layer*context(x)*layers[n]
    if activation_buffers:memory[n]+=stages[n]*pipeline.model.activation_bytes_per_token*(x.spec.input_tokens if x.phase=='prefill' else 1)
  for k,v in links.items():
   cap=pipeline.links[k].capacity_bytes_per_s;util=v/cap if cap else (math.inf if v else 0);peak_util=max(peak_util,util)
   if v>cap+1e-9:viol.append({'kind':'network','object':k,'required':v,'limit':cap})
  for n,v in memory.items():
   peak_memory[n]=max(peak_memory[n],v)
   if v>pipeline.nodes[n].memory_capacity_bytes:viol.append({'kind':'memory','object':n,'required':v,'limit':pipeline.nodes[n].memory_capacity_bytes})
  for v in viol:v.update(time_s=t,side=side,num_prefill=np,num_decode=nd)
  if trace:history.append({'time_s':t,'side':side,'events':events,'num_prefill':np,'num_decode':nd,'ledger':ledgers,'link_commitments':links,'memory':memory,'violations':viol})
  if trace and remaining_prefill_blocking:
   history[-1]['prefill_blocking_components']=[{'request_id':rid,'prefill_start_s':x.prefill_start_s,'prefill_progress_duration_s':x.prefill_progress_duration_s,'full_compute_s':x.prefill_compute,'remaining_fraction':remaining_fraction(t,x.prefill_start_s,x.prefill_progress_duration_s),'remaining_compute_s':remaining_fraction(t,x.prefill_start_s,x.prefill_progress_duration_s)*x.prefill_compute,'intrinsic_s':H*x.spec.input_tokens} for rid,x in sorted(active.items()) if x.phase=='prefill']
  return viol
 def finish():
  return {'baseline_version':VERSION+'+remaining-prefill-v1' if remaining_prefill_blocking else VERSION,'safe':not first,'first_violation':first[0] if first else None,'first_violations':first,'events':epoch,'drained':index==len(requests) and not active,'final_time_s':t,'peak_prefill':peak_p,'peak_decode':peak_d,'peak_network_utilization':peak_util,'peak_memory_bytes':peak_memory,'max_accounted_ttft_s':max_ttft,'max_accounted_tpot_s':max_tpot,'trajectory_hash':fingerprint(trajectory) if trace or drain else None,'runtime_s':time.perf_counter()-started,**({'trace':history,'trajectory':trajectory} if trace else {})}
 while index<len(requests) or active:
  if epoch>=max_events:raise RuntimeError('JB1 event limit exceeded')
  np,nd=counts();candidates=[];due={}
  if index<len(requests):candidates.append(requests[index].arrival_time_s)
  for rid,x in active.items():
   if x.phase=='prefill':candidates.append(x.prefill_end)
   else:
    x.decode_compute=prof.decode_time_per_token(x.spec,context(x),pipeline,np,nd)+(sla.fixed_overhead_s+sla.queue_overhead_s if fixed_in_progress else 0)
    if x.decode_compute<=0:raise ValueError('positive compute required')
    target=min((x.block+1)*16,x.spec.output_tokens);when=t+(target-x.progress)*x.decode_compute
    due[rid]=(when,target);candidates.append(when)
  nt=min(candidates)
  if nt<t-1e-9:raise RuntimeError('backwards event')
  for x in active.values():
   if x.phase=='decode':x.progress=min(x.spec.output_tokens,x.progress+max(0.,nt-t)/x.decode_compute)
  t=nt;epoch+=1
  events=[]
  if precheck:
   vs=check('pre',events)
   if vs and not first:first=vs
   if first and not drain:return finish()
  for rid,(when,target) in due.items():
   if abs(when-t)<=1e-9:
    x=active[rid];x.progress=float(target)
    if target==x.spec.output_tokens:events.append(('Finish',rid));del active[rid]
    else:x.block=target//16;events.append(('DecodeBlockUpdate',rid))
  for rid,x in active.items():
   if x.phase=='prefill' and x.prefill_end<=t+1e-9:x.phase='decode';events.append(('PrefillToDecode',rid))
  arrivals=[]
  while index<len(requests) and requests[index].arrival_time_s<=t+1e-9:
   r=requests[index];active[r.id]=State(r);arrivals.append(r);events.append(('Arrival',r.id));index+=1
  np,nd=counts()
  for r in arrivals:
   x=active[r.id];x.prefill_compute=prof.prefill_time(r,pipeline,np,nd)
   x.prefill_start_s=t
   x.prefill_progress_duration_s=x.prefill_compute+(sla.fixed_overhead_s+sla.queue_overhead_s if fixed_in_progress else 0)
   x.prefill_end=t+x.prefill_compute+(sla.fixed_overhead_s+sla.queue_overhead_s if fixed_in_progress else 0)
  if trace or drain:trajectory.append({'time_s':t,'events':sorted(events),'active':{rid:{'phase':x.phase,'progress':x.progress,'block':x.block,'context':context(x)} for rid,x in sorted(active.items())},'num_prefill':np,'num_decode':nd})
  vs=check('post',events)
  if vs and not first:first=vs
  if first and not drain:return finish()
 return finish()
