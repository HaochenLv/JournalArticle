from pathlib import Path
import multiprocessing
import os
import sys
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from host_execution import spawned_call, process_alive, host_memory_bytes


def fail():
    raise ValueError('test child failure')


def late_write(path):
    time.sleep(3)
    Path(path).write_text('must not finish')


class HostExecutionTests(unittest.TestCase):
    def test_result_and_failure_are_propagated(self):
        self.assertEqual(spawned_call(pow, (2, 10), 10), 1024)
        with self.assertRaisesRegex(RuntimeError, 'ValueError: test child failure'):
            spawned_call(fail, (), 10)

    def test_timeout_kills_and_reaps_child(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'late-result'
            with self.assertRaises(TimeoutError):
                spawned_call(late_write, (str(path),), 0.5)
            self.assertFalse(path.exists())
            self.assertEqual(multiprocessing.active_children(), [])

    def test_process_probe_does_not_kill_live_process(self):
        child = multiprocessing.get_context('spawn').Process(target=time.sleep, args=(30,))
        child.start()
        try:
            self.assertTrue(process_alive(child.pid))
            time.sleep(0.1)
            self.assertTrue(child.is_alive())
            child.terminate()
            child.join()
            self.assertFalse(process_alive(child.pid))
        finally:
            if child.is_alive():
                child.terminate()
                child.join()
            child.close()
        self.assertGreater(host_memory_bytes(), 0)


if __name__ == '__main__':
    unittest.main()
