"""Boundary contracts, not reimplementations of the production evaluator."""
import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from stage6_common import sampled,transitions,monotonicity,decision_for,LIMITS
from analyze_stage6 import sidecar_metrics

def row(x,e,r):
    return {'group':'test','shift':0,'intensity':x,
      'evaluator':{v:{s:{'safe':e} for s in LIMITS} for v in ['raw','legacy']},
      'reference':{s:{'safe':r} for s in LIMITS} if r is not None else {}}

class Stage6Contracts(unittest.TestCase):
    def test_single_output_postfirst_is_null_and_overhead_once(self):
        d=sidecar_metrics({'decode_tpot_s':[.255],'aligned_ttft_s':5.,'true_first_token_ttft_s':5.25})
        self.assertIsNone(d['mean_postfirst_increment_accounted'])
        self.assertIsNone(d['mean_postfirst_increment_raw'])
        self.assertEqual(d['mean_all_increment_raw'],.25)
        self.assertTrue(d['first_increment_completion_exceeds_5_2_s'])

    def test_missing_not_unsafe_or_false_censor(self):
        d=sampled([row(1,True,True),row(2,False,None)],'reference',next(iter(LIMITS)))
        self.assertEqual(d['largest_safe'],1)
        self.assertIsNone(d['nearest_unsafe_above'])
        self.assertIsNone(d['right_censored'])
        self.assertTrue(d['unresolved'])
        self.assertEqual(d['transitions'],[])

    def test_reverse_transition_retained(self):
        d=sampled([row(1,False,False),row(2,True,True),row(3,False,False)],'reference',next(iter(LIMITS)))
        self.assertTrue(d['nonmonotone']);self.assertEqual(d['largest_safe'],2)
        self.assertFalse(d['single_boundary_supported'])

    def test_controls_and_stress_cannot_trigger_refinement(self):
        a=row(1,False,False);b=row(2,False,False)
        for r in [a,b]:
            for s in [-2,-1,0,1,2]:pass
        rows=[]
        import copy
        for s in [-2,-1,0,1,2]:
            for r in [a,b]:
                t=copy.deepcopy(r);t['shift']=s
                for sid in ['TTFT5.2_TPOT0.1','TTFT5.2_TPOT5','TTFT5.2_TPOT10']:
                    t['reference'][sid]['safe']=r['intensity']==2
                rows.append(t)
        self.assertEqual(transitions(rows),[])

    def test_no_safe_is_not_winner_agreement(self):
        import copy
        rows=[]
        for s in [-2,-1,0,1,2]:
            t=row(1,False,False);t['shift']=s;rows.append(t)
        d,_=decision_for(rows,next(iter(LIMITS)),'raw')
        self.assertIsNone(d['winner_agrees']);self.assertIsNone(d['normalized_reference_quality'])
        self.assertTrue(d['abstention'])

if __name__=='__main__':unittest.main()
