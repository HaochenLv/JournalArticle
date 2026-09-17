"""Audit immutable metrics, then freeze Stage 6 before any new SLA evaluation."""
from pathlib import Path
import sys, json, gzip, hashlib, datetime, subprocess, math
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from formal_core import *

OUT=ROOT/'results/stage6_metric_sla'
def read(path):
    if str(path).endswith('.gz'):
        with gzip.open(path,'rt',encoding='utf-8') as f:return json.load(f)
    return json.loads(Path(path).read_text(encoding='utf-8'))

METADATA={
 'term':'maximum accounted decode-iteration latency constraint',
 'aligned_ttft_s':'Prefill end - creation + 0.005 s; accounted Prefill-completion deadline',
 'true_first_token_ttft_s':'first Increment end - creation + 0.005 s; simulator-side first-Increment completion latency',
 'decode_tpot_s':'each Increment end - start + 0.005 s',
 'max_tpot_s':'max(decode_tpot_s)',
 'verdict':'Every request must meet aligned_ttft_s and every Increment must meet the decode deadline; equality passes',
 'q':16,'q_meaning':'evaluator context/progress update granularity, not one shared latency deadline for 16 tokens',
 'overhead':'Already included once in saved metrics; classification adds nothing; raw sidecar subtracts 0.005 from each entry',
 'schema':'Historical field names retained; metadata is additive; no historical schema edits',
 'scope':'Simulator-side metrics, not measured client latency; not a mean-TPOT model',
 'sidecar':'Per request all-Increment mean/max and post-first mean; raw versions subtract 0.005 per interval; post-first mean null for one output token; no quantiles or fitted mean-to-max conversion',
 'arrival_rate':'N/(last scaled arrival - first scaled arrival); finite observed arrival-span rate, not steady-state throughput; null if span=0',
}

def audit_record(raw):
    rr=raw['raw'];w=raw['inputs']['workload'];ms=rr['query_metrics']
    assert rr['finished_requests']==rr['total_requests']==len(w)==len(ms)
    assert set(ms)=={r['id'] for r in w}
    assert raw['inputs']['sla']['fixed_overhead_s']==.005 and raw['inputs']['sla']['queue_overhead_s']==0
    err=0.;intervals=0;ones=0
    for r in w:
        m=ms[r['id']];ds=m['decode_tpot_s']
        assert len(ds)==r['output_tokens'] and ds
        assert m['max_tpot_s']==max(ds)
        delta=abs(m['true_first_token_ttft_s']-m['aligned_ttft_s']-(ds[0]-.005))
        assert delta<1e-8,(r['id'],delta)
        assert all(math.isfinite(x) and x>=.005 for x in ds)
        err=max(err,delta);intervals+=len(ds);ones+=len(ds)==1
    return len(w),intervals,err,ones

