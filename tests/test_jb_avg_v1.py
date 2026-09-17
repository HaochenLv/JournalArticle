"""Hand-checkable A-P frozen-design tests; no HELIX executions."""
from pathlib import Path
import sys, unittest, copy, inspect
from dataclasses import replace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'.deps/evaluator/src'))
from sla_aware_mvp.domain import ModelSpec,GPUNode,Link,Stage,Boundary,Pipeline,RequestSpec
from jb_avg_v1 import BatchProfiles,ProfileTable,State,simulate,round_cost,memory_state,classify


def tiny_pipeline(network=False, bandwidth=10., memory=10**9):
    model=ModelSpec('test',2 if network else 1,0,1,1,1,1,1,1)
    nodes={'a':GPUNode('a',1,memory,hardware_type='test')}
    stages=(Stage('s0',0,1,'a'),);links={};boundaries=()
    if network:
        nodes['b']=GPUNode('b',1,memory,hardware_type='test')
        stages+=(Stage('s1',1,2,'b'),)
        links={'e':Link('e','a','b',bandwidth)}
        boundaries=(Boundary('s0','s1',('e',)),)
    return Pipeline('tiny',model,nodes,links,stages,boundaries)


def profiles():
    # P(Q)=Q seconds, D(1)=2 seconds (singleton), D(2)=2, D(3)=3.
    return BatchProfiles({'test':(ProfileTable(((0,0.),(10,10000.))),
                                  ProfileTable(((0,0.),(2,2000.),(10,10000.))))})


def req(name='a',arrival=0.,inputs=2,outputs=2):
    return RequestSpec(name,arrival,inputs,outputs)


