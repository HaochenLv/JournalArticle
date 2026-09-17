"""Frozen-input formal experiment utilities; legacy results remain separate."""
import json,hashlib,time,gzip,signal,math,csv,statistics
from pathlib import Path
from dataclasses import asdict
from research import *
from journal_baseline import evaluate as jb
CONFIG=json.loads((ROOT/'config/formal_protocol.json').read_text())
PROTOCOL_HASH=fingerprint(CONFIG)
FORMAL=ROOT/'results/formal'

class CachedProfiles(Profiles):
 def __init__(self,*args):super().__init__(*args);self.pc={};self.dc={}
 def key(self,p):return tuple((s.num_layers,p.nodes[s.node_id].hardware_type) for s in p.stages)
 def prefill_time(self,r,p,np,nd):
  key=(self.key(p),r.input_tokens)
  if key not in self.pc:self.pc[key]=super().prefill_time(r,p,np,nd)
  return self.pc[key]
 def decode_time_per_token(self,r,ctx,p,np,nd):
  key=(self.key(p),nd)
  if key not in self.dc:self.dc[key]=super().decode_time_per_token(r,ctx,p,np,nd)
  return self.dc[key]

def check_pins():
 assert hashlib.sha256((ROOT/'src/journal_baseline.py').read_bytes()).hexdigest()==CONFIG['baseline_sha256']
 for name,sha in CONFIG['profile_files'].items():assert hashlib.sha256((HELIX/name).read_bytes()).hexdigest()==sha

def groups():
 out=[]
 for w in CONFIG['workloads']:
  for kind in ['heterogeneous','a100']:
   out.append({'id':w['id']+'-'+kind+'-'+w['primary_link'],'workload':w['id'],'kind':kind,'link':w['primary_link'],'shifts':CONFIG['heterogeneous_shifts'] if kind=='heterogeneous' else [0],'role':'primary'})
  if w['id'] in CONFIG['anchor_opposite_link_workloads']:
   link='slow' if w['primary_link']=='fast' else 'fast'
   out.append({'id':w['id']+'-anchor-'+link,'workload':w['id'],'kind':'heterogeneous','link':link,'shifts':[0],'role':'link_anchor'})
 return out

def load_workload(name):
 d=json.loads((FORMAL/'workloads'/(name+'.json')).read_text())
 return d,tuple(RequestSpec(**r) for r in d['requests'])

def slas(group):return {k:SLA(**v,fixed_overhead_s=CONFIG['fixed_overhead_s']) for k,v in CONFIG['heterogeneous_slas' if group['kind']=='heterogeneous' else 'a100_slas'].items()}

def reference_details(raw,sla):
 metrics=list(raw['raw']['query_metrics'].values());tt=[m['aligned_ttft_s'] for m in metrics];tp=[m['max_tpot_s'] for m in metrics]
 bad=[a>sla.ttft_s or b>sla.tpot_s for a,b in zip(tt,tp)]
 return {'safe':not any(bad),'max_ttft_s':max(tt),'max_native_ttft_s':max(m['true_first_token_ttft_s'] for m in metrics),'max_tpot_s':max(tp),'violating_requests':sum(bad),'request_count':len(metrics),'violating_request_fraction':sum(bad)/len(metrics),'max_ttft_excess_s':max(0.,max(tt)-sla.ttft_s),'max_tpot_excess_s':max(0.,max(tp)-sla.tpot_s),'max_normalized_excess':max(0.,max(tt)/sla.ttft_s-1,max(tp)/sla.tpot_s-1),'drained':raw['raw']['finished_requests']==raw['raw']['total_requests'],'runtime_s':raw['summary']['runtime_s']}

def csv_write(path,rows):
 path.parent.mkdir(parents=True,exist_ok=True)
 if not rows:return
 keys=list(dict.fromkeys(k for r in rows for k in r))
 with path.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys,lineterminator='\n');w.writeheader()
  w.writerows({k:json.dumps(v,separators=(',',':')) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)

def safe_summary(rows,model):
 ordered=sorted(rows,key=lambda r:r['intensity']);seq=[{'intensity':r['intensity'],'safe':r[model+'_safe']} for r in ordered]
 safe=[x['intensity'] for x in seq if x['safe']];maximum=max(safe) if safe else None
 changes=[{'left':a['intensity'],'right':b['intensity'],'left_safe':a['safe'],'right_safe':b['safe']} for a,b in zip(seq,seq[1:]) if a['safe']!=b['safe']]
 nonmono=any(not x['left_safe'] and x['right_safe'] for x in changes)
 higher=[x['intensity'] for x in seq if maximum is not None and x['intensity']>maximum and not x['safe']]
 return {'largest_safe':maximum,'nearest_unsafe_above':min(higher) if higher else None,'all_unsafe':not safe,'right_censored':seq[-1]['safe'],'nonmonotone':nonmono,'single_boundary_supported':bool(safe) and not seq[-1]['safe'] and not nonmono,'transitions':changes,'sequence':seq}

def tied_ranks(scores):
 return {s:1+sum(v>score for v in scores.values())+.5*(sum(v==score for v in scores.values())-1) for s,score in scores.items()}

def decision(es,rs):
 eb=max(es.values());rb=max(rs.values());selected=min([s for s,v in es.items() if v==eb],key=lambda s:(abs(s),s)) if eb>0 else None
 best=sorted(s for s,v in rs.items() if v==rb) if rb>0 else []
 a=tied_ranks(es);b=tied_ranks(rs);av=statistics.mean(a.values());bv=statistics.mean(b.values());den=math.sqrt(sum((v-av)**2 for v in a.values())*sum((v-bv)**2 for v in b.values()))
 rvalues=sorted(rs.values(),reverse=True)
 return {'selected_shift':selected,'evaluator_best_set':sorted(s for s,v in es.items() if v==eb) if eb>0 else [],'reference_best_set':best,'selected_reference_rank':1+sum(v>rs[selected] for v in rs.values()) if selected is not None and rb>0 else None,'reference_regret':rb-rs[selected] if selected is not None and rb>0 else None,'normalized_reference_quality':rs[selected]/rb if selected is not None and rb>0 else None,'winner_agrees':selected in best if selected is not None and best else None,'abstention':selected is None,'spearman':sum((a[s]-av)*(b[s]-bv) for s in es)/den if den else None,'reference_top_gap':rvalues[0]-rvalues[1] if len(rvalues)>1 else None,'evaluator_scores':es,'reference_scores':rs}