def main():
    assert not (OUT/'protocol_snapshot.json').exists(),'Already frozen; use the guarded runner'
    check_pins()
    head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    assert head=='881f5cbe159dc712178ec413378a3c616a6e739e'
    stage4=read(ROOT/'config/sla_sensitivity_protocol.json')
    # Read all three source protocols; none are modified.
    stage5=read(ROOT/'config/jb1_plus_protocol.json')
    assert stage5['reference']['adapter_commit']==CONFIG['adapter_commit']
    tables={};mins={};prof=Profiles()
    for name in ['a100','l4x2','t4x4']:
        t=prof.tables[name][1]
        values=[(n,t.lookup_seconds_per_layer(n)*(2 if n==1 else 1)) for n in range(1,t.max_x+1)]
        tables[name]={'points_ms':t.points_ms,'integer_batch_range':[1,t.max_x],
          'min_effective_seconds_per_layer':min(v for n,v in values),
          'min_at_batches':[n for n,v in values if v==min(x[1] for x in values)],
          'singleton_seconds_per_layer':values[0][1],
          'downward_segments':[[a,b] for a,b in zip(t.points_ms,t.points_ms[1:]) if b[1]<a[1]]}
        mins[name]=tables[name]['min_effective_seconds_per_layer']
    floors=[]
    for shift,expected in zip(range(-2,3),[.2112,.2176,.224,.2304,.2368]):
        p=pipeline('fast',shift,True)
        floor=sum(s.num_layers*mins[prof._name(p,s)] for s in p.stages)
        singleton=prof.decode_time_per_token(None,0,p,0,1)
        assert math.isclose(floor,expected,abs_tol=1e-12) and math.isclose(singleton,expected,abs_tol=1e-12)
        floors.append({'shift':shift,'compute_s':floor,'accounted_s':floor+.005})
    count=reqs=incs=ones=0;err=0.;groups=[];physical=set()
    for g,n in zip(stage4['groups'],[75,77,70,52,73,63]):
        rows=[read(p) for p in sorted((ROOT/'results/sla_sensitivity/points'/g['id']).glob('*.json.gz'))]
        grid=sorted({r['intensity'] for r in rows});assert len(grid)==n and len(rows)==n*5
        for s in range(-2,3):assert sorted(r['intensity'] for r in rows if r['shift']==s)==grid
        groups.append({**g,'original_grid':grid,'original_grid_size':n})
        for r in rows:
            raw=read(ROOT/r['reference_path'])
            assert fingerprint(raw['inputs'])==r['reference_cache_key']
            assert physical_fingerprint(raw['inputs'])==r['physical_fingerprint']
            assert r['physical_fingerprint'] not in physical;physical.add(r['physical_fingerprint'])
            a,b,c,d=audit_record(raw);count+=1;reqs+=a;incs+=b;err=max(err,c);ones+=d
    assert count==2050
    audited=datetime.datetime.now(datetime.timezone.utc).isoformat()
    audit={'passed':True,'audited_utc':audited,'source_head':head,'metric_metadata':METADATA,
      'physical_records':count,'request_records':reqs,'increment_records':incs,'output_one_records':ones,
      'max_native_minus_aligned_identity_error_s':err,'identity_tolerance_s':1e-8,
      'all_drained':True,'iteration_count_matches_output_tokens':True,'max_matches_full_list':True,
      'nominal_decode_profiles':tables,'candidate_compute_floors':floors,
      'floor_scope':'Pinned profiles and path only; nonnegative networking/queueing can only add to compute. Not a universal real-GPU lower bound.',
      'endpoint_audit':'Pinned adapter extract_helix_query_metrics and Query.get_next_iteration source checked; compact records do not retain original event timestamps, so endpoint formulas are source-verified and saved identities are data-verified.',
      'new_helix_runs':0}
    write_json(OUT/'metric_audit.json',audit)
    protocol={'protocol_id':'FI-STAGE6-METRIC-SLA-v1','source_commit':head,'plan_basis':head,
      'study':'Metric contract audit and bounded parameter supplement on h101-h106; not new held-out validation',
      'groups':groups,'candidate_shifts':[-2,-1,0,1,2],'semantics':stage4['semantics'],
      'variant_labels':{'raw':'Raw-Full','legacy':'Legacy-Full'},
      'slas':[{'id':f'TTFT5.2_TPOT{x:g}','ttft_s':5.2,'tpot_s':x} for x in [.1,.15,.2,.25,.3,.5,5.,10.]],
      'metric_metadata':METADATA,'controls':[.1,.15,.2],'primary_tight':[.25,.3,.5],'stress_comparators':[5.,10.],
      'fixed_overhead_s':.005,'queue_overhead_s':0.,
      'reuse':{'physical_points':2050,'old_tpot':[.3,5.,10.],'new_tpot':[.1,.15,.2,.25,.5],
        'new_initial_evaluator_calls':20500,'initial_new_helix_runs':0,
        'rule':'Hash-verified full Stage4 Raw/Legacy outputs reused for .3/5/10; others call original JB1 evaluate. Reference reclassified using all saved query_metrics lists; never use early-stop maxima for new evaluator verdicts.'},
      'refinement':{'enabled':True,'trigger_tpot':[.25,.3,.5],'relative_resolution':.025,
        'max_added_intensities_per_workload':4,'max_rounds':4,'max_new_unique_physical_points':120,
        'midpoint':'round(sqrt(lower*upper),10)','priority':'descending log(upper/lower), then lower ascending',
        'intervals':'Union of both-direction adjacent boolean transitions across all five candidates, Raw/Legacy/reference at .25/.30/.50 only; null never unsafe',
        'batch':'Select all legal ranked midpoints up to remaining workload budget in each round',
        'range':'No extension of Stage4 final min/max','fairness':'Each intensity, all five candidates, all eight SLAs',
        'stop':'No unresolved/legal transition, 4 intensities, or 4 rounds. Retain unresolved; no budget extension'},
      'reference':{**stage4['reference'],'reuse_original_physical_points':2050,'cache':'Old records read-only; new reference only results/stage6_metric_sla/reference','reclassify':'Full immutable per-request lists; no extra overhead'},
      'scheduler':stage4['scheduler'],'tie_break':stage4['tie_break'],'capacity':stage4['capacity'],
      'decision':stage4['decision'],'loss':stage4['loss'],
      'checks':['all old .3/5/10 labels, complete evaluator records, capacities and decisions reproduced on original Stage4 final grids','physical SLA monotonicity','common final grids','full drain','attempt/retry/cache accounting','protected bytes'],
      'scope_exclusions':['Remaining','A100 experiments','new workload/model/GPU/network/profile stress','new algorithm','manuscript','final-source archaeology'],
      'publication_boundary':stage4['publication_boundary']}
    write_json(ROOT/'config/stage6_metric_sla_protocol.json',protocol)
    paths=[]
    for folder in ['results','src','config','docs','scripts','tests']:
        paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and OUT not in p.parents and 'stage6' not in p.name)
    paths.extend(ROOT/n for n in ['FORMAL_EVIDENCE_REPORT.md','STAGE3_EVIDENCE_REPORT.md','SLA_SENSITIVITY_EVIDENCE_REPORT.md','JB1_PLUS_EVIDENCE_REPORT.md'])
    for folder in ['.deps/evaluator/src','.deps/helix/simulator']:
        paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    manifest={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}
    write_json(OUT/'source_manifest.json',manifest)
    write_json(OUT/'protocol_snapshot.json',{'protocol':protocol,'protocol_hash':fingerprint(protocol),
      'config_sha256':hashlib.sha256((ROOT/'config/stage6_metric_sla_protocol.json').read_bytes()).hexdigest(),
      'source_manifest_hash':fingerprint(manifest),'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'metric_audit_sha256':hashlib.sha256((OUT/'metric_audit.json').read_bytes()).hexdigest(),
      'before_new_threshold_results':True})
    print(json.dumps({'audit':{k:audit[k] for k in ['physical_records','request_records','increment_records','max_native_minus_aligned_identity_error_s']},'protocol_hash':fingerprint(protocol),'protected_files':len(manifest)},indent=2))

if __name__=='__main__':main()
