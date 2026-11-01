"""Independent streaming scoreboard, reusable by pyuvm and plain cocotb."""
from verification_evidence.scoreboard import Scoreboard, Comparison
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
        self.matcher = Scoreboard(recorder, interface=interface, obligation="ORDER",
            drain_obligation="DRAIN", checker="stream-model", kind="stream",
            predictor=lambda p: p["data"]["bits"],
            comparator=lambda expected, p: Comparison(
                "pass" if p["data"]["bits"] == expected else "fail", "observed FIFO data/order"))
        self.epoch = 0
        self.reset_active = False
        self.previous = {}

    @property
    def pending(self):
        return self.matcher.pending

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
                self.matcher.reset(tick, cancel=True)
                self.epoch = self.matcher.epoch
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
        payload = {"channel": port, **{
            name: {"width": len(bits), "bits": bits} for name, bits in signals.items()}}
        if port == "tx":
            self.matcher.request(payload, tick=tick)
        else:
            self.matcher.response(payload, tick=tick)

    def finish(self, tick, error=None):
        pending = self.matcher.close(tick)
        return self.recorder.finish(pending_by_obligation=pending, error=error)
