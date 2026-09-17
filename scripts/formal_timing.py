"""Sequential planning-cost measurements; run after the parallel matrix exits."""
from pathlib import Path
import sys,json,time,gzip,statistics,platform,subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from formal_core import *

def main():
 check_pins();out=[]
 for wid in ['h101-o60-d30','h102-o300-d120']:
  g=next(g for g in groups() if g['workload']==wid and len(g['shifts'])==5)
  state=json.loads((FORMAL/'groups'/(g['id']+'.json')).read_text());assert state['status']=='complete'
  rows=[r for r in state['rows'] if r['shift']==0 and r['status']=='ok'];safe=[r for r in rows if r['evaluator']['decode']['safe'] and r['reference']['decode']['safe']]
  row=max(safe,key=lambda r:r['intensity']) if safe else min(rows,key=lambda r:r['intensity'])
  wd,base=load_workload(wid);w=scale_workload(base,row['intensity']);p=pipeline(g['link'],0,True);sla=slas(g)['decode'];prof=CachedProfiles()
  with gzip.open(ROOT/'results/raw_reference'/(row['reference_cache_key']+'.json.gz'),'rt') as f:expected=json.load(f)['raw']['query_metrics']
  dest=FORMAL/'runtime'/(wid+'.json')
  if dest.exists():out.append(json.loads(dest.read_text()));continue
  et=[];rt=[]
  for i in range(11):
   begin=time.perf_counter();e=jb(p,w,sla,prof);elapsed=time.perf_counter()-begin
   assert e['safe']==row['evaluator']['decode']['safe']
   if i:et.append(elapsed)
  for i in range(4):
   begin=time.perf_counter();r=ref.evaluate_helix_fixed_reference(pipeline=p,workload=w,sla=sla,helix_root=HELIX);elapsed=time.perf_counter()-begin
   assert json.loads(json.dumps(asdict(r)))['query_metrics']==expected
   if i:rt.append(elapsed)
  result={'protocol_hash':PROTOCOL_HASH,'group':g['id'],'shift':0,'regime':'decode','intensity':row['intensity'],'selection_rule':'highest observed both-safe shift0 point, otherwise lowest point','request_count':len(w),'evaluator_safe':e['safe'],'reference_safe':r.feasible,'warmups_per_model':1,'evaluator_wall_s':et,'reference_wall_s':rt,'evaluator_median_s':statistics.median(et),'reference_median_s':statistics.median(rt),'reference_to_evaluator_median_ratio':statistics.median(rt)/statistics.median(et),'metric_equality':True,'execution':'fresh sequential reference calls; no cache; evaluator CSV profile objects initialized before timing; planning CPU wall time, not inference speedup','python':platform.python_version(),'machine':platform.machine(),'cpu_logical':int(subprocess.check_output(['sysctl','-n','hw.logicalcpu'])),'memory_bytes':int(subprocess.check_output(['sysctl','-n','hw.memsize']))}
  write_json(dest,result);out.append(result);print(json.dumps(result),flush=True)
 write_json(FORMAL/'runtime/summary.json',{'protocol_hash':PROTOCOL_HASH,'rows':out})

if __name__=='__main__':main()
