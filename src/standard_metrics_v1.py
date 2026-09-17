"""Standard simulator-side latency metrics, read-only cache recovery and SLO classification.

No dependency on a simulator, evaluator, fitted correction or global overhead.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from decimal import Decimal, ROUND_CEILING
from statistics import mean

VERSION = 'standard-metrics-v1'


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def execution_identity(inputs):
    """Accounting/SLA labels do not alter the pinned reference execution.

    Keep pipeline, workload, source versions, schema and dispatch extension.
    Compare reconstructed metrics across aliases before accepting a deduplication.
    """
    physical = copy.deepcopy(inputs)
    physical.pop('sla', None)
    return fingerprint(physical)


def request_metrics(request_id, arrival, output_tokens, t_first, t_last):
    if not isinstance(output_tokens, int) or isinstance(output_tokens, bool) or output_tokens < 1:
        raise ValueError('output_tokens must be a positive integer')
    if not all(math.isfinite(x) for x in [arrival, t_first, t_last]):
        raise ValueError('nonfinite request time')
    if not arrival <= t_first <= t_last:
        raise ValueError('request completion order invalid')
    if output_tokens == 1 and t_first != t_last:
        raise ValueError('single output must have identical first and last times')
    return {'request_id': request_id, 'arrival_time_s': arrival, 'output_tokens': output_tokens,
            't_first_s': t_first, 't_last_s': t_last, 'ttft_s': t_first - arrival,
            'average_tpot_s': (t_last - t_first) / (output_tokens - 1) if output_tokens > 1 else None}


def classify(metrics, sla, target=0.90):
    """Pure postprocessor: no mutation, no latency verdict for unsupported data.

    Empty workloads carry no attainment evidence (safe=None). Resource failures
    have safe=False with latency counts undefined, never fabricated SLO misses.
    Legacy SLA accounting fields, if supplied, have no role in this classifier.
    """
    def limit(key):
        x = sla[key] if isinstance(sla, dict) else getattr(sla, key)
        if isinstance(x, bool) or not math.isfinite(x) or x < 0:
            raise ValueError('SLA limits must be finite and nonnegative')
        return x
    ttft, tpot = limit('ttft_s'), limit('tpot_s')
    if not math.isfinite(target) or not 0 <= target <= 1:
        raise ValueError('target must be in [0,1]')
    result = {'metric_version': VERSION, 'safe': None, 'status': metrics['status'],
              'resource_feasible': metrics.get('resource_feasible'), 'target': target,
              'total_requests': metrics['total_requests'], 'required_pass_count': None,
              'attainment_fraction': None, 'joint_pass_count': None, 'ttft_fail_count': None,
              'tpot_fail_count': None, 'both_fail_count': None, 'request_pass': {}}
    if metrics.get('resource_feasible') is False:
        result['safe'] = False
        return result
    if metrics['status'] != 'complete' or not metrics.get('drained'):
        return result
    rs = metrics['request_metrics']; n = metrics['total_requests']
    if len(rs) != n:
        raise ValueError('incomplete request metrics')
    if n == 0:
        result['status'] = 'empty_workload'
        return result
    if metrics.get('resource_feasible') is not True:
        return result
    required = int((Decimal(str(target)) * n).to_integral_value(rounding=ROUND_CEILING))
    tf = df = both = passed = 0
    for rid, r in rs.items():
        m = r['output_tokens']; t = r['ttft_s']; d = r['average_tpot_s']
        if not isinstance(m, int) or isinstance(m, bool) or m < 1:
            raise ValueError('invalid output token count')
        if not math.isfinite(t) or t < 0:
            raise ValueError('invalid TTFT')
        if (m == 1 and d is not None) or (m > 1 and (d is None or not math.isfinite(d) or d < 0)):
            raise ValueError('invalid average TPOT')
        a = t > ttft; b = m > 1 and d > tpot
        tf += a; df += b; both += a and b; passed += not (a or b)
        result['request_pass'][rid] = not (a or b)
    result.update(status='classified', safe=passed >= required, required_pass_count=required,
                  attainment_fraction=passed/n, joint_pass_count=passed,
                  ttft_fail_count=tf, tpot_fail_count=df, both_fail_count=both)
    return result


class MigrationError(ValueError):
    def __init__(self, code, detail, unsupported=False):
        super().__init__(detail)
        self.code, self.unsupported = code, unsupported


def migrate_record(record, tolerance_s=1e-7):
    """Recover unaccounted endpoints; never edit a cache or infer missing metadata.

    Final-time consistency uses absolute 1e-7 s plus relative 1e-10 tolerance,
    allowing cancellation in long finite traces. First-token/Prefill identity is
    checked separately when available. No per-token simulation is performed.
    """
    def require(ok, code, detail, unsupported=False):
        if not ok:
            raise MigrationError(code, detail, unsupported)
    try:
        require(isinstance(record, dict), 'malformed_record', 'Record must be an object')
        inputs = record['inputs']; raw = record['raw']
        require(isinstance(inputs, dict) and isinstance(raw, dict),
                'malformed_record', 'inputs and raw must be objects')
        workload = inputs['workload']
        require(isinstance(workload, list), 'malformed_record', 'workload must be a list')
        metadata = inputs.get('sla', {})
        require(isinstance(metadata, dict), 'missing_overhead_metadata', 'No SLA accounting object', True)
        require(all(k in metadata for k in ['fixed_overhead_s', 'queue_overhead_s']),
                'missing_overhead_metadata', 'Both fixed and queue metadata required', True)
        fixed, queue = metadata['fixed_overhead_s'], metadata['queue_overhead_s']
        require(all(isinstance(x, (float, int)) and not isinstance(x, bool) and math.isfinite(x) and x >= 0
                    for x in [fixed, queue]), 'invalid_overhead_metadata', 'Invalid accounting metadata')
        overhead = fixed + queue
        ms = raw.get('query_metrics')
        require(isinstance(ms, dict), 'missing_metrics', 'query_metrics unavailable', True)
        require(raw.get('finished_requests') == raw.get('total_requests') == len(workload),
                'full_drain_failure', 'Requests not fully drained')
        ids = [r['id'] for r in workload]
        require(len(ids) == len(set(ids)) and set(ms) == set(ids),
                'output_count_inconsistent', 'Request IDs/count inconsistent')
        recovered = {}; maximum_identity_error = 0.; maximum_formula_error = 0.
        for r in workload:
            rid = r['id']; m = ms[rid]; ds = m.get('decode_tpot_s'); count = r['output_tokens']
            require(isinstance(count, int) and not isinstance(count, bool) and count > 0,
                    'output_count_inconsistent', f'{rid}: invalid output count')
            require(isinstance(ds, (list, tuple)) and 'true_first_token_ttft_s' in m,
                    'missing_metrics', f'{rid}: no complete duration/first-token metrics', True)
            require(len(ds) == count, 'output_length_mismatch', f'{rid}: {len(ds)} vs {count}')
            require(all(isinstance(x, (int, float)) and math.isfinite(x) and x >= overhead for x in ds),
                    'invalid_duration', f'{rid}: invalid accounted duration')
            if 'max_tpot_s' in m:
                require(m['max_tpot_s'] == max(ds), 'max_list_mismatch', f'{rid}: max/list mismatch')
            first = m['true_first_token_ttft_s']
            require(math.isfinite(first) and first >= overhead, 'invalid_first_token', f'{rid}: invalid first token')
            ttft = first - overhead
            if 'aligned_ttft_s' in m:
                residual = abs(first - m['aligned_ttft_s'] - (ds[0] - overhead))
                maximum_identity_error = max(maximum_identity_error, residual)
                require(residual <= tolerance_s, 'endpoint_identity_mismatch', f'{rid}: first-token identity')
            post = [x - overhead for x in ds[1:]]
            arrival = r['arrival_time_s']; t_first = arrival + ttft
            t_last = t_first + math.fsum(post)
            req = request_metrics(rid, arrival, count, t_first, t_last)
            # Direct differences avoid loss of precision from re-adding arrivals.
            req['ttft_s'] = ttft
            req['average_tpot_s'] = mean(post) if post else None
            if post:
                maximum_formula_error = max(maximum_formula_error,
                    abs(req['average_tpot_s'] - (t_last-t_first)/(count-1)))
            recovered[rid] = req
        saved_final = raw.get('final_time_s')
        require(isinstance(saved_final, (int, float)) and math.isfinite(saved_final),
                'missing_final_time', 'Saved final execution time unavailable', True)
        final = max((r['t_last_s'] for r in recovered.values()), default=0.)
        require(math.isclose(final, saved_final, abs_tol=tolerance_s, rel_tol=1e-10),
                'final_completion_mismatch', f'Reconstructed {final} vs saved {saved_final}')
        return {'metric_version': VERSION, 'status': 'complete', 'migration_status': 'recoverable',
                'resource_feasible': True, 'resource_evidence': 'successful complete pinned reference execution',
                'drained': True, 'total_requests': len(workload), 'request_metrics': recovered,
                'record_overhead_s': overhead, 'physical_fingerprint': execution_identity(inputs),
                'final_time_s': final, 'saved_final_time_s': saved_final,
                'final_completion_error_s': abs(final-saved_final),
                'max_endpoint_identity_error_s': maximum_identity_error,
                'max_average_endpoint_formula_error_s': maximum_formula_error,
                'm1_count': sum(r['output_tokens'] == 1 for r in recovered.values())}
    except (MigrationError, KeyError, TypeError, ValueError, OverflowError, AttributeError) as exc:
        unsupported = isinstance(exc, MigrationError) and exc.unsupported
        inputs = record.get('inputs') if isinstance(record, dict) else None
        workload = inputs.get('workload') if isinstance(inputs, dict) else None
        return {'metric_version': VERSION, 'status': 'unsupported' if unsupported else 'migration_failed',
                'migration_status': 'unsupported' if unsupported else 'migration_failed',
                'resource_feasible': None, 'drained': False,
                'total_requests': len(workload) if isinstance(workload, list) else None,
                'request_metrics': {}, 'error_code': getattr(exc, 'code', 'malformed_record'),
                'error_detail': str(exc)}
