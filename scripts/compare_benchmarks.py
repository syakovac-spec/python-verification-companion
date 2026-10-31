"""Conservative local regression gate; incompatible or noisy samples are incomplete."""
import argparse
import json
from pathlib import Path


def compare(baseline, current, runtime_limit=1.25, memory_limit=1.15):
    if not baseline['rows'] or not current['rows'] or not baseline['comparisons'] or len(baseline['comparisons']) != len(current['comparisons']):
        return {'gate': 'incomplete', 'reason': 'missing or unequal workload groups'}
    if not baseline['qualified'] or not current['qualified']:
        return {'gate': 'failed', 'reason': 'benchmark qualification failed'}
    for key in ('tools', 'dependencies', 'build_flags', 'test_flags', 'platform', 'cpu_count', 'waves', 'checks', 'seed', 'workers', 'cache_enabled'):
        if baseline['environment'].get(key) != current['environment'].get(key):
            return {'gate': 'incomplete', 'reason': f'environment mismatch: {key}'}
    def keys(report):
        return {(r['lanes'], r['transactions'], r['variant'], r['corrupt'], r['semantic_sha256'], r['stimulus_sha256']) for r in report['rows']}
    if keys(baseline) != keys(current):
        return {'gate': 'incomplete', 'reason': 'workload or checked evidence differs'}
    changes = []
    for before, after in zip(baseline['comparisons'], current['comparisons']):
        if before['lanes'] != after['lanes']:
            return {'gate': 'incomplete', 'reason': 'workload order differs'}
        for variant in ('baseline', 'cached'):
            for metric, limit in [('loop_seconds', runtime_limit), ('process_seconds', runtime_limit), ('peak_rss_kib', memory_limit)]:
                a, b = before[variant][metric], after[variant][metric]
                if min(a['samples'], b['samples']) < 3 or max(a['relative_spread'], b['relative_spread']) > .20:
                    return {'gate': 'incomplete', 'reason': f'need >=3 stable samples: {metric}'}
                ratio = b['median'] / a['median']
                changes.append(dict(lanes=before['lanes'], variant=variant, metric=metric, ratio=ratio, limit=limit))
    return {'gate': 'failed' if any(c['ratio'] > c['limit'] for c in changes) else 'pass', 'comparisons': changes}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('baseline', type=Path)
    parser.add_argument('current', type=Path)
    args = parser.parse_args()
    result = compare(json.loads(args.baseline.read_text()), json.loads(args.current.read_text()))
    print(json.dumps(result, indent=2))
    return {'pass': 0, 'failed': 1, 'incomplete': 3}[result['gate']]


if __name__ == '__main__':
    raise SystemExit(main())
