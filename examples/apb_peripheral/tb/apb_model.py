"""Independent monitor state machine/reference model. No simulator imports."""
from dataclasses import dataclass
from apb_functional import region

ID = 0x43564301
SIGNALS = ("reset", "sel", "enable", "write", "ready", "error", "addr", "wdata", "rdata")


@dataclass(frozen=True)
class Finding:
    obligation: str
    outcome: str
    reason: str
    tick: int
    epoch: int
    correlation: str
    payload: dict


def vector(bits):
    return {"width": len(bits), "bits": bits.lower()}


def pattern(value):
    names = {0: "zero", 0xffffffff: "ones", 0xaaaaaaaa: "alt_a", 0x55555555: "alt_5"}
    if value in names:
        return names[value]
    if value > 0 and value & (value - 1) == 0:
        return f"walk_{value.bit_length()-1:02d}"
    return None


def obligation_names():
    names = ["APB-001.id", "APB-002.write", "APB-002.readback", "APB-003.reject", "APB-003.unchanged",
             "APB-004.write", "APB-004.readback", "APB-004.event_read",
             "APB-006.read", "APB-006.write", "APB-009.clean", "APB-010.drained"]
    names += [f"APB-001.{reset}.{reg}" for reset in ("startup", "after_write") for reg in ("id", "scratch", "status")]
    names += [f"APB-002.{p}" for p in ["zero", "ones", "alt_a", "alt_5"] + [f"walk_{n:02d}" for n in range(32)]]
    names += [f"APB-004.{p}" for p in ("set", "zero_preserve", "one_clear", "repeat_set", "reserved")]
    names += [f"APB-005.{kind}.{direction}" for kind in ("unmapped", "misaligned") for direction in ("read", "write")]
    names += ["APB-005.preserve_scratch", "APB-005.preserve_status"]
    names += [f"APB-007.{pair}.{address}" for pair in ("rr", "rw", "wr", "ww") for address in ("same", "different")]
    names += [f"APB-008.{phase}.{direction}" for phase in ("setup", "wait", "completion") for direction in ("read", "write")]
    return names


