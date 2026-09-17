from pathlib import Path
import sys,json,csv,statistics
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research import *

def upper(d,which):
 s=d[which+'_summary'];low=s['largest_observed_safe']
 if not s['single_boundary_supported'] or low is None:return None
 return min(r['lambda'] for r in d['rows'] if r['lambda']>low and not r[which]['safe'])

def main():
 nominal=[];cases=[]
 for path in sorted((ROOT/'results/diagnostic/nominal_gap').glob('*.json')):
  d=json.loads(path.read_text())
  if 'reference_summary' not in d:continue
  cases.append(d);e=d['evaluator_summary'];r=d['reference_summary']
  counts={key:sum(x['type']==key for x in d['disagreements']) for key in ['optimistic','conservative']}
  nominal.append({'case':d['case']['id'],'ttft_s':d['sla']['ttft_s'],'tpot_s':d['sla']['tpot_s'],'pairs':len(d['rows']),'evaluator_safe_max':e['largest_observed_safe'],'evaluator_next_unsafe':upper(d,'evaluator'),'reference_safe_max':r['largest_observed_safe'],'reference_next_unsafe':upper(d,'reference'),'reference_monotonic':r['sampled_monotonic'],'reference_right_censored':r['right_censored'],'relative_observed_gap_pct':100*(r['largest_observed_safe']/e['largest_observed_safe']-1) if e['largest_observed_safe'] and r['largest_observed_safe'] else None,'first_disagreement':d['disagreements'][0] if d['disagreements'] else None,**counts,'native_definition_changes_safe_verdict':sum(x['reference']['safe'] and x['reference']['max_native_ttft_s']>d['sla']['ttft_s'] for x in d['rows'])})
 write_json(ROOT/'results/diagnostic/nominal_summary.json',{'rows':nominal,'totals':{'cases':len(nominal),'pairs':sum(r['pairs'] for r in nominal),'optimistic':sum(r['optimistic'] for r in nominal),'conservative':sum(r['conservative'] for r in nominal)}})
 with (ROOT/'results/diagnostic/nominal_summary.csv').open('w') as f:
  writer=csv.DictWriter(f,fieldnames=list(nominal[0]),lineterminator='\n');writer.writeheader();writer.writerows(nominal)
 ranking={}
 for path in (ROOT/'results/diagnostic/partition_ranking').glob('hetero-*.json'):
  d=json.loads(path.read_text())
  if 'reference_summary' not in d:continue
  c=d['case'];key=c['id'].split('-shift')[0];ranking.setdefault(key,[]).append(d)
 rankrows=[]
 for key,ds in sorted(ranking.items()):
  if len(ds)!=5:continue
  byshift={d['case']['shift']:d for d in ds}
  scores={k:{s:d[k+'_summary']['largest_observed_safe'] or 0 for s,d in byshift.items()} for k in ['evaluator','reference']}
  best={k:max(values.values()) for k,values in scores.items()}
  ties={k:sorted(s for s,v in values.items() if v==best[k]) for k,values in scores.items()}
  selected=min(ties['evaluator'],key=lambda s:(abs(s),s));rank=1+sum(v>scores['reference'][selected] for v in scores['reference'].values())
  rankrows.append({'case':key,'evaluator_scores':scores['evaluator'],'reference_scores':scores['reference'],'evaluator_best_set':ties['evaluator'],'reference_best_set':ties['reference'],'evaluator_selected':selected,'reference_rank_of_evaluator_selected':rank,'reference_quality_ratio':scores['reference'][selected]/best['reference'] if best['reference'] else None,'reference_censored':any(d['reference_summary']['right_censored'] for d in ds),'reference_nonmonotone_candidates':[d['case']['shift'] for d in ds if not d['reference_summary']['sampled_monotonic']],'candidate_intervals':{s:{'evaluator_lower':scores['evaluator'][s],'evaluator_upper':upper(d,'evaluator'),'reference_lower':scores['reference'][s],'reference_upper':upper(d,'reference')} for s,d in byshift.items()}})
 write_json(ROOT/'results/diagnostic/partition_ranking/summary.json',{'scope':'largest safe observed probes per candidate; use reported intervals/censoring before asserting a strict rank','trials':rankrows})
 # Bias rankings on the SAME candidate-specific grid, against unchanged reference scores.
 mismatch=ROOT/'results/diagnostic/profile_mismatch/trials.csv'
 if mismatch.exists():
  with mismatch.open() as f:mr=list(csv.DictReader(f))
  changes=[]
  for trial in rankrows:
   for variant in sorted({r['variant'] for r in mr if r['source']=='partition_ranking'}):
    if not all(any(r['case']==trial['case']+'-shift'+str(s) and r['variant']==variant for r in mr) for s in [-2,-1,0,1,2]):continue
    scores={s:max((float(r['lambda']) for r in mr if r['case']==trial['case']+'-shift'+str(s) and r['variant']==variant and r['evaluator_safe']=='True'),default=0) for s in [-2,-1,0,1,2]}
    selected=max(scores,key=lambda s:(scores[s],-abs(s),-s));refs=trial['reference_scores'];rb=max(refs.values());rv=refs[selected]
    changes.append({'case':trial['case'],'variant':variant,'evaluator_scores':scores,'selected':selected,'changed_from_nominal':selected!=trial['evaluator_selected'],'reference_rank':1+sum(v>rv for v in refs.values()),'reference_quality_ratio':rv/rb if rb else None})
  write_json(ROOT/'results/diagnostic/partition_ranking/mismatch_rankings.json',changes)
  # Resolution control: use exactly the same loads for every candidate.
  from partition_ranking import GRID
  common=[];loads=set(GRID)
  for trial in rankrows:
   key=trial['case'];ds=ranking[key]
   refs={d['case']['shift']:max((r['lambda'] for r in d['rows'] if r['lambda'] in loads and r['reference']['safe']),default=0) for d in ds}
   for variant in sorted({r['variant'] for r in mr if r['source']=='partition_ranking'}):
    scores={s:max((float(r['lambda']) for r in mr if r['case']==key+'-shift'+str(s) and r['variant']==variant and float(r['lambda']) in loads and r['evaluator_safe']=='True'),default=0) for s in [-2,-1,0,1,2]}
    selected=max(scores,key=lambda s:(scores[s],-abs(s),-s));best=max(refs.values())
    common.append({'case':key,'variant':variant,'evaluator_scores':scores,'reference_scores':refs,'selected':selected,'reference_rank':1+sum(v>refs[selected] for v in refs.values()),'reference_quality_ratio':refs[selected]/best if best else None})
  write_json(ROOT/'results/diagnostic/partition_ranking/common_grid_rankings.json',{'scope':'identical 19-load grid for all candidates; under-resolves some partition differences','trials':common})
 print(json.dumps({'nominal':nominal,'ranking':rankrows},indent=2))

if __name__=='__main__':main()
