"""Serial post-campaign reporting/audit. Run only after run.py has exited."""
from common import *
import subprocess,time,datetime

def main():
    assert read(OUT/'checks/stop_summary.json')['status']=='complete'
    assert (OUT/'runtime/planning_cost.json').exists(),'Campaign finally block must finish first'
    modules=[]
    for name in ['finalize','supplement','figures','audit_evidence']:
        started=time.perf_counter();log=OUT/'checks'/(name+'_execution.log')
        with log.open('a',encoding='utf-8') as f:
            f.write('\nSTART '+datetime.datetime.now(datetime.timezone.utc).isoformat()+'\n');f.flush()
            result=subprocess.run([sys.executable,str(OUT/'code'/(name+'.py'))],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        record={'module':name,'wall_s':time.perf_counter()-started,'returncode':result.returncode,'log':str(log.relative_to(OUT))};modules.append(record)
        write(OUT/'runtime/postprocessing_cost.json',{'modules':modules,'new_physical_executions':0})
        print('POSTPROCESS',name,record['returncode'],round(record['wall_s'],2),flush=True)
        if result.returncode:raise RuntimeError('Postprocessing failed; inspect '+str(log))
    cost=read(OUT/'runtime/planning_cost.json')
    cost['postprocessing_modules_wall_s']=sum(r['wall_s'] for r in modules)
    start=read(OUT/'provenance/starting_state.json')['utc'];end=read(OUT/'provenance/freeze_manifest.json')['frozen_utc']
    cost['preflight_freeze_wall_s']=(datetime.datetime.fromisoformat(end)-datetime.datetime.fromisoformat(start)).total_seconds()
    cost['campaign_elapsed_scope']='run.py after its initial source guard through physical execution, benchmarking, classification, G0/G1 analysis and final bookkeeping; excludes earlier protocol preparation and later reporting/audit'
    cost['postprocessing_scope']='finalize, supplement, figures and independent audit; no extra E or R physical runs'
    cost['one_planning_ledger']={'primary_E_execution_s':cost['one_planning_execution_s'],'profile_and_process_initialization_s':sum(r['startup_wall_s'] for r in cost['worker_startups']),
      'E_and_R_postclassification_s':cost['actual_classifier_s'],'cached_reference_processing_s':cost['actual_cache_processing_s'],
      'note':'Cache processing includes R reclassification, so do not sum it again with the full classifier field. Benchmark repetitions are research measurement cost, not one planning execution.',
      'exact_end_to_end_single_planning_total_s':None,'NA_reason':'The campaign interleaves measurement repeats and refinement; controller/input/serialization components are recorded but a separate repeat-free end-to-end planning run was not authorized or executed.'}
    cost['actual_R_timing_scope']='adapter invocation including initialization/extraction, result dataclass materialization and stdout log context; subsequent JSON/gzip output and six-SLA classification are outside this timer'
    cost['E_timing_scope']='simulate on prepared objects, including default diagnostics and trajectory hashing; additional repeat-verification hash and JSON/gzip output are outside this timer'
    from finalize import csvread
    samples=csvread(OUT/'runtime/evaluator_samples.csv');processing=csvread(OUT/'runtime/cache_processing.csv')
    cost['one_planning_ledger']['E_only_six_SLA_classification_s']=sum(float(r['six_E_classify_s']) for r in processing)
    cost['one_planning_ledger']['primary_E_input_object_preparation_s']=sum(float(r.get('input_object_preparation_s') or 0) for r in samples if r['warmup']=='True')
    cost['one_planning_ledger']['primary_E_serialization_and_verification_hash_s']=sum(float(r.get('serialization_and_semantic_hash_s') or 0) for r in samples if r['warmup']=='True')
    cost['one_planning_ledger']['unmeasured_components']=['controller JSON transport/parse separated from measured object preparation','controller-side grid selection and miscellaneous output writing separately from measured analysis modules']
    attempts=[json.loads(line) for line in (OUT/'runtime/helix_attempts.jsonl').read_text().splitlines()] if (OUT/'runtime/helix_attempts.jsonl').exists() else []
    cost['actual_R_attempt_wall_s_including_failures']=sum(r['wall_s'] for r in attempts)
    cost['peak_memory_limitation']='process-lifetime high-water mark, not isolated per-call or per-model allocation'
    write(OUT/'runtime/planning_cost.json',cost)
    write(OUT/'checks/reporting_completion.json',{'status':'complete_pending_visual_review_and_git_delivery','modules':modules,'quality_passed':read(OUT/'checks/quality_checks.json')['passed'],'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
if __name__=='__main__':main()
