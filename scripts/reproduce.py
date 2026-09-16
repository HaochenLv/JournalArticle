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

if __name__=='__main__':
 {'paper1':paper1,'paper2':paper2}[sys.argv[1]]()
