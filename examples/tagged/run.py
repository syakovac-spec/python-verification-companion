"""Qualify tagged matching against real reordered RTL outputs and counterexamples."""
import argparse
from dataclasses import asdict
import hashlib
from importlib import metadata
import json
from pathlib import Path
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from verification_evidence import simulation, load, summarize, catalog_digest
from verification_evidence.model import Manifest, Compatibility, Artifact
from contract import plan

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def run_one(root, name, corrupt, drop, reorder):
    out = root/name; out.mkdir()
    sources = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in [*HERE.glob('*.py'), *HERE.glob('rtl/*.sv'),
                         *(ROOT/'src/verification_evidence').glob('*.py')]}
    tools = simulation.identity()
    config = dict(corrupt=corrupt, drop=drop, allow_reordering=reorder,
                  build_flags=simulation.build_flags())
    deps = {d.metadata['Name']: d.version for d in metadata.distributions()}
    inputs = dict(sources=sources, configuration=config, tools=tools, dependencies=deps)
    (out/'inputs.json').write_text(json.dumps(inputs, indent=2))
    checker = digest(sources)
    command = [sys.executable, str(HERE/'run.py'), '--worker', '--out', str(out),
               '--sim', simulation.simulator()]
    manifest = Manifest(str(uuid.uuid4()), Compatibility(1, catalog_digest(plan(checker)),
        sources['examples/tagged/rtl/tagged_top.sv'], digest(config), 'tagged', digest(tools),
        checker, 'tagged-snapshot-v1'), 10_000_000, checker, digest(deps), tools, {}, command,
        [Artifact('inputs.json', hashlib.sha256((out/'inputs.json').read_bytes()).hexdigest())], '')
    (out/'manifest.json').write_text(json.dumps(asdict(manifest), indent=2))
    row = dict(case=name, qualified=False, gate='infrastructure_error', tools=tools)
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=180)
        (out/'stdout.log').write_text(result.stdout); (out/'stderr.log').write_text(result.stderr)
        bundle = load(out/'bundle.json')
        gate = summarize(bundle)['gate']
        checks = bundle.runs[0].checks
        failures = sorted({c.obligation_id for c in checks if c.outcome == 'fail'})
        reasons = sorted({c.reason for c in checks if c.outcome == 'fail'})
        cases = list(ET.parse(out/'results.xml').getroot().iter('testcase'))
        failed_tests = sum(c.find('failure') is not None or c.find('error') is not None for c in cases)
        expected = ['DRAIN', 'MATCH'] if drop else ['MATCH'] if corrupt or not reorder else []
        sensitive = (not drop or 'response deadline expired' in reasons) and (
            reorder or 'response reordered when forbidden' in reasons)
        qualified = (result.returncode in (0, 1) and len(cases) == 1 and
                     failed_tests == bool(expected) and failures == expected and sensitive and
                     gate == ('failed' if expected else 'pass'))
        if expected: qualified &= 'TAGGED_CHECK_FAILURE' in result.stdout
        row.update(qualified=bool(qualified), gate=gate, failed=failures, reasons=reasons)
    except (OSError, ValueError, ET.ParseError, subprocess.TimeoutExpired) as exc:
        row['error'] = str(exc)
    print(json.dumps(row), flush=True)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', action='store_true'); parser.add_argument('--out', type=Path)
    simulation.configure(parser)
    args = parser.parse_args(); simulation.select(args)
    if args.worker:
        config = json.loads((args.out/'inputs.json').read_text())['configuration']
        simulation.run(sources=[HERE/'rtl/tagged_top.sv'], top='tagged_top',
            parameters={'CORRUPT': config['corrupt'], 'DROP': config['drop']}, out=args.out,
            module='test_tagged', test_dir=HERE, extra_env={'TAGGED_OUT': str(args.out)})
        return 0
    out = (args.out or ROOT/'evidence/tagged'/str(uuid.uuid4())).resolve()
    out.mkdir(parents=True, exist_ok=False)
    cases = [('reordered', 0, 0, True), ('wrong-data', 1, 0, True),
             ('forbidden-reorder', 0, 0, False), ('missing', 0, 1, True)]
    rows = [run_one(out, *case) for case in cases]
    result = dict(qualified=all(r['qualified'] for r in rows), runs=rows)
    (out/'qualification.json').write_text(json.dumps(result, indent=2)+'\n')
    print(str(out/'qualification.json'))
    return 0 if result['qualified'] else 1


if __name__ == '__main__':
    sys.exit(main())
