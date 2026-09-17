"""Paired scientific outputs; no composite score or favorable-case selection."""
from jb1_plus_common import *
from collections import Counter
import statistics

def stats(values):
 values=[v for v in values if v is not None]
 return {'n':len(values),'min':min(values) if values else None,'median':statistics.median(values) if values else None,'max':max(values) if values else None,'mean':statistics.mean(values) if values else None}

def group_tables(rows,sl):
 rawrows=[];js=[];cs=[];ds=[];shifts=sorted({r['shift'] for r in rows})
 for sid,sla in sl.items():
  for variant in VARIANTS:
   paired=[]
   meta={'group':rows[0]['group'],'workload':rows[0]['workload'],'sla':sid,'ttft_s':sla.ttft_s,'tpot_s':sla.tpot_s,'variant':variant}
   for r in rows:
    e=r['evaluator'][variant][sid];rr=r['reference'].get(sid,{})
    rawrows.append({**meta,'shift':r['shift'],'intensity':r['intensity'],'status':r['status'],'evaluator_safe':e['safe'],'reference_safe':rr.get('safe'),
     'events':e['events'],'runtime_s':e['runtime_s'],'first_violation':e['first_violation'],'reference_violating_requests':rr.get('violating_requests'),'reference_violating_fraction':rr.get('violating_request_fraction')})
    if rr:paired.append((e['safe'],rr['safe']))
   js.append({**meta,'both_safe':paired.count((True,True)),'both_unsafe':paired.count((False,False)),
    'optimistic':paired.count((True,False)),'conservative':paired.count((False,True)),'paired_denominator':len(paired),'missing':len(rows)-len(paired)})
   summaries={s:{m:sampled([r for r in rows if r['shift']==s],m,sid) for m in [variant,'reference']} for s in shifts}
   for s,c in summaries.items():
    a=c[variant]['largest_safe'];b=c['reference']['largest_safe']
    cs.append({**meta,'shift':s,'evaluator':c[variant],'reference':c['reference'],'signed_gap':a-b if a is not None and b is not None else None,'relative_signed_gap':(a-b)/b if a is not None and b else None})
   es={s:c[variant]['largest_safe'] or 0. for s,c in summaries.items()};rs={s:c['reference']['largest_safe'] or 0. for s,c in summaries.items()}
   d=decision(es,rs);selected=d['selected_shift'];overlap=sorted(set(d['evaluator_best_set'])&set(d['reference_best_set']))
   incomplete=any(c['reference']['missing_count'] for c in summaries.values())
   d.update(best_set_overlap=overlap,incomplete_reference=incomplete,mismatch_type='incomplete reference' if incomplete else 'no-safe recommendation' if d['abstention'] else 'no-safe reference' if not d['reference_best_set'] else 'agreement' if d['winner_agrees'] else 'tie-break mismatch' if overlap else 'strict best-set mismatch')
   B=max(rs.values());S=summaries[selected]['reference']['largest_safe'] if selected is not None else None;L=es[selected] if selected is not None else None
   point=next((r for r in rows if r['shift']==selected and r['intensity']==L),None);exact=point['reference'].get(sid,{}) if point else {};safe=exact.get('safe')
   usable=L if safe is True else 0. if safe is False or d['abstention'] else None
   ds.append({**meta,**d,'reference_best_capacity':B,'selected_partition_reference_capacity':S,'evaluator_recommended_intensity':L,
    'partition_selection_loss':1-S/B if B and S is not None else None,'operating_point_loss':1-L/B if B and L is not None else None,
    'allocation_component':(S-L)/B if B and S is not None and L is not None else None,'exact_reference_safe':safe,'safe_usable_load':usable,
    'safe_operating_point_loss':1-usable/B if B and usable is not None else None,'recommendation_violations':exact,
    'reference_nonmonotone':any(c['reference']['nonmonotone'] for c in summaries.values()),'evaluator_nonmonotone':any(c[variant]['nonmonotone'] for c in summaries.values()),
    'reference_no_safe_candidates':[s for s,c in summaries.items() if c['reference']['no_safe']],
    'evaluator_no_safe_candidates':[s for s,c in summaries.items() if c[variant]['no_safe']],
    'unresolved':any(c[m]['unresolved'] for c in summaries.values() for m in [variant,'reference'])})
 return rawrows,js,cs,ds

