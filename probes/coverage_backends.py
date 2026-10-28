"""Finite relation, weighted choice, coverage sampling and repeatability probes."""
from collections import Counter
import json
from pathlib import Path
import random
import time

from cocotb_coverage.crv import Randomized
from cocotb_coverage.coverage import CoverPoint, coverage_db


class Transaction(Randomized):
    def __init__(self):
        super().__init__()
        self.address = 0
        self.data = 0
        self.add_rand("address", [0, 4, 8, 12])
        self.add_rand("data", list(range(16)))
        self.add_constraint(lambda address, data: (address != 0) or (data == 0))
        self.add_constraint(lambda address: 3 if address == 4 else 1)


@CoverPoint("probe.address", xf=lambda address: address, bins=[0, 4, 8, 12])
def sample_address(address):
    pass


def cc_trace(seed):
    random.seed(seed)
    tx = Transaction()
    trace = []
    for _ in range(128):
        tx.randomize()
        assert tx.address in (0, 4, 8, 12) and 0 <= tx.data < 16
        assert tx.address != 0 or tx.data == 0
        trace.append([tx.address, tx.data])
    return trace


def vsc_probe():
    import vsc

    @vsc.randobj
    class VTransaction:
        def __init__(self):
            self.address = vsc.rand_uint8_t()
            self.data = vsc.rand_uint8_t()

        @vsc.constraint
        def legal(self):
            self.address.inside(vsc.rangelist(0, 4, 8, 12))
            self.data < 16
            with vsc.if_then(self.address == 0):
                self.data == 0
            vsc.dist(self.address, [vsc.weight(0, 1), vsc.weight(4, 3), vsc.weight(8, 1), vsc.weight(12, 1)])

    @vsc.covergroup
    class AddressCoverage:
        def __init__(self):
            self.with_sample(address=vsc.uint8_t())
            self.cp = vsc.coverpoint(self.address, bins={"addresses": vsc.bin_array([], 0, 4, 8, 12)})

    def trace():
        tx = VTransaction()
        tx.set_randstate(vsc.RandState.mkFromSeed(42))
        result = []
        for _ in range(128):
            tx.randomize()
            address, data = int(tx.address), int(tx.data)
            assert address in (0, 4, 8, 12) and 0 <= data < 16
            assert address != 0 or data == 0
            result.append([address, data])
        return result

    first, second = trace(), trace()
    assert first == second, "PyVSC same-state trace mismatch"
    cg = AddressCoverage()
    for address, _ in first:
        cg.sample(address)
    assert cg.get_coverage() == 100.0
    return {"status": "pass", "trace": first, "histogram": dict(Counter(a for a, _ in first)), "coverage_percent": cg.get_coverage(), "repeatable": True}


start = time.perf_counter()
first, second = cc_trace(42), cc_trace(42)
assert first == second
assert coverage_db["probe.address"].coverage == 0, "Generation unexpectedly sampled coverage"
for address, _ in first:
    sample_address(address)
assert coverage_db["probe.address"].coverage == 4
results = {"cocotb-coverage": {"status": "pass", "trace": first, "histogram": dict(Counter(a for a, _ in first)), "coverage_bins": 4, "repeatable": True, "seconds": time.perf_counter()-start}}
start = time.perf_counter()
try:
    results["pyvsc"] = vsc_probe()
except Exception as exc:
    results["pyvsc"] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
results["pyvsc"]["seconds"] = time.perf_counter()-start
out = Path(__file__).resolve().parents[1] / "evidence" / "m0"
out.mkdir(parents=True, exist_ok=True)
(out / "backends.json").write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps({k: {f: v for f,v in result.items() if f != "trace"} for k,result in results.items()}, indent=2))
