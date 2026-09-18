"""Protocol-defined G0/G1 summaries and full evidence tables."""
from common import *
from collections import Counter,defaultdict
import time

def weighted_errors(points,metric,normalized_by=None,relative=False):
    groups=defaultdict(lambda:defaultdict(list));requests=0;omitted=0
    for point in points:
        if not point['classifications']['pairable']:continue
        vals=[]
        for rid,e in point['E']['request_metrics'].items():
            r=point['R']['request_metrics'][rid];a=e[metric];b=r[metric]
            if a is None or b is None:omitted+=1;continue
            if relative and b<.001:omitted+=1;continue
            vals.append((a-b)/(b if relative else normalized_by or 1))
        if vals:groups[point['item']['workload']][point['item']['candidate']].append(vals);requests+=len(vals)
    values=[];nw=len(groups);nc=sum(len(c) for c in groups.values());np=sum(len(ps) for c in groups.values() for ps in c.values())
    for candidates in groups.values():
        for ps in candidates.values():
            for vals in ps:
                weight=Fraction(1,nw*len(candidates)*len(ps)*len(vals))
                values.extend((v,weight) for v in vals)
    return {**summary(values),'valid_workloads':nw,'valid_candidates':nc,'valid_points':np,'valid_requests':requests,'inapplicable_or_small_reference_requests':omitted,'weighting':'equal workload/candidate/point/request'}

def confusion(rows,sid,latency_only=False,near_only=False):
    selected=[r for r in rows if (not latency_only or r['E'][sid]['attainment_fraction'] is not None and r['R'][sid]['attainment_fraction'] is not None) and (not near_only or r['R'][sid]['joint_pass_count'] is not None and abs(r['R'][sid]['joint_pass_count']-r['R'][sid]['required_pass_count'])<=1)]
    counts=Counter(taxonomy(r['E'][sid]['safe'],r['R'][sid]['safe']) for r in selected);d=sum(counts[k] for k in ['BS','BU','O','C']);n=len(selected)
    c={k:counts[k] for k in ['BS','BU','O','C','unknown']};c.update(scheduled=n,decidable=d)
    c.update(E_approved=sum(r['E'][sid]['safe'] is True for r in selected),unverified_approval=sum(r['E'][sid]['safe'] is True and r['R'][sid]['safe'] is None for r in selected))
    nums={'optimistic_approval_fraction':(c['O'],c['BS']+c['O']),'reference_safe_missed_fraction':(c['C'],c['BS']+c['C']),'false_positive_rate':(c['O'],c['BU']+c['O']),'E_approval_coverage':(c['E_approved'],n),'both_decision_coverage':(d,n),**{k+'_fraction':(c[k],d) for k in ['BS','BU','O','C']}}
    for k,(a,b) in nums.items():c.update({k:ratio(a,b),k+'_numerator':a,k+'_denominator':b,k+'_na_reason':None if b else 'zero denominator'})
    ds=[r['E'][sid]['attainment_fraction']-r['R'][sid]['attainment_fraction'] for r in selected if r['E'][sid]['attainment_fraction'] is not None and r['R'][sid]['attainment_fraction'] is not None]
    c.update(attainment_mean_bias=statistics.mean(ds) if ds else None,attainment_MAE=statistics.mean(abs(x) for x in ds) if ds else None,attainment_P90_absolute=quantile([abs(x) for x in ds],.9),attainment_na_reason=None if ds else 'no both-attainment-defined points',subset_status='present' if selected else 'absent')
    return c