def aggregate(js,cs,ds,sid=None):
 out=[]
 for v in VARIANTS:
  j=[x for x in js if x['variant']==v and (sid is None or x['sla']==sid)]
  c=[x for x in cs if x['variant']==v and (sid is None or x['sla']==sid)]
  d=[x for x in ds if x['variant']==v and (sid is None or x['sla']==sid)]
  gaps=[x['relative_signed_gap'] for x in c if x['relative_signed_gap'] is not None]
  out.append({'variant':v,'sla':sid or 'all',**{k:sum(x[k] for x in j) for k in ['both_safe','both_unsafe','optimistic','conservative','paired_denominator','missing']},
   'gap':stats(gaps),'absolute_gap':stats([abs(g) for g in gaps]),'gap_negative':sum(g<0 for g in gaps),'gap_positive':sum(g>0 for g in gaps),
   'evaluator_flags':{k:sum(x['evaluator'][k] is True for x in c) for k in ['no_safe','nonmonotone','right_censored','unresolved']},
   'reference_flags':{k:sum(x['reference'][k] is True for x in c) for k in ['no_safe','nonmonotone','right_censored','unresolved']},
   'decision_types':dict(Counter(x['mismatch_type'] for x in d)),'decisions':len(d),
   'unsafe_recommendations':sum(x['exact_reference_safe'] is False for x in d),'safe_recommendations':sum(x['exact_reference_safe'] is True for x in d),'abstentions':sum(x['abstention'] for x in d),
   **{k:stats([x[k] for x in d]) for k in ['partition_selection_loss','operating_point_loss','safe_operating_point_loss']}})
 return out

def paired_comparisons(rows,cs,ds):
 result={}
 for sem in ['Raw','Legacy']:
  full=sem+'-Full';rem=sem+'-Remaining';changes=[];decchanges=[];gapchanges=[]
  for r in rows:
   for sid in r['evaluator'][full]:
    f=verdict(r,full,sid);a=verdict(r,rem,sid);truth=verdict(r,'reference',sid)
    if f!=a:changes.append({'group':r['group'],'shift':r['shift'],'intensity':r['intensity'],'sla':sid,'full_safe':f,'remaining_safe':a,'reference_safe':truth,'new_optimistic':a is True and truth is False,'removed_conservative':a is True and truth is True})
  dm={(d['group'],d['sla'],d['variant']):d for d in ds}
  for f in [x for x in ds if x['variant']==full]:
   a=dm[f['group'],f['sla'],rem]
   decchanges.append({'group':f['group'],'sla':f['sla'],'full_selected':f['selected_shift'],'remaining_selected':a['selected_shift'],'full_type':f['mismatch_type'],'remaining_type':a['mismatch_type'],
    'full_safe':f['exact_reference_safe'],'remaining_safe':a['exact_reference_safe'],
    **{prefix+'_'+k:d['recommendation_violations'].get(k) for prefix,d in [('full',f),('remaining',a)] for k in ['violating_requests','violating_request_fraction','max_ttft_excess_s','max_tpot_excess_s']},
    **{k+'_delta':a[k]-f[k] if a[k] is not None and f[k] is not None else None for k in ['partition_selection_loss','operating_point_loss','safe_operating_point_loss']}})
  cm={(x['group'],x['sla'],x['shift'],x['variant']):x for x in cs}
  for f in [x for x in cs if x['variant']==full]:
   a=cm[f['group'],f['sla'],f['shift'],rem];fg=f['relative_signed_gap'];ag=a['relative_signed_gap']
   gapchanges.append({'group':f['group'],'sla':f['sla'],'shift':f['shift'],'full_gap':fg,'remaining_gap':ag,'absolute_gap_delta':abs(ag)-abs(fg) if ag is not None and fg is not None else None})
  result[sem]={'label_changes':changes,'new_optimistic':sum(x['new_optimistic'] for x in changes),'removed_conservative':sum(x['removed_conservative'] for x in changes),
   'safe_to_unsafe':sum(x['remaining_safe'] is False for x in changes),'decisions':decchanges,'capacity_pairs':gapchanges,
   'absolute_gap_delta':stats([x['absolute_gap_delta'] for x in gapchanges]),'capacity_improved':sum(x['absolute_gap_delta'] is not None and x['absolute_gap_delta']<0 for x in gapchanges),
   'capacity_worsened':sum(x['absolute_gap_delta'] is not None and x['absolute_gap_delta']>0 for x in gapchanges),
   'new_unsafe_recommendations':sum(x['remaining_safe'] is False and x['full_safe'] is not False for x in decchanges),
   'removed_unsafe_recommendations':sum(x['full_safe'] is False and x['remaining_safe'] is not False for x in decchanges),
   'unsafe_recommendation_severity_worsened':sum(x['full_safe'] is False and x['remaining_safe'] is False and x['remaining_violating_request_fraction']>x['full_violating_request_fraction'] for x in decchanges)}
 return result

