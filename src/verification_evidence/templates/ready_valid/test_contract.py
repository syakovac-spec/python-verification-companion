"""Pure checker qualification. These synthetic observations are not DUT evidence."""
import unittest
from verification_evidence.model import Manifest, Compatibility, catalog_digest
from verification_evidence.recording import EvidenceRecorder
from coverage_plan import PROFILE
from model import plan, StreamModel
from interface_config import SPEC


class ContractTests(unittest.TestCase):
    def setUp(self):
        digest = 'a' * 64
        cat = plan(digest)
        manifest = Manifest('checker-unit', Compatibility(1, catalog_digest(cat), digest,
            digest, PROFILE, digest, digest, 'ready-valid-v1'), 1000,
            digest, digest, {'test': 'synthetic'}, {'traffic': '42'}, ['unittest'], [], '')
        self.model = StreamModel(EvidenceRecorder(cat, manifest))
        self.tick = 0

    def sample(self, port, valid=1, ready=1, data=1, reset='1'):
        self.tick += 10
        self.model.sample(port, self.tick, dict(reset=reset, valid=str(valid), ready=str(ready),
            data=format(data, f'0{SPEC["width"]}b')))

    def failed(self):
        bundle = self.model.finish(self.tick + 10)
        return {c.obligation_id for c in bundle.runs[0].checks if c.outcome == 'fail'}

    def test_positive(self):
        self.sample('tx'); self.sample('rx')
        self.assertEqual(self.failed(), set())

    def test_missing_response(self):
        self.sample('tx')
        self.assertIn('DRAIN', self.failed())

    def test_unexpected_response(self):
        self.sample('rx')
        self.assertIn('ORDER', self.failed())

    def test_reset_interruption(self):
        self.sample('tx'); self.sample('tx', reset='0'); self.sample('rx', reset='0')
        self.sample('tx', data=1); self.sample('rx', data=1)
        self.assertEqual(self.model.epoch, 1)
        self.assertEqual(self.failed(), set())

    def test_stale_response_after_reset(self):
        self.sample('tx'); self.sample('tx', reset='0'); self.sample('rx')
        self.assertIn('ORDER', self.failed())

    def test_malformed_stalled_traffic(self):
        self.sample('tx', ready=0, data=0); self.sample('tx', ready=0, data=1)
        self.assertIn('HOLD.tx', self.failed())


if __name__ == '__main__':
    unittest.main()
