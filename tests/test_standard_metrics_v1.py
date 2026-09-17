from pathlib import Path
import sys,unittest,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from standard_metrics_v1 import classify,migrate_record,execution_identity


def record(overhead=.02,outputs=3):
    ds=[.5,2.,4.][:outputs];first=1.5
    return {'inputs':{'sla':{'fixed_overhead_s':overhead/2,'queue_overhead_s':overhead/2,'ttft_s':5,'tpot_s':1},
      'workload':[{'id':'r','arrival_time_s':10.,'input_tokens':2,'output_tokens':outputs}]},
      'raw':{'finished_requests':1,'total_requests':1,'final_time_s':10+first+sum(ds[1:]),
      'query_metrics':{'r':{'aligned_ttft_s':1.+overhead,'true_first_token_ttft_s':first+overhead,
      'decode_tpot_s':[x+overhead for x in ds],'max_tpot_s':max(ds)+overhead}}}}


def population(n,tt_fail=(),tp_fail=()):
    return {'status':'complete','drained':True,'resource_feasible':True,'total_requests':n,
      'request_metrics':{str(i):{'output_tokens':2,'ttft_s':2 if i in tt_fail else 1,
                               'average_tpot_s':2 if i in tp_fail else 1} for i in range(n)}}


class StandardMetricsTests(unittest.TestCase):
    def test_N_required_ceil_90_percent(self):
        for n,required in [(10,9),(11,10),(0,None)]:
            r=classify(population(n),{'ttft_s':1,'tpot_s':1})
            self.assertEqual(r['required_pass_count'],required)
        self.assertTrue(classify(population(10,[0]),{'ttft_s':1,'tpot_s':1})['safe'])
        self.assertFalse(classify(population(11,[0,1]),{'ttft_s':1,'tpot_s':1})['safe'])
        self.assertTrue(classify(population(11,[0]),{'ttft_s':1,'tpot_s':1})['safe'])

    def test_O_disjoint_success_trap(self):
        r=classify(population(10,[0],[1]),{'ttft_s':1,'tpot_s':1})
        self.assertFalse(r['safe']);self.assertEqual(r['joint_pass_count'],8)
        self.assertEqual(r['ttft_fail_count'],1);self.assertEqual(r['tpot_fail_count'],1)
        self.assertEqual(r['both_fail_count'],0)

    def test_record_specific_overhead_no_mutation_and_postfirst(self):
        for h in [0.,.005,.02,.15]:
            old=record(h);saved=copy.deepcopy(old);m=migrate_record(old)
            self.assertEqual(m['status'],'complete');self.assertEqual(old,saved)
            self.assertAlmostEqual(m['request_metrics']['r']['ttft_s'],1.5)
            self.assertAlmostEqual(m['request_metrics']['r']['average_tpot_s'],3.)
            self.assertAlmostEqual(m['final_time_s'],17.5)

    def test_single_token_TPOT_none_and_only_TTFT(self):
        m=migrate_record(record(outputs=1));r=m['request_metrics']['r']
        self.assertIsNone(r['average_tpot_s']);self.assertEqual(r['t_first_s'],r['t_last_s'])
        self.assertTrue(classify(m,{'ttft_s':2,'tpot_s':0})['safe'])
        self.assertFalse(classify(m,{'ttft_s':1,'tpot_s':100})['safe'])

    def test_missing_overhead_is_unsupported(self):
        r=record();del r['inputs']['sla']['queue_overhead_s']
        m=migrate_record(r);self.assertEqual(m['status'],'unsupported')
        self.assertEqual(m['error_code'],'missing_overhead_metadata')
        self.assertIsNone(classify(m,{'ttft_s':1,'tpot_s':1})['safe'])

    def test_integrity_failures_retained(self):
        cases=[]
        r=record();r['raw']['finished_requests']=0;cases.append((r,'full_drain_failure'))
        r=record();r['inputs']['workload'][0]['output_tokens']=2;cases.append((r,'output_length_mismatch'))
        r=record();r['raw']['query_metrics']['r']['max_tpot_s']=9;cases.append((r,'max_list_mismatch'))
        r=record();r['raw']['final_time_s']+=1;cases.append((r,'final_completion_mismatch'))
        r=record();del r['raw']['query_metrics'];cases.append((r,'missing_metrics'))
        r=record();r['raw']['query_metrics']['r']['aligned_ttft_s']=0;cases.append((r,'endpoint_identity_mismatch'))
        for r,code in cases:
            m=migrate_record(r);self.assertEqual(m['error_code'],code)
            self.assertEqual(m['request_metrics'],{});self.assertIsNone(m['resource_feasible'])

    def test_physical_identity_ignores_accounting_but_not_workload(self):
        a=record(.02)['inputs'];b=record(.005)['inputs'];b['sla']['ttft_s']=999
        self.assertEqual(execution_identity(a),execution_identity(b))
        b['workload'][0]['output_tokens']=1
        self.assertNotEqual(execution_identity(a),execution_identity(b))

    def test_malformed_definedness_rejected(self):
        p=population(1);p['request_metrics']['0']['average_tpot_s']=None
        with self.assertRaises(ValueError):classify(p,{'ttft_s':1,'tpot_s':1})

    def test_malformed_record_shapes_are_retained_not_raised(self):
        bad=record();bad['raw']['query_metrics']['r']=None
        for r in [None,{}, {'inputs':None,'raw':{}}, {'inputs':{'workload':None},'raw':{}},bad]:
            m=migrate_record(r)
            self.assertEqual(m['status'],'migration_failed')
            self.assertIsNone(classify(m,{'ttft_s':1,'tpot_s':1})['safe'])


if __name__=='__main__':unittest.main()
