"""Freeze the one-shot correction and outcome-blind held-out workloads."""
from pathlib import Path
import sys, subprocess, hashlib, datetime, statistics
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from formal_core import *

def main():
 out=ROOT/'results/jb1_plus'; assert not (out/'protocol_snapshot.json').exists()
 source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
 assert source=='4e579bba911ed807c42bd51c0c87d1ecabb17133';check_pins()
 stage4=json.loads((ROOT/'config/sla_sensitivity_protocol.json').read_text())
 used={i%1200 for w in CONFIG['workloads'] for i in range(w['interval_offset'],w['interval_offset']+w['duration_s']//3)}
 cursor=max(w['interval_offset']+w['duration_s']//3 for w in CONFIG['workloads']);workloads=[]
 for seed,duration,link in zip(range(201,205),[30,120,30,120],['fast','slow','slow','fast']):
  while True:
   indices=[i%1200 for i in range(cursor,cursor+duration//3)]
   if not (set(indices)&used):
    try:w=build_helix_azure_conversation_workload(HELIX,commit=HELIX_COMMIT,duration_s=duration,target_request_rate=.5,seed=seed,interval_offset=cursor).requests
    except ValueError:cursor+=1;continue
    break
   cursor+=1
  gaps=[b.arrival_time_s-a.arrival_time_s for a,b in zip(w,w[1:])]
  record={'id':f'w{seed}','seed':seed,'interval_offset':cursor,'source_interval_indices':indices,'duration_s':duration,'global_target_rate':.5,'primary_link':link,
   'requests':[asdict(r) for r in w],'workload_fingerprint':fingerprint([asdict(r) for r in w]),
   'features':{'request_count':len(w),'input_mean':statistics.mean(r.input_tokens for r in w),'input_min':min(r.input_tokens for r in w),'input_max':max(r.input_tokens for r in w),
   'output_mean':statistics.mean(r.output_tokens for r in w),'output_min':min(r.output_tokens for r in w),'output_max':max(r.output_tokens for r in w),'output_tokens':sum(r.output_tokens for r in w),
   'interarrival_cv':statistics.pstdev(gaps)/statistics.mean(gaps)}}
  write_json(out/'workloads'/(record['id']+'.json'),record);workloads.append({k:v for k,v in record.items() if k!='requests'})
  used.update(indices);cursor+=duration//3
 variants={f'{sem}-{debt}':{'fixed_in_progress':sem=='Legacy','remaining_prefill_blocking':debt=='Remaining'} for sem in ['Raw','Legacy'] for debt in ['Full','Remaining']}
 p={'protocol_id':'FI-JB1-PLUS-v1','source_commit':source,'correction':'D(t)=sum(clip(1-(t-start)/duration,0,1)*prefill_compute + H*input_tokens). Only compute is scaled. Duration=compute for Raw, compute+fixed+queue for Legacy. Zero duration: remaining fraction 0 at/after start, 1 before start.',
  'variants':variants,'fixed_overhead_s':.005,'queue_overhead_s':0.,'candidate_shifts':[-2,-1,0,1,2],
  'unchanged':'arrival, progress trajectories, block size, profiles, H, TTFT/TPOT ledgers except blocking compute term, network, memory, buffers, KV, overhead, pre/post checks, tie-break, adapter, simulator and reference thresholds',
  'phase_a':{'scope':'post-hoc diagnosis, not independent validation','groups':stage4['groups'],'slas':stage4['slas'],'physical_points':2050,'grid':'Stage 4 final common grids, no refinement',
   'a100_controls':'all six primary A100 groups on original formal grids, both original SLAs, reuse reference and full variants',
   'mechanisms':['h105/A100/fast/4.096/TTFT2/TPOT1','h103/A100/slow/0.016/TTFT2/TPOT0.15','h101/heterogeneous/fast/4.096/TTFT5.2/TPOT10/shifts0,2']},
  'phase_b':{'scope':'four outcome-blind held-out workloads; same source distribution is not external validation','workloads':workloads,
   'generation':'Same frozen Azure constructor/filtering (no additional filter), paired token distribution, target rate 0.5. Starting immediately after last prior window, scan forward for first legal unused nonempty window; retain constructor modulo-1200 indexing. No outcomes inspected. Offset 1200 wraps to source interval 0; all actual source intervals disjoint from h101-h106 and each other.',
   'slas':[{'id':f'TTFT5.2_TPOT{x:g}','ttft_s':5.2,'tpot_s':x} for x in [.3,1.2,5.,10.]],'initial_grid':CONFIG['initial_grid'],'minimum_probe':CONFIG['minimum_probe'],'maximum_probe':CONFIG['maximum_probe'],
   'refinement':{'relative_resolution':.025,'max_added_intensities':16,'max_rounds':4,'max_physical_points':500,'midpoint':'round(sqrt(lower*upper),10)',
   'priority':'descending log(upper/lower), then ascending lower; deduplicate midpoint',
   'transitions':'union of safe->unsafe and unsafe->safe across five shifts, four SLAs, reference and all four variants; null labels never unsafe',
   'range_extension':False,'stop':'no unresolved transitions, no legal midpoint, 16 additions or 4 rounds; retain unresolved and censoring; no budget extension',
   'fairness':'Every new intensity is used by all five shifts, four SLAs and four variants'}},
  'reference':{'helix_commit':HELIX_COMMIT,'adapter_commit':CONFIG['adapter_commit'],'timeout_s':600,'retry_count':1,'full_drain':True,'failed_verdict':None,'cache':'Existing reference read-only; all new records under results/jb1_plus/reference'},
  'scheduler':{'worker_ceiling':12,'memory_budget_gib':24,'reserve_gib':6,'cost':'ceil((512+.30*output_tokens)/256)*256 MiB'},
  'metrics':{'judgment':['both_safe','both_unsafe','optimistic','conservative'],'capacity':'largest sampled safe, signed and absolute relative gap with median/min/max; full sequences, no-safe, nonmonotone, right-censored, missing and unresolved flags',
   'decision':'agreement, disjoint best-set strict mismatch, tie-break mismatch, selected reference rank; smaller absolute shift then negative',
   'loss':'B=reference-best capacity, S=selected-partition reference capacity, L=recommended intensity; partition=1-S/B, operating=1-L/B, allocation=(S-L)/B. exact reference-safe(L), violation count/fraction; safe usable L if safe else 0 for unsafe/abstention, null if missing. B=0 or missing required capacity => undefined relative loss.',
   'paired':'Raw-Full -> Raw-Remaining and Legacy-Full -> Legacy-Remaining; preserve adverse cases, no composite score',
   'runtime':'sequential fresh evaluator timing on all initial Phase B grid points with shared cached profiles; median/p95 CPU wall planning runtime and event count; not GPU speedup'},
  'checks':['off-mode field equivalence except runtime','drained full/remaining trajectory equality','all Stage 4 Full fields reused exactly','protected hashes','pins/profiles/adapter','full reference per-token drain','workload freeze before outcomes','shared grids','SLA relaxation monotonicity','formula audit','no missing-to-unsafe conversion'],
  'publication':'JB1 is specified journal evaluator; Legacy semantic control. Withdrawn unpublished AICCC is not prior publication. Accepted Evaluator-Guided SLA-Aware Layer Partitioning for Heterogeneous LLM Pipelines is prior work. Only mechanism-guided correction evidence is new.',
  'stop':'one correction only, no fitted parameters, no extra workloads/SLAs/profiles/models; report negative/trade-off outcomes; no JB1++; no manuscript'}
 write_json(ROOT/'config/jb1_plus_protocol.json',p);write_json(out/'phase_b_workloads.json',workloads)
 tracked=subprocess.check_output(['git','ls-files','-z'],text=True).split('\0')
 manifest={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in tracked if name and name not in ['CURRENT_STATUS.md','EXPERIMENT_LOG.md']}
 write_json(out/'source_manifest.json',manifest)
 write_json(out/'protocol_snapshot.json',{'protocol':p,'protocol_hash':fingerprint(p),'config_sha256':hashlib.sha256((ROOT/'config/jb1_plus_protocol.json').read_bytes()).hexdigest(),'source_manifest_hash':fingerprint(manifest),'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'workload_files':{w['id']:hashlib.sha256((out/'workloads'/(w['id']+'.json')).read_bytes()).hexdigest() for w in workloads}})
 print(json.dumps({'protocol_hash':fingerprint(p),'protected_files':len(manifest),'workloads':workloads},indent=2))

if __name__=='__main__':main()
