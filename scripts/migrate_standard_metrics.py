"""Read-only migration of saved compressed references, deduplicated by execution.

Writes only results/standard_metrics_v1; never imports or invokes HELIX.
"""
from pathlib import Path
import sys,csv,json,gzip,hashlib,collections,math
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from standard_metrics_v1 import migrate_record,execution_identity,fingerprint

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/standard_metrics_v1'


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    temp.replace(path)


def equal_metrics(a,b):
    if a.keys()!=b.keys():return False
    for rid in a:
        if a[rid].keys()!=b[rid].keys():return False
        for key,v in a[rid].items():
            w=b[rid][key]
            if isinstance(v,float) and isinstance(w,(int,float)):
                if not math.isclose(v,w,rel_tol=1e-10,abs_tol=1e-7):return False
            elif v!=w:return False
    return True


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    entries=[];physical={};skipped=0;total=0;errors=collections.Counter()
    for path in sorted((ROOT/'results').rglob('*.json.gz')):
        if OUT in path.parents:continue
        total+=1
        try:
            with gzip.open(path,'rt',encoding='utf-8') as f:record=json.load(f)
        except (OSError,ValueError,EOFError) as exc:
            if 'reference' not in path.as_posix():
                skipped+=1;continue
            record=None;result={'status':'migration_failed','error_code':'unreadable_record','error_detail':str(exc)}
        else:
            if not isinstance(record,dict) or 'inputs' not in record or 'raw' not in record:
                skipped+=1;continue
            result=migrate_record(record)
        entry={'source':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
               'status':result['status'],'migration_status':result.get('migration_status','migration_failed')}
        pid=None
        if record and isinstance(record.get('inputs'),dict):
            try:pid=execution_identity(record['inputs'])
            except (TypeError,ValueError):pass
        entry['physical_fingerprint']=pid
        if result['status']=='complete':
            entry.update({k:result[k] for k in ['record_overhead_s','total_requests','m1_count',
              'final_completion_error_s','max_endpoint_identity_error_s','max_average_endpoint_formula_error_s']})
        else:
            entry.update(error_code=result['error_code'],error_detail=result['error_detail']);errors[result['error_code']]+=1
        entries.append(entry)
        if pid:
            point=physical.setdefault(pid,{'sources':[],'result':None,'conflict':False})
            point['sources'].append(len(entries)-1)
            if result['status']=='complete':
                if point['result'] is not None and not equal_metrics(point['result']['request_metrics'],result['request_metrics']):
                    point['conflict']=True
                elif point['result'] is None:point['result']=result
        if len(entries)%500==0:print('AUDITED',len(entries),'reference records',flush=True)
    points=[];csv_path=OUT/'request_metrics.csv'
    row_count=0;m1=0;recovered=0;by_scope=collections.defaultdict(set)
    with csv_path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['physical_point_id','request_id','output_tokens','ttft_s','average_tpot_s'],lineterminator='\n')
        writer.writeheader()
        for index,(pid,point) in enumerate(sorted(physical.items()),1):
            sources=[entries[i] for i in point['sources']]
            result=point['result'];ok=result is not None and not point['conflict']
            meta={'physical_point_id':index,'physical_fingerprint':pid,'record_indices':point['sources'],
                  'status':'recoverable' if ok else 'migration_failed',
                  'reason':'duplicate_reconstruction_conflict' if point['conflict'] else None if ok else 'no_recoverable_record'}
            for source in sources:source['physical_point_id']=index
            if ok:
                recovered+=1;m1+=result['m1_count']
                for rid,r in sorted(result['request_metrics'].items()):
                    writer.writerow({'physical_point_id':index,'request_id':rid,
                                     **{k:r[k] for k in ['output_tokens','ttft_s','average_tpot_s']}});row_count+=1
                meta.update(request_count=result['total_requests'],m1_count=result['m1_count'],
                    saved_final_time_s=result['saved_final_time_s'],reconstructed_final_time_s=result['final_time_s'])
            if any(x['source'].startswith('results/stage6_metric_sla/') for x in sources):by_scope['paused_stage6_records'].add(pid)
            if any(not x['source'].startswith('results/stage6_metric_sla/') for x in sources):by_scope['pre_stage6_records'].add(pid)
            points.append(meta)
    # Identify the known Stage4+Stage5 heterogeneous 2550-point inventory without evaluating it.
    inventory=set()
    source_index={x['source']:x for x in entries}
    for directory in ['results/sla_sensitivity/points','results/jb1_plus/phase_b_points']:
        for path in sorted((ROOT/directory).rglob('*.json.gz')):
            with gzip.open(path,'rt',encoding='utf-8') as f:row=json.load(f)
            # Stage5 may use variant-specific field names; reference path is common.
            refpath=row.get('reference_path')
            if refpath:
                matching=source_index.get(refpath)
                if matching and ('-heterogeneous-' in row.get('group','') or row.get('workload','').startswith('w2')):
                    inventory.add(matching['physical_fingerprint'])
    status_counts=dict(collections.Counter(x['migration_status'] for x in entries))
    complete=[e for e in entries if e['status']=='complete']
    audit={'metric_version':'standard-metrics-v1','total_compressed_files_scanned':total,
      'non_reference_files_skipped':skipped,'total_records':len(entries),'record_status_counts':status_counts,
      'unique_physical_points':len(physical),'recoverable_points':recovered,
      'recoverable_percentage':100*recovered/len(physical) if physical else None,
      'failed_migration_points':len(physical)-recovered,
      'failed_migration_records':len(entries)-len(complete),'unidentifiable_records':sum(x['physical_fingerprint'] is None for x in entries),
      'error_codes':dict(errors),'missing_metrics':errors['missing_metrics'],
      'missing_overhead_metadata':errors['missing_overhead_metadata'],'m1_count':m1,
      'output_length_list_length_mismatch':errors['output_length_mismatch'],
      'full_drain_failures':errors['full_drain_failure'],'output_count_inconsistency':errors['output_count_inconsistent'],
      'max_list_inconsistency':errors['max_list_mismatch'],'final_completion_mismatch':errors['final_completion_mismatch'],
      'duplicate_conflict_points':sum(x['conflict'] for x in physical.values()),
      'request_metrics_rows':row_count,
      'max_final_completion_error_s':max((x['final_completion_error_s'] for x in complete),default=None),
      'max_endpoint_identity_error_s':max((x['max_endpoint_identity_error_s'] for x in complete),default=None),
      'max_average_endpoint_formula_error_s':max((x['max_average_endpoint_formula_error_s'] for x in complete),default=None),
      'scopes':{k:len(v) for k,v in by_scope.items()},'stage4_plus_stage5_inventory_points':len(inventory),
      'overhead_values_s':sorted(set(x['record_overhead_s'] for x in complete)),
      'new_helix_runs':0,'formal_evaluator_calls':0,
      'identity':'SHA256 of canonical input with SLA/accounting metadata removed; reconstructed aliases checked before merge',
      'csv_mapping':'physical_point_id maps to points in cache_manifest; empty average_tpot_s means None for m=1; no rounding of floats',
      'tolerances':{'absolute_s':1e-7,'relative_final_and_duplicate':1e-10},
      'limitation':'Saved compact records lack full original timestamp histories. Source-verified lifecycle plus saved first/interval identities and final execution endpoint are checked; no claim of independently measured client timestamps.',
      'source_files_unchanged':True}
    for e in entries:
        assert hashlib.sha256((ROOT/e['source']).read_bytes()).hexdigest()==e['sha256']
    write(OUT/'cache_manifest.json',{'schema':1,'records':entries,'points':points})
    write(OUT/'cache_audit.json',audit)
    print(json.dumps(audit,indent=2))


if __name__=='__main__':main()
