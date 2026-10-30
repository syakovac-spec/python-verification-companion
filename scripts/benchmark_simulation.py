"""Repeatable checked simulation benchmarks; see docs/22_PERFORMANCE_BENCHMARKS.md."""
import argparse
from dataclasses import asdict
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import signal
import statistics
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET

from verification_evidence import simulation
from verification_evidence.scaffold import create_agent
from verification_evidence.model import Compatibility, Manifest, catalog_digest

ROOT = Path(__file__).resolve().parents[1]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def stats(values):
    return dict(median=statistics.median(values), minimum=min(values), maximum=max(values),
                samples=len(values), relative_spread=(max(values)-min(values))/statistics.median(values)
                if statistics.median(values) else 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    simulation.configure(parser)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--transactions', type=int, default=1000)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--lanes', type=int, nargs='+', default=[1, 1024])
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--kit', type=Path)
    parser.add_argument('--variant', choices=['baseline', 'cached'], default='baseline')
    parser.add_argument('--corrupt', type=int, choices=[0, 1], default=0)
    args = parser.parse_args()
    if sys.platform != 'linux':
        parser.error('simulation RSS measurement currently requires Linux or WSL')
    simulation.select(args)
    if args.transactions < 24 or args.repeats < 1 or any(n < 1 or n > 65536 for n in args.lanes):
        parser.error('transactions >= 24, repeats >= 1, lanes in 1..65536 required')
    out = args.out.resolve()
    if args.worker:
        simulation.run(sources=[args.kit / 'rtl/stream_top.sv'], top='stream_top',
            parameters={'LANES': args.lanes[0], 'CORRUPT': args.corrupt}, out=out,
            module='test_benchmark', test_dir=args.kit,
            extra_env={'STREAM_OUT': str(out), 'BENCH_TRANSACTIONS': str(args.transactions),
                       'BENCH_VARIANT': args.variant, 'BENCH_LANES': str(args.lanes[0])})
        return 0
    out.mkdir(parents=True, exist_ok=False)
    kit = out / 'kit'
    create_agent(ROOT / 'interfaces/packet16.json', kit)
    (kit / 'test_benchmark.py').write_bytes((ROOT / 'benchmarks/test_benchmark.py').read_bytes())
    rtl = kit / 'rtl/stream_top.sv'
    source = rtl.read_text().replace('parameter integer CORRUPT = 0', 'parameter integer CORRUPT = 0, parameter integer LANES = 1')
    source = source.replace('endmodule', (ROOT / 'benchmarks/load.sv.inc').read_text() + '\nendmodule')
    rtl.write_text(source)
    sys.path.insert(0, str(kit))
    from model import plan
    from coverage_plan import PROFILE
    sources = {str(p.relative_to(kit)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in kit.rglob('*') if p.is_file() and p.suffix in ('.py', '.sv', '.json')}
    import verification_evidence
    sources.update({'core/' + p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in Path(verification_evidence.__file__).parent.glob('*.py')})
    tools = simulation.identity()
    dependencies = {d.metadata['Name']: d.version for d in metadata.distributions()}
    environment = dict(python=sys.version, platform=platform.platform(), processor=platform.processor(),
                       cpu_count=os.cpu_count(), build_flags=simulation.build_flags(),
                       test_flags=json.loads(os.environ.get('PVC_TEST_ARGS', '[]')),
                       dependencies=dependencies, tools=tools, sources=sources,
                       build_policy='fresh directory and rebuild per sample; OS file cache uncontrolled',
                       waves=False, checks=True, seed=42)
    (out / 'environment.json').write_text(json.dumps(environment, indent=2))
    rows = []
    for lanes in args.lanes:
        for repeat in range(args.repeats):
            # Alternate order to reduce systematic first-run bias.
            variants = ['baseline', 'cached'] if repeat % 2 == 0 else ['cached', 'baseline']
            for variant in variants:
                target = out / f'lanes-{lanes}-repeat-{repeat}-{variant}'
                target.mkdir()
                config = dict(lanes=lanes, transactions=args.transactions, variant=variant, corrupt=args.corrupt)
                cat = plan(digest(sources))
                cmd = [sys.executable, str(Path(__file__).resolve()), '--worker', '--out', str(target),
                       '--kit', str(kit), '--sim', args.sim, '--lanes', str(lanes),
                       '--transactions', str(args.transactions), '--variant', variant, '--corrupt', str(args.corrupt)]
                manifest = Manifest(str(uuid.uuid4()), Compatibility(1, catalog_digest(cat),
                    sources['rtl/stream_top.sv'], digest(config), PROFILE, digest(tools), digest(sources),
                    'benchmark-v1'), 1000, digest(sources), digest(dependencies), tools, {'traffic': '42'}, cmd, [], '')
                (target / 'manifest.json').write_text(json.dumps(asdict(manifest)))
                start = time.perf_counter()
                with (target / 'process.log').open('w') as log:
                    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                    try:
                        returncode = proc.wait(timeout=1800)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait()
                        returncode = -1
                row = dict(config, repeat=repeat, process_seconds=time.perf_counter()-start,
                           returncode=returncode, qualified=False, directory=target.name)
                try:
                    row.update(json.loads((target / 'metrics.json').read_text()))
                    row['timing'] = json.loads((target / 'timing.json').read_text())
                    if 'test_seconds' in row['timing']:
                        row['startup_shutdown_residual_seconds'] = row['timing']['test_seconds'] - row['body_seconds']
                    row['transactions_per_loop_second'] = args.transactions / row['loop_seconds']
                    cases = list(ET.parse(target / 'results.xml').getroot().iter('testcase'))
                    failures = sum(c.find('failure') is not None or c.find('error') is not None for c in cases)
                    row['qualified'] = (returncode in ((0, 1) if args.corrupt else (0,)) and len(cases) == 1 and failures == args.corrupt
                        and row['gate'] == ('failed' if args.corrupt else 'pass')
                        and row['failed'] == (['ORDER'] if args.corrupt else [])
                        and row['rtl_load_checked'])
                    if args.corrupt:
                        row['qualified'] &= 'BENCH_CHECK_FAILURE' in (target / 'process.log').read_text()
                except (OSError, ValueError, ET.ParseError, KeyError) as exc:
                    row['error'] = str(exc)
                rows.append(row)
                (out / 'partial.json').write_text(json.dumps(rows, indent=2))
                print(json.dumps(row), flush=True)
    comparisons = []
    for lanes in args.lanes:
        selected = [r for r in rows if r['lanes'] == lanes]
        fingerprints = {r.get('semantic_sha256') for r in selected}
        equivalent = len(fingerprints) == 1 and None not in fingerprints
        item = dict(lanes=lanes, semantic_equivalence=equivalent)
        for variant in ('baseline', 'cached'):
            group = [r for r in selected if r['variant'] == variant and r['qualified']]
            item[variant] = {key: stats([r[key] for r in group]) for key in
                            ('loop_seconds', 'monitor_seconds', 'checking_seconds', 'finalize_seconds',
                             'summary_seconds', 'write_seconds', 'process_seconds', 'peak_rss_kib') } if group else {}
        comparisons.append(item)
    result = dict(qualified=all(r['qualified'] for r in rows) and all(c['semantic_equivalence'] for c in comparisons),
                  environment=environment, rows=rows, comparisons=comparisons,
                  limitations=['Synthetic RTL workload, not a customer design.',
                    'RTL/VPI/scheduler residual is not pure native RTL time.',
                    'Peak RSS is simulator process high-water mark, not total concurrent process-tree memory.',
                    'Startup/shutdown residual includes cocotb import and runner overhead; not independently traced.'])
    (out / 'report.json').write_text(json.dumps(result, indent=2))
    return 0 if result['qualified'] else 1


if __name__ == '__main__':
    sys.exit(main())
