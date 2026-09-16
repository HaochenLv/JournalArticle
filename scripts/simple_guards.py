"""Small guard ablation, deliberately including simple non-learned baselines."""
from pathlib import Path
import sys,json,csv,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research import *

def main():
 rows=[]
 for path in sorted((ROOT/'results/diagnostic/nominal_gap').glob('*.json')):
  d=json.loads(path.read_text())
  if 'reference_summary' not in d:continue
  c=d['case'];p=pipeline(c['placement'],c['shift'],c['hetero']);base=tuple(RequestSpec(**r) for r in d['requests']);sla=SLA(**d['sla'])
  for bias in [1.,.9]:
   capacity=max((r['lambda'] for r in d['rows'] if evaluator(p,scale_workload(base,r['lambda']),sla,Profiles(bias,bias))['safe']),default=0.)
   for r in d['rows']:
    v=r['lambda'];w=scale_workload(base,v)
    def call(ps=bias,ds=bias,load=v,limits=sla):return evaluator(p,scale_workload(base,load),limits,Profiles(ps,ds))['safe']
    policies={
     'unmodified':lambda:call(),
     'fixed_compute_margin_10pct':lambda:call(bias*1.1,bias*1.1),
     'fixed_compute_margin_25pct':lambda:call(bias*1.25,bias*1.25),
     'fixed_sla_margin_10pct':lambda:call(limits=replace(sla,ttft_s=sla.ttft_s*.9,tpot_s=sla.tpot_s*.9)),
     'load_stress_10pct':lambda:call(load=v/.9),
     'load_stress_20pct':lambda:call(load=v/.8),
     'capacity_derating_10pct':lambda:v<=capacity*.9,
     'capacity_derating_20pct':lambda:v<=capacity*.8,
     # Evaluate all scenarios, not just the slowest: progress changes can be nonmonotone.
     'finite_four_scenarios':lambda:all([call(ps,ds) for ps,ds in [(bias,bias),(bias*1.25,bias),(bias,bias*1.25),(bias*1.25,bias*1.25)]]),
    }
    for name,fn in policies.items():
     start=time.perf_counter();safe=fn()
     rows.append({'case':c['id'],'bias':bias,'lambda':v,'policy':name,'accepted':safe,'reference_safe':r['reference']['safe'],'optimistic':safe and not r['reference']['safe'],'validated_acceptance':safe and r['reference']['safe'],'runtime_s':time.perf_counter()-start})
 out=ROOT/'results/diagnostic/simple_guards';out.mkdir(parents=True,exist_ok=True)
 with (out/'trials.csv').open('w') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
 summary=[]
 for bias in [1.,.9]:
  for policy in sorted({r['policy'] for r in rows}):
   group=[r for r in rows if r['bias']==bias and r['policy']==policy]
   capacities=[]
   for case in sorted({r['case'] for r in group}):
    rs=[r for r in group if r['case']==case];oracle=max((r['lambda'] for r in rs if r['reference_safe']),default=0);validated=max((r['lambda'] for r in rs if r['validated_acceptance']),default=0)
    capacities.append({'case':case,'largest_validated_acceptance':validated,'largest_reference_safe':oracle,'retention':validated/oracle if oracle else None})
   summary.append({'bias':bias,'policy':policy,'pairs':len(group),'optimistic':sum(r['optimistic'] for r in group),'validated_acceptance':sum(r['validated_acceptance'] for r in group),'runtime_s':sum(r['runtime_s'] for r in group),'capacities':capacities})
 write_json(out/'summary.json',{'scope':'exploratory deterministic guard comparison; no fitting or risk-probability claims','policies':summary})
 print(json.dumps([{k:v for k,v in r.items() if k!='capacities'} for r in summary],indent=2))
if __name__=='__main__':main()
