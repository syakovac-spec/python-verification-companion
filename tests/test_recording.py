import unittest
from pathlib import Path
from verification_evidence.recording import EvidenceRecorder
from verification_evidence.model import load, EvidenceError
from verification_evidence.core import summarize


class RecordingTests(unittest.TestCase):
    def recorder(self):
        b = load(Path(__file__).parent / "fixtures/passing.json")
        return EvidenceRecorder(b.catalog, b.runs[0].manifest)

    def observation(self, r, epoch=0, correlation="transfer-1"):
        return r.observe(interface="custom0", epoch=epoch, correlation=correlation, tick=10,
                         kind="transfer", payload={"data": {"width": 4, "bits": "10xz"}})

    def evaluate(self, r, ids, outcome="pass"):
        ob = r.bundle.catalog.obligations[0]
        return r.evaluate(obligation_id=ob.id, checker_id=ob.checker_ids[0], event_ids=ids,
                          outcome=outcome, reason="independent model", tick=10)

    def test_observation_alone_cannot_close(self):
        r = self.recorder()
        self.observation(r)
        self.assertEqual(summarize(r.finish())["gate"], "incomplete")

    def test_checked_observation_closes_and_preserves_vectors(self):
        r = self.recorder()
        self.evaluate(r, [self.observation(r)])
        b = r.finish()
        self.assertEqual(summarize(b)["gate"], "pass")
        self.assertEqual(b.runs[0].events[0].payload["data"]["bits"], "10xz")
        with self.assertRaises(EvidenceError):
            self.observation(r)

    def test_failed_check_and_pending_work_cannot_be_overridden(self):
        r = self.recorder()
        self.evaluate(r, [self.observation(r)], "fail")
        self.assertEqual(r.finish().runs[0].finalization.status, "fail")
        r = self.recorder()
        self.evaluate(r, [self.observation(r)])
        self.assertEqual(summarize(r.finish(pending_by_obligation={"OB-1": 1}))["gate"], "incomplete")

    def test_cross_epoch_group_rejected(self):
        r = self.recorder()
        self.evaluate(r, [self.observation(r, 0), self.observation(r, 1)])
        with self.assertRaises(EvidenceError):
            r.finish()

    def test_undefined_checker_rejected(self):
        r = self.recorder()
        with self.assertRaises(EvidenceError):
            r.evaluate(obligation_id="OB-1", checker_id="wrong", event_ids=[self.observation(r)],
                       outcome="pass", reason="bad binding", tick=10)
