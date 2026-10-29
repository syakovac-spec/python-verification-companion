"""pyuvm sequence/agent. Closure decisions use checker observations, not intent."""
from collections import Counter
import json
import pyuvm
from apb_random import Streams
from apb_functional import REGIONS, GOAL, active_names


class BusItem(pyuvm.uvm_sequence_item):
    def __init__(self, action, fields):
        super().__init__("request")
        self.action = action
        self.fields = fields


class ClosureSequence(pyuvm.uvm_sequence):
    def __init__(self, model, driver, root, wait, directory, gap=False):
        super().__init__("constrained_closure")
        self.model, self.driver = model, driver
        self.streams = Streams(root, wait)
        self.names = active_names(wait)
        self.directory, self.gap = directory, gap
        self.generated = []
        self.progress = []
        self.wait = wait

    def counts(self):
        # Correlation/epoch identifies an actually checked operation; deduplicate.
        hits = {name: set() for name in self.names}
        for f in self.model.findings:
            if f.obligation in hits and f.outcome == "pass":
                hits[f.obligation].add((f.epoch, f.correlation))
        return {name: len(events) for name, events in hits.items()}

    def checkpoint(self, stage):
        counts = self.counts()
        self.progress.append(dict(stage=stage, counts=counts, missing=[n for n in self.names if counts[n] < GOAL]))

    async def send(self, action, **fields):
        item = BusItem(action, fields)
        self.generated.append(dict(action=action, **fields))
        await self.start_item(item)
        await self.finish_item(item)

    async def transaction(self, values):
        await self.send("transfer", **values)
        # Readback after writes is still scored solely from sampled bus activity.
        if values["write"]:
            address = values["address"]
            for read in ([4] if address == 4 else [8] if address in (8, 12) else [0] if address == 0 else [4, 8]):
                await self.send("transfer", address=read, write=False, data=0)

    async def target(self, name):
        parts = name.split(".")
        if parts[0] == "FC-001":
            await self.transaction(self.streams.draw(address=REGIONS[parts[2]], write=int(parts[1] == "write")))
        elif parts[0] == "FC-002":
            await self.transaction(self.streams.draw(write=int(parts[2] == "write")))
        elif parts[0] == "FC-003":
            for direction in parts[1]:
                await self.send("transfer", **self.streams.draw(write=int(direction == "w")))
        elif parts[0] == "FC-004":
            await self.send("abort", **self.streams.draw_reset(("setup", "wait", "completion").index(parts[1]), int(parts[2] == "write")))
        elif parts[0] == "FC-005":
            await self.transaction(self.streams.draw(address=4, write=1, high=int(parts[1][1:]), low=int(parts[2][1:])))

    async def body(self):
        self.model.functional = True
        self.driver.record("functional_sampling_start", streams=self.streams.seeds)
        self.checkpoint("before_random")
        for index in range(8 if self.gap else 48):
            await self.transaction(self.streams.draw(address=4 if self.gap else None))
            for _ in range(self.streams.idle.randrange(3)):
                await self.send("idle")
            if not self.gap and index % 12 == 11:
                await self.send("abort", **self.streams.draw_reset())
        self.checkpoint("after_random")
        if not self.gap:
            for index in range(96):
                missing = [n for n, count in self.counts().items() if count < GOAL]
                if not missing or self.model.failures:
                    break
                target = missing[0]
                self.driver.record("coverage_target", obligation=target)
                await self.target(target)
                self.checkpoint(f"target_{index}:{target}")
        await self.send("idle")
        self.checkpoint("final_provisional")
        (self.directory / "closure_progress.json").write_text(json.dumps(self.progress, indent=2) + "\n")
        (self.directory / "generated.json").write_text(json.dumps({"algorithm": "apb-stream-v1", "streams": self.streams.seeds,
              "items": self.generated}, indent=2) + "\n")
        # Distribution uses independent observed accepts only, after sampling start.
        observed = Counter()
        for f in self.model.findings:
            if f.obligation.startswith("FC-001."):
                observed[f.obligation] += 1
        (self.directory / "distribution.json").write_text(json.dumps(dict(observed), indent=2) + "\n")


class RandomAgent(pyuvm.uvm_agent):
    def build_phase(self):
        super().build_phase()
        self.sequencer = pyuvm.uvm_sequencer("sequencer", self)

    async def exercise(self, model, driver, root, wait, directory, gap=False):
        sequence = ClosureSequence(model, driver, root, wait, directory, gap)
        try:
            await sequence.start(self.sequencer)
        finally:
            (directory / "solver-profile.json").write_text(json.dumps({
                "solver": sequence.streams.solver, "calls": sequence.streams.solve_profile,
                "scope": "randomize call wall time including constraint construction"}, indent=2) + "\n")
