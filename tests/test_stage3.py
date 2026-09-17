"""Checks for semantic isolation and scientifically distinct loss measures."""
from pathlib import Path
import sys, unittest, json
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'scripts'),str(Path(__file__).resolve().parents[1]/'src')]
from stage3_evidence import *

class Stage3Tests(unittest.TestCase):
    def test_mismatch_distinguishes_overlap_from_selected_winner(self):
        self.assertEqual(mismatch(decision({0:2,1:2},{0:1,1:3})), 'tie-break mismatch')
        self.assertEqual(mismatch(decision({0:2,1:1},{0:1,1:3})), 'strict best-set mismatch')
        self.assertEqual(mismatch(decision({0:0,1:0},{0:1,1:3})), 'no-safe recommendation')

    def test_fixed_overhead_only_changes_progress(self):
        p=pipeline('fast');w=(RequestSpec('single',0,100,32),)
        sla=SLA(ttft_s=100,tpot_s=100,fixed_overhead_s=.005)
        prof=CachedProfiles()
        raw=jb(p,w,sla,prof);control=legacy_progress(p,w,sla,prof)
        self.assertAlmostEqual(control['final_time_s']-raw['final_time_s'],33*.005)
        self.assertEqual(raw['max_accounted_ttft_s'],control['max_accounted_ttft_s'])
        self.assertEqual(raw['max_accounted_tpot_s'],control['max_accounted_tpot_s'])
        with self.assertRaises(AssertionError):
            legacy_progress(p,w,replace(sla,queue_overhead_s=.001),prof)

    def test_saved_decomposition_and_derating(self):
        path=FORMAL/'decision_loss_decomposition.json'
        if not path.exists():self.skipTest('Stage 3 artifacts not generated yet')
        rows=json.loads(path.read_text())['rows']
        self.assertEqual(len(rows),24)
        raw=[r for r in rows if r['variant']=='raw' and r['regime']=='prefill']
        self.assertEqual([r['mismatch_type'] for r in raw],['strict best-set mismatch']*4+['tie-break mismatch']*2)
        for r in rows:
            self.assertAlmostEqual(r['partition_selection_regret']+r['within_selected_partition_operating_loss'],r['operating_point_loss'])
            self.assertEqual(r['safe_usable_quality'],r['recommended_load_utilization'] if r['exact_recommendation_reference_safe'] else 0)
        audit=json.loads((FORMAL/'mitigation_derating_audit/summary.json').read_text())
        self.assertEqual(len(audit['rows']),56)
        h101=next(r for r in audit['rows'] if r['group']=='h101-o60-d30-heterogeneous-fast' and r['regime']=='decode' and r['bias']==1.)
        self.assertEqual(h101['grid_snapped_output'],.004)
        self.assertAlmostEqual(h101['realized_derating'],1-.004/.0099348625)

if __name__=='__main__':unittest.main()
