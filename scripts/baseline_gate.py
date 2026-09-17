"""Recover paper semantics and explicitly record incompatible published edges."""
from pathlib import Path
import sys,json,hashlib,subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research import *
from journal_baseline import evaluate as jb,VERSION
from nominal_gap import summarize

def main():
 out=ROOT/'results/baseline_gate';out.mkdir(parents=True,exist_ok=True);sla=SLA(2.,.15,fixed_overhead_s=.005)
 rows=[];traces=[];sweeps=[]
 for seed,low in [(0,.015),(1,.0159),(2,.0102),(3,.0152),(7,.0131),(19,.0152)]:
  for place in ['slow','fast']:
   p=pipeline(place);w=workload(seed);values=[low,round(low+.0001,4)]
   v={mode:[jb(p,scale_workload(w,x),sla,fixed_in_progress=(mode=='fixed_progress_ablation'))['safe'] for x in values] for mode in ['JB1','fixed_progress_ablation']}
   rows.append({'seed':seed,'placement':place,'published_pair':values,'verdicts':v,'JB1_matches_published':v['JB1']==[True,False],'fixed_progress_matches_published':v['fixed_progress_ablation']==[True,False]})
   for x in values:
    a=jb(p,scale_workload(w,x),sla,intrinsic=False,drain=True);b=jb(p,scale_workload(w,x),sla,intrinsic=True,drain=True)
    assert a['trajectory_hash']==b['trajectory_hash'];traces.append({'seed':seed,'placement':place,'intensity':x,'hash_equal':True})
   seq=[]
   for i in range(161):
    x=round(.006+i*.0001,7)
    seq.append({'lambda':x,**{k:{'safe':jb(p,scale_workload(w,x),sla,intrinsic=k=='accounting_only')['safe']} for k in ['baseline','accounting_only']}})
   sweeps.append({'seed':seed,'placement':place,'rows':seq,'baseline':summarize(seq,'baseline'),'accounting_only':summarize(seq,'accounting_only')})
 w=(RequestSpec('isolated-2051',0,2051,143),);p=pipeline()
 counter={str(flag):jb(p,w,sla,intrinsic=flag,drain=True) for flag in [False,True]}
 result={'version':VERSION,'source_sha256':hashlib.sha256((ROOT/'src/journal_baseline.py').read_bytes()).hexdigest(),'counterexample':counter,'published_pairs':rows,'trajectory_pairs':traces,'full_published_grid_sweeps':sweeps,'interpretation':'JB1 follows raw-compute progress equations; published endpoints require legacy fixed overhead in progress. No numerical retuning is used.'}
 write_json(out/'validation.json',result)
 print(json.dumps({'published_pairs_matches':sum(r['JB1_matches_published'] for r in rows),'fixed_progress_ablation_matches':sum(r['fixed_progress_matches_published'] for r in rows),'trajectory_pairs':len(traces),'sweeps':[(x['seed'],x['placement'],x['accounting_only']['largest_observed_safe']) for x in sweeps]},indent=2))
if __name__=='__main__':main()
