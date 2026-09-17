"""Auditable bridge to pinned conference code and the HELIX reference simulator.

Recovered accounting-only ledger over the public E31 progress engine. This is
not represented as the unavailable final paper-1 source snapshot.
"""
from pathlib import Path
import sys, os, json, hashlib, gzip, time
import copy
from dataclasses import asdict, replace
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLBACKEND','Agg')
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.mplconfig'))
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'.deps/evaluator/src'))
from sla_aware_mvp.domain import SLA, RequestSpec, EvaluatorConfig, Phase, RequestRuntime, Stage
from sla_aware_mvp.evaluator import evaluate, _network_bytes_by_link
from sla_aware_mvp.helix import HelixA100Llama2Profiler, HelixLayerProfile
from sla_aware_mvp.helix_demo import HELIX_COMMIT, build_helix_pipelines
from sla_aware_mvp.exact_singleton_decode_demo import ExactHelixDecodeRuntimeProfiler
from sla_aware_mvp.capacity import scale_workload
from sla_aware_mvp.workload import build_helix_azure_conversation_workload
from sla_aware_mvp.prefill_debt_budget_ablation import E22_BLOCKING_OVERHEAD_S_PER_TOKEN as H
import sla_aware_mvp.helix_fixed_reference as ref
HELIX=ROOT/'.deps/helix'
# Group profiles are supplied by HELIX itself; only dispatch names are extended.
_original_machine=ref._helix_machine_type
ref._helix_machine_type=lambda name: {'L4x2':'L4x2','T4x4':'T4x4'}.get(name) or _original_machine(name)

