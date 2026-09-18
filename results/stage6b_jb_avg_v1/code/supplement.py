"""Supplementary macro, environment and verification records; no new simulation."""
from common import *
from finalize import csvread,num
from collections import defaultdict,Counter
import platform,ctypes,subprocess,datetime
import importlib.metadata

def main():
    caps=csvread(OUT/'capacity/capacities.csv');ops=csvread(OUT/'decisions/operating_points.csv');ranks=csvread(OUT/'decisions/ranking.csv');acc=csvread(OUT/'metrics/request_accuracy.csv')
    out=[]
    for v in ['G0','G1']:
        for sid in [s['id'] for s in P['slas']]:
            for wid in [w['short_id'] for w in P['workloads']]+['ALL']:
                rows=[r for r in caps if r['grid_version']==v and r['SLA']==sid and (wid=='ALL' or r['workload']==wid)]
                for field in ['signed_gap','signed_relative_gap']:
                    groups=defaultdict(list)
                    for r in rows:
                        x=num(r[field])
                        if x is not None:groups[r['workload']].append(x)
                    vals=[(x,Fraction(1,len(groups)*len(xs))) for xs in groups.values() for x in xs]
                    out.append({'grid_version':v,'SLA':sid,'workload':wid,'metric':field,'weighting':'equal valid candidate then equal workload','valid_workloads':len(groups),'valid_candidates':sum(len(xs) for xs in groups.values()),**summary(vals),'total_candidates':len(rows),'E_no_safe':sum(r['E_no_safe']=='True' for r in rows),'R_no_safe':sum(r['R_no_safe']=='True' for r in rows),'E_unknown':sum(int(r['E_unknown_count'])>0 for r in rows),'R_unknown':sum(int(r['R_unknown_count'])>0 for r in rows),'E_right_censored':sum(r['E_right_censored']=='True' for r in rows),'R_right_censored':sum(r['R_right_censored']=='True' for r in rows)})
    csvwrite(OUT/'capacity/capacity_macro_summary.csv',out)
    rankstats=[]
    for v in ['G0','G1']:
        for sid in [s['id'] for s in P['slas']]+['ALL_SLA_DESCRIPTIVE']:
            for uncensored in [False,True]:
                rs=[r for r in ranks if r['grid_version']==v and (sid=='ALL_SLA_DESCRIPTIVE' or r['SLA']==sid) and (not uncensored or r['censored_best_set']=='False')]
                defined=[r for r in rs if r['exact_set_agreement'] in ['True','False']];n=len(defined);same=sum(r['exact_set_agreement']=='True' for r in defined)
                rankstats.append({'grid_version':v,'SLA':sid,'scope':'uncensored' if uncensored else 'all_cases','scheduled_cases':len(rs),'both_nonempty_identified':n,'exact_set_agreement':same,'exact_set_agreement_fraction':ratio(same,n),'defined_coverage':ratio(n,len(rs)),'na_reason':None if n else 'no two identified nonempty best sets','counts':dict(Counter(r['comparison'] for r in rs)),'strict_mismatch':sum(r['strict_mismatch']=='True' for r in rs),'tie_only_mismatch':sum(r['tie_only_mismatch']=='True' for r in rs),'selected_equal':sum(r['selected_equal']=='True' for r in rs),'abstention':dict(Counter(r['abstention'] for r in rs if r['abstention']))})
    csvwrite(OUT/'decisions/ranking_summary.csv',rankstats)
    opstats=[]
    for v in ['G0','G1']:
        for sid in [s['id'] for s in P['slas']]:
            rs=[r for r in ops if r['grid_version']==v and r['SLA']==sid]
            for field in ['safe_usable_loss','arithmetic_loss','candidate_loss','load_selection_loss']:
                vals=[num(r[field]) for r in rs if num(r[field]) is not None]
                opstats.append({'grid_version':v,'SLA':sid,'metric':field,'valid_workloads':len(vals),'scheduled_workloads':len(rs),**summary([(x,Fraction(1,len(vals))) for x in vals]),'safe':sum(r['safe_R']=='True' for r in rs),'unsafe':sum(r['safe_R']=='False' for r in rs),'abstentions':sum(r['candidate']=='' for r in rs),'unknown_recommendations':sum(r['candidate']!='' and r['safe_R']=='' for r in rs)})
    csvwrite(OUT/'decisions/operating_summary.csv',opstats)
    subtypes=[];judgments=csvread(OUT/'metrics/judgments.csv')
    for v in ['G0','G1']:
        for w in P['workloads']:
            for sla in P['slas']:
                rs=[r for r in judgments if r['grid_version']==v and r['workload']==w['short_id'] and r['SLA']==sla['id']]
                subtypes.append({'grid_version':v,'workload':w['short_id'],'SLA':sla['id'],'scheduled':len(rs),
                  'reference_safe_E_unsupported':sum(r['safe_R']=='True' and r['E_status'].startswith('unsupported') for r in rs),
                  'reference_safe_E_hard_resource':sum(r['safe_R']=='True' and r['E_reason']=='hard_resource' for r in rs),
                  'conservative_latency':sum(r['taxonomy']=='C' and r['E_reason']=='latency' for r in rs),
                  'optimistic_latency':sum(r['taxonomy']=='O' and r['R_reason']=='latency' for r in rs),
                  'optimistic_reference_hard_resource':sum(r['taxonomy']=='O' and r['R_reason']=='hard_resource' for r in rs),
                  'unverified_approval':sum(r['safe_E']=='True' and r['safe_R']=='' for r in rs),
                  'E_profile_domain_unknown':sum(r['E_status']=='unsupported_profile_domain' for r in rs),
                  'E_service_cost_unknown':sum(r['E_status']=='unsupported_service_cost' for r in rs),
                  'E_hard_resource_rejection':sum(r['E_reason']=='hard_resource' for r in rs),
                  'E_latency_rejection':sum(r['E_reason']=='latency' for r in rs),
                  'R_unknown':sum(r['safe_R']=='' for r in rs)})
    csvwrite(OUT/'status/disagreement_subtypes.csv',subtypes)
    # Supplemental physical-point pooled evidence differs explicitly from request-pooled.
    vals=defaultdict(list)
    for version in ['G0','G1']:
        rows=read(OUT/'status'/(version.lower()+'_rows.json'))
        for r in rows:
            if not r['pairable']:continue
            p=read(OUT/'metrics/physical'/(r['physical_id']+'.json.gz'))
            for key,name in [('ttft_s','TTFT'),('average_tpot_s','TPOT')]:
                errors=[e[key]-p['R']['request_metrics'][rid][key] for rid,e in p['E']['request_metrics'].items() if e[key] is not None]
                if errors:vals[version,name].append(errors)
    csvwrite(OUT/'metrics/physical_point_pooled_supplement.csv',[{'grid_version':v,'metric':m,'weighting':'equal physical point, then applicable request; supplemental',**summary([(x,Fraction(1,len(ps)*len(xs))) for xs in ps for x in xs])} for (v,m),ps in vals.items()])
    env=read(OUT/'runtime/environment.json')
    class MS(ctypes.Structure):_fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ['total_physical','available_physical','total_pagefile','available_pagefile','total_virtual','available_virtual','extended_virtual']]
    ms=MS();ms.length=ctypes.sizeof(ms);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms));env['RAM_total_bytes']=ms.total_physical
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as k:env['CPU_name']=winreg.QueryValueEx(k,'ProcessorNameString')[0].strip()
    except OSError:env['CPU_name']=platform.processor()
    env['software_versions']=sorted({d.metadata.get('Name','unknown')+'=='+d.version for d in importlib.metadata.distributions()})
    env['reference_dependency_check']=read(OUT/'checks/reference_environment_check.json')
    env['vendored_runtime_dependency_manifest']='provenance/runtime_dependency_manifest.json'
    write(OUT/'runtime/environment.json',env)
    hashes={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted((OUT/'code').glob('*.py'))}
    frozenrun=next(h for p,h in read(OUT/'provenance/runner_manifest.json')['files'].items() if p.replace('\\','/').endswith('/code/run.py'))
    assert sha(OUT/'code/run.py')==frozenrun
    write(OUT/'provenance/final_runner_manifest.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':hashes,'scope':'analysis/reporting completion after frozen protocol; no model/source/scientific-definition edits','frozen_execution_runner_sha256':frozenrun})
    report=OUT/'reports/FINAL_EVIDENCE_REPORT.md';text=report.read_text(encoding='utf-8').replace('39 targeted tests','41 targeted tests')
    text+='\n## Per-workload primary variation\n\n| Workload | TTFT median signed (s) | TTFT median absolute (s) | TTFT P90 absolute (s) | TPOT median signed (ms) | TPOT median absolute (ms) | TPOT P90 absolute (ms) |\n|---|---:|---:|---:|---:|---:|---:|\n'
    for w in P['workloads']:
        rs={r['metric']:r for r in acc if r['grid_version']=='G0' and r['workload']==w['short_id'] and r['scope']=='full_grid' and r['error_kind']=='seconds' and not r['SLA']}
        values=[]
        for m,scale in [('TTFT',1),('TPOT',1000)]:
            for k in ['median_signed','median_absolute','p90_absolute']:
                x=num(rs[m][k]);values.append(f'{x*scale:.8g}' if x is not None else 'NA (no paired evidence)')
        text+='| '+w['short_id']+' | '+' | '.join(values)+' |\n'
    text+='\nCapacity macro summaries use equal valid candidate then equal workload weighting, separately for each SLA, in `capacity/capacity_macro_summary.csv`. Ranking defined denominators and uncensored strata are in `decisions/ranking_summary.csv`. Operating loss distributions are in `decisions/operating_summary.csv`. Physical-point-pooled and request-pooled accuracy remain supplemental.\n'
    fs=read(OUT/'reports/final_summary.json')
    for v in ['G0','G1']:
        s=fs[v]
        text+=f"\n{v} exact capacity comparisons: {s['identified_capacity_pair_rows']}/300 rows; relative capacity error is defined in {s['relative_capacity_error_valid_rows']}/300 rows, from workloads {s['relative_capacity_error_workloads']}. The displayed error median/P90 describes only these identifiable positive-reference-capacity rows, not the unidentified remainder.\n"
    report.write_text(text,encoding='utf-8')
if __name__=='__main__':main()
