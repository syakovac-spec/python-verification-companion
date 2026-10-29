import json
import os
from pathlib import Path
import cocotb
from cocotb.triggers import FallingEdge, RisingEdge, ReadOnly, Timer
from cocotb.utils import get_sim_time
import pyuvm
if os.environ.get("APB_REPLAY"):
    import sys
    class NoRandomBackend:
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in ("vsc", "apb_random", "apb_agent"):
                raise RuntimeError("random backend forbidden during recorded replay")
    sys.meta_path.insert(0, NoRandomBackend())
from apb_model import Analyzer, SIGNALS
from apb_evidence import Recorder


def tick():
    return int(get_sim_time(units="ps"))


def snapshot(dut, captured=True):
    signals = dict(reset="PRESETn", sel="PSEL", enable="PENABLE", write="PWRITE", ready="PREADY",
                   error="PSLVERR", addr="PADDR", wdata="PWDATA", rdata="PRDATA")
    return {name: str(getattr(dut, "s_" + name if captured else signals[name]).value).lower() for name in SIGNALS}


class EvidenceSink(pyuvm.uvm_subscriber):
    def write(self, finding):
        self.recorder.write(finding)


class Scoreboard(pyuvm.uvm_subscriber):
    def build_phase(self):
        self.findings = pyuvm.uvm_analysis_port("findings", self)
        self.model = Analyzer(int(os.environ["APB_WAIT"]), self.findings.write)

    def write(self, observation):
        kind, time, frame = observation
        if kind == "reset":
            self.model.reset(time, frame)
        else:
            self.model.sample(frame, time)


class Monitor(pyuvm.uvm_monitor):
    def build_phase(self):
        self.observations = pyuvm.uvm_analysis_port("observations", self)
        self.dut = cocotb.top
        self.tasks = []

    async def sample_loop(self):
        while True:
            await RisingEdge(self.dut.PCLK)
            await ReadOnly()
            # RisingEdge is a notification, not a portable pre-NBA sampling
            # region. HDL captures acceptance/state before sequential updates.
            frame = snapshot(self.dut)
            scratch_before = str(self.dut.s_scratch.value).lower()
            after = snapshot(self.dut, captured=False)
            self.log.write(json.dumps({"kind": "sample", "tick": tick(), "signals": frame,
                                       "post_nba_rdata": after["rdata"]}) + "\n")
            self.observations.write(("sample", tick(), frame))
            # Architectural state probe: compare against the sampled-bus model,
            # never against stimulus intent. Only diagnose premature side effects.
            if frame["reset"] == "1" and frame["sel"] == "1" and frame["enable"] == "1" and frame["ready"] == "0" and frame["write"] == "1":
                actual = str(self.dut.dut.scratch.value).lower()
                expected = scratch_before
                self.model.emit("APB-006.write", actual == expected, "SIDE_EFFECT_BEFORE_ACCEPT", tick(),
                                dict(frame, architectural_scratch=actual))

    async def reset_loop(self):
        while True:
            await FallingEdge(self.dut.PRESETn)
            frame = snapshot(self.dut, captured=False)
            self.log.write(json.dumps({"kind": "reset", "tick": tick(), "signals": frame}) + "\n")
            self.observations.write(("reset", tick(), frame))

    def start(self, directory):
        self.log = (directory / "samples.jsonl").open("w", buffering=1)
        self.tasks = [cocotb.start_soon(self.sample_loop()), cocotb.start_soon(self.reset_loop())]

    def stop(self):
        error = None
        for task in self.tasks:
            try:
                if task.done():
                    task.result()  # propagate monitor failures, never silently lose evidence
            except Exception as exc:
                error = exc
            finally:
                task.kill()
        self.log.close()
        if error:
            raise error


