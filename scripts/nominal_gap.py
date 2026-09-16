"""Paired finite-grid diagnostics; do not assume reference monotonicity."""
from pathlib import Path
import sys,json,argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research import *

CASES=[
 {'id':f'a100-s{seed}-{place}-{regime}','seed':seed,'placement':place,'shift':0,'hetero':False,'ttft':2.,'tpot':tpot}
 for seed in [0,7] for place,regime,tpot in [('slow','decode',.15),('fast','decode',.15),('slow','prefill',1.)]
]
CASES += [
 {'id':f'a100-s19-{place}-decode','seed':19,'placement':place,'shift':0,'hetero':False,'ttft':2.,'tpot':.15} for place in ['slow','fast']
]
CASES += [
 {'id':f'a100-s{seed}-slow-ttft','seed':seed,'placement':'slow','shift':0,'hetero':False,'ttft':1.8,'tpot':10.} for seed in [0,7]
]
GRID=[.006,.010,.0131,.0132,.015,.020,.025,.04,.08,.16,.32,.64,1.28]

def summarize(rows,which):
 ordered=sorted(rows,key=lambda r:r['lambda']);safe=[r['lambda'] for r in ordered if r[which]['safe']]
 transitions=[{'left':a['lambda'],'right':b['lambda'],'left_safe':a[which]['safe'],'right_safe':b[which]['safe']} for a,b in zip(ordered,ordered[1:]) if a[which]['safe']!=b[which]['safe']]
 monotone=not any(not t['left_safe'] and t['right_safe'] for t in transitions)
 return {'largest_observed_safe':max(safe) if safe else None,'all_unsafe':not safe,'right_censored':ordered[-1][which]['safe'],'sampled_monotonic':monotone,'transitions':transitions,'single_boundary_supported':monotone and bool(safe) and not ordered[-1][which]['safe']}

def run_case(case,grid=GRID,refine=2,folder='nominal_gap'):
 dest=ROOT/'results/diagnostic'/folder/(case['id']+'.json')
 p=pipeline(case['placement'],case['shift'],case['hetero']);base=workload(case['seed'],case.get('duration',30));sla=SLA(case['ttft'],case['tpot'],fixed_overhead_s=.005)
 rows={}
 def probe(v):
  v=round(v,10)
  if v not in rows:
   w=scale_workload(base,v);r={'lambda':v,'evaluator':evaluator(p,w,sla),'reference':reference(p,w,sla)};rows[v]=r
   write_json(dest,{'case':case,'requests':[asdict(r) for r in base],'pipeline':asdict(p),'sla':asdict(sla),'rows':sorted(rows.values(),key=lambda x:x['lambda'])})
   print(json.dumps({'case':case['id'],'lambda':v,'E':r['evaluator']['safe'],'R':r['reference']['safe'],'ttft':r['reference']['max_ttft_s'],'tpot':r['reference']['max_tpot_s']}),flush=True)
 for v in grid:probe(v)
 # Seek the reference's own failure rather than stopping at the evaluator edge.
 # A finite cap prevents an unbounded sweep; retain explicit right censoring.
 high=max(rows)
 while rows[high]['reference']['safe'] and high<10:
  high=round(high*2,10);probe(high)
 for _ in range(refine):
  ordered=sorted(rows.values(),key=lambda x:x['lambda'])
  gaps=[(a['lambda'],b['lambda']) for a,b in zip(ordered,ordered[1:]) if any(a[k]['safe']!=b[k]['safe'] for k in ['evaluator','reference'])]
  for a,b in gaps:probe((a+b)/2)
 ordered=sorted(rows.values(),key=lambda x:x['lambda'])
 e=summarize(ordered,'evaluator');r=summarize(ordered,'reference')
 disagreements=[{'lambda':x['lambda'],'type':'optimistic' if x['evaluator']['safe'] else 'conservative'} for x in ordered if x['evaluator']['safe']!=x['reference']['safe']]
 result={'case':case,'requests':[asdict(r) for r in base],'pipeline':asdict(p),'sla':asdict(sla),'rows':ordered,'evaluator_summary':e,'reference_summary':r,'disagreements':disagreements}
 if e['largest_observed_safe'] and r['largest_observed_safe']:result['observed_safe_point_ratio_R_over_E']=r['largest_observed_safe']/e['largest_observed_safe']
 write_json(dest,result)
 return result

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--case',type=int);parser.add_argument('--from-case',type=int,default=0);args=parser.parse_args()
 if args.case is not None:run_case(CASES[args.case])
 else:
  from concurrent.futures import ProcessPoolExecutor
  with ProcessPoolExecutor(max_workers=2) as pool:list(pool.map(run_case,CASES[args.from_case:]))
