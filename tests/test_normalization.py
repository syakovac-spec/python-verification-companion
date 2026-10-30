from dataclasses import asdict
import json
from pathlib import Path
import unittest
from verification_evidence.model import canonical, normalized, load


class NormalizationTests(unittest.TestCase):
    def test_direct_traversal_matches_deepcopy_representation(self):
        bundle = load(Path(__file__).parent / 'fixtures/passing.json')
        before = asdict(bundle)
        self.assertEqual(canonical(bundle), json.dumps(before, sort_keys=True,
                         separators=(',', ':'), allow_nan=False))
        actual = normalized(bundle)
        actual['runs'][0]['events'][0]['payload']['extra'] = 'changed'
        self.assertEqual(asdict(bundle), before)
        self.assertEqual(canonical((bundle,)), '[' + canonical(bundle) + ']')

    def test_nonfinite_values_still_rejected_and_unknowns_preserved(self):
        for value in (float('nan'), float('inf'), -float('inf')):
            with self.assertRaises(ValueError):
                canonical({'nested': [value]})
        self.assertEqual(canonical({'data': {'width': 4, 'bits': '10xZ'}}),
                         '{"data":{"bits":"10xZ","width":4}}')
