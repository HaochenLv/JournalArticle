"""Independent arithmetic and provenance audit. Never simulates or changes evidence."""
from common import *
from finalize import csvread,num,boolean
from collections import Counter,defaultdict
import datetime

def main():
    checks=[]
    def check(name,ok,detail=None):
        checks.append({'name':name,'passed':bool(ok),'detail':detail})
        if not ok:
            write(OUT/'checks/independent_audit.json',{'passed':False,'checks':checks})
            raise AssertionError((name,detail))
    rows=read(OUT/'status/g1_rows.json');g0=read(OUT/'status/g0_rows.json');points={};samples=csvread(OUT/'runtime/evaluator_samples.csv');by=defaultdict(list)
    original=read(OUT/'status/g0_complete.json')
    check('G0_original_recommendations_unchanged',sha(OUT/'decisions/g0_operating_points.csv')==original['original_operating_points_sha256'])
    for sample in samples:by[sample['physical_id']].append(sample)
    for i,row in enumerate(rows):
        pid=row['physical_id'];p=read(OUT/'metrics/physical'/(pid+'.json.gz'));points[pid]=p
        for m in ['E','R']:
            actual=classification(p[m]);check('recomputed_standard_classification',actual==row[m],[pid,m])
        e=read(OUT/'evaluator'/(pid+'.json.gz'))
        if 'trajectory' in e:
            check('saved_trajectory_hash',fingerprint(e['trajectory'])==e['trajectory_hash'],pid)
            semantic=fingerprint({k:v for k,v in e.items() if k!='runtime_s'})
            check('saved_primary_matches_repeats',all(s.get('semantic_hash')==semantic for s in by[pid] if s.get('semantic_hash')),pid)
        check('six_scheduled_runtime_samples',set(s['repeat'] for s in by[pid])=={'0','1','2','3','4','5'},pid)
        if row['source']:
            check('reference_source_hash',sha(ROOT/row['source'])==row['source_sha256'],pid)
            ref=read(ROOT/row['source']);check('physical_identity',execution_identity(ref['inputs'])==pid,pid)
            check('reference_migration',migrate_record(ref)==p['R'],pid)
        if p['R']['status']=='complete':
            for rid,rr in p['R']['request_metrics'].items():
                ordered=rr['arrival_time_s']<=rr['t_first_s']<=rr['t_last_s']
                first=math.isclose(rr['ttft_s'],rr['t_first_s']-rr['arrival_time_s'],abs_tol=1e-7,rel_tol=1e-10)
                average=(rr['average_tpot_s'] is None and rr['t_first_s']==rr['t_last_s']) if rr['output_tokens']==1 else math.isclose(rr['average_tpot_s'],(rr['t_last_s']-rr['t_first_s'])/(rr['output_tokens']-1),abs_tol=1e-7,rel_tol=1e-10)
                check('reference_endpoint_formulas',ordered and first and average,[pid,rid])
        if row['pairable']:
            for rid,er in p['E']['request_metrics'].items():
                rr=p['R']['request_metrics'][rid]
                check('paired_request_identity',er['request_id']==rr['request_id'] and er['arrival_time_s']==rr['arrival_time_s'] and er['output_tokens']==rr['output_tokens'],[pid,rid])
        if i%500==0:print('AUDIT physical',i,'/',len(rows),flush=True)
    caps=csvread(OUT/'capacity/capacities.csv');ops=csvread(OUT/'decisions/operating_points.csv');ranks=csvread(OUT/'decisions/ranking.csv')
    for v,vs in [('G0',g0),('G1',rows)]:
        for w in P['workloads']:
            wid=w['short_id'];rs=[r for r in vs if r['workload']==wid]
            grids=[sorted(r['intensity'] for r in rs if r['candidate']==s) for s in P['candidate_shifts']]
            check('common_grid',all(g==grids[0] for g in grids),[v,wid])
            for sla in P['slas']:
                sid=sla['id'];own={};refcaps=[]
                for candidate in P['candidate_shifts']:
                    own[candidate]={}
                    seq=[r for r in rs if r['candidate']==candidate];saved=next(r for r in caps if r['grid_version']==v and r['workload']==wid and r['candidate']==str(candidate) and r['SLA']==sid)
                    for model in ['E','R']:
                        lower=max([r['intensity'] for r in seq if r[model][sid]['safe'] is True]+[0]);upper=max([r['intensity'] for r in seq if r[model][sid]['safe'] is not False]+[0]);own[candidate][model]=(lower,upper)
                        check('capacity_direct_maxima',num(saved[model+'_C_lower'])==lower and num(saved[model+'_C_upper'])==upper and boolean(saved[model+'_identified'])==(lower==upper),[v,wid,sid,candidate,model])
                    if own[candidate]['R'][0]==own[candidate]['R'][1]:refcaps.append(own[candidate]['R'][0])
                options=[(r['intensity'],P['tie_break'].index(r['candidate']),r) for r in rs if r['E'][sid]['safe'] is True]
                choice=sorted(options,key=lambda x:(-x[0],x[1]))[0][2] if options else None
                op=next(r for r in ops if r['grid_version']==v and r['workload']==wid and r['SLA']==sid)
                check('original_E_only_recommendation',op['physical_id']==(choice['physical_id'] if choice else ''),[v,wid,sid])
                L=choice['intensity'] if choice else 0;safe=choice['R'][sid]['safe'] if choice else None;U=0 if not choice or safe is False else L if safe is True else None
                B=max(refcaps) if len(refcaps)==5 else None
                check('operating_raw_values',num(op['L'])==L and num(op['U'])==U and num(op['B'])==B,[v,wid,sid])
                if B and U is not None:check('operating_loss',num(op['safe_usable_loss'])==1-U/B and num(op['arithmetic_loss'])==1-L/B,[v,wid,sid])
                rank=next(r for r in ranks if r['grid_version']==v and r['workload']==wid and r['SLA']==sid)
                for model in ['E','R']:
                    identified=all(a[model][0]==a[model][1] for a in own.values());maximum=max(a[model][0] for a in own.values())
                    expected=[c for c in P['tie_break'] if own[c][model][0]==maximum] if identified and maximum>0 else [] if identified else None
                    actual=json.loads(rank['best_'+model]) if rank['best_'+model] else None
                    check('best_set_direct',actual==expected,[v,wid,sid,model])
    ledger=read(OUT/'checks/budget_ledger.json');history=[json.loads(line) for line in (OUT/'grids/refinement_history.jsonl').read_text().splitlines() if line]
    selected=[r for r in history if r['phase']=='selected'];terminal=[r for r in history if r['phase']=='all_five_terminal'];attempts=[json.loads(s) for s in (OUT/'runtime/helix_attempts.jsonl').read_text().splitlines()] if (OUT/'runtime/helix_attempts.jsonl').exists() else []
    check('selected_all_five_terminal',len(selected)==len(terminal)==ledger['new_common_intensities'] and all(len(r['points'])==5 for r in terminal))
    check('attempt_ledger',len(attempts)==ledger['helix_attempts'] and len({r['physical_id'] for r in attempts})==ledger['new_helix_unique_starts'])
    check('attempt_budget',len(attempts)<=600 and all(n<=2 for n in Counter(r['physical_id'] for r in attempts).values()))
    # Replay selection order from G0 records, not from final capacities or favorable results.
    current=list(g0);order=[w['short_id'] for w in P['workloads']];last=-1;round_no=0;quotas=Counter()
    for select,done in zip(selected,terminal):
        wid=select['workload'];index=order.index(wid)
        if index<=last:round_no+=1
        last=index
        eligible=brackets([r for r in current if r['workload']==wid]);legal=[r for r in eligible if r['legal']]
        check('refinement_deterministic_selection',eligible==select['eligible_before_selection'] and legal[0]==select['selected'],[wid,round_no])
        selected_mid=Decimal(select['selected']['midpoint']);quotas[wid]+=1
        check('workload_quota',quotas[wid]<=6,wid)
        new=[r for r in rows if r['workload']==wid and Decimal(str(r['intensity']))==selected_mid and r['membership']!='G0']
        check('refinement_five_candidates',{r['candidate'] for r in new}==set(P['candidate_shifts']) and len(new)==5,wid);current.extend(new)
    check('G1_replay_count',len(current)==len(rows))
    dep=read(OUT/'provenance/runtime_dependency_manifest.json')
    for p,h in dep['files'].items():check('runtime_dependency_hash',sha(ROOT/p)==h,p)
    write(OUT/'checks/independent_audit.json',{'passed':True,'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'check_count':len(checks),'no_new_simulation_calls':True})
    q=read(OUT/'checks/quality_checks.json');q.update(independent_audit_passed=True,independent_check_count=len(checks));write(OUT/'checks/quality_checks.json',q)
    print('INDEPENDENT AUDIT PASSED',len(checks),flush=True)
if __name__=='__main__':main()
