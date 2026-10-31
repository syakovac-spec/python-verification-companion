"""Bounded subprocess support, independent of simulator or verification library."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading


def worker_limit(jobs, cpu_slots, memory_mb, job_memory_mb, license_slots=None):
    values = [jobs, cpu_slots, memory_mb, job_memory_mb]
    if license_slots is not None:
        values.append(license_slots)
    if any(type(v) is not int or v < 1 for v in values) or memory_mb < job_memory_mb:
        raise ValueError('positive budgets required, with memory for at least one job')
    count = min(jobs, cpu_slots, memory_mb // job_memory_mb)
    return min(count, license_slots) if license_slots is not None else count


class Processes:
    """Linux process groups ensure timeout/cancellation also stops simulator children."""
    def __init__(self):
        self.lock = threading.RLock()
        self.active = set()
        self.cancelled = threading.Event()

    def cancel(self):
        self.cancelled.set()
        with self.lock:
            for proc in self.active:
                self._kill(proc)

    @staticmethod
    def _kill(proc):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    def run(self, command, logfile, timeout):
        if sys.platform != 'linux':
            raise ValueError('process-group regression execution requires Linux/WSL')
        if timeout <= 0:
            raise ValueError('timeout must be positive')
        with Path(logfile).open('w') as log:
            with self.lock:
                if self.cancelled.is_set():
                    return {'returncode': -1, 'execution_status': 'aborted'}
                try:
                    proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                except OSError as exc:
                    log.write(str(exc))
                    return {'returncode': -1, 'execution_status': 'infrastructure_error'}
                self.active.add(proc)
            status = 'finished'
            try:
                try:
                    code = proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    self._kill(proc)
                    code = proc.wait()
                    status = 'timed_out'
                if self.cancelled.is_set():
                    status = 'aborted'
                elif code < 0 and status == 'finished':
                    status = 'aborted'
                return {'returncode': code, 'execution_status': status}
            finally:
                with self.lock:
                    self.active.discard(proc)
