from pathlib import Path
import sys,json,shutil
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research import *

def paper1():
 sla=SLA(2.,.150,fixed_overhead_s=.005);p=pipeline('slow')
 w=(RequestSpec('isolated-2051',0.,2051,1),)
 a=evaluator(p,w,sla,intrinsic=False);b=evaluator(p,w,sla);r=reference(p,w,sla)
 result={'counterexample':{'baseline':a,'accounting_only':b,'reference':r},'sampled_transition':[]}
 base=workload(7)
 for v in [.010,.0131,.0132]:
  w=scale_workload(base,v)
  row={'lambda':v,'evaluator':evaluator(p,w,sla),'reference':reference(p,w,sla)}
  result['sampled_transition'].append(row);print(json.dumps(row),flush=True)
 write_json(ROOT/'results/reproduction/paper1.json',result)

def paper2():
 sys.path.insert(0,str(ROOT/'.deps/partition/src'))
 from sla_partition_sensitivity.phase13_evaluator_guided_search import run,write_outputs
 cfg=json.loads((ROOT/'.deps/partition/config/phase13.json').read_text())
 trace=ROOT/'.deps/partition/data/runtime_helix_trace';trace.mkdir(parents=True,exist_ok=True)
 for name in cfg['phase11']['expected_sha256']:
  source=next((HELIX/'simulator/trace_generator').rglob(name));shutil.copyfile(source,trace/name)
 cfg['phase6']['profile_root']=str(ROOT/'.deps/partition/data/helix_profiles/llama2_70b')
 cfg['phase11']['runtime_trace_root']=str(trace)
 cfg['phase11']['workload_seeds']=[7]
 rows,summary,log=run(cfg)
 write_outputs(rows,summary,log,ROOT/'results/reproduction/paper2_seed7')
 csv_path=ROOT/'results/reproduction/paper2_seed7/method_comparison.csv'
 csv_path.write_text(csv_path.read_text())
 print(json.dumps(summary['trial_summaries']),flush=True)

def paper1_edges():
 expected={0:.0150,1:.0159,2:.0102,3:.0152,7:.0131,19:.0152}
 rows=[]
 for seed,low in expected.items():
  for place in ['slow','fast']:
   p=pipeline(place);base=workload(seed);sla=SLA(2.,.15,fixed_overhead_s=.005)
   verdicts=[evaluator(p,scale_workload(base,v),sla)['safe'] for v in [low,round(low+.0001,4)]]
   rows.append({'seed':seed,'placement':place,'safe_lambda':low,'unsafe_lambda':round(low+.0001,4),'observed_verdicts':verdicts,'matches_paper':verdicts==[True,False]})
 write_json(ROOT/'results/reproduction/paper1_all_edges.json',rows)
 assert all(r['matches_paper'] for r in rows)
 print('12/12 published evaluator transition endpoint pairs recovered.')

def paper2_revision():
 sys.path.insert(0,str(ROOT/'.deps/partition/src'))
 from sla_partition_sensitivity.phase16_coarse_to_fine_search import _run_condition
 cfg=json.loads((ROOT/'.deps/partition/config/phase14.json').read_text())
 cfg['phase6']['profile_root']=str(ROOT/'.deps/partition/data/helix_profiles/llama2_70b')
 cfg['phase11']['runtime_trace_root']=str(ROOT/'.deps/partition/data/runtime_helix_trace')
 rows,profiles,logs=_run_condition(cfg,condition='expanded_20_seed',seeds=list(range(20)),bandwidth_multiplier=1.,radius=4)
 write_json(ROOT/'results/reproduction/paper2_revision_20seeds.json',{'rows':rows,'profiles':profiles})
 for regime in ['decode_constrained','prefill_constrained']:
  selected=[r for r in rows if r['regime']==regime and r['method']=='coarse_top1']
  print(regime,len(selected),sum(r['matches_oracle_shift'] for r in selected),sum(r['near_oracle'] for r in selected),flush=True)

if __name__=='__main__':
 {'paper1':paper1,'paper2':paper2,'paper1_edges':paper1_edges,'paper2_revision':paper2_revision}[sys.argv[1]]()
