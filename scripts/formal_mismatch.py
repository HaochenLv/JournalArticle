"""Evaluate structured profile stresses on frozen nominal common grids."""
from pathlib import Path
import sys,json,collections,gzip,argparse
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
from formal_core import *
from formal_analyze import flatten,matrix
VARIANTS=[('nominal',1.,1.,None)]+[(f'{phase}_minus{pct}',1-pct/100 if phase in ['prefill','both'] else 1.,1-pct/100 if phase in ['decode','both'] else 1.,None) for phase in ['prefill','decode','both'] for pct in [5,10,20]]

def run_group(g):
 path=FORMAL/'groups'/(g['id']+'.json')
 if not path.exists():return None
 d=json.loads(path.read_text())
 if d['status']!='complete':return None
 out=FORMAL/'rq4_profile_mismatch/groups'/(g['id']+'.json.gz');source_hash=fingerprint(d)
 if out.exists():
  with gzip.open(out,'rt') as f:old=json.load(f)
  assert old['source_hash']==source_hash and old['protocol_hash']==PROTOCOL_HASH
  return old
 base_rows=flatten(d);wd,w=load_workload(g['workload']);limits=slas(g);rows=[];ps={s:pipeline(g['link'],s,g['kind']=='heterogeneous') for s in g['shifts']}
 variants=VARIANTS+([('l4x2_minus10',1.,1.,('l4x2',.9))] if g['kind']=='heterogeneous' else [])
 for label,pp,dd,dev in variants:
  prof=CachedProfiles(pp,dd,dev)
  for r in base_rows:
   row={k:r[k] for k in ['case_id','group','workload','kind','shift','regime','link','intensity','status','reference_safe','reference_cache_key']};row['variant']=label;row['evaluator_profile_fingerprint']=fingerprint({'nominal_profiles':CONFIG['profile_fingerprint'],'prefill_scale':pp,'decode_scale':dd,'device':dev})
   if label=='nominal':row.update(evaluator_safe=r['evaluator_safe'],evaluator_runtime_s=r['evaluator_runtime_s'],first_violation=r['evaluator_first_violation'])
   else:
    try:
     e=jb(ps[r['shift']],scale_workload(w,r['intensity']),limits[r['regime']],prof);row.update(evaluator_safe=e['safe'],evaluator_runtime_s=e['runtime_s'],first_violation=e['first_violation'])
    except Exception as ex:row.update(status='error',evaluator_safe=None,error=type(ex).__name__+': '+str(ex).replace(str(ROOT),'<journal>'))
   rows.append(row)
  print('MISMATCH_VARIANT',g['id'],label,flush=True)
 result={'protocol_hash':PROTOCOL_HASH,'source_hash':source_hash,'group':g,'rows':rows};out.parent.mkdir(parents=True,exist_ok=True)
 temp=out.with_suffix('.tmp-'+str(os.getpid()))
 with gzip.open(temp,'wt') as f:json.dump(result,f,separators=(',',':'))
 temp.replace(out);return result

def summarize(partial=False):
 data=[];missing=[]
 for g in groups():
  path=FORMAL/'rq4_profile_mismatch/groups'/(g['id']+'.json.gz')
  if not path.exists():missing.append(g['id']);continue
  with gzip.open(path,'rt') as f:data.append(json.load(f))
 if missing and not partial:raise SystemExit('Missing mismatch groups: '+','.join(missing))
 rows=[r for d in data for r in d['rows']];counts=[];caps=[];trials=[]
 for kind in ['a100','heterogeneous']:
  for variant in sorted({r['variant'] for r in rows if r['kind']==kind}):
   rs=[r for r in rows if r['kind']==kind and r['variant']==variant];counts.append({'kind':kind,'variant':variant,**matrix(rs)})
 bycase=collections.defaultdict(list)
 for r in rows:bycase[r['case_id'],r['variant']].append(r)
 for (case,variant),rs in bycase.items():
  if any(r['status']!='ok' for r in rs):caps.append({'case_id':case,'variant':variant,'status':'incomplete'});continue
  e=safe_summary(rs,'evaluator');ref=safe_summary(rs,'reference');a=e['largest_safe'];b=ref['largest_safe']
  caps.append({'case_id':case,'group':rs[0]['group'],'regime':rs[0]['regime'],'shift':rs[0]['shift'],'variant':variant,'status':'ok','evaluator':{k:v for k,v in e.items() if k!='sequence'},'reference':{k:v for k,v in ref.items() if k!='sequence'},'relative_gap':(a-b)/b if a is not None and b else None})
 for d in data:
  g=d['group']
  if len(g['shifts'])!=5:continue
  for regime in slas(g):
   for variant in sorted({r['variant'] for r in d['rows']}):
    cs=[c for c in caps if c.get('group')==g['id'] and c.get('regime')==regime and c['variant']==variant]
    if len(cs)!=5 or any(c['status']!='ok' for c in cs):continue
    es={c['shift']:c['evaluator']['largest_safe'] or 0. for c in cs};rs={c['shift']:c['reference']['largest_safe'] or 0. for c in cs}
    trials.append({'group':g['id'],'regime':regime,'variant':variant,**decision(es,rs),'evaluator_right_censored':any(c['evaluator']['right_censored'] for c in cs),'evaluator_nonmonotone':any(c['evaluator']['nonmonotone'] for c in cs)})
 for t in trials:
  nominal=next(x for x in trials if x['group']==t['group'] and x['regime']==t['regime'] and x['variant']=='nominal');t['selected_changed_from_nominal']=t['selected_shift']!=nominal['selected_shift'];t['new_decision_error']=nominal['winner_agrees'] is True and t['winner_agrees'] is False
 write_json(FORMAL/'rq4_profile_mismatch/summary.json',{'protocol_hash':PROTOCOL_HASH,'status':'partial' if missing else 'complete','missing_groups':missing,'rows':len(rows),'counts':counts,'decision_trials':trials});csv_write(FORMAL/'rq4_profile_mismatch/summary.csv',counts);csv_write(FORMAL/'rq4_profile_mismatch/decision_trials.csv',trials)
 write_json(FORMAL/'rq4_profile_mismatch/capacity.json',caps)
 print(json.dumps({'rows':len(rows),'missing':len(missing),'decision_trials':len(trials),'new_decision_errors':sum(x['new_decision_error'] for x in trials)}))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--partial',action='store_true');ap.add_argument('--workers',type=int,default=2);args=ap.parse_args();check_pins()
 from concurrent.futures import ProcessPoolExecutor
 with ProcessPoolExecutor(max_workers=args.workers) as pool:list(pool.map(run_group,groups()))
 summarize(args.partial)
