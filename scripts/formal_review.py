"""Summarize saved formal evidence; no simulation or tuning is performed."""
from pathlib import Path
import collections
import json
import statistics

ROOT = Path(__file__).resolve().parents[1]
F = ROOT / 'results/formal'


def read(path):
    return json.loads((F / path).read_text(encoding='utf-8'))


def aggregate(rows):
    out = {key: sum(r[key] for r in rows) for key in
           ['attempted', 'paired', 'failed', 'both_safe', 'both_unsafe', 'optimistic', 'conservative']}
    out['optimistic_among_evaluator_safe'] = out['optimistic'] / (out['both_safe'] + out['optimistic'])
    out['conservative_among_reference_safe'] = out['conservative'] / (out['both_safe'] + out['conservative'])
    return out


def main():
    rq1 = read('rq1_reliability/summary.json')
    caps = read('rq2_capacity/summary.json')['rows']
    trials = read('rq3_decision_transfer/summary.json')['trials']
    stress = read('rq4_profile_mismatch/summary.json')
    mitigation = read('mitigation/results.json')['rows']
    result = {'protocol_hash': rq1['protocol_hash'], 'rq1': rq1['totals'],
              'rq1_by_kind': {kind: aggregate([r for r in rq1['configurations'] if r['kind'] == kind])
                              for kind in ['a100', 'heterogeneous']}}
    finite = [r for r in caps if r['relative_gap'] is not None]
    result['rq2'] = {
        'configuration_regimes': len(caps), 'finite_gaps': len(finite),
        'median_relative_gap': statistics.median(r['relative_gap'] for r in finite),
        'min_relative_gap': min(r['relative_gap'] for r in finite),
        'max_relative_gap': max(r['relative_gap'] for r in finite),
        'negative_gaps': sum(r['relative_gap'] < 0 for r in finite),
        'zero_gaps': sum(r['relative_gap'] == 0 for r in finite),
        'positive_gaps': sum(r['relative_gap'] > 0 for r in finite),
        'single_boundary_supported': sum(r['precise_sampled_gap'] for r in caps),
        'no_evaluator_safe': sum(r['evaluator']['largest_safe'] is None for r in caps),
        'no_reference_safe': sum(r['reference']['largest_safe'] is None for r in caps),
        'max_relative_bracket': max(r['largest_relative_bracket'] or 0 for r in caps),
        'brackets_above_protocol_resolution': sum((r['largest_relative_bracket'] or 0) > .025 for r in caps),
        'reference_nonmonotone': [r['case_id'] for r in caps if r['reference']['nonmonotone']],
        'reference_right_censored': sum(r['reference']['right_censored'] for r in caps),
        'evaluator_right_censored': sum(r['evaluator']['right_censored'] for r in caps),
        'evaluator_nonmonotone': sum(r['evaluator']['nonmonotone'] for r in caps)}
    result['rq3'] = trials
    result['rq4'] = []
    for variant in sorted({r['variant'] for r in stress['counts']}):
        rows = [r for r in stress['counts'] if r['variant'] == variant]
        ts = [r for r in stress['decision_trials'] if r['variant'] == variant]
        result['rq4'].append({'variant': variant, **aggregate(rows), 'decision_trials': len(ts),
                             'winner_agreements': sum(t['winner_agrees'] is True for t in ts),
                             'new_errors_vs_nominal': sum(t['new_decision_error'] for t in ts),
                             'selection_changes': sum(t['selected_changed_from_nominal'] for t in ts),
                             'evaluator_nonmonotone_trials': sum(t['evaluator_nonmonotone'] for t in ts),
                             'evaluator_censored_trials': sum(t['evaluator_right_censored'] for t in ts)})
    result['mitigation'] = []
    for bias in [1., .9]:
        for policy in sorted({r['policy'] for r in mitigation}):
            rows = [r for r in mitigation if r['bias'] == bias and r['policy'] == policy]
            qs = [r['normalized_usable_quality'] for r in rows if r['normalized_usable_quality'] is not None]
            result['mitigation'].append({'bias': bias, 'policy': policy, 'trials': len(rows),
                'unsafe_outputs': sum(r['selected_optimistic'] for r in rows),
                'abstentions': sum(r['abstention'] for r in rows), 'quality_denominator': len(qs),
                'mean_usable_quality_over_defined_oracles': statistics.mean(qs),
                'reference_calls': sum(r['reference_calls'] for r in rows),
                'unique_physical_reference_queries': len({(r['group'], q['shift'], q['intensity']) for r in rows for q in r['query_trace']}),
                'max_reference_calls_per_trial': max(r['reference_calls'] for r in rows),
                'evaluator_calls': sum(r['evaluator_calls'] for r in rows)})
    # Deterministic, explanatory selection after outcomes. Not prevalence sampling.
    group = read('groups/h103-o500-d30-heterogeneous-slow.json')
    above = min(v for v in group['grid'] if v > 2.8963093757)
    result['mechanism_selection'] = [
        {'name': 'optimistic_h103_a100', 'group': 'h103-o500-d30-a100-slow', 'shift': 0,
         'intensity': .016, 'regime': 'decode', 'p_scale': 1., 'd_scale': 1.,
         'reason': 'Short nominal optimistic case with a large TPOT excess; no prevalence inference.'},
        {'name': 'large_gap_correct_winner_h103_stress', 'group': group['group']['id'], 'shift': 0,
         'intensity': above, 'regime': 'prefill', 'p_scale': .9, 'd_scale': .9,
         'reason': 'Stress case: -70.27% capacity gap yet correct reference-best shift0, stable across Both-5% and Both-10%. No large-gap correct-winner nominal case is claimed.'},
        *[{'name': 'reversal_h101_shift' + str(s), 'group': 'h101-o60-d30-heterogeneous-fast',
           'shift': s, 'intensity': 4.096, 'regime': 'prefill', 'p_scale': 1., 'd_scale': 1.,
           'reason': 'Same common load for evaluator-selected shift2 and reference-best shift0; full common-grid scores establish nominal reversal.'}
          for s in [0, 2]]]
    out = F / 'research_review.json'
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'rq3'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
