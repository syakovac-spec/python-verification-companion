"""PyVSC constraint backend with reproducible, independent object streams."""
import hashlib
import random
import time
from functools import wraps
import vsc


def profiled_solve(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        start = time.perf_counter_ns()
        failed = False
        try:
            return method(self, *args, **kwargs)
        except Exception:
            failed = True
            raise
        finally:
            row = self.solve_profile.setdefault(method.__name__, {"calls": 0, "failures": 0, "total_ns": 0, "max_ns": 0})
            elapsed = time.perf_counter_ns() - start
            row["calls"] += 1
            row["failures"] += int(failed)
            row["total_ns"] += elapsed
            row["max_ns"] = max(row["max_ns"], elapsed)
    return call


def seed_for(root, path):
    return int.from_bytes(hashlib.sha256(f"apb-stream-v1:{root}:{path}".encode()).digest()[:4], "big")


@vsc.randobj
class Request:
    def __init__(self):
        self.address = vsc.rand_uint8_t()
        self.write = vsc.rand_bit_t(1)
        self.data = vsc.rand_bit_t(32)

    @vsc.constraint
    def legal(self):
        self.address.inside(vsc.rangelist(0, 4, 8, 12, 16, 6))
        vsc.dist(self.address, [vsc.weight(0, 1), vsc.weight(4, 3), vsc.weight(8, 1),
                               vsc.weight(12, 1), vsc.weight(16, 1), vsc.weight(6, 1)])


@vsc.randobj
class ResetRequest:
    def __init__(self, wait):
        self.wait = wait
        self.phase = vsc.rand_uint8_t()
        self.write = vsc.rand_bit_t(1)
        self.data = vsc.rand_bit_t(32)

    @vsc.constraint
    def legal(self):
        self.phase < 3
        if self.wait == 0:
            self.phase != 1


class Streams:
    def __init__(self, root, wait, path="env.random"):
        self.solve_profile = {}
        self.solver = vsc.get_solver_backend() if hasattr(vsc, "get_solver_backend") else "boolector"
        self.seeds = {key: seed_for(root, path + "." + key) for key in ("transactions", "resets", "idle")}
        self.tx = Request()
        self.tx.set_randstate(vsc.RandState.mkFromSeed(self.seeds["transactions"]))
        self.reset = ResetRequest(wait)
        self.reset.set_randstate(vsc.RandState.mkFromSeed(self.seeds["resets"]))
        self.idle = random.Random(self.seeds["idle"])

    @profiled_solve
    def draw(self, address=None, write=None, high=None, low=None):
        tx = self.tx
        with tx.randomize_with():
            if address is not None:
                tx.address == address
            if write is not None:
                tx.write == write
            if high is not None:
                (tx.data >> 31) == high
            if low is not None:
                (tx.data & 3) == low
        return dict(address=int(tx.address), write=bool(tx.write), data=int(tx.data))

    @profiled_solve
    def draw_reset(self, phase=None, write=None):
        item = self.reset
        with item.randomize_with():
            if phase is not None:
                item.phase == phase
            if write is not None:
                item.write == write
        return dict(phase=("setup", "wait", "completion")[int(item.phase)], write=bool(item.write), data=int(item.data))
