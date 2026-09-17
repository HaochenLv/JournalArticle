"""Stage 6 evidence tables; sampled quantities and undefined outcomes stay explicit."""
from stage6_common import *
from collections import Counter
from statistics import mean,median

def sidecar_metrics(m):
    ds=m['decode_tpot_s'];raw=[x-.005 for x in ds]
    return {'output_iterations':len(ds),'aligned_ttft_s':m['aligned_ttft_s'],
      'mean_all_increment_accounted':mean(ds),'max_all_increment_accounted':max(ds),
      'mean_postfirst_increment_accounted':mean(ds[1:]) if len(ds)>1 else None,
      'mean_all_increment_raw':mean(raw),'max_all_increment_raw':max(raw),
      'mean_postfirst_increment_raw':mean(raw[1:]) if len(ds)>1 else None,
      'first_increment_duration_accounted_s':ds[0],'first_increment_duration_raw_s':raw[0],
      'first_increment_completion_latency_accounted_s':m['true_first_token_ttft_s'],
      'first_increment_completion_latency_raw_s':m['true_first_token_ttft_s']-.005,
      'first_increment_completion_exceeds_5_2_s':m['true_first_token_ttft_s']>5.2}

def main():
    guard();judgments=[];capacities=[];decisions=[];sidecar=[];allpoints=[];histories=[]
    for g in P['groups']:
        rows=points(g);allpoints.extend(rows)
        hist=read(OUT/'refinement'/(g['id']+'.json'));assert hist['status']=='complete';histories.append(hist)
        _,base=load_workload(g['workload'])
        for sid,sla in LIMITS.items():
            for variant in P['semantics']:
                meta={'workload':g['workload'],'group':g['id'],'sla':sid,'ttft_s':sla.ttft_s,'tpot_s':sla.tpot_s,'semantics':variant,'variant':P['variant_labels'][variant]}
                pairs=[(verdict(r,variant,sid),verdict(r,'reference',sid)) for r in rows if verdict(r,'reference',sid) is not None]
                judgments.append({**meta,**{field:pairs.count(pair) for field,pair in [
                  ('both_safe',(True,True)),('both_unsafe',(False,False)),('optimistic',(True,False)),('conservative',(False,True))]},
                  'paired_denominator':len(pairs),'physical_denominator':len(rows),'missing_reference':len(rows)-len(pairs),
                  'evaluator_approvals':sum(verdict(r,variant,sid) is True for r in rows),
                  'reference_approvals':sum(verdict(r,'reference',sid) is True for r in rows)})
                d,cs=decision_for(rows,sid,variant)
                for s,c in cs.items():
                    a=c[variant]['largest_safe'];b=c['reference']['largest_safe']
                    gap=a-b if a is not None and b is not None else None
                    rel=gap/b if gap is not None and b else None
                    capacities.append({**meta,'shift':s,'evaluator':c[variant],'reference':c['reference'],
                      'signed_gap':gap,'absolute_gap':abs(gap) if gap is not None else None,
                      'relative_signed_gap':rel,'relative_absolute_gap':abs(rel) if rel is not None else None})
                selected=d['selected_shift'];chosen=cs.get(selected)
                B=max(c['reference']['largest_safe'] or 0 for c in cs.values())
                S=chosen['reference']['largest_safe'] if chosen else None
                L=chosen[variant]['largest_safe'] if chosen else None
                point=next((r for r in rows if r['shift']==selected and r['intensity']==L),None)
                exact=point['reference'].get(sid,{}) if point else {};safe=exact.get('safe')
                usable=L if safe is True else 0. if safe is False or d['abstention'] else None
                rate=span=start=end=None;native_count=None;native_max=None
                if point:
                    scaled=scale_workload(base,L);arrivals=[r.arrival_time_s for r in scaled]
                    start=min(arrivals);end=max(arrivals);span=end-start;rate=len(scaled)/span if span else None
                    if point['status']=='ok':
                        ms=read(ROOT/point['reference_path'])['raw']['query_metrics']
                        native_count=sum(m['true_first_token_ttft_s']>5.2 for m in ms.values())
                        native_max=max(m['true_first_token_ttft_s'] for m in ms.values())
                        for rid,m in ms.items():sidecar.append({**meta,'shift':selected,'intensity':L,
                          'physical_fingerprint':point['physical_fingerprint'],'request_id':rid,
                          'measurement_scope':'simulator-side; one row per recommendation/request; repeated physical metrics are not independent runs',**sidecar_metrics(m)})
                decisions.append({**meta,**d,'B':B,'S':S,'L':L,
                  'reference_selected_shift':min(d['reference_best_set'],key=lambda s:(abs(s),s)) if d['reference_best_set'] else None,
                  'partition_loss':1-S/B if B and S is not None else None,
                  'operating_loss':1-L/B if B and L is not None else None,
                  'allocation_component':(S-L)/B if B and S is not None and L is not None else None,
                  'exact_reference_safe':safe,'safe_usable_load':usable,
                  'safe_operating_loss':1-usable/B if B and usable is not None else None,
                  'recommendation_violations':exact,
                  'violating_request_ids':exact.get('violating_request_ids'),
                  **{k:exact.get(k) for k in ['violating_requests','request_count','violating_request_fraction','max_ttft_excess_s','max_tpot_excess_s','max_normalized_excess']},
                  'finite_window_request_count':len(base) if point else None,'scaled_first_arrival_s':start,'scaled_last_arrival_s':end,
                  'scaled_arrival_span_s':span,'finite_window_request_rate_rps':rate,
                  'first_increment_completion_violating_requests':native_count,
                  'first_increment_completion_exceeds_5_2_s':native_count>0 if native_count is not None else None,
                  'max_first_increment_completion_latency_accounted_s':native_max,
                  'reference_no_safe_candidates':[s for s,c in cs.items() if c['reference']['no_safe']],
                  'evaluator_no_safe_candidates':[s for s,c in cs.items() if c[variant]['no_safe']],
                  'reference_nonmonotone':any(c['reference']['nonmonotone'] for c in cs.values()),
                  'evaluator_nonmonotone':any(c[variant]['nonmonotone'] for c in cs.values()),
                  'unresolved':any(c[m]['unresolved'] for c in cs.values() for m in [variant,'reference'])})
    aggregate=[]
    for sid,sla in LIMITS.items():
        for v in P['semantics']:
            js=[x for x in judgments if x['sla']==sid and x['semantics']==v]
            ds=[x for x in decisions if x['sla']==sid and x['semantics']==v]
            cc=[x for x in capacities if x['sla']==sid and x['semantics']==v]
            gaps=[x['relative_signed_gap'] for x in cc if x['relative_signed_gap'] is not None]
            a={'sla':sid,'tpot_s':sla.tpot_s,'semantics':v,
              **{k:sum(x[k] for x in js) for k in ['both_safe','both_unsafe','optimistic','conservative','paired_denominator','physical_denominator','missing_reference','evaluator_approvals','reference_approvals']},
              'decision_types':dict(Counter(x['mismatch_type'] for x in ds)),
              'winner_agreement':sum(x['winner_agrees'] is True for x in ds),
              'winner_defined_denominator':sum(x['winner_agrees'] is not None for x in ds),
              'unsafe_recommendations':sum(x['exact_reference_safe'] is False for x in ds),
              'abstentions':sum(x['abstention'] for x in ds),'reference_no_safe_workloads':sum(x['B']==0 for x in ds),
              'defined_capacity_gaps':len(gaps),'capacity_relative_signed_min':min(gaps) if gaps else None,
              'capacity_relative_signed_median':median(gaps) if gaps else None,'capacity_relative_signed_max':max(gaps) if gaps else None,
              'capacity_relative_absolute_mean':mean(abs(x) for x in gaps) if gaps else None,
              'native_endpoint_violating_recommendations':sum(x['first_increment_completion_exceeds_5_2_s'] is True for x in ds)}
            for label in ['evaluator','reference']:
                for flag in ['no_safe','nonmonotone','right_censored','unresolved']:
                    a[label+'_'+flag]=sum(x[label][flag] is True for x in cc)
            for field in ['partition_loss','operating_loss','safe_operating_loss','finite_window_request_rate_rps']:
                vals=[x[field] for x in ds if x[field] is not None]
                a[field+'_defined_count']=len(vals)
                for suffix,fn in [('mean',mean),('min',min),('max',max)]:a[field+'_'+suffix]=fn(vals) if vals else None
            aggregate.append(a)
    new=[r for r in allpoints if r['origin']=='stage6_new'];attempts=[a for r in new for a in r['attempts']]
    execution={'old_unique_physical_points_reused':2050,'cache_reuse_count':2050,
      'new_unique_physical_points':len(new),'physical_attempts':len(attempts),'retries':sum(max(0,len(r['attempts'])-1) for r in new),
      'successful_new_physical_points':sum(r['status']=='ok' for r in new),'failed_points':sum(r['status']!='ok' for r in allpoints),
      'timeouts':sum(a['status']=='timeout' for a in attempts),'failed_attempts':sum(a['status']!='ok' for a in attempts),
      'total_unique_physical_points':len(allpoints),'initial_new_helix_runs':0,
      'new_evaluator_calls_initial':20500,'new_evaluator_calls_refinement':len(new)*16,'reused_evaluator_outputs':12300,
      'total_evaluator_judgments':len(allpoints)*16,'reference_sla_classifications':sum(len(r['reference']) for r in allpoints),
      'groups':[{'workload':g['workload'],'original_grid':g['original_grid_size'],'final_grid':len(h['final_grid']),
        'added_intensities':h['added_intensities'],'unresolved_intervals':len(h['unresolved_transitions']),'stop_reason':h['stop_reason']} for g,h in zip(P['groups'],histories)]}
    for name,data in [('judgment',judgments),('capacity',capacities),('decisions',decisions),('operating_points',decisions),('metric_sidecar',sidecar)]:csv_write(OUT/(name+'.csv'),data)
    write_json(OUT/'summary.json',{'protocol_hash':PH,'metric_metadata':P['metric_metadata'],'execution':execution,
      'judgment':judgments,'capacity':capacities,'decisions':decisions,'aggregate':aggregate,
      'sidecar_scope':'Per request at every defined recommendation; same physical point can repeat across SLA/variant. No quantiles. Non-recommended raw metrics remain accessible via point reference_path.',
      'metric_sidecar_rows':len(sidecar)})
    write_json(OUT/'refinement_history.json',histories)
    print(json.dumps({'execution':execution,'aggregate':aggregate},indent=2))

if __name__=='__main__':main()
