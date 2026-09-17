"""Focused tests for the new sampling and missing-data rules."""
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from sla_sensitivity_common import *

def fake(value,safe):
    return [{'group':'test','shift':s,'intensity':value,'reference':{sid:{'safe':safe} for sid in LIMITS} if safe is not None else {},
             'evaluator':{v:{sid:{'safe':safe} for sid in LIMITS} for v in P['semantics']}} for s in P['candidate_shifts']]

class Stage4Tests(unittest.TestCase):
    def test_both_transition_directions_and_union(self):
        t=transitions(fake(1.,True)+fake(4.,False)+fake(16.,True))
        self.assertEqual([x['midpoint'] for x in t],[2.,8.])
        self.assertEqual(len(t[0]['witnesses']),5*8*3)
        self.assertEqual(t[1]['witnesses'][0]['right_safe'],True)
    def test_failed_is_not_unsafe(self):
        rows=fake(1.,True)+fake(4.,None)+fake(16.,False)
        self.assertEqual(transitions(rows),[])
        d=sampled([r for r in rows if r['shift']==0],'reference',next(iter(LIMITS)))
        self.assertTrue(d['unresolved']);self.assertEqual(d['missing_count'],1)
        self.assertIsNone(d['sequence'][1]['safe']);self.assertEqual(d['transitions'],[])
    def test_relaxation_bug_detected(self):
        rows=fake(1.,True)
        rows[0]['evaluator']['raw']['TTFT5.2_TPOT10']['safe']=False
        self.assertTrue(monotonicity(rows))
    def test_nonmonotone_and_no_safe_retained(self):
        rows=[r for r in fake(1.,False)+fake(2.,True)+fake(3.,False) if r['shift']==0]
        d=sampled(rows,'reference',next(iter(LIMITS)))
        self.assertTrue(d['nonmonotone']);self.assertFalse(d['single_boundary_supported'])
        self.assertTrue(sampled(fake(1.,False)[:1],'raw',next(iter(LIMITS)))['no_safe'])
    def test_tie_break_remains_absolute_then_negative(self):
        d=decision({-2:1,-1:2,0:0,1:2,2:1},{-2:1,-1:1,0:0,1:2,2:1})
        self.assertEqual(d['selected_shift'],-1)
        self.assertEqual(d['evaluator_best_set'],[-1,1]);self.assertFalse(d['winner_agrees'])

if __name__=='__main__':unittest.main()
