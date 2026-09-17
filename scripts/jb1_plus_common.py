"""Isolated Stage 5 IO, protocol checks and shared-grid accounting."""
from sla_sensitivity_common import read,write_gz,sampled,decision_for,verdict
from formal_core import *
from journal_baseline_plus import evaluate as plus
import subprocess
OUT=ROOT/'results/jb1_plus'
P=read(ROOT/'config/jb1_plus_protocol.json');PH=fingerprint(P)
VARIANTS=P['variants']
def limits(phase='a'):
 return {s['id']:SLA(s['ttft_s'],s['tpot_s'],fixed_overhead_s=.005) for s in P['phase_'+phase]['slas']}
def guard():
 check_pins();snap=read(OUT/'protocol_snapshot.json');assert snap['protocol_hash']==PH
 assert snap['config_sha256']==hashlib.sha256((ROOT/'config/jb1_plus_protocol.json').read_bytes()).hexdigest()
 manifest=read(OUT/'source_manifest.json');assert fingerprint(manifest)==snap['source_manifest_hash']
 for name,sha in manifest.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
 for name,sha in snap['workload_files'].items():assert hashlib.sha256((OUT/'workloads'/(name+'.json')).read_bytes()).hexdigest()==sha
 assert subprocess.check_output(['git','show','e3887ca:config/jb1_plus_protocol.json'],cwd=ROOT)==(ROOT/'config/jb1_plus_protocol.json').read_bytes()
 assert subprocess.check_output(['git','-C',str(HELIX),'rev-parse','HEAD'],text=True).strip()==HELIX_COMMIT
 dep=read(FORMAL/'quality_checks.json')['dependency_source_integrity']['adapter_files_equal_git_objects']
 for name,sha in dep.items():assert hashlib.sha256((ROOT/'.deps/evaluator'/name).read_bytes()).hexdigest()==sha
def b_groups():
 return [{'id':w['id']+'-heterogeneous-'+w['primary_link'],'workload':w['id'],'link':w['primary_link'],'shifts':P['candidate_shifts'],'kind':'heterogeneous'} for w in P['phase_b']['workloads']]
def b_workload(g):
 d=read(OUT/'workloads'/(g['workload']+'.json'));return d,tuple(RequestSpec(**r) for r in d['requests'])
def point_path(phase,g,s,v):return OUT/('phase_'+phase+'_points')/g['id']/(fingerprint([s,v])+'.json.gz')
def points(phase,g):return [read(p) for p in sorted((OUT/('phase_'+phase+'_points')/g['id']).glob('*.json.gz'))]
def evaluate_all(p,w,sl,variants=None):
 prof=CachedProfiles()
 return {v:{sid:plus(p,w,sla,prof,**VARIANTS[v]) for sid,sla in sl.items()} for v in (variants or VARIANTS)}
def classify(raw,sl):return {sid:reference_details(raw,sla) for sid,sla in sl.items()}
def physical_inputs(p,w):
 return {'schema':1,'helix_commit':HELIX_COMMIT,'adapter_commit':CONFIG['adapter_commit'],'group_dispatch_extension':1,'pipeline':asdict(p),'workload':[asdict(r) for r in w],'sla':asdict(next(iter(limits('b').values())))}
def b_base(g,s,v):
 wd,w=b_workload(g);p=pipeline(g['link'],s,True);w=scale_workload(w,v)
 return p,w,{'group':g['id'],'workload':g['workload'],'shift':s,'intensity':v,'protocol_hash':PH,'origin':'phase_b_new','workload_fingerprint':wd['workload_fingerprint'],
  'scaled_workload_fingerprint':fingerprint([asdict(r) for r in w]),'partition_fingerprint':fingerprint(asdict(p)),'profile_fingerprint':CONFIG['profile_fingerprint'],'physical_fingerprint':physical_fingerprint(physical_inputs(p,w))}
def monotonicity(rows,sl):
 errors=[]
 for r in rows:
  for m in [*VARIANTS,'reference']:
   for a,sa in sl.items():
    for b,sb in sl.items():
     if sa.ttft_s<=sb.ttft_s and sa.tpot_s<=sb.tpot_s and verdict(r,m,a) is True and verdict(r,m,b) is False:errors.append([r['group'],r['shift'],r['intensity'],m,a,b])
 return errors
def transitions(rows):
 by={(r['shift'],r['intensity']):r for r in rows};grid=sorted({r['intensity'] for r in rows});out=[]
 for a,b in zip(grid,grid[1:]):
  witnesses=[]
  for s in P['candidate_shifts']:
   for sid in limits('b'):
    for model in [*VARIANTS,'reference']:
     x=verdict(by[s,a],model,sid);y=verdict(by[s,b],model,sid)
     if x is not None and y is not None and x!=y:witnesses.append({'shift':s,'sla':sid,'model':model,'left_safe':x,'right_safe':y})
  if witnesses and b/a-1>.025:out.append({'lower':a,'upper':b,'relative_width':b/a-1,'midpoint':round(math.sqrt(a*b),10),'witnesses':witnesses})
 return sorted(out,key=lambda x:(-math.log(x['upper']/x['lower']),x['lower']))
