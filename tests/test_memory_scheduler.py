from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from memory_scheduler import MemoryAwareExecutor


class MemorySchedulerTests(unittest.TestCase):
    def test_small_jobs_pass_waiting_large_jobs_without_exceeding_budget(self):
        gate = threading.Event()
        started = threading.Event()
        def work(group, blocked=False):
            if blocked:
                started.set()
                if not gate.wait(5):
                    raise TimeoutError('test gate')
            return group['id']
        with ThreadPoolExecutor(3) as pool:
            with MemoryAwareExecutor(pool, 3, 10, {'large': 7, 'small': 3}, lambda: 100, 0) as scheduler:
                first = scheduler.submit(work, {'id': 'large'}, True)
                self.assertTrue(started.wait(2))
                second = scheduler.submit(work, {'id': 'large'})
                small = scheduler.submit(work, {'id': 'small'})
                try:
                    self.assertEqual(small.result(timeout=2), 'small')
                    self.assertFalse(second.done())
                    self.assertLessEqual(scheduler.peak_reserved, 10)
                finally:
                    gate.set()
                self.assertEqual(first.result(timeout=2), 'large')
                self.assertEqual(second.result(timeout=2), 'large')

    def test_headroom_recovers_and_allows_queued_job(self):
        headroom = [5]
        called = threading.Event()
        def work(group):
            called.set()
            return 1
        with ThreadPoolExecutor(1) as pool:
            with MemoryAwareExecutor(pool, 1, 10, {'g': 7}, lambda: headroom[0], 2) as scheduler:
                future = scheduler.submit(work, {'id': 'g'})
                self.assertFalse(called.wait(.1))
                with scheduler.condition:
                    headroom[0] = 20
                    scheduler.condition.notify_all()
                self.assertEqual(future.result(timeout=2), 1)

    def test_exception_releases_budget_and_does_not_change_next_result(self):
        def work(group, fail):
            if fail:
                raise ValueError('sentinel error')
            return {'untouched': [1, 2, 3]}
        with ThreadPoolExecutor(2) as pool:
            with MemoryAwareExecutor(pool, 2, 10, {'g': 10}, lambda: 100, 0) as scheduler:
                failed = scheduler.submit(work, {'id': 'g'}, True)
                good = scheduler.submit(work, {'id': 'g'}, False)
                with self.assertRaisesRegex(ValueError, 'sentinel error'):
                    failed.result(timeout=2)
                self.assertEqual(good.result(timeout=2), {'untouched': [1, 2, 3]})
                self.assertEqual(scheduler.peak_active, 1)


if __name__ == '__main__':
    unittest.main()
