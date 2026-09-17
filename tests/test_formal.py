from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from formal_core import *
class FormalTests(unittest.TestCase):
 def test_frozen_inputs_and_heldout_separation(self):
  check_pins();self.assertEqual(len(CONFIG['workloads']),6)
  for w in CONFIG['workloads']:
   d,reqs=load_workload(w['id']);self.assertGreater(w['seed'],19)
   self.assertEqual(fingerprint([asdict(r) for r in reqs]),w['workload_fingerprint'])
  self.assertEqual(sum(len(g['shifts'])*2 for g in groups()),76)
 def test_cached_profile_equals_nominal_and_biased(self):
  for args in [(),(.9,.8), (1.,1.,('l4x2',.9))]:
   a=Profiles(*args);b=CachedProfiles(*args)
   for s in [-2,0,2]:
    p=pipeline('fast',s,True);r=RequestSpec('r',0,1789,100)
    self.assertEqual(a.prefill_time(r,p,2,3),b.prefill_time(r,p,2,3))
    for n in [1,5,25]:self.assertEqual(a.decode_time_per_token(r,1800,p,2,n),b.decode_time_per_token(r,1800,p,2,n))
 def test_nonmonotone_and_no_safe_are_not_boundaries(self):
  r=safe_summary([{'intensity':i,'reference_safe':v} for i,v in [(1,True),(2,False),(3,True),(4,False)]],'reference')
  self.assertTrue(r['nonmonotone']);self.assertFalse(r['single_boundary_supported'])
  d=decision({-1:0,0:0,1:0},{-1:0,0:0,1:0});self.assertTrue(d['abstention']);self.assertIsNone(d['winner_agrees'])
 def test_tie_ranks_regret_and_correlation(self):
  d=decision({-1:1,0:2,1:2},{-1:1,0:2,1:3})
  self.assertEqual(d['selected_shift'],0);self.assertEqual(d['reference_regret'],1);self.assertEqual(d['selected_reference_rank'],2)
  self.assertAlmostEqual(d['normalized_reference_quality'],2/3)
if __name__=='__main__':unittest.main()
