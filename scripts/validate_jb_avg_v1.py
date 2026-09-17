"""Deterministic tests, small CPU runtime sanity and immutable-source verification."""
from pathlib import Path
import sys,json,hashlib,unittest,io,time,statistics,math,platform
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts'),str(ROOT/'tests')]
from migrate_standard_metrics import write,OUT
from standard_metrics_v1 import fingerprint
from jb_avg_v1 import simulate
from test_jb_avg_v1 import tiny_pipeline,profiles,req


def main():
    loader=unittest.TestLoader();suite=unittest.TestSuite()
    for name in ['test_jb_avg_v1','test_standard_metrics_v1']:suite.addTests(loader.loadTestsFromName(name))
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    test={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
          'passed':result.wasSuccessful(),'output':stream.getvalue()}
    write(OUT/'deterministic_tests.json',test)
    if not result.wasSuccessful():
        print(stream.getvalue());raise SystemExit(1)
    reuse_runtime='--reuse-runtime' in sys.argv
    benchmarks=json.loads((OUT/'runtime_sanity.json').read_text())['benchmarks'] if reuse_runtime else []
    workloads=[] if reuse_runtime else [('single_33_outputs',[req(outputs=33)]),
                   ('eight_staggered_requests',[req(str(i),arrival=i*.125,inputs=1,outputs=33) for i in range(8)])]
    for name,w in workloads:
        p=tiny_pipeline();prof=profiles()
        for _ in range(5):simulate(p,w,prof)
        times=[];hashes=set();events=set()
        for _ in range(50):
            start=time.perf_counter();r=simulate(p,w,prof);times.append(time.perf_counter()-start)
            assert r['drained'];hashes.add(r['trajectory_hash']);events.add(len(r['trajectory']))
        assert len(hashes)==len(events)==1
        benchmarks.append({'workload':name,'requests':len(w),'output_tokens':sum(x.output_tokens for x in w),
          'warmup':5,'measured_repetitions':50,'median_s':statistics.median(times),
          'p95_s':sorted(times)[math.ceil(.95*len(times))-1],'minimum_s':min(times),'maximum_s':max(times),
          'event_batches':next(iter(events)),'trajectory_hash':next(iter(hashes)),
          'samples_s':times})
    write(OUT/'runtime_sanity.json',{'scope':'CPU virtual-planning time for two tiny deterministic fixtures; not GPU speedup or a formal cost comparison',
      'python':platform.python_version(),'system':platform.system(),'machine':platform.machine(),'benchmarks':benchmarks,
      'new_helix_runs':0,'formal_matrix_calls':0})
    manifest=json.loads((OUT/'protected_manifest.json').read_text(encoding='utf-8'))
    changed=[p for p,h in manifest['files'].items() if not (ROOT/p).is_file() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    assert not changed,changed
    audit=json.loads((OUT/'cache_audit.json').read_text())
    # Independently validate the compact delivered CSV, including undefined m=1.
    import csv
    with (OUT/'request_metrics.csv').open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
    assert len(rows)==audit['request_metrics_rows']
    assert len({(r['physical_point_id'],r['request_id']) for r in rows})==len(rows)
    assert sum(int(r['output_tokens'])==1 for r in rows)==audit['m1_count']
    for r in rows:
        assert math.isfinite(float(r['ttft_s'])) and float(r['ttft_s'])>=0
        if int(r['output_tokens'])==1:assert r['average_tpot_s']==''
        else:assert math.isfinite(float(r['average_tpot_s'])) and float(r['average_tpot_s'])>=0
    checks={'passed':True,'tests_run':result.testsRun,'protected_files_unchanged':len(manifest['files']),
      'cache_csv_rows':len(rows),'cache_anomalies_retained':audit['failed_migration_records'],
      'new_helix_runs':0,'formal_matrix_calls':0,'stage6_refinement_resumed':False,
      'design_sha256':hashlib.sha256((ROOT/'config/jb_avg_v1_design.json').read_bytes()).hexdigest(),
      'implementation_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
        ['src/jb_avg_v1.py','src/standard_metrics_v1.py','scripts/migrate_standard_metrics.py','scripts/validate_jb_avg_v1.py',
         'tests/test_jb_avg_v1.py','tests/test_standard_metrics_v1.py']}}
    write(OUT/'validation_checks.json',checks)
    print(json.dumps({'tests':result.testsRun,'protected_files':len(manifest['files']),
                     'benchmarks':[{k:v for k,v in b.items() if k!='samples_s'} for b in benchmarks]},indent=2))


if __name__=='__main__':main()