class Driver(pyuvm.uvm_driver):
    def build_phase(self):
        self.dut = cocotb.top
        self.wait_cycles = int(os.environ["APB_WAIT"])

    async def run_phase(self):
        if not os.environ["APB_CASE"].startswith("m3") or os.environ.get("APB_REPLAY"):
            return
        while True:
            item = await self.seq_item_port.get_next_item()
            await getattr(self, item.action)(**item.fields)
            self.seq_item_port.item_done()

    def drive(self, name, value):
        getattr(self.dut, name).value = value
        self.pins.append(dict(tick=tick(), name=name, value=int(value)))

    def record(self, action, **kwargs):
        if action == "functional_sampling_start":
            self.pins.append(dict(tick=tick(), name="functional", value=1))
        self.log.write(json.dumps(dict(tick=tick(), action=action, **kwargs)) + "\n")

    async def edge(self):
        await RisingEdge(self.dut.PCLK)
        await ReadOnly()

    async def idle(self):
        await FallingEdge(self.dut.PCLK)
        self.drive("PSEL", 0)
        self.drive("PENABLE", 0)
        await self.edge()

    async def reset(self, short=False):
        await FallingEdge(self.dut.PCLK)
        self.drive("PSEL", 0)
        self.drive("PENABLE", 0)
        await Timer(1, units="ns")
        self.drive("PRESETn", 0)
        self.record("reset", short=short)
        if short:
            await Timer(2, units="ns")  # pulse ends before next rising edge
        else:
            await self.edge()
            await self.edge()
            await FallingEdge(self.dut.PCLK)
        self.drive("PRESETn", 1)
        self.record("release_reset")
        await self.edge()

    async def setup(self, address, write=False, data=0):
        await FallingEdge(self.dut.PCLK)
        self.drive("PSEL", 1)
        self.drive("PENABLE", 0)
        self.drive("PADDR", address)
        self.drive("PWRITE", int(write))
        self.drive("PWDATA", data)
        self.record("transfer", address=address, write=bool(write), data=data)
        self.recorder.intent(tick(), address, write, data)
        await self.edge()

    async def transfer(self, address, write=False, data=0):
        await self.setup(address, write, data)
        await FallingEdge(self.dut.PCLK)
        self.drive("PENABLE", 1)
        for _ in range(self.wait_cycles + 4):
            await self.edge()
            # Driver consults only the bus handshake; no expected-data checking.
            if str(self.dut.s_ready.value) == "1":
                return True
        return False  # monitor owns the missing-response diagnosis

    async def abort(self, phase, write, data=0xdeadbeef):
        await self.setup(4, write, data)
        if phase != "setup":
            await FallingEdge(self.dut.PCLK)
            self.drive("PENABLE", 1)
            if phase == "completion":
                for _ in range(self.wait_cycles):
                    await self.edge()
                    await FallingEdge(self.dut.PCLK)
                self.drive("reset_at_edge", 1)
                self.record("reset_at_completion")
                await self.edge()
                await FallingEdge(self.dut.PCLK)
                self.drive("reset_at_edge", 0)
            else:
                await Timer(1, units="ns")
                self.drive("PRESETn", 0)
                self.record("reset_during_wait")
        else:
            await FallingEdge(self.dut.PCLK)
            self.drive("PRESETn", 0)
            self.record("reset_during_setup")
        # Maintain bus phase until reset watcher observes the cancellation.
        await self.edge()
        await FallingEdge(self.dut.PCLK)
        self.drive("PSEL", 0)
        self.drive("PENABLE", 0)
        self.drive("PRESETn", 1)
        await self.edge()
        await self.transfer(4)
        await self.transfer(8)
        await self.transfer(0)


class Environment(pyuvm.uvm_env):
    def build_phase(self):
        self.driver = Driver("driver", self)
        self.monitor = Monitor("monitor", self)
        self.scoreboard = Scoreboard("scoreboard", self)
        self.evidence = EvidenceSink("evidence", self)
        if os.environ["APB_CASE"].startswith("m3") and not os.environ.get("APB_REPLAY"):
            from apb_agent import RandomAgent
            self.random = RandomAgent("random", self)

    def connect_phase(self):
        self.monitor.observations.connect(self.scoreboard.analysis_export)
        self.scoreboard.findings.connect(self.evidence.analysis_export)
        if hasattr(self, "random"):
            self.driver.seq_item_port.connect(self.random.sequencer.seq_item_export)


