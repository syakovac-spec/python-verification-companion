from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import tempfile
import time
import unittest
from verification_evidence.regression import Processes, worker_limit


class RegressionTests(unittest.TestCase):
    def test_cpu_memory_and_license_admission(self):
        self.assertEqual(worker_limit(8, 4, 1024, 512), 2)
        self.assertEqual(worker_limit(8, 4, 4096, 512, 1), 1)
        with self.assertRaises(ValueError): worker_limit(1, 1, 128, 512)

    @unittest.skipUnless(sys.platform=='linux', 'Linux process groups')
    def test_failure_timeout_and_abort_are_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            log=Path(directory)/'process.log'; processes=Processes()
            result=processes.run([sys.executable,'-c','raise SystemExit(7)'],log,5)
            self.assertEqual(result['returncode'],7)
            self.assertEqual(result['execution_status'],'finished')
            self.assertEqual(processes.run(['/nonexistent/pvc-command'],log,5)['execution_status'],'infrastructure_error')
            self.assertEqual(processes.run([sys.executable,'-c','import time; time.sleep(30)'],log,.2)['execution_status'],'timed_out')
            with ThreadPoolExecutor(1) as executor:
                future=executor.submit(processes.run,[sys.executable,'-c','import time; time.sleep(30)'],log,10)
                for _ in range(100):
                    with processes.lock:
                        if processes.active: break
                    time.sleep(.01)
                processes.cancel()
                self.assertEqual(future.result()['execution_status'],'aborted')
            self.assertEqual(processes.run([sys.executable,'-c','print(1)'],log,5)['execution_status'],'aborted')
