"""Frozen Stage 6B campaign. No historical runner entry points are imported."""
from common import *
import subprocess,time,queue,threading,datetime,platform,os,traceback
from dataclasses import asdict
from research import pipeline,scale_workload,RequestSpec

class Worker:
    def __init__(self):self.process=None;self.starts=[]
    def close(self):
        if self.process and self.process.poll() is None:self.process.kill();self.process.wait()
        self.process=None
    def start(self):
        t=time.perf_counter();self.q=queue.Queue()
        self.process=subprocess.Popen([sys.executable,str(OUT/'code/worker.py')],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(OUT/'runtime/worker_stderr.log').open('a'),text=True,encoding='utf-8',bufsize=1)
        def reader(proc,q):
            for line in proc.stdout:q.put(line)
            q.put(None)
        threading.Thread(target=reader,args=(self.process,self.q),daemon=True).start()
        line=self.q.get(timeout=60);info=json.loads(line);assert info['ready'];info['startup_wall_s']=time.perf_counter()-t;self.starts.append(info)
    def call(self,job):
        if self.process is None:self.start()
        t=time.perf_counter()
        try:
            self.process.stdin.write(json.dumps(job)+'\n');self.process.stdin.flush()
            line=self.q.get(timeout=600)
            if line is None:self.close();return {'status':'process_interruption','wall_s':time.perf_counter()-t}
            return json.loads(line)
        except queue.Empty:self.close();return {'status':'timeout','wall_s':time.perf_counter()-t}
        except (BrokenPipeError,OSError) as e:self.close();return {'status':'io_failure','detail':str(e),'wall_s':time.perf_counter()-t}

def unknown(status,n,detail=None):return {'status':status,'total_requests':n,'request_metrics':{},'resource_feasible':None,'drained':False,'error_detail':detail}
def guard():
    f=read(OUT/'provenance/freeze_manifest.json')
    assert f['data_gate']=='passed'
    assert sha(ROOT/'config/stage6b_jb_avg_protocol.json')==f['config_sha256']
    assert sha(ROOT/'docs/STAGE6B_FORMAL_VALIDATION_PROTOCOL.md')==f['protocol_sha256']
    assert sha(OUT/'grids/g0.json')==f['g0_sha256']
    for rel,h in read(OUT/'provenance/source_hashes.json').items():assert sha((OUT if rel=='grids/g0.json' else ROOT)/rel)==h,rel

