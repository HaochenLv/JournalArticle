from pathlib import Path
import sys,json,time,gzip
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from formal_core import *
from reference_storage import compact_reference_storage

def main():
 selected=[]
 for name in ['h101-o60-d30-heterogeneous-fast','h102-o300-d120-heterogeneous-slow']:
  d=json.loads((FORMAL/'groups'/(name+'.json')).read_text());r=next(x for x in d['rows'] if x['status']=='ok' and x['shift']==-2 and x['intensity']==.001)
  g=d['group'];wd,w=load_workload(g['workload']);p=pipeline(g['link'],-2,True);sla=next(iter(slas(g).values()))
  with gzip.open(ROOT/'results/raw_reference'/(r['reference_cache_key']+'.json.gz'),'rt') as f:original=json.load(f)
  start=time.perf_counter()
  with compact_reference_storage():new=ref.evaluate_helix_fixed_reference(pipeline=p,workload=scale_workload(w,.001),sla=sla,helix_root=HELIX)
  actual=json.loads(json.dumps(asdict(new)));assert actual==original['raw']
  selected.append({'group':name,'requests':len(w),'reference_key':r['reference_cache_key'],'raw_result_exactly_equal':True,'original_runtime_s':original['summary']['runtime_s'],'compact_runtime_s':time.perf_counter()-start})
  print(selected[-1],flush=True)
 write_json(FORMAL/'reference_storage_validation.json',{'scope':'all raw fields including every per-token metric bit-identical on one short and one long trace; full simulator event/request dynamics unchanged','runs':selected})
if __name__=='__main__':main()
