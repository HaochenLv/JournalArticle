from pathlib import Path
import sys, unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from formal_core import *
from journal_baseline_plus import evaluate as plus, remaining_fraction
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import jb1_plus_common as common

class Constant:
 def prefill_time(self,r,p,np,nd):return .4
 def decode_time_per_token(self,r,c,p,np,nd):return .1

class PlusTests(unittest.TestCase):
 def test_shared_transition_union_and_missingness(self):
  rows=[]
  for s in [-2,-1,0,1,2]:
   for intensity in [1.,2.,4.]:
    e={v:{sid:{'safe':intensity==2.} for sid in common.limits('b')} for v in common.VARIANTS}
    rows.append({'group':'test','shift':s,'intensity':intensity,'evaluator':e,'reference':{sid:{'safe':None if intensity==2 else False} for sid in common.limits('b')}})
  ts=common.transitions(rows)
  self.assertEqual([(t['lower'],t['upper']) for t in ts],[(1,2),(2,4)])
  self.assertFalse(any(w['model']=='reference' for t in ts for w in t['witnesses']))
  summary=common.sampled([r for r in rows if r['shift']==0],'reference',next(iter(common.limits('b'))))
  self.assertEqual(summary['missing_count'],1);self.assertFalse(summary['all_unsafe']);self.assertTrue(summary['unresolved'])
 def test_clipping_and_zero_duration(self):
  for t,want in [(-1,1),(0,1),(.2,.5),(.4,0),(1,0)]:self.assertEqual(remaining_fraction(t,0,.4),want)
  self.assertEqual(remaining_fraction(0,0,0),0)
 def test_off_mode_exact_all_fields(self):
  for legacy in [False,True]:
   for drain in [False,True]:
    for sla in [SLA(100,100),SLA(.5,.2,fixed_overhead_s=.005)]:
     w=(RequestSpec('a',0,100,33),RequestSpec('b',.2,200,17),RequestSpec('c',.2,30,1))
     a=jb(pipeline(),w,sla,Constant(),trace=True,drain=drain,fixed_in_progress=legacy)
     b=plus(pipeline(),w,sla,Constant(),trace=True,drain=drain,fixed_in_progress=legacy)
     a.pop('runtime_s');b.pop('runtime_s');self.assertEqual(a,b)
 def test_remaining_lifetime_intrinsic_and_trajectory(self):
  w=(RequestSpec('a',0,100,33),RequestSpec('b',.2,200,17));p=pipeline()
  for legacy in [False,True]:
   sla=SLA(100,100,fixed_overhead_s=.1,queue_overhead_s=.1)
   a=plus(p,w,sla,Constant(),trace=True,drain=True,fixed_in_progress=legacy)
   b=plus(p,w,sla,Constant(),trace=True,drain=True,fixed_in_progress=legacy,remaining_prefill_blocking=True)
   self.assertEqual(a['trajectory_hash'],b['trajectory_hash']);self.assertEqual(a['events'],b['events'])
   check=next(x for x in b['trace'] if x['time_s']==.2 and x['side']=='pre')
   c=check['prefill_blocking_components'][0]
   self.assertAlmostEqual(c['remaining_fraction'],2/3 if legacy else .5)
   self.assertAlmostEqual(c['intrinsic_s'],H*100)
   self.assertAlmostEqual(c['remaining_compute_s'],.4*c['remaining_fraction'])
   end=next(x for x in b['trace'] if abs(x['time_s']-(.6 if legacy else .4))<1e-9 and x['side']=='pre')
   c=next(c for c in end['prefill_blocking_components'] if c['request_id']=='a')
   self.assertAlmostEqual(c['remaining_compute_s'],0)
   self.assertAlmostEqual(c['intrinsic_s'],H*100)
 def test_representative_real_profiles_all_fields(self):
  for name in ['h101-o60-d30','h102-o300-d120','h105-o900-d30']:
   w=scale_workload(load_workload(name)[1],4.096)
   for legacy in [False,True]:
    for hetero in [False,True]:
     p=pipeline('fast',0,hetero);sla=SLA(5.2,5,fixed_overhead_s=.005)
     a=jb(p,w,sla,CachedProfiles(),drain=True,fixed_in_progress=legacy)
     b=plus(p,w,sla,CachedProfiles(),drain=True,fixed_in_progress=legacy)
     c=plus(p,w,sla,CachedProfiles(),drain=True,fixed_in_progress=legacy,remaining_prefill_blocking=True)
     a.pop('runtime_s');b.pop('runtime_s');self.assertEqual(a,b)
     for k in ['trajectory_hash','events','final_time_s','peak_memory_bytes','peak_prefill','peak_decode','drained']:
      self.assertEqual(b[k],c[k],k)

if __name__=='__main__':unittest.main()
