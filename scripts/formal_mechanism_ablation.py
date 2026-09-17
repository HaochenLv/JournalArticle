"""One explanatory evaluator-only progress ablation; never replaces JB1 labels."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from formal_core import *


if __name__ == '__main__':
    check_pins()
    group = next(g for g in groups() if g['id'] == 'h103-o500-d30-a100-slow')
    _, base = load_workload(group['workload'])
    workload = scale_workload(base, .016)
    pipe = pipeline(group['link'], 0, False)
    cases = []
    for legacy in [False, True]:
        e = jb(pipe, workload, slas(group)['decode'], CachedProfiles(),
               fixed_in_progress=legacy, trace=True, drain=True)
        finish = next(s['time_s'] for s in e['trajectory'] if ('Finish', 'azure-00013') in s['events'])
        arrival = next(s for s in e['trace'] if s['time_s'] == 1720.25 and s['side'] == 'post')
        cases.append({'fixed_overhead_in_progress': legacy, 'safe': e['safe'],
                      'first_violation': e['first_violation'], 'query13_finish_s': finish,
                      'arrival_epoch': {k: arrival[k] for k in ['time_s','num_prefill','num_decode','ledger']}})
    write_json(FORMAL/'mechanisms/optimistic_progress_ablation.json', {
        'group': group['id'], 'shift': 0, 'intensity': .016, 'regime': 'decode',
        'diagnostic_only': True, 'frozen_baseline_changed': False,
        'interpretation_limit': 'Sensitivity to adding fixed overhead to evaluator progress; not a validated general correction or isolation of reference queue/network delays.',
        'cases': cases})
    print(json.dumps(cases, indent=2))
