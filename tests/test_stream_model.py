"""Counterexamples for the independent streaming scoreboard, without a simulator."""
import importlib.util
from pathlib import Path
import unittest
from verification_evidence import EvidenceRecorder, load, catalog_digest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("stream_example_model", ROOT / "examples/ready_valid/model.py")
stream = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stream)


class StreamModelTests(unittest.TestCase):
    def setUp(self):
        manifest = load(ROOT / "tests/fixtures/passing.json").runs[0].manifest
        catalog = stream.plan(manifest.compatibility.checker_digest)
        manifest.compatibility.catalog_digest = catalog_digest(catalog)
        manifest.compatibility.profile = "elastic-8bit"
        self.model = stream.StreamModel(EvidenceRecorder(catalog, manifest))

    def sample(self, port, tick, data="10100101", valid="1", ready="1", reset="1"):
        self.model.sample(port, tick, dict(data=data, valid=valid, ready=ready, reset=reset))

    def test_corruption_and_unexpected_output_fail(self):
        self.sample("tx", 10)
        self.sample("rx", 20, data="10100100")
        self.sample("rx", 30)
        run = self.model.finish(40).runs[0]
        self.assertEqual([c.outcome for c in run.checks if c.obligation_id == "ORDER"], ["fail", "fail"])

    def test_missing_output_retains_pending(self):
        self.sample("tx", 10)
        run = self.model.finish(20).runs[0]
        self.assertEqual(run.finalization.pending_by_obligation, {"DRAIN": 1})
        self.assertEqual(run.finalization.status, "fail")

    def test_stalled_data_change_fails(self):
        self.sample("rx", 10, ready="0")
        self.sample("rx", 20, ready="0", data="00000000")
        run = self.model.finish(30).runs[0]
        self.assertEqual(next(c.outcome for c in run.checks if c.obligation_id == "HOLD.rx"), "fail")

    def test_unknown_data_is_inconclusive(self):
        self.sample("tx", 10, data="10xz0101")
        run = self.model.finish(20).runs[0]
        self.assertEqual(run.finalization.status, "aborted")
        self.assertEqual(run.events[0].payload["data"]["bits"], "10xz0101")

    def test_reset_discards_pending_and_separates_epochs(self):
        self.sample("tx", 10)
        self.sample("tx", 20, reset="0")
        self.sample("rx", 20, reset="0")
        self.assertEqual(self.model.epoch, 1)
        self.assertFalse(self.model.pending)
        self.sample("tx", 30, data="00000011")
        self.sample("rx", 40, data="00000011")
        run = self.model.finish(50).runs[0]
        check = next(c for c in run.checks if c.obligation_id == "ORDER")
        self.assertEqual(check.outcome, "pass")
        self.assertTrue(all(e.epoch == 1 for e in run.events if e.id in check.event_ids))


if __name__ == "__main__":
    unittest.main()
