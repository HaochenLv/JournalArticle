"""Audit saved instrumented traces and extract descriptive mechanism evidence."""
from pathlib import Path
import gzip
import json

ROOT = Path(__file__).resolve().parents[1]
F = ROOT / 'results/formal'


def read_gzip(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        return json.load(stream)


def summarize(path):
    d = read_gzip(path)
    raw = read_gzip(ROOT/'results/raw_reference'/(d['reference_cache_key']+'.json.gz'))
    assert d['metrics_exactly_equal'] and d['reference_metrics'] == raw['raw']['query_metrics']
    e = d['evaluator']
    out = {k: d[k] for k in ['shift','intensity','regime','p_scale','d_scale','metrics_exactly_equal','reference_cache_key']}
    out.update(name=path.name, group=d['group']['id'], evaluator_safe=e['safe'],
               evaluator_first_violation=e['first_violation'],
               evaluator_max_accounted_tpot_s=e['max_accounted_tpot_s'],
               reference_max_tpot_s=max(m['max_tpot_s'] for m in d['reference_metrics'].values()),
               reference_max_aligned_ttft_s=max(m['aligned_ttft_s'] for m in d['reference_metrics'].values()),
               first_reference_violation=d['reference_violations_in_physical_finish_order'][:1])
    first = e['first_violation']
    if first:
        snap = next(s for s in e['trace'] if s['time_s'] == first['time_s'] and s['side'] == first['side'])
        out['first_evaluator_ledger'] = snap['ledger'].get(first.get('request_id'))
        out['phase_counts_at_first_evaluator_failure'] = next(c for c in d['concurrency_at_evaluator_checks']
                                                            if c['time_s'] == first['time_s'] and c['side'] == first['side'])
    worst = []
    for rid in d['target_request_ids']:
        query = d['reference_queries'][rid]
        it = max(query['iterations'][1:], key=lambda x: x['duration_s'])
        batches = [b for b in d['selected_execution_batches'] if it['uid'] in b['requests']]
        finish = next((t['time_s'] for t in e['trajectory'] if ['Finish', rid] in t['events']), None)
        worst.append({'request_id': rid, 'reference_iteration_start_s': it['start_s'],
                      'reference_iteration_end_s': it['end_s'], 'reference_iteration_duration_s': it['duration_s'],
                      'reference_batch_intervals': len(batches),
                      'shared_batch_service_sum_s': sum(b['end_s'] - b['start_s'] for b in batches),
                      'batches_with_prefill': sum('Initialization' in b['phases'] for b in batches),
                      'evaluator_query_finish_s': finish, 'reference_query_finish_s': query['iterations'][-1]['end_s']})
    out['target_worst_decode_iterations'] = worst
    if out['first_reference_violation']:
        violation = out['first_reference_violation'][0]
        query = d['reference_queries'][violation['request_id']]
        it = query['iterations'][violation['iteration']]
        nearest = min(d['concurrency_at_evaluator_checks'], key=lambda c: abs(c['time_s'] - it['start_s']))
        out['phase_counts_near_reference_violation'] = nearest
        out['arrivals_near_reference_violation'] = [r for r in d['workload'] if abs(r['arrival_time_s'] - it['start_s']) < 3]
    return out


if __name__ == '__main__':
    paths = sorted((F/'mechanisms').glob('*.json.gz'))
    results = [summarize(p) for p in paths]
    assert len(results) == 5
    (F/'mechanisms/summary.json').write_text(json.dumps({'traces': results,
        'scope': 'Explanatory outcome-selected cases. Batch service is shared, not marginal request cost; residual time is not uniquely decomposed into waiting and transfer.'}, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(results, indent=2))
