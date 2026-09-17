"""Verify frozen history, complete matrices, formulas and saved evidence; no HELIX execution."""
from jb1_plus_common import *
from analyze_jb1_plus import group_tables,aggregate,paired_comparisons
import csv,datetime

def canonical(x):return json.loads(json.dumps(x))
def verify_tables(phase,gs,slfunc):
 data=read(OUT/f'phase_{phase}_summary.json.gz');raw=[];js=[];cs=[];ds=[];allrows=[]
 for g in gs:
  rows=points(phase,g);allrows+=rows
  a,b,c,d=group_tables(rows,slfunc(g));raw+=a;js+=b;cs+=c;ds+=d
 for k,want in [('judgment',js),('capacity',cs),('decisions',ds)]:assert data[k]==canonical(want),(phase,k)
 assert data['aggregate']==canonical(aggregate(js,cs,ds))
 assert data['paired']==canonical(paired_comparisons(allrows,cs,ds))
 for name,rs in [('raw',raw),('judgment',js),('capacity',cs),('decisions',ds),('operating_points',ds)]:
  if phase=='a' and name=='raw':continue
  with (OUT/f'phase_{phase}_{name}.csv').open(encoding='utf-8',newline='') as f:actual=list(csv.DictReader(f))
  assert len(actual)==len(rs)
  for got,want in zip(actual,rs):
   for k,v in want.items():assert got[k]==(json.dumps(v,separators=(',',':')) if isinstance(v,(dict,list)) else '' if v is None else str(v)),(phase,name,k)
 for d in ds:
  if d['allocation_component'] is not None:assert abs(d['partition_selection_loss']+d['allocation_component']-d['operating_point_loss'])<1e-12
  if d['exact_reference_safe'] is False:
   assert d['recommendation_violations']['violating_requests']>0
   if d['reference_best_capacity']>0:assert d['safe_operating_point_loss']==1
 return len(raw)

