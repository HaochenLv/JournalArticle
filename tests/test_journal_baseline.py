from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research import *
from journal_baseline import evaluate

class Constant:
 def prefill_time(self,r,p,np,nd):return .1
 def decode_time_per_token(self,r,c,p,np,nd):return .1

class BaselineTests(unittest.TestCase):
 def test_isolated_paper_numbers_and_trajectory(self):
  w=(RequestSpec('r',0.,2051,143),);p=pipeline();sla=SLA(2.,.15,fixed_overhead_s=.005)
  a=evaluate(p,w,sla,intrinsic=False,drain=True);b=evaluate(p,w,sla,drain=True)
  self.assertTrue(a['safe']);self.assertFalse(b['safe']);self.assertEqual(a['trajectory_hash'],b['trajectory_hash'])
  self.assertAlmostEqual(a['max_accounted_ttft_s'],1.8940402816)
  self.assertAlmostEqual(b['max_accounted_ttft_s'],2.0158229367353977)
 def test_fixed_overhead_does_not_change_progress(self):
  w=(RequestSpec('r',0.,20,33),);p=pipeline()
  a=evaluate(p,w,SLA(100,100),Constant(),drain=True);b=evaluate(p,w,SLA(100,100,fixed_overhead_s=.2),Constant(),drain=True)
  self.assertEqual(a['trajectory_hash'],b['trajectory_hash']);self.assertAlmostEqual(a['final_time_s'],3.4)
 def test_tied_arrivals_commute(self):
  w=(RequestSpec('a',0.,20,33),RequestSpec('b',0.,30,17));p=pipeline();sla=SLA(100,100)
  a=evaluate(p,w,sla,Constant(),trace=True,drain=True);b=evaluate(p,w[::-1],sla,Constant(),trace=True,drain=True)
  self.assertEqual(a['trajectory_hash'],b['trajectory_hash']);self.assertEqual(a['trace'][1]['num_prefill'],2)
 def test_fractional_decode_survives_unrelated_arrival(self):
  w=(RequestSpec('a',0.,20,33),RequestSpec('b',.15,20,1));r=evaluate(pipeline(),w,SLA(100,100),Constant(),trace=True,drain=True)
  x=next(x for x in r['trace'] if x['side']=='pre' and abs(x['time_s']-.15)<1e-9)
  self.assertAlmostEqual(x['ledger']['a']['progress'],.5)
 def test_block_context_left_right_and_full_drain(self):
  r=evaluate(pipeline(),(RequestSpec('a',0.,20,33),),SLA(100,100),Constant(),trace=True,drain=True)
  xs=[x for x in r['trace'] if abs(x['time_s']-1.7)<1e-8]
  self.assertEqual([x['ledger']['a']['context'] for x in xs],[36,52]);self.assertTrue(r['drained'])
 def test_simultaneous_constraints_are_retained(self):
  p=pipeline();p=replace(p,nodes={n:replace(x,memory_capacity_bytes=int(p.model.weight_bytes/8+x.workspace_bytes+x.memory_margin_bytes+1)) for n,x in p.nodes.items()})
  r=evaluate(p,(RequestSpec('a',0.,20,33),),SLA(.01,.01),Constant())
  self.assertEqual({x['kind'] for x in r['first_violations']},{'sla_time','memory'})
 def test_activation_buffer_and_prompt_kv_reserved_at_arrival(self):
  p=pipeline();w=(RequestSpec('a',0.,200,1),);sla=SLA(100,100)
  a=evaluate(p,w,sla,Constant(),trace=True);b=evaluate(p,w,sla,Constant(),trace=True,activation_buffers=False)
  self.assertEqual(a['trace'][1]['memory']['n0']-b['trace'][1]['memory']['n0'],200*p.model.activation_bytes_per_token)
 def test_sla_changes_only_ledger_under_full_drain(self):
  p=pipeline();w=(RequestSpec('a',0.,20,33),RequestSpec('b',.15,30,1))
  a=evaluate(p,w,SLA(100,100),Constant(),drain=True);b=evaluate(p,w,SLA(.01,.01),Constant(),drain=True)
  self.assertNotEqual(a['safe'],b['safe']);self.assertEqual(a['trajectory_hash'],b['trajectory_hash'])
 def test_event_limit_is_error(self):
  with self.assertRaises(RuntimeError):evaluate(pipeline(),(RequestSpec('a',0,10,100),),SLA(100,100),max_events=1)
 def test_network_equal_relative_commitment(self):
  p=pipeline();p=replace(p,links={k:replace(v,capacity_bytes_per_s=v.capacity_bytes_per_s*(2 if i%2 else 1)) for i,(k,v) in enumerate(p.links.items())})
  r=evaluate(p,(RequestSpec('a',0,100,1),),SLA(100,100),Constant(),trace=True)
  x=r['trace'][1];ratios=[v/p.links[k].capacity_bytes_per_s for k,v in x['link_commitments'].items() if v]
  self.assertLess(max(ratios)-min(ratios),1e-12)
if __name__=='__main__':unittest.main()
