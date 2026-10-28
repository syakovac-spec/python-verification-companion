import os
import cocotb
from cocotb.triggers import RisingEdge, ReadOnly, Timer
import pyuvm


@cocotb.test()
async def observe_nba(dut):
    for expected in range(4):
        await RisingEdge(dut.clk)
        before = int(dut.q.value)
        await ReadOnly()
        after = int(dut.q.value)
        captured = int(dut.sampled_q.value)
        dut._log.info("NBA_SAMPLE before=%d after=%d captured=%d", before, after, captured)
        assert before == expected
        assert after == expected + 1
        assert captured == expected
    negative = os.environ.get("NBA_NEGATIVE") == "1"
    if negative:
        raise AssertionError("NBA_NEGATIVE_SENTINEL")


class Sink(pyuvm.uvm_subscriber):
    def build_phase(self):
        self.values = []

    def write(self, value):
        self.values.append(value)


@pyuvm.test()
class PublicApiProbe(pyuvm.uvm_test):
    def build_phase(self):
        self.port = pyuvm.uvm_analysis_port("port", self)
        self.sink = Sink("sink", self)

    def connect_phase(self):
        self.port.connect(self.sink.analysis_export)

    async def run_phase(self):
        self.raise_objection()
        self.port.write({"observed": 7})
        await Timer(1, units="ns")
        self.drop_objection()

    def check_phase(self):
        assert self.sink.values == [{"observed": 7}]
