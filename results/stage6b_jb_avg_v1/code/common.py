"""Stage 6B analysis primitives; independent of historical verdict helpers."""
from pathlib import Path
import sys,json,gzip,csv,hashlib,math,statistics
from decimal import Decimal,localcontext,ROUND_HALF_EVEN
from fractions import Fraction
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'results/stage6b_jb_avg_v1'
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'src'))
from standard_metrics_v1 import fingerprint,execution_identity,classify,migrate_record
P=json.loads((ROOT/'config/stage6b_jb_avg_protocol.json').read_text(encoding='utf-8'))
def read(p):
    if str(p).endswith('.gz'):
        with gzip.open(p,'rt',encoding='utf-8') as f:return json.load(f)
    return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_suffix(p.suffix+'.tmp')
    if str(p).endswith('.gz'):
        with gzip.open(temp,'wt',encoding='utf-8') as f:json.dump(v,f,separators=(',',':'),allow_nan=False)
    else:temp.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    temp.replace(p)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def csvwrite(p,rows,fields=None):
    p.parent.mkdir(parents=True,exist_ok=True)
    fields=fields or list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        w.writerows({k:json.dumps(v,separators=(',',':')) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)
def append(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('a',encoding='utf-8') as f:f.write(json.dumps(v,separators=(',',':'),allow_nan=False)+'\n')
def ratio(n,d):return n/d if d else None
def quantile(values,p):
    """Empirical inverse CDF, unweighted."""
    if not values:return None
    return sorted(values)[int((Decimal(str(p))*len(values)).to_integral_value(rounding='ROUND_CEILING'))-1]
def weighted_quantile(values,p):
    if not values:return None
    # Rational weights make CDF equality exact at discrete boundaries.
    ordered=sorted(values);total=sum((w for _,w in ordered),Fraction(0));threshold=Fraction(str(p))*total;cum=Fraction(0)
    for v,w in ordered:
        cum+=w
        if cum>=threshold:return v
    return ordered[-1][0]
def summary(values):
    if not values:return {'median_signed':None,'median_absolute':None,'p90_absolute':None,'p95_absolute':None,'mean_signed':None,'MAE':None,'min':None,'max':None,'na_reason':'empty applicable subset'}
    absolute=[(abs(x),w) for x,w in values];total=sum(w for x,w in values)
    return {'median_signed':weighted_quantile(values,.5),'median_absolute':weighted_quantile(absolute,.5),'p90_absolute':weighted_quantile(absolute,.9),'p95_absolute':weighted_quantile(absolute,.95),'mean_signed':float(sum(Fraction(x)*w for x,w in values)/total),'MAE':float(sum(Fraction(abs(x))*w for x,w in values)/total),'min':min(x for x,w in values),'max':max(x for x,w in values),'na_reason':None}
def taxonomy(e,r):
    if not isinstance(e,bool) or not isinstance(r,bool):return 'unknown'
    return {(True,True):'BS',(False,False):'BU',(True,False):'O',(False,True):'C'}[e,r]
def classification(metrics):
    before=fingerprint(metrics);out={s['id']:classify(metrics,s,.90) for s in P['slas']}
    assert before==fingerprint(metrics),'SLA-changing metrics'
    for s in P['slas']:
        a=out[s['id']]
        if a['safe'] is True:assert metrics['status']=='complete' and metrics['drained'] and metrics['resource_feasible'] is True
        if a['joint_pass_count'] is not None:
            fail=a['ttft_fail_count']+a['tpot_fail_count']-a['both_fail_count']
            assert fail+a['joint_pass_count']==a['total_requests']
            assert a['safe']==(a['joint_pass_count']>=a['required_pass_count'])
        for t in P['slas']:
            b=out[t['id']]
            if s['ttft_s']<=t['ttft_s'] and s['tpot_s']<=t['tpot_s'] and a['joint_pass_count'] is not None:
                assert a['joint_pass_count']<=b['joint_pass_count']
                assert all(not v or b['request_pass'][k] for k,v in a['request_pass'].items())
    return out
def capacity(rows,model,sid):
    seq=[{'intensity':r['intensity'],'safe':r[model][sid]['safe'],'attainment':r[model][sid]['attainment_fraction'],'status':r[model][sid]['status'],'resource_feasible':r[model][sid]['resource_feasible'],'physical_id':r['physical_id']} for r in sorted(rows,key=lambda r:r['intensity'])]
    safe=[r['intensity'] for r in seq if r['safe'] is True];unk=[r['intensity'] for r in seq if r['safe'] is None]
    lo=max(safe,default=0);hi=max(safe+unk,default=0);identified=lo==hi
    higher=[r['intensity'] for r in seq if r['intensity']>lo and r['safe'] is False];nearest=min(higher,default=None) if lo else None
    transitions=[{'a':a['intensity'],'b':b['intensity'],'left':a['safe'],'right':b['safe'],'width':b['intensity']/a['intensity']-1} for a,b in zip(seq,seq[1:]) if isinstance(a['safe'],bool) and isinstance(b['safe'],bool) and a['safe']!=b['safe']]
    witnesses=[{'lower':a['intensity'],'higher':b['intensity']} for i,a in enumerate(seq) if a['safe'] is False for b in seq[i+1:] if b['safe'] is True]
    holes=[r['intensity'] for r in seq if r['safe'] is False and safe and min(safe)<r['intensity']<lo]
    runs=[];run=[]
    for r in seq:
        if r['safe'] is True:run.append(r['intensity'])
        elif run:runs.append(run);run=[]
    if run:runs.append(run)
    upper=next((t for t in transitions if t['a']==lo and t['left'] is True and t['right'] is False),None)
    return {'C_lower':lo,'C_upper':hi,'identified':identified,'C':lo if identified else None,'C_na_reason':None if identified else 'unknown may exceed highest confirmed safe',
      'no_safe':not safe and not unk,'no_certified_safe':not safe,'all_safe':bool(seq) and all(r['safe'] is True for r in seq),'right_censored':seq[-1]['safe'] is True,'upper_status_unknown':seq[-1]['safe'] is None,
      'unknown_count':len(unk),'unknown_positions':unk,'nearest_unsafe_above':nearest,'nearest_unsafe_na_reason':None if nearest is not None else 'no safe point or no observed unsafe above',
      'unknown_between':[x for x in unk if nearest is not None and lo<x<nearest],'nonmonotone':bool(witnesses),'nonmonotonic_witnesses':witnesses,'unsafe_holes':holes,'safe_runs':runs,
      'upper_transition_width':upper['width'] if upper else None,'upper_transition_na_reason':None if upper else 'no adjacent known upper transition','sequence':seq,'transitions':transitions,'unresolved_brackets':[t for t in transitions if Decimal(str(t['b']))/Decimal(str(t['a']))-1>Decimal('.05')]}
def decisions(rows,sid):
    caps={m:{s:capacity([r for r in rows if r['candidate']==s],m,sid) for s in P['candidate_shifts']} for m in ['E','R']}
    best={};chosen={}
    for m in caps:
        valid=all(c['identified'] for c in caps[m].values());mx=max(c['C_lower'] for c in caps[m].values())
        best[m]=[s for s in P['tie_break'] if caps[m][s]['C']==mx] if valid and mx>0 else [] if valid else None
        chosen[m]=next((s for s in P['tie_break'] if caps[m][s]['C_lower']==mx),None) if mx>0 else None
    e,r=best['E'],best['R'];inter=sorted(set(e or [])&set(r or []));c=chosen['E'];L=max(x['C_lower'] for x in caps['E'].values())
    reason='unknown full best set' if e is None or r is None else 'reference no positive sampled service' if not r else 'evaluator abstains' if not e else None
    rank={'best_E':e,'best_R':r,'selected_E':c,'selected_R':chosen['R'],'exact_set_agreement':e==r if e and r else None,'overlap':inter,'strict_mismatch':not inter if e and r else None,
       'comparison':'undefined' if reason else 'exact_set_agreement' if e==r else 'overlap_nonidentical' if inter else 'strict_mismatch','na_reason':reason,
       'selected_equal':c==chosen['R'] if c is not None and chosen['R'] is not None and e and r else None,'selected_E_in_best_R':c in r if c is not None and r else None,
       'tie_only_mismatch':bool(inter) and c not in (r or []),'abstention':None if c is not None else 'abstain_unknown' if any(x['unknown_count'] for x in caps['E'].values()) else 'abstain_no_safe',
       'censored_best_set':any(caps[m][s]['right_censored'] for m in caps for s in (best[m] or [])), 'incomplete_coverage':any(x['unknown_count'] for m in caps for x in caps[m].values()),
       'scores':{m:{s:{k:x[k] for k in ['C_lower','C_upper','identified','C']} for s,x in caps[m].items()} for m in caps}}
    point=next((x for x in rows if x['candidate']==c and x['intensity']==L),None)
    actual=point['R'][sid] if point else None
    B=max(x['C'] for x in caps['R'].values()) if all(x['identified'] for x in caps['R'].values()) else None
    rsafe=actual['safe'] if actual else None;U=0 if point is None or rsafe is False else L if rsafe is True else None
    baseok=B is not None and B>0
    fail=(actual['ttft_fail_count']+actual['tpot_fail_count']-actual['both_fail_count']) if actual and actual['joint_pass_count'] is not None else None
    N=actual['total_requests'] if actual else None;K=actual['required_pass_count'] if actual else None
    op={'candidate':c,'L':L,'physical_id':point['physical_id'] if point else None,'abstention':rank['abstention'],'recommendation_under_incomplete_coverage':any(x['unknown_count'] for x in caps['E'].values()),
      'A_R':actual['attainment_fraction'] if actual else None,'J_R':actual['joint_pass_count'] if actual else None,'N':N,'K':K,'safe_R':rsafe,
      'reference_status':actual['status'] if actual else None,'ttft_fail':actual['ttft_fail_count'] if actual else None,'tpot_fail':actual['tpot_fail_count'] if actual else None,'both_fail':actual['both_fail_count'] if actual else None,'joint_fail':fail,
      'joint_fail_fraction':fail/N if fail is not None else None,'ttft_fail_fraction':actual['ttft_fail_count']/N if fail is not None else None,'tpot_fail_over_N':actual['tpot_fail_count']/N if fail is not None else None,
      'attainment_shortfall':max(0,.90-actual['attainment_fraction']) if fail is not None else None,'excess_fail_count':max(0,fail-(N-K)) if fail is not None else None,
      'B':B,'U':U,'arithmetic_loss':1-L/B if baseok else None,'safe_usable_loss':1-U/B if baseok and U is not None else None,
      'loss_na_reason':None if baseok and U is not None else 'reference maximum unidentified' if B is None else 'reference no positive capacity' if B==0 else 'recommendation safety unknown',
      'actual_na_reason':None if fail is not None else 'abstention' if point is None else 'resource rejection or incomplete reference',
      'candidate_loss':1-caps['R'][c]['C']/B if baseok and c is not None else None,'load_selection_loss':(caps['R'][c]['C']-L)/B if baseok and c is not None else None}
    if U is not None and baseok:assert U<=B
    return caps,rank,op
def brackets(rows):
    by={(r['candidate'],Decimal(str(r['intensity']))):r for r in rows};grid=sorted({k[1] for k in by});out=[]
    with localcontext() as ctx:
        ctx.prec=50
        for a,b in zip(grid,grid[1:]):
            if b/a-1<=Decimal('.05'):continue
            witnesses=[]
            for s in P['candidate_shifts']:
                for sla in P['slas']:
                    for m in ['E','R']:
                        x=by[s,a][m][sla['id']];y=by[s,b][m][sla['id']]
                        if isinstance(x['safe'],bool) and isinstance(y['safe'],bool) and x['safe']!=y['safe']:witnesses.append({'candidate':s,'sla':sla['id'],'model':m,'left':x['safe'],'right':y['safe'],'left_status':x['status'],'right_status':y['status']})
            if witnesses:
                mid=(a*b).sqrt().quantize(Decimal('.0000000001'),rounding=ROUND_HALF_EVEN)
                out.append({'a':str(a),'b':str(b),'ratio':str(b/a),'midpoint':str(mid),'legal':a<mid<b and mid not in grid,'witnesses':witnesses})
        return sorted(out,key=lambda r:(-Decimal(r['ratio']),Decimal(r['a']),Decimal(r['b'])))
