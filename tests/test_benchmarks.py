import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('compare_benchmarks', Path(__file__).parents[1] / 'scripts/compare_benchmarks.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BenchmarkGateTests(unittest.TestCase):
    def report(self):
        metrics = {k: dict(median=1., samples=3, relative_spread=.1) for k in
                   ('loop_seconds', 'process_seconds', 'peak_rss_kib')}
        return dict(qualified=True, environment={k: 'same' for k in
            ('tools', 'dependencies', 'build_flags', 'test_flags', 'platform', 'cpu_count', 'waves', 'checks', 'seed')},
            rows=[dict(lanes=1, transactions=100, variant='baseline', corrupt=0, semantic_sha256='a', stimulus_sha256='b')],
            comparisons=[dict(lanes=1, baseline=copy.deepcopy(metrics), cached=copy.deepcopy(metrics))])

    def test_regression_detected(self):
        a, b = self.report(), self.report()
        self.assertEqual(module.compare(a, b)['gate'], 'pass')
        b['comparisons'][0]['cached']['loop_seconds']['median'] = 1.5
        self.assertEqual(module.compare(a, b)['gate'], 'failed')

    def test_noisy_or_incompatible_cannot_pass(self):
        for mutate in (lambda r: r['environment'].update(tools='other'),
                       lambda r: r['rows'][0].update(semantic_sha256='different'),
                       lambda r: r['comparisons'][0]['cached']['loop_seconds'].update(samples=1),
                       lambda r: r['comparisons'][0]['cached']['loop_seconds'].update(relative_spread=.5)):
            a, b = self.report(), self.report(); mutate(b)
            self.assertEqual(module.compare(a, b)['gate'], 'incomplete')
