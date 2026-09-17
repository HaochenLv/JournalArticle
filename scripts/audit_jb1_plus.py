"""Saved mechanism replay and sequential evaluator-only cost diagnostics."""
from jb1_plus_common import *
import argparse,statistics,datetime

def clean(e):return {k:v for k,v in e.items() if k!='runtime_s'}
def mechanisms():
 result=[]
 for name in ['conservative_h105_a100','optimistic_h103_a100','reversal_h101_shift0','reversal_h101_shift2']:
  paths=list((FORMAL/'mechanisms').glob(name+'.json.gz'))
  if not paths:
   # Names come from the frozen trace inventory, not result-based selection.
   paths=[p for p in (FORMAL/'mechanisms').glob('*.json.gz') if ('h101' in p.name and f'shift{name[-1]}' in p.name)]
  assert len(paths)==1,(name,paths)
  saved=read(paths[0]);g=saved['group'];w=tuple(RequestSpec(**r) for r in saved['workload']);p=pipeline(g['link'],saved['shift'],g['kind']=='heterogeneous');sla=slas(g)[saved['regime']]
  raw=read(ROOT/'results/raw_reference'/(saved['reference_cache_key']+'.json.gz'))
  assert saved['reference_metrics']==raw['raw']['query_metrics']
  ev={v:plus(p,w,sla,CachedProfiles(),trace=True,drain=True,**o) for v,o in VARIANTS.items()}
  original=jb(p,w,sla,CachedProfiles(),trace=True,drain=True);assert clean(original)==clean(ev['Raw-Full'])
  for sem in ['Raw','Legacy']:assert ev[sem+'-Full']['trajectory_hash']==ev[sem+'-Remaining']['trajectory_hash']
  first=ev['Raw-Full']['first_violation'];at={'time_s':first['time_s'],'side':first['side']} if first else None
  epochs={}
  for sem in ['Raw','Legacy']:
   f=ev[sem+'-Full'];r=ev[sem+'-Remaining'];fv=f['first_violation']
   if fv:
    fs=next(x for x in f['trace'] if x['time_s']==fv['time_s'] and x['side']==fv['side']);rs=next(x for x in r['trace'] if x['time_s']==fv['time_s'] and x['side']==fv['side'])
    components=rs['prefill_blocking_components'];fd=sum(x['full_compute_s']+x['intrinsic_s'] for x in components);rd=sum(x['remaining_compute_s']+x['intrinsic_s'] for x in components)
    decode={rid:{'full':x,'remaining':rs['ledger'][rid],'full_required_tpot_s':x['compute_s']+fd+sla.fixed_overhead_s+sla.queue_overhead_s,'remaining_required_tpot_s':x['compute_s']+rd+sla.fixed_overhead_s+sla.queue_overhead_s} for rid,x in fs['ledger'].items() if x['phase']=='decode'}
    epochs[sem]={'time_s':fv['time_s'],'side':fv['side'],'active_prefill':components,'full_debt_s':fd,'remaining_debt_s':rd,'debt_reduction_s':fd-rd,
     'decode':decode,'full_epoch_violations':fs['violations'],'remaining_epoch_violations':rs['violations']}
  item={'name':name,'source_trace':paths[0].relative_to(ROOT).as_posix(),'group':g,'shift':saved['shift'],'intensity':saved['intensity'],'sla':asdict(sla),
   'reference':reference_details(raw,sla),'reference_cache_key':saved['reference_cache_key'],'failure_epoch_comparison':epochs,
   'variants':{v:{k:x for k,x in e.items() if k not in ['trace','trajectory','runtime_s']} for v,e in ev.items()},
   'completion_times':{v:{rid:next((t['time_s'] for t in e['trajectory'] if ('Finish',rid) in t['events']),None) for rid in saved['target_request_ids']} for v,e in ev.items()},
   'source_reference_queries':{rid:saved['reference_queries'][rid]['iterations'][-1]['end_s'] for rid in saved['target_request_ids']}}
  write_gz(OUT/'mechanisms'/(name+'.json.gz'),{'inputs':{'pipeline':asdict(p),'workload':[asdict(r) for r in w],'sla':asdict(sla)},'evaluator':ev,'summary':item})
  result.append(item)
 write_json(OUT/'phase_a_mechanisms.json',{'protocol_hash':PH,'new_reference_runs':0,'cases':result,'scope':'post-hoc cases; correction leaves progress and completion-time drift unchanged within each semantic variant'})
 print(json.dumps(result,indent=2))

def timing():
 guard();rows=[]
 for g in b_groups():
  prof=CachedProfiles()
  for i,v in enumerate(P['phase_b']['initial_grid']):
   for s in P['candidate_shifts']:
    p,w,_=b_base(g,s,v)
    for sid,sla in limits('b').items():
     # Deterministic rotating order reduces persistent order/cache asymmetry.
     names=list(VARIANTS);rotation=(i+s)%4;names=names[rotation:]+names[:rotation]
     for variant in names:
      opts=VARIANTS[variant]
      e=(plus(p,w,sla,prof,**opts) if opts['remaining_prefill_blocking'] else jb(p,w,sla,prof,fixed_in_progress=opts['fixed_in_progress']))
      saved=read(point_path('b',g,s,v))['evaluator'][variant][sid]
      assert clean(e)==clean(saved)
      rows.append({'group':g['id'],'shift':s,'intensity':v,'sla':sid,'variant':variant,'runtime_s':e['runtime_s'],'events':e['events']})
 def dist(xs):
  xs=sorted(xs);return {'n':len(xs),'median':statistics.median(xs),'p95':xs[math.ceil(.95*len(xs))-1],'max':max(xs)}
 report={'protocol_hash':PH,'measured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'Sequential same-process evaluator calls after physical campaign; one pass all 180 initial points x 4 SLAs x 4 variants, shared CachedProfiles per workload, deterministic rotating variant order; Full calls frozen journal_baseline.py and Remaining calls journal_baseline_plus.py. perf_counter wall seconds on CPU, no reference query.',
  'variants':{v:{'runtime_s':dist([r['runtime_s'] for r in rows if r['variant']==v]),'events':dist([r['events'] for r in rows if r['variant']==v])} for v in VARIANTS},
  'complexity':'Two stored scalars (start, progress duration) per active Prefill; existing frozen compute reused; fraction computed transiently. O(active Prefill) per check, same asymptotic debt-scan order. Early rejection can change measured event count; full-drain trajectories unchanged.'}
 csv_write(OUT/'runtime_samples.csv',rows);write_json(OUT/'runtime.json',report);print(json.dumps(report,indent=2))

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['mechanisms','timing']);a=ap.parse_args()
 (mechanisms if a.mode=='mechanisms' else timing)()