def main():
 guard();assert not subprocess.check_output(['git','-C',str(HELIX),'status','--porcelain'],text=True).strip()
 used={i%1200 for w in CONFIG['workloads'] for i in range(w['interval_offset'],w['interval_offset']+w['duration_s']//3)}
 cursor=1140
 for meta in P['phase_b']['workloads']:
  assert meta['interval_offset']==cursor
  indices=[i%1200 for i in range(cursor,cursor+meta['duration_s']//3)];assert indices==meta['source_interval_indices'];assert not used.intersection(indices)
  w=build_helix_azure_conversation_workload(HELIX,commit=HELIX_COMMIT,duration_s=meta['duration_s'],target_request_rate=.5,seed=meta['seed'],interval_offset=cursor).requests
  saved=read(OUT/'workloads'/(meta['id']+'.json'))
  assert [asdict(r) for r in w]==saved['requests'];assert fingerprint(saved['requests'])==meta['workload_fingerprint']
  frozen=subprocess.check_output(['git','show','e3887ca:results/jb1_plus/workloads/'+meta['id']+'.json'],cwd=ROOT)
  assert frozen==(OUT/'workloads'/(meta['id']+'.json')).read_bytes();used.update(indices);cursor+=meta['duration_s']//3
 allrows=[];full_fields=0;refchecked=0;ids=set();attempts=[];physical_by_phase={'a':set(),'b':set(),'controls':set()}
 for phase,gs,slfunc in [('a',P['phase_a']['groups'],lambda g:limits('a')),('b',b_groups(),lambda g:limits('b')),('controls',[g for g in groups() if g['kind']=='a100'],slas)]:
  for g in gs:
   rows=points(phase,g);sl=slfunc(g);grid=sorted({r['intensity'] for r in rows});assert not monotonicity(rows,sl)
   for shift in g['shifts']:assert sorted(r['intensity'] for r in rows if r['shift']==shift)==grid
   if phase=='a':
    history=read(ROOT/'results/sla_sensitivity/refinement'/(g['id']+'.json'));assert grid==history['final_grid']
   if phase=='controls':
    old=read(FORMAL/'groups'/(g['id']+'.json'));assert grid==old['grid']
    om={(r['shift'],r['intensity']):r for r in old['rows']}
    lm={(r['shift'],r['intensity'],r['regime']):r['legacy_result'] for r in read(FORMAL/'legacy_progress_sensitivity/groups'/(g['id']+'.json'))['rows']}
   if phase=='b':
    h=read(OUT/'refinement'/(g['id']+'.json'));assert h['status']=='complete' and len(h['rounds'])<=4 and h['final_grid']==grid
    assert len(grid)<=25 and len(grid)-9==h['added_intensities'];assert min(grid)==.001 and max(grid)==65.536
    known=list(P['phase_b']['initial_grid'])
    for rnd in h['rounds']:
     assert rnd['grid_before']==sorted(known)
     ts=transitions([r for r in rows if r['intensity'] in known]);assert ts==rnd['unresolved_before']
     legal=[x for x in ts if x['lower']<x['midpoint']<x['upper'] and x['midpoint'] not in known]
     expected=list(dict.fromkeys(x['midpoint'] for x in legal))[:16-(len(known)-9)]
     assert expected==rnd['selected'];assert rnd['unselected']==[x for x in ts if x['midpoint'] not in expected];known+=expected
    assert sorted(known)==grid and h['unresolved_transitions']==transitions(rows)
   for r in rows:
    key=(phase,g['id'],r['shift'],r['intensity']);assert key not in ids;ids.add(key)
    if phase=='a':
     old=read(ROOT/r['source_point'])
     assert r['evaluator']['Raw-Full']==old['evaluator']['raw'] and r['evaluator']['Legacy-Full']==old['evaluator']['legacy']
     assert r['reference']==old['reference'];full_fields+=16
    if phase=='controls':
     old=om[r['shift'],r['intensity']];assert r['evaluator']['Raw-Full']==old['evaluator']
     for sid in sl:assert r['evaluator']['Legacy-Full'][sid]==lm[r['shift'],r['intensity'],sid];full_fields+=1
    if phase=='b':
     p,w,want=b_base(g,r['shift'],r['intensity'])
     for k,v in want.items():assert r[k]==v
     assert len(r['attempts'])<=2
     assert read(OUT/'attempts'/g['id']/(fingerprint([r['shift'],r['intensity']])+'.json'))==r['attempts']
     assert all(x['status'] in ['ok','error','timeout'] for x in r['attempts']);attempts+=r['attempts']
     if len(r['attempts'])==2:assert r['attempts'][0]['status']!='ok'
    else:
     w=scale_workload(load_workload(g['workload'])[1],r['intensity']);p=pipeline(g['link'],r['shift'],phase=='a')
     assert r['attempts']==[]
    assert set(r['evaluator'])==set(VARIANTS)
    for v in VARIANTS:
     assert set(r['evaluator'][v])==set(sl)
     for e in r['evaluator'][v].values():
      assert e['safe']==(not e['first_violations']) and e['first_violation']==(e['first_violations'][0] if e['first_violations'] else None)
      assert not e['safe'] or e['drained']
    for sem in ['Raw','Legacy']:
     for sid in sl:assert not verdict(r,sem+'-Full',sid) or verdict(r,sem+'-Remaining',sid)
    if r['status']=='ok':
     raw=read(ROOT/r['reference_path']);assert fingerprint(raw['inputs'])==r['reference_cache_key']
     physical=physical_fingerprint(raw['inputs']);assert physical not in physical_by_phase[phase];physical_by_phase[phase].add(physical)
     assert raw['inputs']['pipeline']==canonical(asdict(p)) and raw['inputs']['workload']==[asdict(x) for x in w]
     rr=raw['raw'];assert rr['finished_requests']==rr['total_requests']==len(w)
     assert set(rr['query_metrics'])=={x.id for x in w}
     for request in w:
      m=rr['query_metrics'][request.id];assert len(m['decode_tpot_s'])==request.output_tokens and m['max_tpot_s']==max(m['decode_tpot_s'])
     reclassified=classify(raw,sl)
     for sid in sl:
      for k,v in reclassified[sid].items():assert r['reference'][sid][k]==v,(key,sid,k)
     refchecked+=len(sl)
    else:assert r['status']=='failed' and not r['reference']
    allrows.append((phase,r))
  verify_tables(phase,gs,slfunc)
 assert sum(phase=='a' for phase,r in allrows)==2050
 assert sum(phase=='controls' for phase,r in allrows)==130
 old4=read(ROOT/'results/sla_sensitivity/summary.json');newa=read(OUT/'phase_a_summary.json.gz')
 dmap={(d['group'],d['sla'],d['variant']):d for d in newa['decisions']}
 for old in old4['decisions']:
  new=dmap[old['group'],old['sla'],{'raw':'Raw-Full','legacy':'Legacy-Full'}[old['semantics']]]
  for k in old.keys() & new.keys():assert old[k]==new[k],('Stage4 decision',old['group'],old['sla'],k)
 cmap={(c['group'],c['sla'],c['shift'],c['variant']):c for c in newa['capacity']}
 for old in old4['capacity']:
  new=cmap[old['group'],old['sla'],old['shift'],{'raw':'Raw-Full','legacy':'Legacy-Full'}[old['semantics']]]
  for k in old.keys() & new.keys():assert old[k]==new[k],('Stage4 capacity',k)
 br=[r for phase,r in allrows if phase=='b'];assert len(br)<=500
 assert not physical_by_phase['b'].intersection(physical_by_phase['a']|physical_by_phase['controls'])
 ex=read(OUT/'execution_summary.json');assert ex['phase_b_unique_physical_points']==len(br) and ex['physical_attempts']==len(attempts)
 assert ex['failed_points']==sum(r['status']!='ok' for r in br)
 assert len(list((OUT/'reference').glob('*.json.gz')))==ex['phase_b_successful_points']
 scheduler=read(OUT/'scheduler_snapshot.json')
 assert scheduler['max_workers']==12 and scheduler['budget_bytes']==24*1024**3 and scheduler['reserve_bytes']==6*1024**3
 assert scheduler['peak_active']<=12 and scheduler['peak_reserved_bytes']<=24*1024**3 and scheduler['active']==scheduler['pending']==0
 formula_checks=0
 for path in (OUT/'mechanisms').glob('*.json.gz'):
  case=read(path);ev=case['evaluator'];sla=SLA(**case['inputs']['sla'])
  for sem in ['Raw','Legacy']:
   full=ev[sem+'-Full'];rem=ev[sem+'-Remaining'];assert full['trajectory']==rem['trajectory']
   for fs,rs in zip(full['trace'],rem['trace']):
    components=rs['prefill_blocking_components']
    for c in components:
     duration=c['full_compute_s']+(sla.fixed_overhead_s+sla.queue_overhead_s if sem=='Legacy' else 0)
     fraction=max(0.,min(1.,1-(rs['time_s']-c['prefill_start_s'])/duration)) if duration>0 else 0
     assert abs(c['remaining_fraction']-fraction)<1e-12 and abs(c['remaining_compute_s']-fraction*c['full_compute_s'])<1e-12
     request=next(r for r in case['inputs']['workload'] if r['id']==c['request_id']);assert c['intrinsic_s']==H*request['input_tokens'];formula_checks+=1
    for rid,ledger in rs['ledger'].items():
     if ledger['phase']=='decode':
      assert abs(ledger['blocking_charge_s']-sum(c['remaining_compute_s']+c['intrinsic_s'] for c in components))<1e-10
      assert abs(fs['ledger'][rid]['blocking_charge_s']-sum(c['full_compute_s']+c['intrinsic_s'] for c in components))<1e-10
     else:assert ledger==fs['ledger'][rid]
 tests=read(OUT/'test_results.json');assert tests['passed']
 timing=read(OUT/'runtime.json');assert all(x['runtime_s']['n']==720 for x in timing['variants'].values())
 checks={'passed':True,'protocol_hash':PH,'protocol_freeze_commit':'e3887ca','protected_files':len(read(OUT/'source_manifest.json')),
  'phase_a_physical_points':2050,'a100_controls':130,'phase_b_physical_points':len(br),'full_stage4_results_exact':True,'stage4_decisions_reproduced':96,'stage4_capacity_records_reproduced':480,
  'baseline_off_mode_equivalence':tests,'reference_threshold_checks':refchecked,'formula_component_checks':formula_checks,
  'checks':['protected hashes unchanged','protocol/workloads committed before outcomes','exact disjoint source windows regenerated','pinned HELIX/adapter/profiles unchanged','all old cache records read only','full per-request drain and token metrics','four variants share every grid','SLA relaxation monotonicity','Full-safe implies Remaining-safe','both transition directions and refinement priority replayed','500-point budget and at most two attempts','missing labels never unsafe','CSV/JSON tables recomputed','loss identity and exact recommendation safety','remaining compute and unscaled H audited','full-drain trajectories unchanged','runtime outputs equal saved scientific outputs'],
  'source_hashes':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'src/journal_baseline_plus.py',ROOT/'tests/test_jb1_plus.py',*(ROOT/'scripts').glob('*jb1_plus*.py')]}}
 write_json(OUT/'quality_checks.json',checks);print(json.dumps(checks,indent=2))

if __name__=='__main__':main()
