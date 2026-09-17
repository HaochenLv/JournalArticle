"""RQ1 confusion, RQ2 sampled gaps, RQ3 common-grid decisions."""
from pathlib import Path
import sys,json,argparse,collections
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from formal_core import *

def flatten(state):
 g=state['group'];wd,_=load_workload(g['workload']);limits=slas(g);out=[]
 for r in state['rows']:
  for regime,sla in limits.items():
   e=r['evaluator'].get(regime);ref=r['reference'].get(regime)
   row={'case_id':g['id']+'-'+regime+'-shift'+str(r['shift']),'group':g['id'],'role':g['role'],'workload':g['workload'],'duration_s':wd['duration_s'],'interval_offset':wd['interval_offset'],'seed':wd['seed'],'kind':g['kind'],'shift':r['shift'],'regime':regime,'link':g['link'],'ttft_s':sla.ttft_s,'tpot_s':sla.tpot_s,'intensity':r['intensity'],'status':r['status'],'evaluator_safe':e['safe'] if e else None,'reference_safe':ref['safe'] if ref else None,'evaluator_first_violation':e['first_violation'] if e else None,'evaluator_all_first_violations':e['first_violations'] if e else None,'evaluator_drained':e['drained'] if e else None,'evaluator_runtime_s':e['runtime_s'] if e else None,'reference_cache_key':r.get('reference_cache_key'),'reference_access_wall_s':r.get('reference_access_wall_s'),'reference_was_cached':r.get('reference_was_cached'),'workload_fingerprint':state['workload_fingerprint'],'scaled_workload_fingerprint':r['scaled_workload_fingerprint'],'partition_fingerprint':r['partition_fingerprint'],'profile_fingerprint':state['profile_fingerprint'],'baseline_sha256':state['baseline_sha256'],'attempts':r['attempts']}
   if ref:row.update({'reference_'+k:v for k,v in ref.items() if k!='safe'})
   row['execution_host']=r.get('execution_host',{'origin':'laptop_pretransfer'})
   row['reference_runtime_origin']=r.get('reference_runtime_origin','laptop_pretransfer')
   row['disagreement']='error' if r['status']!='ok' else ('optimistic' if e['safe'] else 'conservative') if e['safe']!=ref['safe'] else 'agreement'
   out.append(row)
 return out

def matrix(rows):
 ok=[r for r in rows if r['status']=='ok']
 return {'attempted':len(rows),'paired':len(ok),'failed':len(rows)-len(ok),'both_safe':sum(r['evaluator_safe'] and r['reference_safe'] for r in ok),'optimistic':sum(r['evaluator_safe'] and not r['reference_safe'] for r in ok),'conservative':sum(not r['evaluator_safe'] and r['reference_safe'] for r in ok),'both_unsafe':sum(not r['evaluator_safe'] and not r['reference_safe'] for r in ok)}

def main(partial=False):
 states=[];missing=[]
 for g in groups():
  p=FORMAL/'groups'/(g['id']+'.json')
  if p.exists():
   d=json.loads(p.read_text());assert d['protocol_hash']==PROTOCOL_HASH
   if d['status']=='complete':states.append(d);continue
  missing.append(g['id'])
 if missing and not partial:raise SystemExit('Incomplete groups: '+', '.join(missing))
 rows=[r for d in states for r in flatten(d)];bycase=collections.defaultdict(list)
 for r in rows:bycase[r['case_id']].append(r)
 matrices=[];caps=[]
 for case,rs in sorted(bycase.items()):
  meta={k:rs[0][k] for k in ['case_id','group','workload','duration_s','seed','kind','shift','regime','link','role']}
  matrices.append({**meta,**matrix(rs)})
  valid=[r for r in rs if r['status']=='ok']
  if len(valid)!=len(rs):caps.append({**meta,'status':'incomplete','failed':len(rs)-len(valid)});continue
  e=safe_summary(rs,'evaluator');r=safe_summary(rs,'reference');a=e['largest_safe'];b=r['largest_safe']
  caps.append({**meta,'status':'ok','evaluator':e,'reference':r,'absolute_gap':a-b if a is not None and b is not None else None,'relative_gap':(a-b)/b if a is not None and b else None,'precise_sampled_gap':e['single_boundary_supported'] and r['single_boundary_supported'],'largest_relative_bracket':max([(s['nearest_unsafe_above']/s['largest_safe']-1) for s in [e,r] if s['largest_safe'] and s['nearest_unsafe_above']],default=None)})
 decisions=[]
 for d in states:
  g=d['group']
  if len(g['shifts'])!=5:continue
  grids={s:sorted(r['intensity'] for r in d['rows'] if r['shift']==s) for s in g['shifts']}
  assert all(x==grids[g['shifts'][0]] for x in grids.values())
  for regime in slas(g):
   cs=[x for x in caps if x['group']==g['id'] and x['regime']==regime]
   if any(x['status']!='ok' for x in cs):decisions.append({'group':g['id'],'regime':regime,'status':'incomplete'});continue
   es={x['shift']:x['evaluator']['largest_safe'] or 0. for x in cs};rs={x['shift']:x['reference']['largest_safe'] or 0. for x in cs}
   decisions.append({'group':g['id'],'workload':g['workload'],'regime':regime,'link':g['link'],'status':'ok','grid_points':len(d['grid']),'grid_fingerprint':fingerprint(d['grid']),'any_reference_censoring':any(x['reference']['right_censored'] for x in cs),'any_reference_nonmonotonicity':any(x['reference']['nonmonotone'] for x in cs),**decision(es,rs)})
 csv_write(FORMAL/'rq1_reliability/raw.csv',rows);csv_write(FORMAL/'rq1_reliability/summary.csv',matrices)
 write_json(FORMAL/'rq1_reliability/summary.json',{'protocol_hash':PROTOCOL_HASH,'status':'partial' if missing else 'complete','missing_groups':missing,'totals':matrix(rows),'configurations':matrices})
 write_json(FORMAL/'rq2_capacity/summary.json',{'protocol_hash':PROTOCOL_HASH,'status':'partial' if missing else 'complete','rows':caps})
 csv_write(FORMAL/'rq2_capacity/summary.csv',[{k:v for k,v in r.items() if k not in ['evaluator','reference']}|{which+'_'+k:v for which in ['evaluator','reference'] for k,v in r.get(which,{}).items() if k not in ['sequence','transitions']} for r in caps])
 write_json(FORMAL/'rq3_decision_transfer/summary.json',{'protocol_hash':PROTOCOL_HASH,'status':'partial' if missing else 'complete','trials':decisions});csv_write(FORMAL/'rq3_decision_transfer/summary.csv',decisions)
 print(json.dumps({'complete_groups':len(states),'missing_groups':len(missing),'matrix':matrix(rows),'decisions':len(decisions),'winner_agreement':sum(x.get('winner_agrees') is True for x in decisions)},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--partial',action='store_true');args=p.parse_args();main(args.partial)
