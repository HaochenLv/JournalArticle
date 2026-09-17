"""JB-Avg-v1: threshold-free serial mixed-cohort virtual-round execution.

No candidate search, SLA budget, intrinsic correction, fixed accounting delay,
common-gamma slowdown, independent phase capacities or HELIX replay.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import math
import time

from standard_metrics_v1 import fingerprint, request_metrics, classify

VERSION = 'JB-Avg-v1'


class UnsupportedProfileDomain(ValueError):
    pass


@dataclass(frozen=True)
class ProfileTable:
    points_ms: tuple[tuple[int, float], ...]

    def __post_init__(self):
        xs = [x for x, y in self.points_ms]
        if len(xs) < 2 or xs != sorted(set(xs)) or xs[0] != 0:
            raise ValueError('Profile must have ordered unique points beginning at zero')
        if any(not math.isfinite(y) or y < 0 for x, y in self.points_ms):
            raise ValueError('Invalid profile time')
        if self.points_ms[0][1] != 0:
            raise ValueError('Empty cohort must cost zero')

    def seconds(self, count):
        if count < 0 or count > self.points_ms[-1][0]:
            raise UnsupportedProfileDomain(f'Count {count} outside [0,{self.points_ms[-1][0]}]')
        for i, (right, value) in enumerate(self.points_ms):
            if count == right:
                return value * .001
            if count < right:
                left, low = self.points_ms[i-1]
                return (low + (value-low)*(count-left)/(right-left)) * .001
        raise AssertionError('Unreachable interpolation')


class BatchProfiles:
    """Per-layer batch times; pinned singleton decode interpolation is doubled."""
    def __init__(self, tables):
        self.tables = tables

    @classmethod
    def pinned(cls, helix_root=None):
        root = Path(helix_root) if helix_root else Path(__file__).resolve().parents[1]/'.deps/helix'
        tables = {}
        for hardware, directory in [('A100-40GB', 'a100'), ('L4x2', 'l4x2'), ('T4x4', 't4x4')]:
            phases = []
            for phase in ['prompt', 'decode']:
                path = root/'simulator/model_manager/llama2_70b'/directory/(phase+'_bs2time.csv')
                with path.open(newline='', encoding='utf-8') as f:
                    phases.append(ProfileTable(tuple((int(x), float(y)) for x, y in csv.reader(f))))
            tables[hardware] = tuple(phases)
        return cls(tables)

    def costs(self, hardware, prompt_tokens, decode_count):
        if hardware not in self.tables:
            raise UnsupportedProfileDomain(f'No pinned profile for {hardware}')
        p, d = self.tables[hardware]
        return p.seconds(prompt_tokens), d.seconds(decode_count)*(2 if decode_count == 1 else 1)


@dataclass
class State:
    spec: object
    phase: str = 'PREFILL'
    prefill_progress: float = 0.
    decode_progress: float = 0.
    block: int = 0
    t_first: float | None = None
    t_last: float | None = None


def context(state, q):
    if state.phase == 'PREFILL':
        return state.spec.input_tokens
    return state.spec.input_tokens + min((state.block+1)*q, state.spec.output_tokens)


def round_cost(pipeline, active, profiles, diagnostic_shares=False):
    """Charge each stage batch once and each boundary message once per round."""
    prefill = [x for x in active.values() if x.phase == 'PREFILL']
    decode = [x for x in active.values() if x.phase in ['FIRST_DECODE', 'DECODE']]
    Q = sum(x.spec.input_tokens for x in prefill); N = len(decode)
    stages = []; shares = {}
    for stage in pipeline.stages:
        hardware = pipeline.nodes[stage.node_id].hardware_type
        p, d = profiles.costs(hardware, Q, N)
        cp, cd = stage.num_layers*p, stage.num_layers*d
        stages.append({'stage': stage.id, 'prefill_s': cp, 'decode_s': cd, 'compute_s': cp+cd})
        if diagnostic_shares:
            shares[stage.id] = {x.spec.id: cp*x.spec.input_tokens/Q for x in prefill}
            shares[stage.id].update({x.spec.id: cd/N for x in decode})
    traffic = {k: 0. for k in pipeline.links}
    for boundary in pipeline.boundaries:
        for link in boundary.route_link_ids:
            traffic[link] += pipeline.model.activation_bytes_per_token*(Q+N)
    network = {}; blocked = []
    for link, size in traffic.items():
        bandwidth = pipeline.links[link].capacity_bytes_per_s
        if size and bandwidth == 0:
            blocked.append({'resource': 'network', 'object': link, 'required_bytes': size, 'capacity': 0})
        else:
            network[link] = size/bandwidth if size else 0.
    compute = math.fsum(x['compute_s'] for x in stages)
    serialization = math.fsum(network.values())
    result = {'prompt_tokens': Q, 'decode_count': N, 'stages': stages,
              'link_bytes': traffic, 'link_serialization_s': network,
              'compute_s': compute, 'serialization_s': serialization,
              'round_s': compute+serialization, 'blocked_resources': blocked}
    if diagnostic_shares:
        result['diagnostic_shares'] = shares
    return result


def memory_state(pipeline, active, q):
    layers = pipeline.layers_by_node()
    stage_counts = {n: sum(s.node_id == n for s in pipeline.stages) for n in pipeline.nodes}
    memory = {n: pipeline.model.weight_bytes*layers[n]/pipeline.model.num_layers +
              (node.workspace_bytes+node.memory_margin_bytes if layers[n] else 0)
              for n, node in pipeline.nodes.items()}
    for x in active.values():
        for n in memory:
            memory[n] += pipeline.model.kv_bytes_per_token_per_layer*context(x,q)*layers[n]
            memory[n] += stage_counts[n]*pipeline.model.activation_bytes_per_token*(
                x.spec.input_tokens if x.phase == 'PREFILL' else 1)
    return memory


def simulate(pipeline, workload, profiles=None, *, q=16, diagnostic_shares=False, max_events=100_000):
    """Fully drain a supported/resource-feasible workload before any classification.

    A timestamp batch removes completions, changes phases/block contexts and admits
    arrivals atomically, then checks resources once on the resulting state. Rates
    are recomputed only after that batch. Diagnostics never affect the trajectory.
    """
    started = time.perf_counter(); pipeline.validate()
    if not isinstance(q, int) or isinstance(q, bool) or q < 1:
        raise ValueError('q must be a positive integer')
    requests = tuple(sorted(workload, key=lambda r:(r.arrival_time_s,r.id)))
    if len({r.id for r in requests}) != len(requests):
        raise ValueError('Duplicate request IDs')
    for r in requests:
        if not math.isfinite(r.arrival_time_s) or r.arrival_time_s < 0:
            raise ValueError('Invalid arrival')
        if any(not isinstance(n,int) or isinstance(n,bool) or n < 1 for n in [r.input_tokens,r.output_tokens]):
            raise ValueError('Invalid token count')
    for link in pipeline.links.values():
        if not math.isfinite(link.capacity_bytes_per_s) or link.capacity_bytes_per_s < 0:
            raise ValueError('Invalid link bandwidth')
    profiles = profiles or BatchProfiles.pinned()
    active = {}; finished = {}; index = 0; t = 0.; batches = []; diagnostics = []
    status = 'complete'; failures = []; resource_feasible = True
    peak_memory = memory_state(pipeline,active,q)

    def snapshot():
        return {rid: {'phase':x.phase,'prefill_progress':x.prefill_progress,
                      'decode_progress':x.decode_progress,'block':x.block,'context':context(x,q),
                      't_first_s':x.t_first,'t_last_s':x.t_last} for rid,x in sorted(active.items())}

    while index < len(requests) or active:
        if len(batches) >= max_events:
            status = 'event_limit_exceeded'; resource_feasible = None; break
        before = snapshot(); before_memory = memory_state(pipeline,active,q)
        due = {}; candidates = []
        if index < len(requests):
            candidates.append(requests[index].arrival_time_s)
        cost = None
        if active:
            try:
                cost = round_cost(pipeline,active,profiles,diagnostic_shares)
            except UnsupportedProfileDomain as exc:
                status = 'unsupported_profile_domain'; resource_feasible = None
                failures.append({'time_s':t,'resource':'profile','detail':str(exc)}); break
            if cost['blocked_resources']:
                status = 'hard_resource_infeasible'; resource_feasible = False
                failures.extend({'time_s':t,**x} for x in cost['blocked_resources']); break
            if not math.isfinite(cost['round_s']) or cost['round_s'] <= 0:
                status = 'unsupported_service_cost'; resource_feasible = None; break
            for rid, x in active.items():
                if x.phase == 'PREFILL':
                    target = 1.; progress = x.prefill_progress
                else:
                    target = 1. if x.phase == 'FIRST_DECODE' else min((x.block+1)*q,x.spec.output_tokens)
                    progress = x.decode_progress
                when = t+(target-progress)*cost['round_s']
                due[rid] = (when,target); candidates.append(when)
        nt = min(candidates)
        if nt < t:
            raise RuntimeError('Backward virtual event')
        delta = (nt-t)/cost['round_s'] if cost else 0.
        for x in active.values():
            if x.phase == 'PREFILL':
                x.prefill_progress = min(1.,x.prefill_progress+delta)
            else:
                x.decode_progress = min(float(x.spec.output_tokens),x.decode_progress+delta)
        previous_time = t; t = nt
        tolerance = max(1e-12,8*math.ulp(t))
        events = []
        for rid,(when,target) in due.items():
            if abs(when-t) > tolerance:
                continue
            x = active[rid]
            if x.phase == 'PREFILL':
                x.prefill_progress=1.; x.phase='FIRST_DECODE'
                events.append(('PrefillDone',rid))
            else:
                x.decode_progress=float(target)
                if x.phase == 'FIRST_DECODE':
                    x.t_first=t; x.phase='DECODE'; events.append(('FirstToken',rid))
                if target == x.spec.output_tokens:
                    x.t_last=t; x.phase='FINISHED'; events.append(('Finish',rid))
                    finished[rid]=request_metrics(rid,x.spec.arrival_time_s,x.spec.output_tokens,x.t_first,x.t_last)
                    del active[rid]
                elif target % q == 0:
                    x.block=int(target)//q; events.append(('DecodeBlockUpdate',rid))
        while index < len(requests) and requests[index].arrival_time_s <= t:
            r=requests[index]; active[r.id]=State(r); index+=1; events.append(('Arrival',r.id))
        memory=memory_state(pipeline,active,q)
        for n,size in memory.items():
            peak_memory[n]=max(peak_memory[n],size)
            if size > pipeline.nodes[n].memory_capacity_bytes:
                failures.append({'time_s':t,'resource':'memory','object':n,'required_bytes':size,
                                 'capacity_bytes':pipeline.nodes[n].memory_capacity_bytes})
        batch={'time_s':t,'events':sorted(events),'before':before,'after':snapshot(),
               'memory_before':before_memory,'memory_after':memory}
        batches.append(batch)
        if cost:
            diagnostics.append({'start_s':previous_time,'end_s':t,**cost})
        if failures:
            status='hard_resource_infeasible';resource_feasible=False;break
    return {'model_version':VERSION,'status':status,'resource_feasible':resource_feasible,
            'resource_failures':failures,'drained':status=='complete' and not active and index==len(requests),
            'total_requests':len(requests),'finished_requests':len(finished),'request_metrics':finished,
            'final_time_s':t,'trajectory':batches,'trajectory_hash':fingerprint(batches),
            'round_diagnostics':diagnostics,'peak_memory_bytes':peak_memory,
            'q':q,'runtime_s':time.perf_counter()-started}