class Analyzer:
    def __init__(self, wait_cycles, publish=None):
        self.wait_cycles = wait_cycles
        self.publish = publish
        self.findings = []
        self.epoch = 0
        self.in_reset = False
        self.pending = None
        self.scratch = self.status = 0
        self.ever_write = False
        self.last_pattern = None
        self.status_action = None
        self.ro_written = False
        self.invalid_write = False
        self.abort = None
        self.reset_kind = "startup"
        self.reset_pending = set()
        self.previous = None
        self.cycle = 0
        self.serial = 0
        self.last_frame = {name: "0" * (32 if name in ("addr", "wdata", "rdata") else 1) for name in SIGNALS}
        self.accepted = []
        self.functional = False

    def emit(self, obligation, good, reason, tick, frame=None, correlation=None, outcome=None):
        item = Finding(obligation, outcome or ("pass" if good else "fail"), reason, tick, self.epoch,
                       correlation or f"sample-{self.cycle}", {k: vector(v) for k, v in (frame or self.last_frame).items()})
        self.findings.append(item)
        if self.publish:
            self.publish(item)

    @property
    def failures(self):
        return [f for f in self.findings if f.outcome != "pass"]

    def reset(self, tick, frame):
        if self.in_reset:
            return
        self.in_reset = True
        self.epoch += 1
        if self.pending:
            phase = "setup" if frame["enable"] == "0" else ("wait" if self.pending["waits"] < self.wait_cycles else "completion")
            self.abort = (phase, "write" if self.pending["write"] else "read")
        else:
            self.abort = None
        self.reset_kind = "after_write" if self.ever_write else "startup"
        self.reset_pending = {0, 4, 8}
        self.scratch = self.status = 0
        self.pending = self.previous = self.last_pattern = self.status_action = None
        self.ro_written = self.invalid_write = False

    def sample(self, frame, tick):
        self.cycle += 1
        self.last_frame = dict(frame)
        if frame["reset"] == "0":
            self.reset(tick, frame)
            return
        self.in_reset = False
        # Ignore data buses when idle; preserve all bits in emitted evidence.
        required = ["reset", "sel", "enable"]
        if frame["sel"] == "1":
            required += ["write", "addr"]
            if frame["write"] == "1":
                required += ["wdata"]
            if frame["enable"] == "1":
                required += ["ready"]
                if frame["ready"] == "1":
                    required += ["error"]
                    if frame["write"] == "0":
                        required += ["rdata"]
        if any(set(frame[k].lower()) - {"0", "1"} for k in required):
            self.emit("APB-009.clean", False, "XZ: unknown relevant bus value", tick, frame, outcome="inconclusive")
            return
        d = {k: int(frame[k], 2) for k in required}
        if not d["sel"]:
            if d["enable"] or self.pending:
                self.emit("APB-009.clean", False, "PHASE: idle/enable or dropped pending operation", tick)
            return
        if not d["enable"]:
            if self.pending:
                self.emit("APB-009.clean", False, "PHASE: setup replaced unfinished operation", tick)
                return
            self.serial += 1
            self.pending = dict(addr=d["addr"], write=d["write"], data=d.get("wdata", 0), waits=0,
                                setup=self.cycle, correlation=f"txn-{self.serial}", valid=True)
            return
        if self.pending is None:
            self.emit("APB-009.clean", False, "PHASE: extra access without setup", tick)
            return
        p = self.pending
        stable = d["addr"] == p["addr"] and d["write"] == p["write"] and (not p["write"] or d.get("wdata") == p["data"])
        if not stable:
            p["valid"] = False
            self.emit("APB-009.clean", False, "STABILITY: address/direction/write data changed", tick, correlation=p["correlation"])
        direction = "write" if p["write"] else "read"
        if not d["ready"]:
            p["waits"] += 1
            if p["waits"] == self.wait_cycles + 1:
                self.emit(f"APB-006.{direction}", False, "LATENCY: missing response at required edge", tick, correlation=p["correlation"])
            return
        # Model uses actual observed accepted controls, never a driver completion.
        addr, write, data = d["addr"], d["write"], d.get("wdata", 0)
        error = addr not in (0, 4, 8, 12) or (write and addr == 0)
        expected_data = {0: ID, 4: self.scratch, 8: self.status, 12: 0}.get(addr, 0)
        good = d["error"] == int(error) and (write or d["rdata"] == expected_data)
        reason = f"RESPONSE: expected error={int(error)} data=0x{expected_data:08x}"
        def emit(name, condition=good, why=reason):
            self.emit(name, condition, why, tick, correlation=p["correlation"])
        emit(f"APB-006.{direction}", p["waits"] == self.wait_cycles, f"LATENCY: observed {p['waits']}, expected {self.wait_cycles}")
        emit("APB-009.clean", p["valid"], "PROTOCOL: setup/access controls stable")
        if self.functional:
            checked = good and p["valid"] and p["waits"] == self.wait_cycles
            emit(f"FC-001.{direction}.{region(addr)}", checked)
            emit(f"FC-002.wait_{self.wait_cycles}.{direction}", checked)
        if addr not in (0, 4, 8, 12):
            emit(f"APB-005.{'misaligned' if addr % 4 else 'unmapped'}.{direction}")
            if write:
                self.invalid_write = True
        elif write:
            emit({0: "APB-003.reject", 4: "APB-002.write", 8: "APB-004.write", 12: "APB-004.write"}[addr])
            if addr == 0:
                self.ro_written = True
            elif addr == 4:
                self.scratch = data
                self.last_pattern = pattern(data)
            elif addr == 8:
                # A clear/preserve scenario must begin set to distinguish a bug.
                self.status_action = ("one_clear" if data & 1 else ("reserved" if data else "zero_preserve")) if self.status else None
                self.status &= ~(data & 1)
            elif addr == 12:
                self.status_action = "repeat_set" if self.status and data & 1 else ("set" if data & 1 else "reserved")
                self.status |= data & 1
            if not error:
                self.ever_write = True
                self.invalid_write = False
                self.reset_pending.discard(4 if addr == 4 else 8)
        else:
            emit({0: "APB-001.id", 4: "APB-002.readback", 8: "APB-004.readback", 12: "APB-004.event_read"}[addr])
            if addr in self.reset_pending:
                emit(f"APB-001.{self.reset_kind}.{ {0:'id',4:'scratch',8:'status'}[addr]}")
                self.reset_pending.remove(addr)
            if addr == 0 and self.ro_written:
                emit("APB-003.unchanged")
            if addr == 4 and self.last_pattern:
                emit(f"APB-002.{self.last_pattern}")
            if self.functional and addr == 4:
                emit(f"FC-005.h{expected_data >> 31}.l{expected_data & 3}")
            if addr == 8 and self.status_action:
                emit(f"APB-004.{self.status_action}")
            if self.invalid_write and addr in (4, 8):
                emit("APB-005.preserve_" + ("scratch" if addr == 4 else "status"))
            if addr == 4 and self.abort:
                emit(f"APB-008.{self.abort[0]}.{self.abort[1]}")
                if self.functional:
                    emit(f"FC-004.{self.abort[0]}.{self.abort[1]}")
                self.abort = None
        if self.previous and p["setup"] == self.previous["cycle"] + 1:
            pair = ("w" if self.previous["write"] else "r") + ("w" if write else "r")
            address = "same" if self.previous["addr"] == addr else "different"
            emit(f"APB-007.{pair}.{address}", good and p["valid"], "ORDER: consecutive accepted transfers with setup")
            if self.functional:
                emit(f"FC-003.{pair}", good and p["valid"], "ORDER: observed back-to-back operation pair")
        self.previous = dict(addr=addr, write=write, cycle=self.cycle)
        self.accepted.append(dict(tick=tick, epoch=self.epoch, addr=addr, write=write, data=data,
                                  read=d.get("rdata"), waits=p["waits"], correlation=p["correlation"]))
        self.pending = None

    def finish(self, tick):
        self.emit("APB-010.drained", self.pending is None, "DRAIN: pending operation" if self.pending else "DRAIN: no pending operations", tick)
