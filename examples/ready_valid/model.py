"""Independent streaming scoreboard, reusable by pyuvm and plain cocotb."""
from collections import deque
from verification_evidence.model import Catalog, Requirement, Checker, Bin, Obligation


def plan(digest):
    names = {"ORDER": ("Output preserves accepted input data and order", 8),
             "HOLD.tx": ("Source holds valid/data under backpressure", 2),
             "HOLD.rx": ("DUT holds valid/data under backpressure", 2),
             "DRAIN": ("No outstanding transfers at shutdown", 1)}
    return Catalog("1.0", "ready-valid-v1",
        [Requirement(n, desc, "elastic-buffer-contract-v1") for n, (desc, _) in names.items()],
        [Checker("stream-model", "1", digest, "Observed input/output queue and stall stability", ["stream"], "relevant X/Z => inconclusive")],
        [Bin(n, "1", digest, desc, goal) for n, (desc, goal) in names.items()],
        [Obligation(n, n, n, ["stream-model"], goal, ["elastic-8bit"]) for n, (_, goal) in names.items()], [])


class StreamModel:
    def __init__(self, recorder, interface="pipe0"):
        self.recorder = recorder
        self.interface = interface
        self.pending = deque()
        self.epoch = 0
        self.reset_active = False
        self.previous = {}
        self.serial = 0

    def event(self, port, tick, correlation, signals):
        return self.recorder.observe(interface=self.interface, epoch=self.epoch, correlation=correlation,
            tick=tick, kind="stream", payload={"channel": port, **{
                name: {"width": len(bits), "bits": bits} for name, bits in signals.items()}})

    def check(self, name, ids, tick, outcome, reason):
        self.recorder.evaluate(obligation_id=name, checker_id="stream-model", event_ids=ids,
                              outcome=outcome, reason=reason, tick=tick)

    def sample(self, port, tick, signals):
        reset, valid, ready, data = (signals[n] for n in ("reset", "valid", "ready", "data"))
        if reset == "0":
            if not self.reset_active:
                self.epoch += 1
                self.pending.clear()  # reset explicitly discards in-flight work by this DUT contract
                self.previous.clear()
            self.reset_active = True
            return
        self.reset_active = False
        relevant = reset + valid + ready + (data if valid == "1" else "")
        if any(bit not in "01" for bit in relevant):
            e = self.event(port, tick, f"unknown-{port}-{tick}", signals)
            self.check("HOLD." + port, [e], tick, "inconclusive", "unknown active bus value")
            return
        previous = self.previous.get(port)
        if previous and previous["valid"] == "1" and previous["ready"] == "0":
            e = self.event(port, tick, f"stall-{port}-{tick}", signals)
            good = valid == "1" and data == previous["data"]
            self.check("HOLD." + port, [e], tick, "pass" if good else "fail", "valid/data stable until acceptance")
        self.previous[port] = dict(signals)
        if valid != "1" or ready != "1":
            return
        if port == "tx":
            correlation = f"transfer-{self.serial}"
            self.serial += 1
            e = self.event(port, tick, correlation, signals)
            self.pending.append((e, data, correlation))
        else:
            if self.pending:
                input_id, expected, correlation = self.pending.popleft()
                e = self.event(port, tick, correlation, signals)
                self.check("ORDER", [input_id, e], tick, "pass" if data == expected else "fail", "observed FIFO data/order")
            else:
                e = self.event(port, tick, f"unexpected-{tick}", signals)
                self.check("ORDER", [e], tick, "fail", "output with no accepted input")

    def finish(self, tick, error=None):
        e = self.event("shutdown", tick, "drain", {})
        self.check("DRAIN", [e], tick, "fail" if self.pending else "pass", "outstanding observed input transfers")
        return self.recorder.finish(pending_by_obligation={"DRAIN": len(self.pending)} if self.pending else {}, error=error)
