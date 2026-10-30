import cocotb
import pyuvm
from cocotb.utils import get_sim_time
from bfm import StreamConfig, reset, drain
from evidence import session, finish
from uvm_components import StreamAgent, StreamScoreboard, StreamSequence


class StreamEnvironment(pyuvm.uvm_env):
    def build_phase(self):
        self.directory, model = session()
        self.scoreboard = StreamScoreboard("scoreboard", self)
        self.scoreboard.model = model
        self.source = StreamAgent("source", self)
        self.source.config = StreamConfig.bind(cocotb.top, "tx", "tx")
        self.source.role = "source"
        self.sink = StreamAgent("sink", self)
        self.sink.config = StreamConfig.bind(cocotb.top, "rx", "rx")
        self.sink.role = "sink"

    def connect_phase(self):
        for agent in (self.source, self.sink):
            agent.monitor.observed.connect(self.scoreboard.analysis_export)


@pyuvm.test(timeout_time=20, timeout_unit="us")
class StreamTest(pyuvm.uvm_test):
    def build_phase(self):
        self.env = StreamEnvironment("env", self)

    async def run_phase(self):
        self.raise_objection()
        error = None
        try:
            await reset(self.env.source.config)
            await StreamSequence("traffic").start(self.env.source.sequencer)
            await drain(self.env.source.config)
        except Exception as exc:
            error = str(exc)
        finally:
            self.result = finish(self.env.directory, self.env.scoreboard.model,
                                 int(get_sim_time(units="ps")), error)
            self.drop_objection()

    def check_phase(self):
        assert self.result["gate"] == "pass", "STREAM_CHECK_FAILURE: " + str(self.result["requirements"])
