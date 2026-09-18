import unittest
from common import *
from analyze import weighted_errors,confusion
def row(x,e,r,c=0):
    def d(v):return {'safe':v,'attainment_fraction':1 if v else 0 if v is False else None,'status':'complete' if v is not None else 'unsupported','resource_feasible':True if v is not None else None,'total_requests':10,'required_pass_count':9 if v is not None else None,'joint_pass_count':10 if v else 0 if v is False else None,'ttft_fail_count':0 if v else 10 if v is False else None,'tpot_fail_count':0 if v is not None else None,'both_fail_count':0 if v is not None else None}
    return {'workload':'h101','physical_id':str((x,c)),'candidate':c,'intensity':x,'E':{s['id']:d(e) for s in P['slas']},'R':{s['id']:d(r) for s in P['slas']}}
class ProtocolTests(unittest.TestCase):
    def test_inverse_cdf_exact_boundary(self):
        self.assertEqual(quantile([1,2,3,4],.5),2)
        self.assertEqual(weighted_quantile([(i,Fraction(1,10)) for i in range(10)],.9),8)
    def test_unknown_below_max_identified(self):
        c=capacity([row(1,None,True),row(2,True,True)],'E','S1')
        self.assertEqual((c['C'],c['unknown_count'],c['right_censored']),(2,1,True))
    def test_unknown_above_max_bounds(self):
        c=capacity([row(1,True,True),row(2,None,True)],'E','S1')
        self.assertFalse(c['identified']);self.assertEqual((c['C_lower'],c['C_upper']),(1,2))
    def test_nonmonotonic_and_hole(self):
        c=capacity([row(1,True,True),row(2,False,True),row(3,True,True)],'E','S1')
        self.assertTrue(c['nonmonotone']);self.assertEqual(c['unsafe_holes'],[2]);self.assertEqual(c['C'],3)
    def test_resource_rejection_not_unknown(self):
        c=capacity([row(1,False,False)],'E','S1');self.assertTrue(c['no_safe']);self.assertEqual(c['C'],0)
    def test_zero_denominators(self):
        c=confusion([row(1,False,False)],'S1');self.assertIsNone(c['optimistic_approval_fraction']);self.assertEqual(c['E_approval_coverage'],0)
    def test_tiebreak_and_no_reference_fallback(self):
        rows=[row(x,True,c!=0,c) for c in range(-2,3) for x in [1,2]]
        caps,rank,op=decisions(rows,'S1');self.assertEqual(op['candidate'],0);self.assertFalse(op['safe_R']);self.assertEqual(op['U'],0);self.assertEqual(op['safe_usable_loss'],1)
    def test_all_no_safe_not_ranking_agreement(self):
        _,rank,op=decisions([row(1,False,False,c) for c in range(-2,3)],'S1')
        self.assertIsNone(rank['exact_set_agreement']);self.assertEqual(rank['comparison'],'undefined');self.assertEqual(op['abstention'],'abstain_no_safe')
    def test_refine_union_bool_only(self):
        rows=[row(x,False if x==1 else None,False,c) for c in range(-2,3) for x in [1,4]]
        self.assertEqual(brackets(rows),[])
        rows[-1]=row(4,True,False,2)
        self.assertEqual(brackets(rows)[0]['midpoint'],'2.0000000000')
    def test_width_exact_five_percent_not_trigger(self):
        self.assertEqual(brackets([row(x,x==1,False,c) for c in range(-2,3) for x in [1,1.05]]),[])
    def test_hierarchy_does_not_pool_requests(self):
        def point(w,c,values):
            return {'item':{'workload':w,'candidate':c},'classifications':{'pairable':True},'E':{'request_metrics':{str(i):{'ttft_s':v+1} for i,v in enumerate(values)}},'R':{'request_metrics':{str(i):{'ttft_s':1} for i,v in enumerate(values)}}}
        s=weighted_errors([point('a',0,[0]*100),point('b',0,[10])],'ttft_s')
        self.assertEqual(s['mean_signed'],5);self.assertEqual(s['median_signed'],0);self.assertEqual(s['p90_absolute'],10)
    def test_abstention_safe_usable_loss_with_positive_reference(self):
        _,rank,op=decisions([row(1,False,True,c) for c in range(-2,3)],'S1')
        self.assertEqual(op['U'],0);self.assertEqual(op['safe_usable_loss'],1);self.assertIsNone(op['safe_R'])
if __name__=='__main__':unittest.main(verbosity=2)
