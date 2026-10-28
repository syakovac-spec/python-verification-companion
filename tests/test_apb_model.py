import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples" / "apb_peripheral" / "tb"))
from apb_model import Analyzer, ID


def frame(reset=1, sel=0, enable=0, write=0, ready=0, error=0, addr=0, wdata=0, rdata=0):
    values = locals()
    return {k: format(v, "032b" if k in ("addr", "wdata", "rdata") else "01b") for k, v in values.items()}


class ModelTests(unittest.TestCase):
    def test_functional_sampling_starts_only_when_enabled(self):
        m = self.start()
        self.transfer(m, 0, read=ID)
        self.assertFalse(any(f.obligation.startswith("FC-") for f in m.findings))
        m.functional = True
        self.transfer(m, 0, read=ID)
        self.assertTrue(any(f.obligation == "FC-001.read.id" and f.outcome == "pass" for f in m.findings))

    def test_bad_response_cannot_close_functional_bin(self):
        m = self.start()
        m.functional = True
        self.transfer(m, 0, read=ID ^ 1)
        rows = [f for f in m.findings if f.obligation == "FC-001.read.id"]
        self.assertTrue(rows)
        self.assertFalse(any(f.outcome == "pass" for f in rows))

    def start(self, waits=0):
        m = Analyzer(waits)
        m.sample(frame(reset=0), 0)
        return m

    def transfer(self, m, address, write=False, data=0, read=0, error=0):
        m.sample(frame(sel=1, addr=address, write=int(write), wdata=data), m.cycle*10+10)
        for _ in range(m.wait_cycles):
            m.sample(frame(sel=1, enable=1, addr=address, write=int(write), wdata=data), m.cycle*10+10)
        m.sample(frame(sel=1, enable=1, ready=1, addr=address, write=int(write), wdata=data, rdata=read, error=error), m.cycle*10+10)

    def test_observed_write_then_read(self):
        m = self.start(3)
        self.transfer(m, 4, True, 0xffffffff)
        self.transfer(m, 4, read=0xffffffff)
        m.finish(100)
        self.assertFalse(m.failures)
        self.assertTrue(any(f.obligation == "APB-002.ones" for f in m.findings))

    def test_wrong_read_is_not_driver_success(self):
        m = self.start()
        self.transfer(m, 4, True, 0xffffffff)
        self.transfer(m, 4, read=0x7fffffff)
        self.assertIn("APB-002.readback", {f.obligation for f in m.failures})

    def test_no_bus_activity_cannot_create_transactions(self):
        m = self.start()
        for t in (10, 20, 30): m.sample(frame(), t)
        m.finish(40)
        self.assertEqual(m.accepted, [])
        self.assertFalse(any(f.obligation.startswith("APB-002") for f in m.findings))

    def test_missing_response_and_pending_shutdown(self):
        m = self.start(1)
        m.sample(frame(sel=1), 10)
        for t in (20, 30): m.sample(frame(sel=1, enable=1), t)
        m.finish(40)
        self.assertEqual({f.obligation for f in m.failures}, {"APB-006.read", "APB-010.drained"})

    def test_extra_response_without_setup(self):
        m = self.start()
        m.sample(frame(sel=1, enable=1, ready=1, rdata=ID), 10)
        self.assertIn("PHASE", m.failures[0].reason)

    def test_control_change_during_wait(self):
        m = self.start(1)
        m.sample(frame(sel=1, addr=4, write=1, wdata=1), 10)
        m.sample(frame(sel=1, enable=1, addr=4, write=1, wdata=2), 20)
        self.assertIn("STABILITY", m.failures[0].reason)

    def test_xz_not_coerced(self):
        m = self.start()
        m.sample(frame(sel=1), 10)
        f = frame(sel=1, enable=1, ready=1, rdata=ID); f["rdata"] = "x"*32
        m.sample(f, 20)
        self.assertEqual(m.failures[0].outcome, "inconclusive")
        self.assertEqual(m.failures[0].payload["rdata"]["bits"], "x"*32)
        self.assertEqual(m.accepted, [])

    def test_reset_cancels_wait_and_new_epoch_reads_zero(self):
        m = self.start(3)
        self.transfer(m, 4, True, 9)
        m.sample(frame(sel=1, addr=4, write=1, wdata=99), 100)
        m.reset(101, frame(reset=0, sel=1, enable=1))
        self.assertIsNone(m.pending)
        self.transfer(m, 4, read=0)
        self.assertFalse(m.failures)
        self.assertTrue(any(f.obligation == "APB-008.wait.write" for f in m.findings))

    def test_reset_read_credit_requires_unmodified_state(self):
        m = self.start()
        self.transfer(m, 4, True, 9)
        self.transfer(m, 4, read=9)
        self.assertFalse(any(f.obligation == "APB-001.startup.scratch" for f in m.findings))

    def test_w1c_zero_preserves_and_one_clears(self):
        m = self.start()
        for a, data, expected in ((12, 1, 1), (8, 0, 1), (8, 1, 0)):
            self.transfer(m, a, True, data)
            self.transfer(m, 8, read=expected)
        self.assertFalse(m.failures)

    def test_error_on_invalid_write_does_not_update_model(self):
        m = self.start()
        self.transfer(m, 4, True, 23)
        self.transfer(m, 6, True, 99, error=1)
        self.transfer(m, 4, read=23)
        self.assertFalse(m.failures)

    def test_w1c_does_not_credit_vacuous_clear_or_preserve(self):
        for data in (0, 1):
            m = self.start()
            self.transfer(m, 8, True, data)
            self.transfer(m, 8, read=0)
            self.assertFalse(any(f.obligation in ("APB-004.one_clear", "APB-004.zero_preserve") for f in m.findings))

    def test_stale_write_after_reset_is_detected(self):
        m = self.start(1)
        m.sample(frame(sel=1, write=1, addr=4, wdata=99), 10)
        m.reset(11, frame(reset=0, sel=1, enable=1))
        self.transfer(m, 4, read=99)
        self.assertIn("APB-008.wait.write", {f.obligation for f in m.failures})

    def test_early_response_fails_exact_latency(self):
        m = self.start(3)
        m.sample(frame(sel=1), 10)
        m.sample(frame(sel=1, enable=1, ready=1, rdata=ID), 20)
        self.assertIn("APB-006.read", {f.obligation for f in m.failures})


if __name__ == "__main__":
    unittest.main()
