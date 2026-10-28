"""Standard pyuvm agent/sequencer/driver/monitor/subscriber composition.

Construct StreamAgent instances for each port; set config and role in the
parent build_phase before children build. Role 'passive' creates no driver.
"""
import pyuvm
from bfm import observe, send, sink, data_sequence


class StreamItem(pyuvm.uvm_sequence_item):
    def __init__(self, name, data):
        super().__init__(name)
        self.data = data


class StreamSequence(pyuvm.uvm_sequence):
    async def body(self):
        for index, value in enumerate(data_sequence()):
            item = StreamItem(f"word-{index}", value)
            await self.start_item(item)
            await self.finish_item(item)


class StreamDriver(pyuvm.uvm_driver):
    async def run_phase(self):
        if self.role == "sink":
            await sink(self.config)
        else:
            while True:
                item = await self.seq_item_port.get_next_item()
                await send(self.config, item.data)
                self.seq_item_port.item_done()


class StreamMonitor(pyuvm.uvm_monitor):
    def build_phase(self):
        self.observed = pyuvm.uvm_analysis_port("observed", self)

    async def run_phase(self):
        await observe(self.config, self.observed.write)


class StreamAgent(pyuvm.uvm_agent):
    def build_phase(self):
        if self.role not in ("source", "sink", "passive"):
            raise ValueError("agent role must be source, sink or passive")
        self.monitor = StreamMonitor("monitor", self)
        self.monitor.config = self.config
        if self.role != "passive":
            self.driver = StreamDriver("driver", self)
            self.driver.config, self.driver.role = self.config, self.role
        if self.role == "source":
            self.sequencer = pyuvm.uvm_sequencer("sequencer", self)

    def connect_phase(self):
        if self.role == "source":
            self.driver.seq_item_port.connect(self.sequencer.seq_item_export)


class StreamScoreboard(pyuvm.uvm_subscriber):
    def write(self, observed):
        # No sequencer/driver connection. All expected data comes from accepted
        # input observations; all actual data comes from output observations.
        self.model.sample(*observed)
