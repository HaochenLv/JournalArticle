"""Derive all Stage 4 tables from saved points, preserving missingness and ties."""
from sla_sensitivity_common import *
from collections import Counter
import statistics

def main():
    guard();rawrows=[];judgments=[];capacities=[];decisions=[];histories=[];allpoints=[];changes=[];resolution=[]
    old=read(FORMAL/'legacy_progress_sensitivity/decision_summary.json')['trials']
    for g in P['groups']:
        rows=points(g);allpoints.extend(rows)
        hist=read(OUT/'refinement'/(g['id']+'.json'));assert hist['status']=='complete';histories.append(hist)
        for sid,sla in LIMITS.items():
            for variant in P['semantics']:
                paired=[]
                for r in rows:
                    e=r['evaluator'][variant][sid];rr=r['reference'].get(sid,{})
                    # Complete ledgers and fingerprints remain in the referenced
                    # point record; avoid replicating them sixteen times in CSV.
                    record={k:r[k] for k in ['group','shift','intensity','origin','status']}
                    record.update(sla=sid,semantics=variant,point_record=fingerprint([r['shift'],r['intensity']]),
                      evaluator_safe=e['safe'],reference_safe=rr.get('safe'),
                      evaluator_first_violation_count=len(e['first_violations']),
                      **{'reference_'+k:rr.get(k) for k in ['violation_type','violating_requests','request_count','violating_request_fraction','max_ttft_excess_s','max_tpot_excess_s']})
                    rawrows.append(record)
                    if rr:paired.append((e['safe'],rr['safe']))
                judgments.append({'workload':g['workload'],'group':g['id'],'sla':sid,'ttft_s':sla.ttft_s,'tpot_s':sla.tpot_s,'semantics':variant,
                  'both_safe':sum(e and r for e,r in paired),'both_unsafe':sum(not e and not r for e,r in paired),
                  'optimistic_disagreement':sum(e and not r for e,r in paired),'conservative_disagreement':sum(not e and r for e,r in paired),
                  'paired_denominator':len(paired),'failed_or_missing':len(rows)-len(paired)})
                d,cs=decision_for(rows,sid,variant)
                initial,_=decision_for([r for r in rows if r['origin']=='stage3_reuse'],sid,variant)
                resolution.append({'group':g['id'],'workload':g['workload'],'sla':sid,'semantics':variant,
                    'initial_selected':initial['selected_shift'],'final_selected':d['selected_shift'],
                    'initial_type':initial['mismatch_type'],'final_type':d['mismatch_type'],
                    'initial_evaluator_best_set':initial['evaluator_best_set'],'final_evaluator_best_set':d['evaluator_best_set'],
                    'initial_reference_best_set':initial['reference_best_set'],'final_reference_best_set':d['reference_best_set'],
                    'type_changed':initial['mismatch_type']!=d['mismatch_type'],
                    'selection_changed':initial['selected_shift']!=d['selected_shift']})
                for s,c in cs.items():
                    a=c[variant]['largest_safe'];b=c['reference']['largest_safe']
                    capacities.append({'workload':g['workload'],'group':g['id'],'shift':s,'sla':sid,'ttft_s':sla.ttft_s,'tpot_s':sla.tpot_s,'semantics':variant,
                      'evaluator':c[variant],'reference':c['reference'],'signed_gap':a-b if a is not None and b is not None else None,
                      'relative_signed_gap':(a-b)/b if a is not None and b else None})
                selected=d['selected_shift'];chosen=cs.get(selected)
                B=max(c['reference']['largest_safe'] or 0 for c in cs.values())
                S=chosen['reference']['largest_safe'] if chosen else None
                L=chosen[variant]['largest_safe'] if chosen else None
                point=next((r for r in rows if r['shift']==selected and r['intensity']==L),None)
                exact=point['reference'].get(sid,{}) if point else {}
                safe=exact.get('safe')
                usable=L if safe is True else 0. if safe is False or d['abstention'] else None
                row={'group':g['id'],'workload':g['workload'],'sla':sid,'ttft_s':sla.ttft_s,'tpot_s':sla.tpot_s,'semantics':variant,**d,
                  'reference_selected_shift':min(d['reference_best_set'],key=lambda s:(abs(s),s)) if d['reference_best_set'] else None,
                  'reference_best_capacity':B,'selected_partition_reference_capacity':S,'evaluator_recommended_intensity':L,
                  'partition_selection_loss':1-S/B if B and S is not None else None,
                  'operating_point_loss':1-L/B if B and L is not None else None,
                  'allocation_component':(S-L)/B if B and S is not None and L is not None else None,
                  'exact_reference_safe':safe,'safe_usable_load':usable,
                  'safe_operating_point_loss':1-usable/B if B and usable is not None else None,
                  'recommendation_violations':exact,'reference_nonmonotone':any(c['reference']['nonmonotone'] for c in cs.values()),
                  'evaluator_nonmonotone':any(c[variant]['nonmonotone'] for c in cs.values()),
                  'reference_no_safe_candidates':[s for s,c in cs.items() if c['reference']['no_safe']],
                  'evaluator_no_safe_candidates':[s for s,c in cs.items() if c[variant]['no_safe']],
                  'unresolved':any(c[m]['unresolved'] for c in cs.values() for m in [variant,'reference'])}
                decisions.append(row)
                if sid in OLD:
                    prior=next(x for x in old if (x['group'],x['regime'],x['variant'])==(g['id'],OLD[sid],variant))
                    changes.append({'workload':g['workload'],'sla':sid,'semantics':variant,
                      'old_selected':prior['selected_shift'],'new_selected':d['selected_shift'],
                      'old_evaluator_best':prior['evaluator_best_set'],'new_evaluator_best':d['evaluator_best_set'],
                      'old_reference_best':prior['reference_best_set'],'new_reference_best':d['reference_best_set'],
                      'old_mismatch_type':prior['mismatch_type'],'new_mismatch_type':d['mismatch_type'],
                      'selected_changed':prior['selected_shift']!=d['selected_shift'],'mismatch_changed':prior['mismatch_type']!=d['mismatch_type'],
                      'best_sets_changed':prior['evaluator_best_set']!=d['evaluator_best_set'] or prior['reference_best_set']!=d['reference_best_set']})
    aggregate=[]
    for sid,sla in LIMITS.items():
        for v in P['semantics']:
            js=[x for x in judgments if x['sla']==sid and x['semantics']==v]
            ds=[x for x in decisions if x['sla']==sid and x['semantics']==v]
            cc=[x for x in capacities if x['sla']==sid and x['semantics']==v]
            gaps=[x['relative_signed_gap'] for x in cc if x['relative_signed_gap'] is not None]
            a={'sla':sid,'ttft_s':sla.ttft_s,'tpot_s':sla.tpot_s,'semantics':v,
              **{k:sum(x[k] for x in js) for k in ['both_safe','both_unsafe','optimistic_disagreement','conservative_disagreement','paired_denominator','failed_or_missing']},
              'decision_types':dict(Counter(x['mismatch_type'] for x in ds)),
              'unsafe_recommendations':sum(x['exact_reference_safe'] is False for x in ds),
              'no_safe_recommendations':sum(x['abstention'] for x in ds),'defined_capacity_gaps':len(gaps),
              'capacity_gap_negative':sum(x<0 for x in gaps),'capacity_gap_zero':sum(x==0 for x in gaps),'capacity_gap_positive':sum(x>0 for x in gaps),
              'capacity_gap_min':min(gaps) if gaps else None,'capacity_gap_median':statistics.median(gaps) if gaps else None,'capacity_gap_max':max(gaps) if gaps else None}
            for field in ['partition_selection_loss','operating_point_loss','safe_operating_point_loss']:
                vals=[x[field] for x in ds if x[field] is not None]
                a[field+'_defined_count']=len(vals)
                a[field+'_mean']=statistics.mean(vals) if vals else None
                a[field+'_min']=min(vals) if vals else None;a[field+'_max']=max(vals) if vals else None
            aggregate.append(a)
    attempts=[a for r in allpoints for a in r['attempts']]
    new=[r for r in allpoints if r['origin']=='stage4_new']
    execution={'protocol_hash':PH,'cache_reuse_count':sum(r['origin']=='stage3_reuse' for r in allpoints),
      'new_unique_physical_points':len(new),'successful_new_physical_points':sum(r['status']=='ok' for r in new),
      'physical_attempts':len(attempts),'retries':sum(max(0,len(r['attempts'])-1) for r in new),
      'timeouts':sum(a['status']=='timeout' for a in attempts),'failed_attempts':sum(a['status']!='ok' for a in attempts),
      'failed_points':sum(r['status']!='ok' for r in allpoints),'total_physical_points':len(allpoints),
      'evaluator_judgments':len(rawrows),'evaluator_original_grid':1450*16,'evaluator_added_grid':len(new)*16,
      'reference_sla_classifications':sum(len(r['reference']) for r in allpoints),
      'summed_new_physical_runtime_s':sum(read(ROOT/r['reference_path'])['summary']['runtime_s'] for r in new if r['status']=='ok'),
      'groups':[{'workload':g['workload'],'before':g['original_grid_size'],'after':len(h['final_grid']),'added':h['added_intensities'],
        'rounds_with_additions':sum(bool(r['selected']) for r in h['rounds']),'unresolved_intervals':len(h['unresolved_transitions']),'stop_reason':h['stop_reason']} for g,h in zip(P['groups'],histories)]}
    for name,data in [('raw',rawrows),('judgment',judgments),('capacity',capacities),('decisions',decisions),('operating_points',decisions)]:csv_write(OUT/(name+'.csv'),data)
    write_json(OUT/'summary.json',{'protocol_hash':PH,'judgment':judgments,'capacity':capacities,'decisions':decisions,'aggregate':aggregate,'stage3_resolution_comparison':changes,'initial_grid_decision_comparison':resolution})
    csv_write(OUT/'initial_grid_decision_comparison.csv',resolution)
    write_json(OUT/'execution_summary.json',execution)
    write_json(OUT/'refinement_history.json',histories)
    write_json(OUT/'failed_points.json',[r for r in allpoints if r['status']!='ok'])
    print(json.dumps(execution,indent=2))

if __name__=='__main__':main()
