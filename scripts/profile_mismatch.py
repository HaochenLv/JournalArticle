"""Structured evaluator-only perturbation; reference stays byte-for-byte fixed."""
from pathlib import Path
import sys,json,csv
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research import *

VARIANTS=[('nominal',1.,1.,None)]+[(f'{phase}_minus{percent}',1-percent/100 if phase in ('prefill','both') else 1.,1-percent/100 if phase in ('decode','both') else 1.,None) for phase in ['prefill','decode','both'] for percent in [5,10,20]]

def main():
 rows=[]
 for folder in ['nominal_gap','partition_ranking']:
  for path in sorted((ROOT/'results/diagnostic'/folder).glob('*.json')):
   d=json.loads(path.read_text())
   if 'reference_summary' not in d:continue
   case=d['case'];p=pipeline(case['placement'],case['shift'],case['hetero']);base=tuple(RequestSpec(**r) for r in d['requests']);sla=SLA(**d['sla'])
   variants=VARIANTS+([('l4x2_minus10',1.,1.,('l4x2',.9))] if case['hetero'] else [])
   for label,ps,ds,device in variants:
    prof=Profiles(ps,ds,device)
    for r in d['rows']:
     e=evaluator(p,scale_workload(base,r['lambda']),sla,prof);ref=r['reference']
     assert label!='nominal' or e['safe']==r['evaluator']['safe']
     rows.append({'case':case['id'],'source':folder,'variant':label,'lambda':r['lambda'],'evaluator_safe':e['safe'],'reference_safe':ref['safe'],'disagreement':('optimistic' if e['safe'] else 'conservative') if e['safe']!=ref['safe'] else 'agreement','evaluator_violation':(e['first_violation'] or {}).get('kind'),'reference_violation':ref['first_violation'],'reference_ttft_s':ref['max_ttft_s'],'reference_tpot_s':ref['max_tpot_s'],'reference_cache_key':ref['cache_key'],'evaluator_runtime_s':e['runtime_s']})
 # Isolated held-out counterexample checks profile sensitivity without confounding arrival shifts.
 p=pipeline('slow');w=(RequestSpec('isolated-2051',0.,2051,1),);sla=SLA(2.,.15,fixed_overhead_s=.005);r=reference(p,w,sla)
 for label,ps,ds,device in VARIANTS:
  e=evaluator(p,w,sla,Profiles(ps,ds,device))
  rows.append({'case':'isolated-2051','source':'reproduction','variant':label,'lambda':1.,'evaluator_safe':e['safe'],'reference_safe':r['safe'],'disagreement':('optimistic' if e['safe'] else 'conservative') if e['safe']!=r['safe'] else 'agreement','evaluator_violation':(e['first_violation'] or {}).get('kind'),'reference_violation':r['first_violation'],'reference_ttft_s':r['max_ttft_s'],'reference_tpot_s':r['max_tpot_s'],'reference_cache_key':r['cache_key'],'evaluator_runtime_s':e['runtime_s']})
 out=ROOT/'results/diagnostic/profile_mismatch';out.mkdir(parents=True,exist_ok=True)
 with (out/'trials.csv').open('w') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
 groups=[]
 for source in sorted({r['source'] for r in rows}):
  for variant in sorted({r['variant'] for r in rows if r['source']==source}):
   group=[r for r in rows if r['source']==source and r['variant']==variant]
   groups.append({'source':source,'variant':variant,'pairs':len(group),'both_safe':sum(r['evaluator_safe'] and r['reference_safe'] for r in group),'both_unsafe':sum(not r['evaluator_safe'] and not r['reference_safe'] for r in group),'optimistic':sum(r['disagreement']=='optimistic' for r in group),'conservative':sum(r['disagreement']=='conservative' for r in group)})
 write_json(out/'summary.json',{'interpretation':'deterministic controlled stress grid, not a probability estimate','groups':groups})
 print(json.dumps(groups,indent=2))
if __name__=='__main__':main()