def phase_tables(phase,gs,slfunc):
 allrows=[];raw=[];judgment=[];capacity=[];decisions=[]
 for g in gs:
  rows=points(phase,g);assert rows;allrows+=rows
  a,b,c,d=group_tables(rows,slfunc(g));raw+=a;judgment+=b;capacity+=c;decisions+=d
 result={'judgment':judgment,'capacity':capacity,'decisions':decisions,'aggregate':aggregate(judgment,capacity,decisions),
  'by_sla':[a for sid in dict.fromkeys(x['sla'] for x in judgment) for a in aggregate(judgment,capacity,decisions,sid)],
  'paired':paired_comparisons(allrows,capacity,decisions)}
 for name,rows in [('raw',raw),('judgment',judgment),('capacity',capacity),('decisions',decisions),('operating_points',decisions)]:
  if phase=='a' and name=='raw':continue  # Complete Phase A ledgers already reside in point records.
  csv_write(OUT/(f'phase_{phase}_{name}.csv'),rows)
 write_gz(OUT/(f'phase_{phase}_summary.json.gz'),result)
 return result,allrows

def main():
 guard()
 for g in b_groups():assert read(OUT/'refinement'/(g['id']+'.json'))['status']=='complete',g['id']
 a,ar=phase_tables('a',P['phase_a']['groups'],lambda g:limits('a'))
 b,br=phase_tables('b',b_groups(),lambda g:limits('b'))
 controls,cr=phase_tables('controls',[g for g in groups() if g['kind']=='a100'],slas)
 histories=[read(OUT/'refinement'/(g['id']+'.json')) for g in b_groups()]
 write_json(OUT/'phase_b_refinement_history.json',histories)
 attempts=[a for r in br for a in r['attempts']]
 execution={'protocol_hash':PH,'phase_a_reused_physical_points':len(ar),'a100_reused_physical_points':len(cr),'phase_a_new_reference_runs':0,
  'phase_b_unique_physical_points':len(br),'phase_b_successful_points':sum(r['status']=='ok' for r in br),'physical_attempts':len(attempts),
  'retries':sum(max(0,len(r['attempts'])-1) for r in br),'failed_points':sum(r['status']!='ok' for r in br),'timeouts':sum(x['status']=='timeout' for x in attempts),
  'phase_a_new_evaluator_calls':len(ar)*8*2+len(cr)*2*2,'phase_b_evaluator_calls':len(br)*4*4,
  'evaluator_count_scope':'Saved matrix calls only; mechanism replay and unit-test calls are separate, as are the 2880 sequential evaluator timing calls recorded in runtime_samples.csv.',
  'groups':[{'group':h['group'],'grid_size':len(h['final_grid']),'added_intensities':h['added_intensities'],'unresolved_intervals':len(h['unresolved_transitions']),
   'max_unresolved_relative_width':max([x['relative_width'] for x in h['unresolved_transitions']],default=0),'stop_reason':h['stop_reason']} for h in histories]}
 write_json(OUT/'execution_summary.json',execution);write_json(OUT/'failed_points.json',[r for r in br if r['status']!='ok'])
 summary={'protocol_hash':PH,'phase_a':{k:v for k,v in a.items() if k not in ['capacity']},'phase_b':{k:v for k,v in b.items() if k not in ['capacity']},'a100_controls':{k:v for k,v in controls.items() if k not in ['capacity']}}
 write_json(OUT/'summary.json',summary)
 print(json.dumps({'execution':execution,'phase_a':a['aggregate'],'phase_b':b['aggregate']},indent=2))

if __name__=='__main__':main()
