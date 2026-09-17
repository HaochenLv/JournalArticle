"""Freeze inputs before reference outcomes; refuse silent protocol replacement."""
from pathlib import Path
import sys,json,hashlib,statistics,platform
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research import *
from journal_baseline import VERSION

def main():
 path=ROOT/'config/formal_protocol.json'
 if path.exists():raise SystemExit('Protocol already frozen; version an explicit amendment instead.')
 workloads=[]
 for i,(seed,offset,duration) in enumerate(zip(range(101,107),[60,300,500,700,900,1100],[30,120,30,120,30,120])):
  w=build_helix_azure_conversation_workload(HELIX,commit=HELIX_COMMIT,duration_s=duration,target_request_rate=.5,seed=seed,interval_offset=offset).requests
  gaps=[b.arrival_time_s-a.arrival_time_s for a,b in zip(w,w[1:])];counts=[sum(3*j<=r.arrival_time_s<3*(j+1) for r in w) for j in range(duration//3)]
  record={'id':f'h{seed}-o{offset}-d{duration}','seed':seed,'interval_offset':offset,'duration_s':duration,'global_target_rate':.5,'primary_link':['fast','slow','slow','fast','fast','slow'][i],'requests':[asdict(r) for r in w],'workload_fingerprint':fingerprint([asdict(r) for r in w]),'features':{'request_count':len(w),'input_mean':statistics.mean(r.input_tokens for r in w),'input_max':max(r.input_tokens for r in w),'input_ge1500_fraction':sum(r.input_tokens>=1500 for r in w)/len(w),'output_mean':statistics.mean(r.output_tokens for r in w),'interarrival_cv':statistics.pstdev(gaps)/statistics.mean(gaps),'count_bin_cv':statistics.pstdev(counts)/statistics.mean(counts),'count_bin_peak':max(counts)}}
  write_json(ROOT/'results/formal/workloads'/(record['id']+'.json'),record);workloads.append({k:v for k,v in record.items() if k!='requests'})
 profiles={str(p.relative_to(HELIX)):hashlib.sha256(p.read_bytes()).hexdigest() for name in ['a100','l4x2','t4x4'] for p in (HELIX/'simulator/model_manager/llama2_70b'/name).glob('*bs2time.csv')}
 config={'protocol_id':'FI-JB1-v1','date':'2026-09-17','baseline_version':VERSION,'baseline_sha256':hashlib.sha256((ROOT/'src/journal_baseline.py').read_bytes()).hexdigest(),'helix_commit':HELIX_COMMIT,'adapter_commit':'1cd5c56365b084fb06e3ca14f67448ddbf45275a','profile_files':profiles,'profile_fingerprint':fingerprint(profiles),'workloads':workloads,'heterogeneous_shifts':[-2,-1,0,1,2],'heterogeneous_slas':{'decode':{'ttft_s':5.2,'tpot_s':.30},'prefill':{'ttft_s':5.2,'tpot_s':10.}},'a100_slas':{'decode':{'ttft_s':2.,'tpot_s':.15},'relaxed_decode':{'ttft_s':2.,'tpot_s':1.}},'fixed_overhead_s':.005,'initial_grid':[round(.001*4**i,10) for i in range(9)],'minimum_probe':.0000625,'maximum_probe':262.144,'relative_transition_resolution':.025,'max_refinement_rounds':6,'max_common_grid_points':128,'timeout_s':600,'workers':8,'anchor_opposite_link_workloads':[workloads[0]['id'],workloads[1]['id']],'mismatch_scales':[.95,.9,.8],'device_bias':['l4x2',.9],'mitigations':['evaluator_only','compute_margin_25pct','capacity_derating_20pct','four_scenarios','selected_point_reference','selected_partition_boundary_reference'],'boundary_validation_budget':5,'python':platform.python_version()}
 write_json(path,config);print(json.dumps(workloads,indent=2))
if __name__=='__main__':main()
