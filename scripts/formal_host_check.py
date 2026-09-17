"""One fresh short-trace migration check; never replaces an inherited cache."""
from pathlib import Path
import datetime
import gzip
import hashlib
import json
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from formal_core import *
from host_execution import host_metadata, spawned_call


def fresh_reference(p, w, sla):
    return asdict(ref.evaluate_helix_fixed_reference(
        pipeline=p, workload=w, sla=sla, helix_root=HELIX))


def main():
    check_pins()
    group_id = 'h105-o900-d30-a100-fast'
    group = next(g for g in groups() if g['id'] == group_id)
    state = json.loads((FORMAL / 'groups' / (group_id + '.json')).read_text())
    row = next(r for r in state['rows'] if r['shift'] == 0 and r['intensity'] == 4.096)
    cache_path = ROOT / 'results/raw_reference' / (row['reference_cache_key'] + '.json.gz')
    before = hashlib.sha256(cache_path.read_bytes()).hexdigest()
    with gzip.open(cache_path, 'rt') as stream:
        original = json.load(stream)
    _, base = load_workload(group['workload'])
    workload = scale_workload(base, row['intensity'])
    p = pipeline(group['link'], 0, False)
    limits = slas(group)
    start = time.perf_counter()
    fresh = json.loads(json.dumps(spawned_call(
        fresh_reference, (p, workload, limits['decode']), CONFIG['timeout_s'])))
    elapsed = time.perf_counter() - start
    assert fresh['query_metrics'] == original['raw']['query_metrics']
    assert fresh['final_time_s'] == original['raw']['final_time_s']
    assert fresh['finished_requests'] == fresh['total_requests'] == len(workload)
    verdicts = {}
    for regime, sla in limits.items():
        new = jb(p, workload, sla, CachedProfiles())
        old = row['evaluator'][regime]
        assert {k:v for k,v in new.items() if k != 'runtime_s'} == {k:v for k,v in old.items() if k != 'runtime_s'}
        details = reference_details({'raw': fresh, 'summary': {'runtime_s': elapsed}}, sla)
        assert {k:v for k,v in details.items() if k != 'runtime_s'} == {k:v for k,v in row['reference'][regime].items() if k != 'runtime_s'}
        verdicts[regime] = {'evaluator_safe': new['safe'], 'reference_safe': details['safe']}
    assert hashlib.sha256(cache_path.read_bytes()).hexdigest() == before
    result = {
        'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'protocol_hash': PROTOCOL_HASH, 'baseline_sha256': CONFIG['baseline_sha256'],
        'host': host_metadata(), 'group': group_id, 'shift': 0, 'intensity': row['intensity'],
        'reference_cache_key': row['reference_cache_key'], 'request_count': len(workload),
        'all_per_request_metrics_exactly_equal': True, 'final_time_exactly_equal': True,
        'all_evaluator_fields_except_runtime_exactly_equal': True,
        'all_reference_fields_except_runtime_exactly_equal': True,
        'verdicts': verdicts, 'cache_unchanged': True, 'fresh_call_wall_s': elapsed,
        'timing_scope': 'Migration validation including spawn overhead; not formal sequential timing.',
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'execution_source_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
            for name in ['src/host_execution.py', 'scripts/formal_run.py', 'scripts/formal_host_check.py']}
    }
    write_json(FORMAL / 'desktop_host_check.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