class JBAvgTests(unittest.TestCase):
    def run_model(self,w,**kw):
        return simulate(tiny_pipeline(),w,profiles(),**kw)

    def test_A_single_output(self):
        r=self.run_model([req(outputs=1)]);m=r['request_metrics']['a']
        self.assertEqual(m['t_first_s'],4);self.assertEqual(m['t_last_s'],4)
        self.assertIsNone(m['average_tpot_s']);self.assertTrue(r['drained'])
        self.assertEqual(r['trajectory'][-1]['events'],[('Finish','a'),('FirstToken','a')])

    def test_B_two_outputs_first_increment_excluded(self):
        r=self.run_model([req()]);m=r['request_metrics']['a']
        self.assertEqual(m['ttft_s'],4);self.assertEqual(m['t_last_s'],6)
        self.assertEqual(m['average_tpot_s'],2)
        pref=next(x for x in r['trajectory'] if ('PrefillDone','a') in x['events'])
        self.assertEqual(pref['time_s'],2);self.assertIsNone(pref['after']['a']['t_first_s'])
        self.assertEqual(pref['after']['a']['phase'],'FIRST_DECODE')

    def test_C_isolated_no_network(self):
        r=self.run_model([req(outputs=33)])
        self.assertEqual(r['final_time_s'],68)
        self.assertTrue(all(x['serialization_s']==0 for x in r['round_diagnostics']))

    def test_D_two_decode_batch_cost_once(self):
        active={x.spec.id:x for x in [State(req('a'),phase='DECODE'),State(req('b'),phase='FIRST_DECODE')]}
        c=round_cost(tiny_pipeline(),active,profiles())
        self.assertEqual(c['compute_s'],2)
        r=self.run_model([req('a'),req('b')])
        self.assertEqual(r['final_time_s'],8) # shared Prefill 4, then two rounds of 2

    def test_E_mixed_resource_cost(self):
        active={'a':State(req(inputs=3)),'b':State(req('b'),phase='DECODE')}
        c=round_cost(tiny_pipeline(),active,profiles())
        self.assertEqual(c['compute_s'],5) # P(3)+D(1), not max, gamma or two phase servers
        self.assertEqual(c['round_s'],5)

    def test_F_two_prefills_use_aggregate_profile(self):
        nonlinear=BatchProfiles({'test':(ProfileTable(((0,0.),(2,3000.),(4,5000.),(10,9000.))),profiles().tables['test'][1])})
        c=round_cost(tiny_pipeline(),{'a':State(req('a')),'b':State(req('b'))},nonlinear)
        self.assertEqual(c['compute_s'],5) # not P(2)+P(2)=6

    def test_G_half_bandwidth_only_serialization_changes(self):
        active={'a':State(req(inputs=2)),'b':State(req('b'),phase='DECODE')}
        a=round_cost(tiny_pipeline(True,10),active,profiles())
        b=round_cost(tiny_pipeline(True,5),active,profiles())
        self.assertEqual(a['compute_s'],b['compute_s']);self.assertEqual(a['link_bytes'],{'e':3.})
        self.assertEqual(b['serialization_s'],2*a['serialization_s'])
        self.assertAlmostEqual(b['round_s']-a['round_s'],a['serialization_s'])
        self.assertEqual(len(a['stages']),2);self.assertEqual(a['compute_s'],8)

    def test_H_midround_fractional_progress_survives(self):
        r=self.run_model([req('a',inputs=2,outputs=2),req('b',arrival=1,inputs=2,outputs=1)])
        arrival=next(x for x in r['trajectory'] if x['time_s']==1)
        self.assertEqual(arrival['after']['a']['prefill_progress'],.5)
        self.assertEqual(arrival['after']['b']['prefill_progress'],0)
        self.assertEqual(next(x['time_s'] for x in r['trajectory'] if ('PrefillDone','a') in x['events']),3)
        # Decode fractional progress: at t=3 an unrelated new prompt arrives.
        s=self.run_model([req('a'),req('b',arrival=3,outputs=1)])
        self.assertEqual(next(x for x in s['trajectory'] if x['time_s']==3)['after']['a']['decode_progress'],.5)

    def test_I_thresholds_only_classify_full_drain(self):
        r=self.run_model([req(),req('b',arrival=3)]);saved=copy.deepcopy(r)
        self.assertFalse(classify(r,{'ttft_s':0,'tpot_s':0})['safe'])
        self.assertTrue(classify(r,{'ttft_s':100,'tpot_s':100})['safe'])
        self.assertEqual(r,saved);self.assertTrue(r['drained'])
        again=self.run_model([req(),req('b',arrival=3)])
        self.assertEqual(r['trajectory_hash'],again['trajectory_hash'])
        self.assertNotIn('sla',inspect.signature(simulate).parameters)
        self.assertNotIn('candidate',inspect.signature(simulate).parameters)

    def test_J_q_does_not_change_isolated_first_token(self):
        a=self.run_model([req(outputs=33)],q=16);b=self.run_model([req(outputs=33)],q=8)
        self.assertEqual(a['request_metrics'],b['request_metrics'])
        self.assertEqual(a['request_metrics']['a']['t_first_s'],4)

    def test_K_KV_block_transition(self):
        r=self.run_model([req(inputs=2,outputs=33)])
        x=next(x for x in r['trajectory'] if ('DecodeBlockUpdate','a') in x['events'])
        self.assertEqual(x['time_s'],34)
        self.assertEqual(x['before']['a']['context'],18)
        self.assertEqual(x['after']['a']['context'],34)
        self.assertEqual(x['memory_after']['a']-x['memory_before']['a'],32)

    def test_L_atomic_finish_and_arrival(self):
        p=tiny_pipeline(memory=7)
        # Each request peaks at 7 bytes; transient overlap would falsely fail.
        w=[req('a',outputs=1),req('b',arrival=4,outputs=1)]
        a=simulate(p,w,profiles());b=simulate(p,w[::-1],profiles())
        self.assertTrue(a['drained']);self.assertEqual(a['trajectory_hash'],b['trajectory_hash'])
        at=next(x for x in a['trajectory'] if x['time_s']==4)
        self.assertEqual(set(at['events']),{('Finish','a'),('FirstToken','a'),('Arrival','b')})
        self.assertEqual(set(at['after']),{'b'})

    def test_M_profile_boundary_and_max_plus_one(self):
        self.assertTrue(self.run_model([req(inputs=10,outputs=1)])['drained'])
        r=self.run_model([req(inputs=11,outputs=1)])
        self.assertEqual(r['status'],'unsupported_profile_domain')
        self.assertIsNone(classify(r,{'ttft_s':100,'tpot_s':100})['safe'])
        active={str(i):State(req(str(i)),phase='DECODE') for i in range(10)}
        self.assertEqual(round_cost(tiny_pipeline(),active,profiles())['compute_s'],10)
        active['10']=State(req('10'),phase='DECODE')
        from jb_avg_v1 import UnsupportedProfileDomain
        with self.assertRaises(UnsupportedProfileDomain):round_cost(tiny_pipeline(),active,profiles())

    def test_P_diagnostic_shares_conserve_without_feedback(self):
        active={'a':State(req('a',inputs=1)),'b':State(req('b',inputs=2)),
                'c':State(req('c'),phase='DECODE'),'d':State(req('d'),phase='DECODE')}
        c=round_cost(tiny_pipeline(True),active,profiles(),True)
        for stage in c['stages']:
            self.assertAlmostEqual(sum(c['diagnostic_shares'][stage['stage']].values()),stage['compute_s'])
        w=[req('a'),req('b',arrival=1)]
        a=self.run_model(w);b=self.run_model(w,diagnostic_shares=True)
        self.assertEqual(a['trajectory_hash'],b['trajectory_hash']);self.assertEqual(a['request_metrics'],b['request_metrics'])

    def test_hard_resource_distinct_from_latency(self):
        for p,kind in [(tiny_pipeline(True,0),'network'),(tiny_pipeline(memory=1),'memory')]:
            r=simulate(p,[req()],profiles());c=classify(r,{'ttft_s':100,'tpot_s':100})
            self.assertEqual(r['status'],'hard_resource_infeasible');self.assertFalse(c['safe'])
            self.assertIsNone(c['ttft_fail_count']);self.assertIsNone(c['attainment_fraction'])
            self.assertEqual(r['resource_failures'][0]['resource'],kind)

    def test_memory_weights_workspace_reserve_KV_activations(self):
        p=tiny_pipeline();p=replace(p,model=replace(p.model,total_params=10),
            nodes={'a':replace(p.nodes['a'],workspace_bytes=3,memory_margin_bytes=4)})
        self.assertEqual(memory_state(p,{'a':State(req(inputs=2))},16)['a'],10+3+4+4+2)

    def test_shared_physical_link_counts_distinct_messages(self):
        p=tiny_pipeline(True)
        # a->b twice with b->a in between: e legitimately carries two boundaries.
        p=replace(p,model=replace(p.model,num_layers=4),
          stages=(Stage('s0',0,1,'a'),Stage('s1',1,2,'b'),Stage('s2',2,3,'a'),Stage('s3',3,4,'b')),
          links={**p.links,'back':Link('back','b','a',10)},
          boundaries=(Boundary('s0','s1',('e',)),Boundary('s1','s2',('back',)),Boundary('s2','s3',('e',))))
        p.validate();c=round_cost(p,{'a':State(req(inputs=2))},profiles())
        self.assertEqual(c['link_bytes'],{'e':4.,'back':2.});self.assertAlmostEqual(c['serialization_s'],.6)

    def test_pinned_profiles_match_every_knot_and_interpolation(self):
        from sla_aware_mvp.helix import HelixLayerProfile
        root=Path(__file__).resolve().parents[1]/'.deps/helix'
        prof=BatchProfiles.pinned(root)
        for hw,name in [('A100-40GB','a100'),('L4x2','l4x2'),('T4x4','t4x4')]:
            for phase,index in [('prompt',0),('decode',1)]:
                path=root/'simulator/model_manager/llama2_70b'/name/(phase+'_bs2time.csv')
                old=HelixLayerProfile.from_csv(path,x_kind=phase)
                for count in range(old.max_x+1):
                    p,d=prof.costs(hw,count if index==0 else 0,count if index==1 else 0)
                    expected=old.lookup_seconds_per_layer(count)*(2 if phase=='decode' and count==1 else 1)
                    self.assertAlmostEqual((p,d)[index],expected,places=14)

    def test_memory_failure_at_block_boundary_not_latency_miss(self):
        # input=2, output=33: first block memory=37, second=69 bytes.
        r=simulate(tiny_pipeline(memory=50),[req(outputs=33)],profiles())
        self.assertEqual(r['status'],'hard_resource_infeasible')
        self.assertEqual(r['resource_failures'][0]['time_s'],34)
        self.assertEqual(r['resource_failures'][0]['required_bytes'],69)

    def test_q_one_firsttoken_and_block_tie(self):
        r=self.run_model([req(outputs=2)],q=1)
        x=next(x for x in r['trajectory'] if ('FirstToken','a') in x['events'])
        self.assertIn(('DecodeBlockUpdate','a'),x['events'])
        self.assertEqual(r['final_time_s'],6)


if __name__=='__main__':unittest.main()