def fingerprint(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def physical_fingerprint(inputs):
 value=copy.deepcopy(inputs)
 # These two thresholds are inspected only AFTER HELIX has fully drained.
 # Fixed/queue overhead is retained because cached metrics already include it.
 value['sla'].pop('ttft_s');value['sla'].pop('tpot_s')
 return fingerprint(value)

def reclassify_record(source,inputs):
 """Reapply the pinned adapter's exact threshold logic to immutable metrics."""
 raw=copy.deepcopy(source['raw']);limits=inputs['sla'];violations=[]
 for request in inputs['workload']:
  m=raw['query_metrics'][request['id']]
  if m['aligned_ttft_s']>limits['ttft_s']:violations.append((request['arrival_time_s']+m['aligned_ttft_s'],'ttft',request['id'],m['aligned_ttft_s'],limits['ttft_s']))
  for i,t in enumerate(m['decode_tpot_s']):
   if t>limits['tpot_s']:violations.append((request['arrival_time_s']+m['aligned_ttft_s']+sum(m['decode_tpot_s'][:i+1]),'tpot',request['id'],t,limits['tpot_s']))
 violations.sort(key=lambda x:(x[0],x[1],x[2]));first=violations[0] if violations else None
 raw.update(feasible=first is None,first_violation_kind=first[1] if first else None,first_violation_request_id=first[2] if first else None,first_violation_observed_s=first[3] if first else None,first_violation_limit_s=first[4] if first else None)
 summary=dict(source['summary']);summary.update(safe=raw['feasible'],first_violation=raw['first_violation_kind'],cache_key=fingerprint(inputs))
 return {'inputs':inputs,'summary':summary,'raw':raw,'derived_from':source['summary']['cache_key'],'reuse_reason':'SLA thresholds do not affect the pinned simulation; complete per-token metrics reused'}

_physical_records={}
_seen_reference_files=set()

def workload(seed=7,duration=30):
 return build_helix_azure_conversation_workload(HELIX,commit=HELIX_COMMIT,duration_s=duration,target_request_rate=1.5,seed=seed).requests

def pipeline(placement='slow',shift=0,heterogeneous=False):
 p=build_helix_pipelines()[0 if placement=='slow' else 1]
 lengths=[10+shift if i%2==0 else 10-shift for i in range(8)]
 start=0; stages=[];nodes=dict(p.nodes)
 for i,(s,n) in enumerate(zip(p.stages,lengths)):
  stages.append(Stage(s.id,start,start+n,s.node_id));start+=n
  if heterogeneous:nodes[s.node_id]=replace(nodes[s.node_id],hardware_type='L4x2' if i%2==0 else 'T4x4')
 return replace(p,id=f'{placement}-shift{shift}-'+('hetero' if heterogeneous else 'a100'),stages=tuple(stages),nodes=nodes)

class Profiles:
 def __init__(self,p_scale=1.,d_scale=1.,device_bias=None):
  self.p_scale=p_scale;self.d_scale=d_scale;self.device_bias=device_bias
  self.tables={}
  for name in ['a100','l4x2','t4x4']:
   base=HELIX/'simulator/model_manager/llama2_70b'/name
   self.tables[name]=(HelixLayerProfile.from_csv(base/'prompt_bs2time.csv',x_kind='prompt'),HelixLayerProfile.from_csv(base/'decode_bs2time.csv',x_kind='decode'))
 def _name(self,p,s):return {'A100-40GB':'a100','L4x2':'l4x2','T4x4':'t4x4'}[p.nodes[s.node_id].hardware_type]
 def _scale(self,name,phase):
  return (self.p_scale if phase==0 else self.d_scale)*(self.device_bias[1] if self.device_bias and name==self.device_bias[0] else 1.)
 def prefill_time(self,r,p,np,nd):
  return sum(s.num_layers*self.tables[self._name(p,s)][0].lookup_seconds_per_layer(r.input_tokens)*self._scale(self._name(p,s),0) for s in p.stages)
 def decode_time_per_token(self,r,ctx,p,np,nd):
  return sum(s.num_layers*self.tables[self._name(p,s)][1].lookup_seconds_per_layer(max(1,nd))*self._scale(self._name(p,s),1) for s in p.stages)*(2 if nd<=1 else 1)

def evaluator(p,w,sla,prof=None,intrinsic=True,debt=True):
 prof=prof or Profiles()
 start=time.perf_counter()
 run=evaluate(pipeline=p,workload=w,sla=sla,config=EvaluatorConfig(record_trace=True,max_events=20_000),profiler=prof)
 byid={r.id:r for r in w}; first=None;max_p=0.;max_d=0.
 for snap in run.trace:
  np,nd=snap.num_prefill,snap.num_decode
  pdebt=sum(prof.prefill_time(byid[rid],p,np,nd)+H*byid[rid].input_tokens for rid,ph in snap.request_phase.items() if ph=='prefill') if debt else 0.
  util=0.
  for rid,ph in snap.request_phase.items():
   r=byid[rid]
   if ph=='prefill':
    compute=prof.prefill_time(r,p,np,nd)+(H*r.input_tokens if intrinsic else 0.)
    limit=sla.ttft_s
   else:
    compute=prof.decode_time_per_token(r,snap.request_context[rid],p,np,nd)+pdebt
    limit=sla.tpot_s
   demand=_network_bytes_by_link(RequestRuntime(r,Phase(ph)),p)
   net=sum(b/p.links[k].capacity_bytes_per_s for k,b in demand.items() if b)
   predicted=compute+net+sla.fixed_overhead_s+sla.queue_overhead_s
   if ph=='prefill':max_p=max(max_p,predicted)
   else:max_d=max(max_d,predicted)
   residual=limit-compute-sla.fixed_overhead_s-sla.queue_overhead_s
   if residual<=1e-9 and first is None:
    first={'kind':ph+'_sla_budget','time_s':snap.time_s,'request_id':rid,'required_s':compute+sla.fixed_overhead_s+sla.queue_overhead_s,'limit_s':limit,'num_prefill':np,'num_decode':nd,'prefill_debt_s':pdebt}
   if residual>1e-9:util+=net/residual
  # Every request traverses the same seven links, so normalized demand is equal.
  if util>1+1e-9 and first is None:first={'kind':'network','time_s':snap.time_s,'utilization':util,'num_prefill':np,'num_decode':nd}
  if first:break
 if run.first_violation is not None and (first is None or run.first_violation.time_s<first['time_s']):
  first=asdict(run.first_violation)
 trajectory=[{'time':s.time_s,'events':s.event_types,'phase':s.request_phase,'progress':s.request_progress,'context':s.request_context} for s in run.trace]
 return {'safe':first is None and run.feasible,'first_violation':first,'max_accounted_ttft_s':max_p,'max_accounted_tpot_s':max_d,'events':run.processed_events,'trajectory_hash':fingerprint(trajectory),'runtime_s':time.perf_counter()-start}

def reference(p,w,sla):
 inputs={'schema':1,'helix_commit':HELIX_COMMIT,'adapter_commit':'1cd5c56365b084fb06e3ca14f67448ddbf45275a','group_dispatch_extension':1,'pipeline':asdict(p),'workload':[asdict(r) for r in w],'sla':asdict(sla)}
 key=fingerprint(inputs);folder=ROOT/'results/raw_reference';folder.mkdir(parents=True,exist_ok=True);path=folder/(key+'.json.gz')
 if path.exists():
  with gzip.open(path,'rt') as f:return json.load(f)['summary']
 for old_path in folder.glob('*.json.gz'):
  if old_path.name in _seen_reference_files:continue
  with gzip.open(old_path,'rt') as f:old=json.load(f)
  _physical_records.setdefault(physical_fingerprint(old['inputs']),old_path)
  _seen_reference_files.add(old_path.name)
 physical=physical_fingerprint(inputs)
 if physical in _physical_records:
  with gzip.open(_physical_records[physical],'rt') as f:source=json.load(f)
  record=reclassify_record(source,inputs)
  temporary=path.with_suffix('.tmp-'+str(os.getpid()))
  with gzip.open(temporary,'wt') as f:json.dump(record,f,separators=(',',':'))
  temporary.replace(path)
  return record['summary']
 start=time.perf_counter();run=ref.evaluate_helix_fixed_reference(pipeline=p,workload=w,sla=sla,helix_root=HELIX);elapsed=time.perf_counter()-start
 metrics=list(run.query_metrics.values())
 summary={'safe':run.feasible,'first_violation':run.first_violation_kind,'max_ttft_s':max(m.aligned_ttft_s for m in metrics),'max_native_ttft_s':max(m.true_first_token_ttft_s for m in metrics),'max_tpot_s':max(m.max_tpot_s for m in metrics),'finished_requests':run.finished_requests,'runtime_s':elapsed,'cache_key':key}
 temporary=path.with_suffix('.tmp-'+str(os.getpid()))
 with gzip.open(temporary,'wt') as f:json.dump({'inputs':inputs,'summary':summary,'raw':asdict(run)},f,separators=(',',':'))
 temporary.replace(path)
 return summary

def write_json(path,data):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 temporary=path.with_suffix('.tmp-'+str(os.getpid()))
 temporary.write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n');temporary.replace(path)
