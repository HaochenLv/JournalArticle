"""Memory-budgeted dispatch of independent jobs; never edits their inputs/results."""
from collections import deque
from concurrent.futures import Future
import threading
import time


class MemoryAwareExecutor:
    """Round-robin groups, skipping jobs that do not fit until reservations free.

    Costs are conservative estimates, not OS-enforced memory limits. The live
    headroom guard additionally stops new admissions when other apps use memory.
    Running jobs finish normally; timeouts start inside the dispatched job.
    """
    def __init__(self, pool, max_workers, budget_bytes, cost_by_group,
                 available_memory, reserve_bytes, on_snapshot=None):
        if max_workers < 1 or budget_bytes <= 0:
            raise ValueError('Invalid worker/memory budget')
        if any(cost <= 0 or cost > budget_bytes for cost in cost_by_group.values()):
            raise ValueError('Every job must fit within the memory budget')
        self.pool = pool
        self.max_workers = max_workers
        self.budget = budget_bytes
        self.costs = cost_by_group
        self.available = available_memory
        self.reserve = reserve_bytes
        self.on_snapshot = on_snapshot
        self.condition = threading.Condition()
        self.queues = {}
        self.ready = deque()
        self.active = {}
        self.reserved = 0
        self.closing = False
        self.failure = None
        self.peak_active = 0
        self.peak_reserved = 0
        self.sequence = 0
        self.thread = threading.Thread(target=self._dispatch, name='memory-dispatch')
        self.thread.start()

    def submit(self, function, group, *args):
        future = Future()
        gid = group['id']
        with self.condition:
            if self.failure:
                raise RuntimeError('Memory dispatcher failed') from self.failure
            if self.closing:
                raise RuntimeError('Executor is closing')
            if gid not in self.queues:
                self.queues[gid] = deque()
                self.ready.append(gid)
            self.queues[gid].append((future, function, (group, *args)))
            self.condition.notify_all()
        return future

    def _finished(self, serial, outer, inner):
        with self.condition:
            item = self.active.pop(serial)
            self.reserved -= item['reserved_bytes']
            self.condition.notify_all()
        try:
            outer.set_result(inner.result())
        except BaseException as error:
            outer.set_exception(error)

    def _snapshot(self, headroom):
        return {'active': len(self.active), 'pending': sum(map(len, self.queues.values())),
                'max_workers': self.max_workers, 'budget_bytes': self.budget,
                'reserved_bytes': self.reserved, 'headroom_bytes': headroom,
                'reserve_bytes': self.reserve, 'peak_active': self.peak_active,
                'peak_reserved_bytes': self.peak_reserved,
                'running': list(self.active.values()), 'checked_unix_s': time.time()}

    def _dispatch(self):
        try:
            self._loop()
        except BaseException as error:
            with self.condition:
                self.failure = error
                self.closing = True
                pending = [item[0] for queue in self.queues.values() for item in queue]
                self.queues.clear()
                self.ready.clear()
                self.condition.notify_all()
            for future in pending:
                future.set_exception(error)

    def _loop(self):
        last_snapshot = 0.
        while True:
            with self.condition:
                headroom = self.available()
                selected = None
                if len(self.active) < self.max_workers:
                    for _ in range(len(self.ready)):
                        gid = self.ready.popleft()
                        cost = self.costs[gid]
                        if (self.reserved + cost <= self.budget
                                and headroom >= self.reserve + cost):
                            selected = (gid, cost, self.queues[gid].popleft())
                            if not self.queues[gid]:
                                del self.queues[gid]
                            else:
                                self.ready.append(gid)
                            break
                        self.ready.append(gid)
                if selected:
                    gid, cost, (outer, function, args) = selected
                    if not outer.set_running_or_notify_cancel():
                        continue
                    serial = self.sequence
                    self.sequence += 1
                    self.active[serial] = {'group': gid, 'reserved_bytes': cost,
                                           'shift': args[1] if len(args) > 1 else None,
                                           'intensity': args[2] if len(args) > 2 else None}
                    self.reserved += cost
                    self.peak_active = max(self.peak_active, len(self.active))
                    self.peak_reserved = max(self.peak_reserved, self.reserved)
                    try:
                        inner = self.pool.submit(function, *args)
                    except BaseException as error:
                        self.active.pop(serial)
                        self.reserved -= cost
                        outer.set_exception(error)
                    else:
                        inner.add_done_callback(lambda f, s=serial, o=outer: self._finished(s, o, f))
                finished = self.closing and not self.queues and not self.active
                if self.on_snapshot and (time.monotonic() - last_snapshot >= 2 or finished):
                    self.on_snapshot(self._snapshot(headroom))
                    last_snapshot = time.monotonic()
                if finished:
                    return
                if not selected:
                    self.condition.wait(timeout=1.)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        with self.condition:
            self.closing = True
            self.condition.notify_all()
        self.thread.join()
        if self.failure and exc[0] is None:
            raise RuntimeError('Memory dispatcher failed') from self.failure
