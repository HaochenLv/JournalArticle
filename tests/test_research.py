from pathlib import Path
import sys,unittest,json,csv,gzip
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from research import *
from nominal_gap import summarize

class ResearchTests(unittest.TestCase):
 def test_nominal_a100_profile_matches_pinned_profiler(self):
  old=ExactHelixDecodeRuntimeProfiler(HelixA100Llama2Profiler.from_artifact(HELIX,commit=HELIX_COMMIT));new=Profiles();p=pipeline()
  for tokens in [512,1024,2051]:
   r=RequestSpec('r',0.,tokens,32)
   self.assertAlmostEqual(old.prefill_time(r,p,1,0),new.prefill_time(r,p,1,0),places=12)
   for nd in [1,2,8]:self.assertAlmostEqual(old.decode_time_per_token(r,tokens,p,0,nd),new.decode_time_per_token(r,tokens,p,0,nd),places=12)

 def test_accounting_correction_and_bias_hold_trajectory_contract(self):
  p=pipeline();w=(RequestSpec('r',0.,2051,1),);sla=SLA(2.,.15,fixed_overhead_s=.005)
  base=evaluator(p,w,sla,intrinsic=False);corrected=evaluator(p,w,sla);biased=evaluator(p,w,sla,Profiles(.95,1.))
  self.assertTrue(base['safe']);self.assertFalse(corrected['safe']);self.assertTrue(biased['safe'])
  self.assertEqual(base['trajectory_hash'],corrected['trajectory_hash'])
  self.assertAlmostEqual(corrected['max_accounted_ttft_s'],2.0158229367353977,places=10)

 def test_nominal_seed7_paper_transition(self):
  p=pipeline();base=workload(7);sla=SLA(2.,.15,fixed_overhead_s=.005)
  self.assertEqual(len(base),17)
  self.assertTrue(evaluator(p,scale_workload(base,.0131),sla)['safe'])
  self.assertFalse(evaluator(p,scale_workload(base,.0132),sla)['safe'])

 def test_nonmonotone_grid_does_not_claim_a_single_boundary(self):
  rows=[{'lambda':v,'reference':{'safe':s}} for v,s in [(1,True),(2,False),(3,True),(4,False)]]
  result=summarize(rows,'reference')
  self.assertFalse(result['single_boundary_supported']);self.assertFalse(result['sampled_monotonic'])
  self.assertEqual(len(result['transitions']),3)

 def test_reference_cache_input_hash_and_complete_requests(self):
  paths=list((ROOT/'results/raw_reference').glob('*.json.gz'))
  self.assertTrue(paths)
  for p in paths:
   with gzip.open(p,'rt') as f:d=json.load(f)
   self.assertEqual(p.name[:-8],fingerprint(d['inputs']))
   self.assertEqual(d['raw']['finished_requests'],d['raw']['total_requests'])
   self.assertEqual(d['summary']['safe'],all(m['aligned_ttft_s']<=d['inputs']['sla']['ttft_s'] and all(t<=d['inputs']['sla']['tpot_s'] for t in m['decode_tpot_s']) for m in d['raw']['query_metrics'].values()))

 def test_paper2_reproduction_matches_frozen_rows(self):
  original=ROOT/'.deps/partition/results/phase13/method_comparison.csv';new=ROOT/'results/reproduction/paper2_seed7/method_comparison.csv'
  with original.open() as f:expected=[r for r in csv.DictReader(f) if r['seed']=='7']
  with new.open() as f:actual=list(csv.DictReader(f))
  self.assertEqual(actual,expected)

 def test_threshold_reuse_matches_independent_complete_simulations(self):
  groups={};comparisons=0
  for path in (ROOT/'results/raw_reference').glob('*.json.gz'):
   with gzip.open(path,'rt') as f:d=json.load(f)
   key=physical_fingerprint(d['inputs'])
   if key in groups:
    old=groups[key];self.assertEqual(old['raw']['query_metrics'],d['raw']['query_metrics'])
    rebuilt=reclassify_record(old,d['inputs']);self.assertEqual(rebuilt['raw'],d['raw']);comparisons+=1
   else:groups[key]=d
  self.assertGreater(comparisons,10)

 def test_planners_return_only_queried_safe_points_within_budget(self):
  from planning import plan
  for policy in ['fixed_grid','round_robin','best_first']:
   calls=[]
   def query(s,j):calls.append((s,j));return j in [0,2,4] if s==0 else j==1
   result=plan([1,2,3,4,5],[-1,0],{-1:[True]*5,0:[True]*5},query,7,policy)
   self.assertEqual(len(calls),len(set(calls)));self.assertLessEqual(len(calls),7)
   self.assertIn(result['chosen'],result['trace']);self.assertTrue(result['chosen']['safe'])

if __name__=='__main__':unittest.main()
