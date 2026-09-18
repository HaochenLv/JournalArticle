"""Stage 6B pre-outcome freeze and read-only data gate. No evaluator/classifier calls."""
from pathlib import Path
import sys, json, gzip, hashlib, subprocess, datetime, csv, re, math
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'results/stage6b_jb_avg_v1'
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT/'src'))
from research import pipeline, scale_workload, RequestSpec
from dataclasses import asdict
from standard_metrics_v1 import execution_identity, migrate_record, fingerprint
PIN='eb614e16c9ad3eba44068d58e51b49eabcbdfe14'
SOURCE=Path('C:/Users/haoch/Downloads/STAGE6B_FORMAL_VALIDATION_PROTOCOL.md')
def read(p):
    if str(p).endswith('.gz'):
        with gzip.open(p,'rt',encoding='utf-8') as f:return json.load(f)
    return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def git(*args,cwd=ROOT):return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()
def equal(a,b):
    if type(a) is dict:return a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
    if isinstance(a,float) and isinstance(b,(int,float)):return math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-7)
    return a==b
def main():
    assert not (OUT/'provenance/freeze_manifest.json').exists(),'Freeze already exists'
    start={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':git('rev-parse','HEAD'),
           'status_short':git('status','--short'),'log_5':git('log','--oneline','-5'),
           'initial_observed_status_before_creating_runner':'clean','formal_evaluator_calls':0,'new_helix_attempts':0}
    assert start['head']==PIN
    for d in ['provenance','grids','evaluator','reference','status','metrics','capacity','decisions','applicability','runtime','checks','reports']:(OUT/d).mkdir(parents=True,exist_ok=True)
    write(OUT/'provenance/starting_state.json',start)
    destination=ROOT/'docs/STAGE6B_FORMAL_VALIDATION_PROTOCOL.md'
    if destination.exists():assert destination.read_bytes()==SOURCE.read_bytes()
    else:destination.write_bytes(SOURCE.read_bytes())
    text=SOURCE.read_text(encoding='utf-8')
    sections={m.group(1):m.group(2) for m in re.finditer(r'^# (\d+)\. (.*?)(?=^# \d+\.|\Z)',text,re.M|re.S)}
    assert len(sections)==23
    formal=read(ROOT/'config/formal_protocol.json')
    ws=[]
    for i,(size,n,link) in enumerate(zip([75,77,70,52,73,63,25,25,25,25],[16,54,15,81,14,49,13,48,5,44],['fast','slow','slow','fast','fast','slow','fast','slow','slow','fast'])):
        wid=formal['workloads'][i]['id'] if i<6 else f'w{201+i-6}'
        ws.append({'id':wid,'short_id':wid[:4],'group':wid+'-heterogeneous-'+link,'link':link,'requests':n,'expected_grid_size':size,
          'source':f"results/{'formal' if i<6 else 'jb1_plus'}/workloads/{wid}.json",
          'inventory':f"results/{'sla_sensitivity/points' if i<6 else 'jb1_plus/phase_b_points'}/{wid}-heterogeneous-{link}",
          'refinement':f"results/{'sla_sensitivity' if i<6 else 'jb1_plus'}/refinement/{wid}-heterogeneous-{link}.json"})
    cfg={'protocol_id':'FI-JBAVG-S6B-v1','implementation_pin':PIN,'helix_commit':formal['helix_commit'],'adapter_commit':formal['adapter_commit'],
      'group_dispatch_extension':1,'profile_files':formal['profile_files'],'workloads':ws,'candidate_shifts':[-2,-1,0,1,2],
      'candidate_layers':{str(s):[10+s,10-s]*4 for s in range(-2,3)},'tie_break':[0,-1,1,-2,2],
      'slas':[{'id':f'S{i+1}','ttft_s':t,'tpot_s':d} for i,(t,d) in enumerate([(2.5,.15),(2.5,.30),(6.,.20),(6.,.25),(6.,.30),(6.,.50)])],
      'joint_target':'0.90','required_pass_count':'ceil(Decimal(0.90)*N)','comparison':'unrounded <=; no tolerance',
      'evaluator':{'name':'JB-Avg-v1','q':16,'diagnostic_shares':False,'max_events':100000,'wall_timeout_s':600,'technical_retry_limit':1},
      'metrics':{'version':'standard_metrics_v1','ttft':'t_first-arrival','average_tpot':'(t_last-t_first)/(m-1) for m>1; null for m=1',
      'primary':['median_signed','median_absolute','p90_absolute'],'supplement':['p95_absolute','mean_signed','MAE','min','max','relative','SLA_budget_normalized'],
      'relative_min_reference_s':.001,'quantile':'empirical inverse CDF; Q(p)=inf{x:F(x)>=p}',
      'weighting':['equal workload','equal valid candidate','equal valid physical point','equal applicable request'],'empty_layer':'NA with reason and valid counts'},
      'g0':{'expected_physical_count':2550,'expected_judgments':15300,'primary_accuracy':True,'membership':'complete historical inventory; exact equality to final_grid; no old verdict selection'},
      'refinement':{'start_after':'complete G0 with original recommendations preserved','trigger':'adjacent bool endpoints of opposite labels in any candidate/SLA/E/R',
      'relative_width_gt':'0.05','priority':['b/a descending Decimal','a ascending','b ascending'],'midpoint':'sqrt(a*b)','decimal_precision':50,'rounding':'ROUND_HALF_EVEN','decimal_places':10,
      'round_robin':[w['short_id'] for w in ws],'one_midpoint_per_turn':True,'all_five_terminal_before_reselect':True,'unknown_triggers':False,'same_label_triggers':False,'cache_lookup_only_after_selection':True,'cache_hit_consumes_quota':True,'range_extension':False},
      'budgets':{'intensities_per_workload':6,'total_intensities':60,'candidate_slots':300,'new_helix_unique_starts':300,'helix_attempts':600,'timeout_s':600,'technical_retries_per_input':1,'timing_only_reference_reruns':0},
      'retry_reasons':['timeout','process_interruption','startup_failure','io_failure'],
      'capacity':{'lower':'max(known safe intensities union {0})','upper':'max(known safe or unknown intensities union {0})','identified':'lower==upper','C':'lower if identified else NA','relative_gap':'(CE-CR)/CR only both identified and CR>0','gap_bounds':['CE_lower-CR_upper','CE_upper-CR_lower'],'monotonicity_assumption':False},
      'taxonomy':{'BS':[True,True],'BU':[False,False],'O':[True,False],'C':[False,True],'hard_resource_safe':False,'unsupported_safe':None,'incomplete_safe':None,'timeout_safe':None},
      'judgment_denominators':['BS+BU+O+C','O/(BS+O)','C/(BS+C)','O/(BU+O)','E_approved/all_scheduled','both_decidable/all_scheduled'],'zero_denominator':'NA','near_boundary':'abs(J_R-K)<=1',
      'ranking':{'requires':'all five full-grid capacities identified and max>0','ties':'exact canonical grid value','best_set':'all candidates attaining max','classes':['exact_set_agreement','overlap_nonidentical','strict_mismatch','undefined'],'tie_only':'intersection nonempty and chosen E not in R best set','abstention':['abstain_no_safe','abstain_unknown']},
      'operating_point':{'selection':'highest confirmed-safe E sampled intensity; fixed candidate tie-break; no R fallback','preserve':['G0','G1'],'arithmetic_loss':'1-L/B','safe_usable_intensity':'L if R safe; 0 if R unsafe or abstain; null if R unknown','safe_usable_loss':'1-U/B','loss_denominator':'all five R capacities identified and B>0','shortfall':'max(0,0.90-A_R)','excess_fail':'max(0,joint_fail-(N-K))'},
      'screen':{'cells':60,'min_requests':10,'both_safe_intensities_same_candidate':2,'service_subset':'R True or E True','complete_paired_coverage':1,'optimistic_approvals':0,'unverified_approvals':0,'absolute_relative_capacity_gap_max':.20,'upper_transition_width_max':.05,'right_censored_allowed':False,'p90_sla_normalized_error_max':.10,'safe_original_recommendation_required':True,'safe_usable_loss_max':.20,'matched_runtime_median_ratio_min':10,'matched_all_five_candidates':True,'versions_checked_separately':['G0','G1'],'NA':'not-assessable','positive_story':'at least two workloads including h and w'},
      'load_bands':{'fixed_endpoints':'G0 min/max','u':'log(lambda/min)/log(max/min)','low':'[0,1/3)','middle':'[1/3,2/3)','high':'[2/3,1]','separate_pass_screen':False},
      'runtime':{'warmups':1,'measured_repeats':5,'state':'clean each simulation','point_estimate':'median five','aggregate':['median','P95','range'],'workers':1,'E_R_concurrent':False,'include_diagnostics_hash':True,'reference_timing':'actual adapter call including initialization/extraction','cached_processing_is_execution':False,'no_matched_evidence':'cost advantage unestablished'},
      'tolerances':{'migration_absolute_s':1e-7,'endpoint_and_alias_relative':1e-10},
      'stop_conditions':{'normal':['no eligible interval','all transitions <=5%','all midpoints illegal','6 intensities/workload','all scheduled terminal and summaries/checks complete'],
      'immediate':['source_pin_changed','protected_file_changed','G0_mismatch','alias_conflict','metric_semantics_contradiction','SLA_changes_trajectory','candidate_grid_asymmetry','count_mismatch','budget_overrun','provenance_loss','repeated_environment_failure'],
      'not_stop_or_extend':['no screen passes','optimistic errors','capacity errors','ranking disagreement','runtime advantage inadequate']},
      'prohibitions':['model edits','baseline','ablation','new SLA','new workload','new hardware','old Stage 6 resume','significance tests','bootstrap','fake CI','manuscript','Stage 6C'],
      'authoritative_sections':sections,'protocol_sha256':sha(destination),'source_attachment':str(SOURCE)}
    write(ROOT/'config/stage6b_jb_avg_protocol.json',cfg)
    checks=[]; hashes={}; registry=[]; grids={}; reuse=[]; seen=set()
    def check(name,ok,detail=None):
        checks.append({'name':name,'passed':bool(ok),'detail':detail})
        if not ok:raise RuntimeError(name+': '+str(detail))
    try:
        check('implementation_pin',git('rev-parse','HEAD')==PIN)
        check('helix_pin',git('rev-parse','HEAD',cwd=ROOT/'.deps/helix')==cfg['helix_commit'])
        check('helix_clean',not git('status','--porcelain',cwd=ROOT/'.deps/helix'))
        # The adapter is an exported snapshot; its bare object store HEAD is not the snapshot pin.
        for p in sorted((ROOT/'.deps/evaluator/src').rglob('*.py')):
            rel=p.relative_to(ROOT/'.deps/evaluator').as_posix()
            expected=subprocess.check_output(['git','show',cfg['adapter_commit']+':'+rel],cwd=ROOT/'.deps/evaluator-git')
            check('adapter_source:'+rel,p.read_bytes().replace(b'\r\n',b'\n')==expected.replace(b'\r\n',b'\n'))
        for rel,h in cfg['profile_files'].items():check('profile:'+rel,sha(ROOT/'.deps/helix'/rel)==h)
        protected=read(ROOT/'results/standard_metrics_v1/protected_manifest.json')['files']
        for rel,h in protected.items():
            # These baseline source/cache files were frozen before Stage 6A; later 6A additions are separately pinned.
            check('protected:'+rel,sha(ROOT/rel)==h)
        for base in ['src','config','tests','.deps/evaluator/src','.deps/helix/simulator']:
            for p in sorted((ROOT/base).rglob('*')):
                if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc']:
                    hashes[p.relative_to(ROOT).as_posix()]=sha(p)
        cache=read(ROOT/'results/standard_metrics_v1/cache_manifest.json')
        by_pid={p['physical_fingerprint']:p for p in cache['points']}
        for w in ws:
            wd=read(ROOT/w['source']);requests=tuple(RequestSpec(**r) for r in wd['requests'])
            check(w['id']+':N',len(requests)==w['requests'])
            hashes[w['source']]=sha(ROOT/w['source']);hashes[w['refinement']]=sha(ROOT/w['refinement'])
            final=read(ROOT/w['refinement'])['final_grid']; by_shift={s:[] for s in cfg['candidate_shifts']}; entries=[]
            for path in sorted((ROOT/w['inventory']).glob('*.json.gz')):
                row=read(path);s=row['shift'];x=row['intensity'];by_shift[s].append(x)
                check('inventory_complete',row['status']=='ok',str(path))
                check('inventory_workload',row['workload']==w['id'],str(path))
                rp=ROOT/row['reference_path'];raw=read(rp);inputs=raw['inputs'];pid=execution_identity(inputs)
                expected_inputs={'schema':1,'helix_commit':cfg['helix_commit'],'adapter_commit':cfg['adapter_commit'],'group_dispatch_extension':1,
                  'pipeline':asdict(pipeline(w['link'],s,True)),'workload':[asdict(r) for r in scale_workload(requests,x)]}
                physical=dict(inputs);physical.pop('sla',None)
                check('physical_input_identity',fingerprint(physical)==fingerprint(expected_inputs),str(path))
                check('reference_cache_key',fingerprint(inputs)==row['reference_cache_key'],str(path))
                check('unique_G0_identity',pid not in seen,pid);seen.add(pid)
                metric=migrate_record(raw);check('metric_recovery',metric['status']=='complete',metric.get('error_detail'))
                cp=by_pid[pid];check('inherited_cache_status',cp['status']=='recoverable',pid)
                aliases=[]
                for ix in cp['record_indices']:
                    alias=cache['records'][ix];ap=ROOT/alias['source'];check('alias_hash',sha(ap)==alias['sha256'],alias['source'])
                    ar=read(ap);am=migrate_record(ar)
                    check('alias_identity',execution_identity(ar['inputs'])==pid,alias['source'])
                    check('alias_metrics',am['status']=='complete' and equal(metric['request_metrics'],am['request_metrics']),alias['source'])
                    aliases.append({'source':alias['source'],'sha256':alias['sha256'],'historical_paused_stage6':alias['source'].startswith('results/stage6_metric_sla/'),'consistent':True})
                hashes[path.relative_to(ROOT).as_posix()]=sha(path)
                item={'workload':w['short_id'],'full_workload':w['id'],'candidate':s,'intensity':x,'physical_id':pid,'input_hash':fingerprint(physical),'source':row['reference_path'],'source_sha256':sha(rp),'inventory_source':path.relative_to(ROOT).as_posix(),'membership':'G0','reference_status':'complete','evaluator_status':'not_run'}
                registry.append(item);entries.append(item);reuse.append({'physical_id':pid,'selected_source':row['reference_path'],'aliases':aliases})
            check(w['id']+':grid_sizes',all(len(v)==w['expected_grid_size'] for v in by_shift.values()))
            check(w['id']+':common_final_grid',all(sorted(v)==final for v in by_shift.values()))
            grids[w['short_id']]={'intensities':final,'points':entries,'source_refinement':w['refinement'],'source_sha256':hashes[w['refinement']]}
            print('GATE',w['short_id'],len(entries),'verified',flush=True)
        check('G0_count',len(seen)==2550,len(seen))
        write(OUT/'grids/g0.json',{'version':'G0','workloads':grids,'physical_count':len(seen),'primary':True})
        with (OUT/'provenance/physical_registry.csv').open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(registry[0]));writer.writeheader();writer.writerows(registry)
        write(OUT/'provenance/cache_reuse_manifest.json',{'G0':reuse,'supplemental_historical_cache_manifest_sha256':sha(ROOT/'results/standard_metrics_v1/cache_manifest.json'),'supplemental_cache_policy':'query only after midpoint selection'})
        write(OUT/'checks/preflight_data_gate.json',{'passed':True,'checks':checks,'physical_count':len(seen),'formal_evaluator_calls':0,'classifications':0})
        hashes['docs/STAGE6B_FORMAL_VALIDATION_PROTOCOL.md']=sha(destination)
        hashes['grids/g0.json']=sha(OUT/'grids/g0.json')
        write(OUT/'provenance/source_hashes.json',hashes)
        write(OUT/'provenance/freeze_manifest.json',{'protocol_id':cfg['protocol_id'],'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'implementation_pin':PIN,'protocol_sha256':sha(destination),'config_sha256':sha(ROOT/'config/stage6b_jb_avg_protocol.json'),'source_hashes_sha256':sha(OUT/'provenance/source_hashes.json'),'g0_sha256':sha(OUT/'grids/g0.json'),'data_gate':'passed','data_gate_sha256':sha(OUT/'checks/preflight_data_gate.json'),'amendments':[],'formal_evaluator_calls_before_freeze':0,'classifications_before_freeze':0,'verified_evidence':'all G0 actual inputs, source hashes, aliases and metric identities','inherited_evidence':'historical execution environment not asserted matched'})
    except Exception as exc:
        write(OUT/'checks/preflight_data_gate.json',{'passed':False,'checks':checks,'error':str(exc),'physical_count_verified':len(seen),'formal_evaluator_calls':0,'classifications':0})
        write(OUT/'checks/stop_summary.json',{'status':'failed_preflight','reason':str(exc),'formal_evaluator_calls':0,'new_helix_runs':0,'protocol_modified_to_fit_data':False})
        raise
if __name__=='__main__':main()
