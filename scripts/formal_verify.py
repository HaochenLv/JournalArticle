"""Evidence-quality checks: failures are explicit, never silently dropped."""
from pathlib import Path
import sys,json,gzip,collections,hashlib,subprocess,tarfile,io
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from formal_core import *

def main():
 check_pins();states=[];errors=[];keys=set();pairs=0;nonmono=0;censored=0;attempt_errors=[];retry_points=0
 for g in groups():
  p=FORMAL/'groups'/(g['id']+'.json');assert p.exists(),g['id'];d=json.loads(p.read_text());assert d['status']=='complete';assert d['protocol_hash']==PROTOCOL_HASH
  grid=d['grid'];assert len(grid)==len(set(grid));assert set(CONFIG['initial_grid'])<=set(grid)
  wd,w=load_workload(g['workload']);assert fingerprint([asdict(r) for r in w])==wd['workload_fingerprint']==d['workload_fingerprint']
  assert len(d['rows'])==len(grid)*len(g['shifts'])
  assert len({(r['shift'],r['intensity']) for r in d['rows']})==len(d['rows'])
  for shift in g['shifts']:assert sorted(r['intensity'] for r in d['rows'] if r['shift']==shift)==grid
  for r in d['rows']:
   ra=[a for a in r['attempts'] if a['part']=='reference'];retry_points+=len(ra)>1
   attempt_errors.extend({'group':g['id'],'shift':r['shift'],'intensity':r['intensity'],**a} for a in r['attempts'] if a.get('status')=='error' or 'error' in a)
   if r['status']!='ok':errors.append({'group':g['id'],'shift':r['shift'],'intensity':r['intensity'],'attempts':r['attempts']});continue
   key=r['reference_cache_key'];keys.add(key)
   with gzip.open(ROOT/'results/raw_reference'/(key+'.json.gz'),'rt') as f:raw=json.load(f)
   assert fingerprint(raw['inputs'])==key
   assert raw['raw']['finished_requests']==raw['raw']['total_requests']==len(w)
   assert r['partition_fingerprint']==fingerprint(raw['inputs']['pipeline'])
   assert r['scaled_workload_fingerprint']==fingerprint(raw['inputs']['workload'])
   assert r['scaled_workload_fingerprint']==fingerprint([asdict(x) for x in scale_workload(w,r['intensity'])])
   assert r['partition_fingerprint']==fingerprint(asdict(pipeline(g['link'],r['shift'],g['kind']=='heterogeneous')))
   assert raw['inputs']['helix_commit']==CONFIG['helix_commit'] and raw['inputs']['adapter_commit']==CONFIG['adapter_commit']
   for regime,sla in slas(g).items():
    assert r['reference'][regime]==reference_details(raw,sla);pairs+=1
  states.append(d)
 summary=json.loads((FORMAL/'rq1_reliability/summary.json').read_text());assert summary['status']=='complete';assert summary['totals']['paired']==pairs
 assert sum(summary['totals'][k] for k in ['both_safe','optimistic','conservative','both_unsafe'])==pairs
 caps=json.loads((FORMAL/'rq2_capacity/summary.json').read_text())['rows']
 for r in caps:
  if r['status']=='ok':nonmono+=r['reference']['nonmonotone'];censored+=r['reference']['right_censored']
 stress_rows=0;stress_errors=0
 for d in states:
  g=d['group'];lookup={(r['shift'],r['intensity'],regime):(r['reference_cache_key'],r['reference'][regime]['safe'],r['evaluator'][regime]['safe']) for r in d['rows'] if r['status']=='ok' for regime in slas(g)}
  p=FORMAL/'rq4_profile_mismatch/groups'/(g['id']+'.json.gz')
  with gzip.open(p,'rt') as f:sd=json.load(f)
  assert sd['protocol_hash']==PROTOCOL_HASH;assert sd['source_hash']==fingerprint(d)
  nvars=11 if g['kind']=='heterogeneous' else 10
  assert len(sd['rows'])==len(d['rows'])*2*nvars
  assert len({(r['shift'],r['intensity'],r['regime'],r['variant']) for r in sd['rows']})==len(sd['rows'])
  for r in sd['rows']:
   stress_rows+=1
   if r['status']!='ok':stress_errors+=1;continue
   key,rs,es=lookup[r['shift'],r['intensity'],r['regime']];assert (r['reference_cache_key'],r['reference_safe'])==(key,rs)
   if r['variant']=='nominal':assert r['evaluator_safe']==es
 mitigation=json.loads((FORMAL/'mitigation/results.json').read_text());assert mitigation['status']=='complete'
 for r in mitigation['rows']:
  q=r['query_trace'];assert len(q)==r['reference_calls'];assert len({(x['shift'],x['intensity']) for x in q})==len(q)
  assert len(q)<=CONFIG['boundary_validation_budget']
  if r['policy'].startswith('selected_') and not r['abstention']:assert any(x['safe'] and x['shift']==r['chosen_shift'] and x['intensity']==r['reported_intensity'] for x in q)
 report={'protocol_hash':PROTOCOL_HASH,'groups':len(states),'configuration_regimes':len(caps),'logical_paired_points':pairs,'unique_reference_records':len(keys),'failed_points':len(errors),'failure_records':errors,'reference_nonmonotone_configurations':nonmono,'reference_right_censored_configurations':censored,'stress_rows':stress_rows,'stress_errors':stress_errors,'mitigation_rows':len(mitigation['rows']),'checks':'frozen baseline/profile/input hashes, common grids, no repeated keys, reference full drain, threshold recomputation, complete denominators, stress immutability, counted validated queries'}
 restart=json.loads((FORMAL/'execution_restart.json').read_text());lookup={d['group']['id']:d for d in states}
 for c in restart['interrupted_probe_candidates']:assert any(r['shift']==c['shift'] and r['intensity']==c['intensity'] for r in lookup[c['group']]['rows'])
 report.update(retried_points=retry_points,attempt_errors=attempt_errors,timeout_attempts=sum('TimeoutError' in a.get('error','') for a in attempt_errors),interrupted_probe_candidates_recovered=len(restart['interrupted_probe_candidates']),analysis_source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'scripts').glob('formal_*.py'))})
 assert subprocess.check_output(['git','-C',str(HELIX),'rev-parse','HEAD'],text=True).strip()==CONFIG['helix_commit']
 assert not subprocess.check_output(['git','-C',str(HELIX),'status','--porcelain'],text=True).strip()
 object_repo=next((p for p in [ROOT/'.deps/evaluator-history.git',ROOT/'.deps/evaluator-git'] if p.exists()),None)
 assert object_repo is not None,'Run scripts/bootstrap.py to obtain pinned adapter git objects'
 archive=subprocess.check_output(['git','--git-dir',str(object_repo),'archive',CONFIG['adapter_commit'],'src'])
 source_hashes={}
 with tarfile.open(fileobj=io.BytesIO(archive)) as tf:
  for member in tf.getmembers():
   if not member.isfile():continue
   original=tf.extractfile(member).read();local=(ROOT/'.deps/evaluator'/member.name).read_bytes();assert original==local,member.name
   source_hashes[member.name]=hashlib.sha256(local).hexdigest()
 report['dependency_source_integrity']={'helix_clean_at_pinned_commit':True,'adapter_files_equal_git_objects':source_hashes}
 write_json(FORMAL/'quality_checks.json',report);print(json.dumps(report,indent=2))
 if errors or stress_errors:raise SystemExit('Recorded failures require explicit reporting; do not delete them.')
if __name__=='__main__':main()
