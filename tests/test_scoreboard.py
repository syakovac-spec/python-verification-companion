"""Synthetic monitor observations; not RTL qualification evidence."""
from copy import deepcopy
from pathlib import Path
import unittest

from verification_evidence import EvidenceRecorder, load, catalog_digest, summarize
from verification_evidence.model import EvidenceError
from verification_evidence.scoreboard import Scoreboard, Comparison


def compare(expected, actual):
    value = actual['data']['bits']
    if any(c not in '01' for c in expected + value):
        return Comparison('inconclusive', 'explicit X/Z policy')
    return Comparison('pass' if expected == value else 'fail', 'independent predicted data')


def data(bits='0011'):
    return {'data': {'width': len(bits), 'bits': bits}}


class ScoreboardTests(unittest.TestCase):
    def board(self, **kwargs):
        bundle = load(Path(__file__).parent / 'fixtures/passing.json')
        cat = bundle.catalog
        original = cat.obligations[0]
        drain = deepcopy(original)
        drain.id, drain.bin_id = 'DRAIN', 'drain-bin'
        bin_ = deepcopy(cat.bins[0]); bin_.id = drain.bin_id
        cat.obligations.append(drain); cat.bins.append(bin_)
        manifest = bundle.runs[0].manifest
        manifest.compatibility.catalog_digest = catalog_digest(cat)
        rec = EvidenceRecorder(cat, manifest)
        options = dict(interface='dut', obligation=original.id, drain_obligation='DRAIN',
                       checker=original.checker_ids[0], predictor=lambda p: p['data']['bits'], comparator=compare)
        options.update(kwargs)
        return Scoreboard(rec, **options)

    def finish(self, board, tick=100):
        result = board.recorder.finish(pending_by_obligation=board.close(tick))
        return result, [c.reason for c in result.runs[0].checks if c.outcome == 'fail']

    def test_fifo_positive_and_correlated_evidence(self):
        b = self.board()
        b.request(data(), tick=1); b.request(data('1010'), tick=2)
        b.response(data(), tick=3); b.response(data('1010'), tick=4)
        bundle, failures = self.finish(b)
        self.assertFalse(failures)
        self.assertEqual(summarize(bundle)['gate'], 'pass')
        for check in bundle.runs[0].checks[:-1]:
            self.assertEqual(len(check.event_ids), 2)
        self.assertEqual(len(bundle.runs[0].coverage), len(bundle.runs[0].checks))

    def test_empty_drain_cannot_earn_matching_credit(self):
        bundle, _ = self.finish(self.board())
        self.assertEqual(summarize(bundle)['gate'], 'incomplete')

    def test_wrong_and_forbidden_fifo_reorder(self):
        b = self.board()
        b.request(data(), tick=1); b.request(data('1010'), tick=2)
        b.response(data('1010'), tick=3); b.response(data(), tick=4)
        bundle, failures = self.finish(b)
        self.assertEqual(len(failures), 2)
        self.assertEqual(summarize(bundle)['gate'], 'failed')

    def test_tagged_permitted_and_forbidden_reordering(self):
        for allow in (True, False):
            b = self.board(mode='tagged', allow_reordering=allow)
            b.request(data(), tick=1, tag=1); b.request(data('1010'), tick=2, tag=2)
            b.response(data('1010'), tick=3, tag=2); b.response(data(), tick=4, tag=1)
            _, failures = self.finish(b)
            self.assertEqual(bool(failures), not allow)
            if failures: self.assertIn('reordered', failures[0])

    def test_duplicate_id_does_not_overwrite_prediction(self):
        b = self.board(mode='tagged')
        b.request(data(), tick=1, tag='a')
        self.assertIsNone(b.request(data('1010'), tick=2, tag='a'))
        b.response(data(), tick=3, tag='a')
        b.response(data(), tick=4, tag='a')
        b.response(data(), tick=5, tag='unknown')
        _, failures = self.finish(b)
        self.assertEqual(len(failures), 3)
        self.assertIn('duplicate outstanding', failures[0])

    def test_deadline_boundary_late_response_and_missing(self):
        b = self.board(mode='tagged', allow_reordering=True)
        b.request(data(), tick=1, tag=1, deadline=5)
        b.request(data(), tick=2, tag=2, deadline=5)
        b.request(data(), tick=3, tag=3, deadline=5)
        b.advance(5)
        b.response(data(), tick=5, tag=1)
        b.advance(6); b.advance(7)
        self.assertEqual(len(b.pending), 2)
        self.assertEqual(sum(c.reason == 'response deadline expired' for c in b.recorder.run.checks), 2)
        b.response(data(), tick=8, tag=2)
        bundle, failures = self.finish(b)
        self.assertIn('response after deadline', failures)
        self.assertIn('missing response at final drain', failures)
        self.assertEqual(bundle.runs[0].finalization.pending_by_obligation, {'DRAIN': 1})

    def test_reset_cancels_without_credit_and_rejects_stale_epoch(self):
        b = self.board(mode='tagged')
        b.request(data(), tick=1, tag=1)
        b.reset(2)
        self.assertFalse(b.pending)
        b.request(data('1010'), tick=3, tag=1)
        b.response(data(), tick=4, tag=1, epoch=0)
        self.assertEqual(len(b.pending), 1)
        b.response(data('1010'), tick=5, tag=1, epoch=1)
        bundle, failures = self.finish(b)
        self.assertIn('response from another reset epoch', failures)
        for c in bundle.runs[0].checks:
            events = [e for e in bundle.runs[0].events if e.id in c.event_ids]
            self.assertEqual(len({e.epoch for e in events}), 1)
        b = self.board(); b.request(data(), tick=1); b.reset(2)
        bundle, _ = self.finish(b)
        self.assertEqual(summarize(bundle)['gate'], 'incomplete')

    def test_required_response_cannot_be_cancelled_silently(self):
        b = self.board(); b.request(data(), tick=1); b.reset(2, cancel=False)
        _, failures = self.finish(b)
        self.assertIn('reset interrupted required response', failures)

    def test_unknowns_preserved_and_no_mutation_aliasing(self):
        b = self.board(); payload = data('10xz')
        b.request(payload, tick=1); payload['data']['bits'] = '0000'
        b.response(data('10xz'), tick=2)
        bundle, _ = self.finish(b)
        self.assertEqual(bundle.runs[0].events[0].payload['data']['bits'], '10xz')
        self.assertEqual(bundle.runs[0].finalization.status, 'aborted')

    def test_stateful_memory_predictor_and_reset(self):
        memory = {}
        def predict(p):
            if p['op'] == 'write': memory[p['address']] = p['data']['bits']
            return memory.get(p['address'], '0000')
        b = self.board(predictor=predict, reset_predictor=memory.clear)
        b.request(dict(data('1010'), op='write', address=2), tick=1)
        b.response(data('1010'), tick=2)
        b.request(dict(data(), op='read', address=2), tick=3)
        b.response(data('1010'), tick=4)
        b.reset(5)
        b.request(dict(data(), op='read', address=2), tick=6)
        b.response(data('0000'), tick=7)
        bundle, failures = self.finish(b)
        self.assertFalse(failures)
        self.assertEqual(summarize(bundle)['gate'], 'pass')

    def test_bad_callbacks_cannot_leave_passing_evidence(self):
        def broken(_): raise RuntimeError('model unavailable')
        b = self.board(predictor=broken)
        with self.assertRaises(RuntimeError): b.request(data(), tick=1)
        bundle, _ = self.finish(b)
        self.assertNotEqual(summarize(bundle)['gate'], 'pass')
        b = self.board(comparator=lambda e, a: True)
        b.request(data(), tick=1)
        with self.assertRaises(EvidenceError): b.response(data(), tick=2)
        self.assertEqual(len(b.pending), 1)
        bundle, _ = self.finish(b)
        self.assertNotEqual(summarize(bundle)['gate'], 'pass')

    def test_invalid_time_tags_and_use_after_close(self):
        b = self.board(mode='tagged')
        for tag in (None, [], True, ''):
            with self.assertRaises(EvidenceError): b.request(data(), tick=1, tag=tag)
        b.request(data(), tick=2, tag=1)
        with self.assertRaises(EvidenceError): b.advance(1)
        with self.assertRaises(EvidenceError): b.advance(True)
        self.finish(b)
        with self.assertRaises(EvidenceError): b.request(data(), tick=101, tag=2)

    def test_prediction_snapshot_and_reset_failure(self):
        state = {'value': 1}
        b = self.board(predictor=lambda p: state,
                       comparator=lambda e, a: Comparison('pass' if e['value'] == 1 else 'fail', 'snapshot'))
        b.request(data(), tick=1)
        state['value'] = 2
        b.pending[0].expected['value'] = 3
        b.response(data(), tick=2)
        _, failures = self.finish(b)
        self.assertFalse(failures)
        def broken(): raise RuntimeError('reset failed')
        b = self.board(reset_predictor=broken)
        b.request(data(), tick=1)
        with self.assertRaises(RuntimeError): b.reset(2)
        self.assertEqual(len(b.pending), 1)
        _, failures = self.finish(b)
        self.assertIn('predictor reset failed', failures)

    def test_invalid_configuration_and_reset_policy(self):
        for options in ({'mode': 'unknown'}, {'allow_reordering': True},
                        {'predictor': None}, {'drain_obligation': 'OB-1'},
                        {'reset_predictor': False}, {'kind': 'unknown'},
                        {'allow_reordering': 'false', 'mode': 'tagged'}):
            with self.subTest(options=options), self.assertRaises(EvidenceError):
                self.board(**options)
        b = self.board()
        with self.assertRaises(EvidenceError): b.reset(1, cancel='false')


if __name__ == '__main__':
    unittest.main()