def analyze_version(rows,version):
    started=time.perf_counter();prefix=version.lower();points=[];pairs=[];statuses=[];judgments=[];summaries=[];accuracies=[];capacities=[];sequences=[];rankings=[];operating=[];bandrows=[]
    for r in rows:
        p=read(OUT/'metrics/physical'/(r['physical_id']+'.json.gz'));points.append(p)
        e,rr=p['E'],p['R'];item=p['item'];n=rr['total_requests']
        for model,m in [('E',e),('R',rr)]:
            statuses.append({'grid_version':version,**{k:r[k] for k in ['physical_id','workload','candidate','intensity']},'model':model,'status':m['status'],'resource_feasible':m['resource_feasible'],'drained':m['drained'],'pairable':r['pairable'],'pair_na_reason':None if r['pairable'] else 'both complete resource-feasible executions required','reason':m.get('error_detail') or m.get('resource_failures'),'decision_defined':{s['id']:r[model][s['id']]['safe'] is not None for s in P['slas']}})
        if version=='G0' or item['membership']!='G0':
            # Includes unpaired requests as explicit NA, never partial easy-request error samples.
            for rid,rv in rr['request_metrics'].items():
                ev=e['request_metrics'].get(rid,{}) if r['pairable'] else {}
                row={**{k:item[k] for k in ['physical_id','workload','candidate','intensity','membership']},'request_id':rid,'arrival_time_s':rv['arrival_time_s'],'output_tokens':rv['output_tokens'],'pairable':r['pairable']}
                for key,name in [('ttft_s','TTFT'),('average_tpot_s','TPOT')]:
                    a=ev.get(key);b=rv[key];err=a-b if a is not None and b is not None else None
                    row.update({name+'_E':a,name+'_R':b,name+'_signed_error':err,name+'_absolute_error':abs(err) if err is not None else None,name+'_signed_relative_error':err/b if err is not None and b>=.001 else None,name+'_na_reason':None if err is not None else 'm=1 TPOT undefined' if key=='average_tpot_s' and rv['output_tokens']==1 else 'execution not pairable',name+'_relative_na_reason':None if err is not None and b>=.001 else 'unpaired, m=1, or reference <0.001 s'})
                pairs.append(row)
        for sla in P['slas']:
            sid=sla['id'];a=r['E'][sid];b=r['R'][sid]
            judgments.append({'grid_version':version,**{k:r[k] for k in ['physical_id','workload','candidate','intensity']},'SLA':sid,'N':n,'K':int((Decimal('.90')*n).to_integral_value(rounding='ROUND_CEILING')),'allowed_failures':n-int((Decimal('.90')*n).to_integral_value(rounding='ROUND_CEILING')),'attainment_resolution':1/n,
              'J_E':a['joint_pass_count'],'A_E':a['attainment_fraction'],'safe_E':a['safe'],'E_status':e['status'],'E_reason':'hard_resource' if e['resource_feasible'] is False else 'latency' if a['safe'] is False else None,'J_R':b['joint_pass_count'],'A_R':b['attainment_fraction'],'safe_R':b['safe'],'R_status':rr['status'],'R_reason':'hard_resource' if rr['resource_feasible'] is False else 'latency' if b['safe'] is False else None,'taxonomy':taxonomy(a['safe'],b['safe']),'near_boundary':abs(b['joint_pass_count']-b['required_pass_count'])<=1 if b['joint_pass_count'] is not None else None,'na_reason':None if a['safe'] is not None and b['safe'] is not None else 'one or both service decisions unknown'})
    for wid in [w['short_id'] for w in P['workloads']]+['ALL']:
        ps=[p for p in points if wid=='ALL' or p['item']['workload']==wid];rs=[r for r in rows if wid=='ALL' or r['workload']==wid]
        for key,label in [('ttft_s','TTFT'),('average_tpot_s','TPOT')]:
            for relative in [False,True]:accuracies.append({'grid_version':version,'workload':wid,'scope':'full_grid','SLA':None,'metric':label,'error_kind':'relative' if relative else 'seconds',**weighted_errors(ps,key,relative=relative)})
        for sla in P['slas']:
            sid=sla['id'];subset=[p for p in ps if p['classifications']['E'][sid]['safe'] is True or p['classifications']['R'][sid]['safe'] is True]
            for scope,selected in [('full_grid',ps),('service_relevant',subset)]:
                for key,label,limit in [('ttft_s','TTFT',sla['ttft_s']),('average_tpot_s','TPOT',sla['tpot_s'])]:
                    accuracies.append({'grid_version':version,'workload':wid,'scope':scope,'SLA':sid,'metric':label,'error_kind':'SLA_budget_normalized',**weighted_errors(selected,key,limit)})
                    if scope=='service_relevant':accuracies.append({'grid_version':version,'workload':wid,'scope':scope,'SLA':sid,'metric':label,'error_kind':'seconds',**weighted_errors(selected,key)})
            for scope,latency,near in [('service',False,False),('latency_only',True,False),('near_boundary',False,True)]:
                cs=[]
                for ww in ([wid] if wid!='ALL' else [w['short_id'] for w in P['workloads']]):
                    for candidate in P['candidate_shifts']:
                        v=confusion([r for r in rs if r['workload']==ww and r['candidate']==candidate],sid,latency,near);cs.append((ww,v))
                        if wid!='ALL':summaries.append({'grid_version':version,'workload':wid,'candidate':candidate,'SLA':sid,'scope':scope,'aggregation':'candidate_raw_counts',**v})
                summaries.append({'grid_version':version,'workload':wid,'candidate':'ALL','SLA':sid,'scope':scope,'aggregation':'pooled_counts',**confusion(rs,sid,latency,near)})
                macro={}
                for key in ['optimistic_approval_fraction','reference_safe_missed_fraction','false_positive_rate','E_approval_coverage','both_decision_coverage','BS_fraction','BU_fraction','O_fraction','C_fraction']:
                    ws=defaultdict(list)
                    for ww,v in cs:
                        if v[key] is not None:ws[ww].append(v[key])
                    vals=[statistics.mean(v) for v in ws.values()]
                    macro.update({key:statistics.mean(vals) if vals else None,key+'_valid_workloads':len(vals),key+'_valid_candidates':sum(len(v) for v in ws.values()),key+'_na_reason':None if vals else 'all denominators zero'})
                ag=defaultdict(lambda:defaultdict(list))
                for row in rs:
                    e,r=row['E'][sid],row['R'][sid]
                    if e['attainment_fraction'] is None or r['attainment_fraction'] is None:continue
                    if near and abs(r['joint_pass_count']-r['required_pass_count'])>1:continue
                    ag[row['workload']][row['candidate']].append(e['attainment_fraction']-r['attainment_fraction'])
                av=[(x,Fraction(1,len(ag)*len(candidates)*len(values))) for candidates in ag.values() for values in candidates.values() for x in values]
                ast=summary(av)
                macro.update(attainment_mean_bias=ast['mean_signed'],attainment_MAE=ast['MAE'],attainment_P90_absolute=ast['p90_absolute'],attainment_na_reason=ast['na_reason'],attainment_valid_workloads=len(ag),attainment_valid_candidates=sum(len(x) for x in ag.values()))
                summaries.append({'grid_version':version,'workload':wid,'candidate':'ALL','SLA':sid,'scope':scope,'aggregation':'equal_candidate_equal_workload_macro',**macro})
            if wid=='ALL':continue
            caps,rank,op=decisions(rs,sid);rankings.append({'grid_version':version,'workload':wid,'SLA':sid,**rank})
            if op['physical_id']:
                p=next(p for p in ps if p['item']['physical_id']==op['physical_id']);nd=sum(r['output_tokens']>1 for r in p['R']['request_metrics'].values());op['N_D']=nd;op['tpot_fail_fraction']=op['tpot_fail']/nd if op['tpot_fail'] is not None and nd else None;op['tpot_fraction_na_reason']=None if op['tpot_fail'] is not None and nd else 'no applicable TPOT requests or no latency counts'
            else:op.update(N_D=None,tpot_fail_fraction=None,tpot_fraction_na_reason='abstention')
            operating.append({'grid_version':version,'workload':wid,'SLA':sid,**op})
            for c in P['candidate_shifts']:
                e,r=caps['E'][c],caps['R'][c];identified=e['identified'] and r['identified'];gap=e['C']-r['C'] if identified else None
                relative=gap/r['C'] if identified and r['C']>0 else None
                capacities.append({'grid_version':version,'workload':wid,'candidate':c,'SLA':sid,**{m+'_'+k:v for m,cap in [('E',e),('R',r)] for k,v in cap.items() if k not in ['sequence','transitions','nonmonotonic_witnesses','safe_runs']},'signed_gap':gap,'absolute_gap':abs(gap) if gap is not None else None,'signed_relative_gap':relative,'absolute_relative_gap':abs(relative) if relative is not None else None,'relative_na_reason':None if relative is not None else 'unidentified capacity' if not identified else 'reference zero sampled capacity','gap_lower':e['C_lower']-r['C_upper'],'gap_upper':e['C_upper']-r['C_lower'],'both_no_safe':identified and e['C']==r['C']==0,'evaluator_approves_reference_no_safe':identified and e['C']>0 and r['C']==0})
                for model,cap in [('E',e),('R',r)]:sequences.append({'grid_version':version,'workload':wid,'candidate':c,'SLA':sid,'model':model,**cap})
        if wid!='ALL':
            g0=read(OUT/'grids/g0.json')['workloads'][wid]['intensities'];lo,hi=g0[0],g0[-1]
            for name,lb,ub in [('low',0,1/3),('middle',1/3,2/3),('high',2/3,1.00000000000001)]:
                bp=[p for p in ps if lb<=math.log(p['item']['intensity']/lo)/math.log(hi/lo)<ub]
                for metric,key in [('TTFT','ttft_s'),('TPOT','average_tpot_s')]:
                    bandrows.append({'grid_version':version,'workload':wid,'band':name,'g0_min':lo,'g0_max':hi,'metric':metric,'scheduled_points':len(bp),'pairable_points':sum(p['classifications']['pairable'] for p in bp),'E_status_counts':dict(Counter(p['E']['status'] for p in bp)),'R_status_counts':dict(Counter(p['R']['status'] for p in bp)),'pairable_coverage':ratio(sum(p['classifications']['pairable'] for p in bp),len(bp)),'coverage_na_reason':None if bp else 'empty band',**weighted_errors(bp,key)})
    for folder,name,data in [('status','point_status',statuses),('metrics','request_pairs',pairs),('metrics','request_accuracy',accuracies),('metrics','judgments',judgments),('metrics','judgment_summary',summaries),('capacity','capacities',capacities),('decisions','ranking',rankings),('decisions','operating_points',operating),('applicability','load_bands',bandrows)]:csvwrite(OUT/folder/(prefix+'_'+name+'.csv'),data)
    with (OUT/'capacity'/(prefix+'_sequences.jsonl')).open('w',encoding='utf-8') as f:
        for r in sequences:f.write(json.dumps(r,separators=(',',':'))+'\n')
    evidence={'version':version,'physical_count':len(rows),'E_status_counts':dict(Counter(p['E']['status'] for p in points)),'R_status_counts':dict(Counter(p['R']['status'] for p in points)),'pairable_points':sum(r['pairable'] for r in rows),'judgment_counts':dict(Counter(r['taxonomy'] for r in judgments)),'accuracy':[r for r in accuracies if r['workload']=='ALL' and r['scope']=='full_grid' and r['SLA'] is None],'ranking_counts':dict(Counter(r['comparison'] for r in rankings)),'unsafe_recommendations':sum(r['safe_R'] is False for r in operating),'safe_recommendations':sum(r['safe_R'] is True for r in operating),'abstentions':sum(r['candidate'] is None for r in operating),'unknown_recommendations':sum(r['candidate'] is not None and r['safe_R'] is None for r in operating),'capacity_rows':len(capacities),'relative_capacity_error_median':quantile([r['absolute_relative_gap'] for r in capacities if r['absolute_relative_gap'] is not None],.5),'relative_capacity_error_P90':quantile([r['absolute_relative_gap'] for r in capacities if r['absolute_relative_gap'] is not None],.9),'right_censored_sequences':sum(r['right_censored'] for r in sequences),'no_safe_sequences':sum(r['no_safe'] for r in sequences),'unknown_sequences':sum(r['unknown_count']>0 for r in sequences),'nonmonotone_sequences':sum(r['nonmonotone'] for r in sequences),'unresolved_brackets':sum(len(r['unresolved_brackets']) for r in sequences),'analysis_wall_s':time.perf_counter()-started}
    write(OUT/'reports'/(prefix+'_summary.json'),evidence)
    return evidence
