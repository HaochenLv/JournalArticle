"""Stage 6 helpers; all writes are confined to the sensitivity directory."""
from pathlib import Path
import sys, json, gzip, math, hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from formal_core import *
OUT=ROOT/'results/stage6_metric_sla'
P=json.loads((ROOT/'config/stage6_metric_sla_protocol.json').read_text())
PH=fingerprint(P)
LIMITS={s['id']:SLA(ttft_s=s['ttft_s'],tpot_s=s['tpot_s'],fixed_overhead_s=.005,queue_overhead_s=0.) for s in P['slas']}
OLD={'TTFT5.2_TPOT0.3':'decode','TTFT5.2_TPOT10':'prefill'}

def read(path):
    if str(path).endswith('.gz'):
        with gzip.open(path,'rt',encoding='utf-8') as f:return json.load(f)
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write_gz(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp-'+str(os.getpid()))
    with gzip.open(tmp,'wt',encoding='utf-8') as f:json.dump(data,f,separators=(',',':'),allow_nan=False)
    tmp.replace(path)

def guard():
    check_pins()
    snap=read(OUT/'protocol_snapshot.json')
    assert PH==snap['protocol_hash']
    assert hashlib.sha256((ROOT/'config/stage6_metric_sla_protocol.json').read_bytes()).hexdigest()==snap['config_sha256']
    manifest=read(OUT/'source_manifest.json')
    assert fingerprint(manifest)==snap['source_manifest_hash']
    for name,sha in manifest.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name

def physical_inputs(p,w):
    return {'schema':1,'helix_commit':HELIX_COMMIT,'adapter_commit':CONFIG['adapter_commit'],
      'group_dispatch_extension':1,'pipeline':asdict(p),'workload':[asdict(r) for r in w],
      'sla':asdict(next(iter(LIMITS.values())))}

def classify(raw):
    result={}
    for sid,sla in LIMITS.items():
        d=reference_details(raw,sla)
        ms=raw['raw']['query_metrics']
        # Main classification checks every Increment, not an early-stop summary.
        bad=[rid for rid,m in ms.items() if m['aligned_ttft_s']>sla.ttft_s or any(x>sla.tpot_s for x in m['decode_tpot_s'])]
        assert d['safe']==(not bad)
        d['violating_request_ids']=bad
        tt=d['max_ttft_excess_s']>0;tp=d['max_tpot_excess_s']>0
        d['violation_type']='both' if tt and tp else 'TTFT only' if tt else 'TPOT only' if tp else None
        result[sid]=d
    return result

def evaluate_all(p,w):
    prof=CachedProfiles()
    return {v:{sid:jb(p,w,sla,prof,fixed_in_progress=opts['fixed_in_progress']) for sid,sla in LIMITS.items()} for v,opts in P['semantics'].items()}

def point_base(g,shift,value):
    wd,w=load_workload(g['workload']);p=pipeline(g['link'],shift,True);w=scale_workload(w,value)
    assert fingerprint(asdict(p))==g['partition_fingerprints'][str(shift)]
    return p,w,{'group':g['id'],'workload':g['workload'],'shift':shift,'intensity':value,
      'workload_fingerprint':wd['workload_fingerprint'],'scaled_workload_fingerprint':fingerprint([asdict(x) for x in w]),
      'partition_fingerprint':fingerprint(asdict(p)),'profile_fingerprint':CONFIG['profile_fingerprint'],
      'physical_fingerprint':physical_fingerprint(physical_inputs(p,w))}

def point_path(g,shift,value):return OUT/'points'/g['id']/(fingerprint([shift,value])+'.json.gz')

def points(g):return [read(p) for p in sorted((OUT/'points'/g['id']).glob('*.json.gz'))]

def verdict(row,model,sid):
    d=row['reference'] if model=='reference' else row['evaluator'][model]
    return d.get(sid,{}).get('safe')

def transitions(rows):
    by={(r['shift'],r['intensity']):r for r in rows};grid=sorted({r['intensity'] for r in rows});out=[]
    for a,b in zip(grid,grid[1:]):
        witnesses=[]
        for s in P['candidate_shifts']:
            for sid in LIMITS:
                if LIMITS[sid].tpot_s not in P['refinement']['trigger_tpot']:continue
                for model in ['raw','legacy','reference']:
                    x=verdict(by[s,a],model,sid);y=verdict(by[s,b],model,sid)
                    if x is not None and y is not None and x!=y:witnesses.append({'shift':s,'sla':sid,'model':model,'left_safe':x,'right_safe':y})
        if witnesses and b/a-1>P['refinement']['relative_resolution']:
            out.append({'lower':a,'upper':b,'relative_width':b/a-1,'midpoint':round(math.sqrt(a*b),10),'witnesses':witnesses})
    return sorted(out,key=lambda x:(-math.log(x['upper']/x['lower']),x['lower']))

def monotonicity(rows):
    failures=[]
    for r in rows:
        for m in ['raw','legacy','reference']:
            for a in P['slas']:
                for b in P['slas']:
                    if a['ttft_s']<=b['ttft_s'] and a['tpot_s']<=b['tpot_s']:
                        if verdict(r,m,a['id']) is True and verdict(r,m,b['id']) is False:
                            failures.append([r['group'],r['shift'],r['intensity'],m,a['id'],b['id']])
    return failures

def sampled(rows,model,sid):
    seq=[{'intensity':r['intensity'],'m_safe':verdict(r,model,sid)} for r in sorted(rows,key=lambda r:r['intensity'])]
    valid=[r for r in seq if r['m_safe'] is not None]
    if valid:d=safe_summary(valid,'m')
    else:d={'largest_safe':None,'nearest_unsafe_above':None,'all_unsafe':False,'right_censored':None,'nonmonotone':False,'single_boundary_supported':False,'transitions':[],'sequence':[]}
    # A missing point is never converted to an unsafe label or silently removed.
    d['sequence']=[{'intensity':r['intensity'],'safe':r['m_safe']} for r in seq]
    d['missing_count']=len(seq)-len(valid)
    if d['missing_count']:
        d['single_boundary_supported']=False
        d['all_unsafe']=False
        d['transitions']=[{'left':a['intensity'],'right':b['intensity'],'left_safe':a['m_safe'],'right_safe':b['m_safe']} for a,b in zip(seq,seq[1:]) if a['m_safe'] is not None and b['m_safe'] is not None and a['m_safe']!=b['m_safe']]
        d['right_censored']=seq[-1]['m_safe']
    d['no_safe']=d['largest_safe'] is None
    a=d['largest_safe'];b=d['nearest_unsafe_above']
    d['bracket_relative_width']=b/a-1 if a and b else None
    d['unresolved']=bool(d['missing_count']) or any(x['right']/x['left']-1>.025 for x in d['transitions'])
    return d

def decision_for(rows,sid,variant):
    cs={s:{m:sampled([r for r in rows if r['shift']==s],m,sid) for m in [variant,'reference']} for s in P['candidate_shifts']}
    d=decision({s:cs[s][variant]['largest_safe'] or 0. for s in cs},{s:cs[s]['reference']['largest_safe'] or 0. for s in cs})
    d['best_set_overlap']=sorted(set(d['evaluator_best_set'])&set(d['reference_best_set']))
    d['incomplete_reference']=any(c['reference']['missing_count'] for c in cs.values())
    if d['incomplete_reference']:d['winner_agrees']=None
    d['mismatch_type']=('incomplete reference' if d['incomplete_reference'] else 'no-safe recommendation' if d['abstention'] else 'no-safe reference' if not d['reference_best_set'] else 'agreement' if d['winner_agrees'] else 'tie-break mismatch' if d['best_set_overlap'] else 'strict best-set mismatch')
    return d,cs