@pyuvm.test(timeout_time=100, timeout_unit="us")
class DirectedAPB(pyuvm.uvm_test):
    def build_phase(self):
        self.env = Environment("env", self)

    async def baseline(self, d):
        for address in (0, 4, 8):
            await d.transfer(address)
        for value in [0, 0xffffffff, 0xaaaaaaaa, 0x55555555] + [1 << n for n in range(32)]:
            await d.transfer(4, True, value)
            await d.transfer(4)
        await d.transfer(0, True, 0)
        await d.transfer(0)
        for address, data in ((12, 1), (12, 1), (8, 0), (8, 0xfffffffe), (8, 1), (12, 0xfffffffe)):
            await d.transfer(address, True, data)
            await d.transfer(8)
        await d.transfer(12)
        await d.transfer(4, True, 0x13579bdf)
        await d.transfer(12, True, 1)
        for address in (0x10, 0x100, 1, 6, 11, 15):
            await d.transfer(address)
            await d.transfer(address, True, 0xffffffff)
            await d.transfer(4)
            await d.transfer(8)
        for first_write, second_write in ((False, False), (False, True), (True, False), (True, True)):
            for second_address in (4, 8):
                await d.transfer(4, first_write, 0x2468ace0)
                await d.transfer(second_address, second_write, 0)
        await d.idle()
        await d.reset(short=True)  # prove asynchronous clear with no reset-active rising edge
        for address in (0, 4, 8):
            await d.transfer(address)
        for phase in ("setup", "wait", "completion"):
            if phase == "wait" and d.wait_cycles == 0:
                continue
            for write in (False, True):
                await d.transfer(4, True, 0x12345678)
                await d.abort(phase, write)
        await d.idle()

    async def negative(self, d, case):
        if case == "wrong_response":
            await FallingEdge(d.dut.PCLK)
            d.drive("fault_read", 1)
            await d.transfer(0)
            await d.idle()
        elif case == "missing_response":
            await FallingEdge(d.dut.PCLK)
            d.drive("fault_stall", 1)
            await d.transfer(0)
            # Leave pending work for end-of-run reconciliation.
        elif case == "unstable_control":
            await d.setup(4, True, 0x1234)
            await FallingEdge(d.dut.PCLK)
            d.drive("PENABLE", 1)
            await d.edge()  # first wait cycle
            await FallingEdge(d.dut.PCLK)
            d.drive("PWDATA", 0x5678)
            for _ in range(d.wait_cycles):
                await d.edge()
            await d.idle()
        elif case == "interrupted":
            await d.setup(4, True, 99)
            raise RuntimeError("DELIBERATE_INTERRUPTION")
        elif case == "truncated":
            await d.setup(4, True, 99)
        else:
            raise ValueError(case)

    async def run_phase(self):
        self.raise_objection()
        directory = Path(os.environ["APB_OUT"])
        recorder = Recorder(directory)
        d, monitor = self.env.driver, self.env.monitor
        d.recorder = self.env.evidence.recorder = recorder
        d.log = (directory / "stimulus.jsonl").open("w")
        d.pins = []
        monitor.model = self.env.scoreboard.model
        monitor.start(directory)
        self.error = None
        try:
            if os.environ.get("APB_REPLAY"):
                trace = json.loads(Path(os.environ["APB_REPLAY"]).read_text())
                for drive in trace["drives"]:
                    delay = drive["tick"] - tick()
                    if delay:
                        await Timer(delay, units="ps")
                    if drive["name"] == "functional":
                        self.env.scoreboard.model.functional = True
                        d.record("functional_sampling_start")
                    else:
                        d.drive(drive["name"], drive["value"])
                if trace["end_tick"] > tick():
                    await Timer(trace["end_tick"] - tick(), units="ps")
            else:
                await self.generate(d, directory)
            # Advance past the monitor's ReadOnly callback before finalization.
            if not os.environ.get("APB_REPLAY"):
                await Timer(1, units="ns")
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
        finally:
            (directory / "pins.json").write_text(json.dumps({"version": 1, "end_tick": tick(), "drives": d.pins}, indent=2))
            try:
                monitor.stop()
            except Exception as exc:
                self.error = f"monitor: {exc}"
            d.log.close()
            self.env.scoreboard.model.finish(tick())
            self.result = recorder.finish(self.env.scoreboard.model, self.error)
            self.drop_objection()

    async def generate(self, d, directory):
        await d.reset()
        if os.environ["APB_CASE"] == "baseline" or os.environ["APB_CASE"].startswith("m3"):
            await self.baseline(d)
            if hasattr(self.env, "random"):
                await self.env.random.exercise(self.env.scoreboard.model, d, int(os.environ["APB_SEED"]),
                                               d.wait_cycles, directory, os.environ["APB_CASE"] == "m3-gap")
        else:
            await self.negative(d, os.environ["APB_CASE"])


    def check_phase(self):
        assert self.error is None, self.error
        failures = [(f.obligation, f.reason) for f in self.env.scoreboard.model.failures]
        assert not failures, f"APB_CHECK_FAILURES: {failures}"
        expected_gate = "incomplete" if os.environ["APB_CASE"] == "m3-gap" else "pass"
        assert self.result["gate"] == expected_gate, f"APB_EVIDENCE_GAPS: {self.result['requirements']}"