def main():
    guard();begin=time.perf_counter();worker=Worker();rows=[];samples=[];cachetimes=[];rtimes=[];registry=[]
    ledger={'new_common_intensities':0,'per_workload':{w['short_id']:0 for w in P['workloads']},'candidate_slots':0,'new_helix_unique_starts':0,'helix_attempts':0,'helix_retries':0,'refinement_cache_hits':0,'timeouts':0,'technical_failures':0,'evaluator_unique_inputs':0,'evaluator_invocations':0,'evaluator_warmups':0,'evaluator_measured_repeats':0,'evaluator_retries':0}
    write(OUT/'runtime/environment.json',{'host':platform.node(),'machine':platform.machine(),'processor':platform.processor(),'os':platform.platform(),'python':sys.version,'python_executable':sys.executable,'workers':1,'thread_env':{k:v for k,v in os.environ.items() if k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']},'timing_clock':time.get_clock_info('perf_counter').__dict__,'execution_policy':'single worker, E and R never concurrent; clean simulate state; profiles reused','pins':{k:P[k] for k in ['implementation_pin','adapter_commit','helix_commit']},'environment_id':fingerprint([platform.node(),platform.platform(),sys.version,sys.executable]),'timing_boundaries':P['runtime'],'memory_scope':'worker process lifetime peak; not per-invocation allocation peak'})
    env=read(OUT/'runtime/environment.json')['environment_id']
    def persist():
        write(OUT/'checks/budget_ledger.json',ledger)
        write(OUT/'status/campaign_progress.json',{'points_completed':len(rows),'G0_completed':sum(r['membership']=='G0' for r in rows),'last_point':rows[-1]['physical_id'] if rows else None,'elapsed_s':time.perf_counter()-begin})
    def process(item,inputs=None,reference_unknown=None):
        pid=item['physical_id'];print('POINT',len(rows)+1,item['workload'],item['candidate'],item['intensity'],flush=True)
        t=time.perf_counter();raw=read(ROOT/item['source']) if item['source'] else None;read_s=time.perf_counter()-t
        inputs=raw['inputs'] if raw else inputs;assert execution_identity(inputs)==pid
        t=time.perf_counter();R=migrate_record(raw) if raw else reference_unknown;recover_s=time.perf_counter()-t
        assert R['status']=='complete' or reference_unknown is not None,'metric identity failure after freeze'
        w=next(w for w in P['workloads'] if w['short_id']==item['workload'])
        job={'inputs':inputs,'physical_id':pid,'candidate':item['candidate'],'link':w['link'],'model':'E'}
        baseline=None;E=None;retry_used=False;ledger['evaluator_unique_inputs']+=1
        for repeat in range(6):
            for attempt in range(2):
                ledger['evaluator_invocations']+=1
                info=worker.call({**job,'save':repeat==0})
                if info['status']=='exception':
                    if info['exception_type'] in ['OSError','IOError']:info['status']='io_failure'
                    else:raise RuntimeError('PROTOCOL_IMPLEMENTATION_CONTRADICTION: '+info['traceback'])
                info.update(physical_id=pid,workload=item['workload'],candidate=item['candidate'],intensity=item['intensity'],repeat=repeat,warmup=repeat==0,attempt=attempt+1,environment_id=env)
                samples.append(info);append(OUT/'runtime/evaluator_samples.jsonl',info)
                technical=info['status'] in ['timeout','process_interruption','startup_failure','io_failure']
                if info['status']=='timeout':ledger['timeouts']+=1
                if not technical:break
                ledger['technical_failures']+=1
                if attempt==0 and not retry_used:ledger['evaluator_retries']+=1;retry_used=True
                else:break
            if repeat==0:ledger['evaluator_warmups']+=1
            else:ledger['evaluator_measured_repeats']+=1
            if technical:
                if repeat==0:E=unknown(info['status'],len(inputs['workload']),info.get('detail'))
                continue
            if baseline is None:baseline=info['semantic_hash']
            assert baseline==info['semantic_hash'],'SLA-independent timing repeat semantics conflict'
        if E is None:E=read(OUT/'evaluator'/(pid+'.json.gz'))
        elif not (OUT/'evaluator'/(pid+'.json.gz')).exists():write(OUT/'evaluator'/(pid+'.json.gz'),E)
        # Compact metrics are kept once per physical point; full trajectory is retained in evaluator/.
        Em={k:v for k,v in E.items() if k not in ['trajectory','round_diagnostics']}
        pairable=E['status']=='complete' and E['drained'] and E['resource_feasible'] is True and R['status']=='complete' and R['drained'] and R['resource_feasible'] is True
        if pairable:
            assert set(E['request_metrics'])==set(R['request_metrics'])
            for rid,er in E['request_metrics'].items():
                rr=R['request_metrics'][rid]
                assert er['arrival_time_s']==rr['arrival_time_s'] and er['output_tokens']==rr['output_tokens']
                assert math.isclose(er['ttft_s'],er['t_first_s']-er['arrival_time_s'],abs_tol=1e-7,rel_tol=1e-10)
                if er['output_tokens']==1:assert er['average_tpot_s'] is None and er['t_first_s']==er['t_last_s']
                else:assert math.isclose(er['average_tpot_s'],(er['t_last_s']-er['t_first_s'])/(er['output_tokens']-1),abs_tol=1e-7,rel_tol=1e-10)
        t=time.perf_counter();ec=classification(Em);eclass=time.perf_counter()-t
        t=time.perf_counter();rc=classification(R);rclass=time.perf_counter()-t
        cachetimes.append({'physical_id':pid,'read_decompress_s':read_s,'recover_s':recover_s,'six_R_classify_s':rclass,'six_E_classify_s':eclass,'is_reference_execution':False})
        r={**item,'E':ec,'R':rc,'pairable':pairable,'E_status':E['status'],'R_status':R['status']}
        write(OUT/'metrics/physical'/(pid+'.json.gz'),{'item':item,'E':Em,'R':R,'classifications':r})
        rows.append(r);registry.append(item)
        raw=raw or {}
        rtimes.append({'physical_id':pid,'workload':item['workload'],'candidate':item['candidate'],'source':item['source'],'cache_hit':bool(raw) and not raw.get('stage6b_actual_execution',False),'actual_new_execution':raw.get('stage6b_actual_execution',False),'wall_s':raw.get('summary',{}).get('runtime_s'),'matched_environment':env if raw.get('stage6b_actual_execution') else None,'matched_na_reason':None if raw.get('stage6b_actual_execution') else 'archival environment/concurrency not proven comparable or incomplete execution'})
        persist();return r
    try:
        g0=read(OUT/'grids/g0.json')
        for w in P['workloads']:
            for item in sorted(g0['workloads'][w['short_id']]['points'],key=lambda r:(r['intensity'],P['tie_break'].index(r['candidate']))):process(item)
        assert len(rows)==2550
        write(OUT/'status/g0_rows.json',rows)
        from analyze import analyze_version
        analyze_version(rows,'G0')
        write(OUT/'status/g0_complete.json',{'physical_count':2550,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'original_operating_points_sha256':sha(OUT/'decisions/g0_operating_points.csv')})
        supplemental=read(ROOT/'results/standard_metrics_v1/cache_manifest.json')
        # Metadata loaded here; identity lookup only occurs below after deterministic selection.
        stopped={}
        while len(stopped)<10:
            for w in P['workloads']:
                wid=w['short_id']
                if wid in stopped:continue
                eligible=brackets([r for r in rows if r['workload']==wid])
                legal=[b for b in eligible if b['legal']]
                if ledger['per_workload'][wid]>=6 or not legal:
                    stopped[wid]={'reason':'intensity quota exhausted' if ledger['per_workload'][wid]>=6 else 'no eligible interval' if not eligible else 'numerical-resolution-limited','unresolved_brackets':eligible};continue
                chosen=legal[0];mid=float(Decimal(chosen['midpoint']));ledger['per_workload'][wid]+=1;ledger['new_common_intensities']+=1;ledger['candidate_slots']+=5
                assert ledger['candidate_slots']<=300 and ledger['new_common_intensities']<=60
                hist={'workload':wid,'eligible_before_selection':eligible,'selected':chosen,'quota_used':ledger['per_workload'][wid],'points':[]}
                append(OUT/'grids/refinement_history.jsonl',{**hist,'phase':'selected'})
                wd=read(ROOT/w['source']);req=tuple(RequestSpec(**r) for r in wd['requests'])
                for s in P['candidate_shifts']:
                    inputs={'schema':1,'helix_commit':P['helix_commit'],'adapter_commit':P['adapter_commit'],'group_dispatch_extension':1,'pipeline':asdict(pipeline(w['link'],s,True)),'workload':[asdict(r) for r in scale_workload(req,mid)],'sla':{'ttft_s':2.5,'tpot_s':.15,'fixed_overhead_s':.005,'queue_overhead_s':0.}}
                    pid=execution_identity(inputs);hit=next((p for p in supplemental['points'] if p['physical_fingerprint']==pid and p['status']=='recoverable'),None)
                    source=None
                    if hit:
                        alias=supplemental['records'][hit['record_indices'][0]];source=alias['source'];assert sha(ROOT/source)==alias['sha256'];ledger['refinement_cache_hits']+=1
                    else:
                        ledger['new_helix_unique_starts']+=1;assert ledger['new_helix_unique_starts']<=300
                        for attempt in range(2):
                            ledger['helix_attempts']+=1;assert ledger['helix_attempts']<=600;persist()
                            info=worker.call({'model':'R','inputs':inputs,'physical_id':pid,'candidate':s,'link':w['link']})
                            append(OUT/'runtime/helix_attempts.jsonl',{'physical_id':pid,'attempt':attempt+1,**info})
                            if info['status']=='complete':source=f'results/stage6b_jb_avg_v1/reference/{pid}.json.gz';break
                            if info['status']=='exception' and info['exception_type'] not in ['OSError','IOError']:raise RuntimeError('PROTOCOL_IMPLEMENTATION_CONTRADICTION: '+info['traceback'])
                            if info['status'] not in ['timeout','process_interruption','startup_failure','io_failure','exception']:break
                            ledger['technical_failures']+=1
                            if info['status']=='timeout':ledger['timeouts']+=1
                            if attempt==0:ledger['helix_retries']+=1
                    terminal=unknown(info['status'],len(inputs['workload']),info.get('detail')) if source is None else None
                    item={'workload':wid,'full_workload':w['id'],'candidate':s,'intensity':mid,'physical_id':pid,'input_hash':pid,'source':source,'source_sha256':sha(ROOT/source) if source else None,'inventory_source':'protocol selected midpoint','membership':'G1_only','reference_status':'complete' if source else terminal['status'],'evaluator_status':'not_run'}
                    result=process(item,inputs,terminal);hist['points'].append({'physical_id':pid,'cache_hit':bool(hit),'E_status':result['E_status'],'R_status':result['R_status']})
                append(OUT/'grids/refinement_history.jsonl',{**hist,'phase':'all_five_terminal'})
        write(OUT/'grids/g1.json',{'version':'G1','physical_count':len(rows),'points':registry,'grids':{w['short_id']:sorted({r['intensity'] for r in rows if r['workload']==w['short_id']}) for w in P['workloads']}})
        write(OUT/'status/g1_rows.json',rows);analyze_version(rows,'G1')
        write(OUT/'checks/stop_summary.json',{'status':'complete','workloads':stopped,'protocol_deviations':[]})
    except Exception as exc:
        write(OUT/'checks/stop_summary.json',{'status':'partial','reason':str(exc),'traceback':traceback.format_exc(),'points_completed':len(rows),'no_model_edits':True})
        print(traceback.format_exc(),flush=True)
        raise
    finally:
        worker.close();persist();csvwrite(OUT/'runtime/evaluator_samples.csv',samples);csvwrite(OUT/'runtime/cache_processing.csv',cachetimes);csvwrite(OUT/'runtime/reference_execution.csv',rtimes)
        write(OUT/'runtime/planning_cost.json',{'campaign_elapsed_s':time.perf_counter()-begin,'worker_startups':worker.starts,'actual_E_benchmark_wall_s':sum(s['wall_s'] for s in samples),'actual_cache_processing_s':sum(x['read_decompress_s']+x['recover_s']+x['six_R_classify_s'] for x in cachetimes),'actual_classifier_s':sum(x['six_E_classify_s']+x['six_R_classify_s'] for x in cachetimes),'historical_rebuild_cost':None,'historical_rebuild_na_reason':'mixed or unknown execution environments; no extrapolation','one_planning_execution_s':sum(s['wall_s'] for s in samples if s['repeat']==0),'planning_scope':'once per unique input plus preparation/classification/grid/serialization; repeats are benchmark cost','complete_breakdown_pending_report':True})
if __name__=='__main__':main()
