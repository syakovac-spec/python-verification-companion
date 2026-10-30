"""Run the public synthetic workload and prepare an opt-in submission ZIP."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SIMULATORS = ('icarus', 'verilator', 'vcs', 'questa', 'xcelium', 'riviera')
METRICS = ('process_seconds', 'loop_seconds', 'monitor_seconds', 'checking_seconds',
           'finalize_seconds', 'summary_seconds', 'write_seconds', 'body_seconds',
           'peak_rss_kib', 'evidence_bytes', 'monitor_wakeups')
FIELDS = ('lanes', 'transactions', 'repeat', 'corrupt', 'returncode')
HASHES = ('semantic_sha256', 'stimulus_sha256')
README = '''Public benchmark submission v1

Attach this ZIP to a Benchmark results issue at:
https://github.com/syakovac-spec/python-verification-companion/issues/new/choose

Review submission.json before uploading. Nothing is uploaded automatically.
Only the supplied public synthetic RTL is exercised. Raw logs, commands, paths,
environment variables, license-server settings and full dependency inventories
are excluded. Tool versions are reduced to version tokens. Custom compiler flags
are represented only by a digest and a non-default indicator.

The archive contains self-reported measurements, not trusted/signoff evidence.
Smoke runs, missing/failed cases and noisy timings must not be ranked as passing
performance baselines. Report useful build/license/timing errors in the issue
after manually removing private details; do not attach the raw output directory.
'''


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def version(value):
    # Keep only a version token, never arbitrary vendor output or paths.
    match = re.search(r'\b(?:[A-Z]-)?\d+\.\d+(?:\.\d+)*(?:-SP\d+)?\b', str(value))
    return match.group() if match else 'unknown'


def public_report(directory, returncode=None):
    path = Path(directory) / 'report.json'
    if not path.exists():
        return dict(status='unavailable', returncode=returncode, environment={}, rows=[])
    report = json.loads(path.read_text())
    env = report.get('environment', {})
    tools = env.get('tools', {})
    simulator = tools.get('simulator')
    if simulator not in SIMULATORS:
        raise ValueError('unsupported simulator in report')
    safe_env = dict(simulator=simulator, python=version(tools.get('python')),
        cocotb=version(tools.get('cocotb')),
        simulator_version=version(tools.get({'icarus': 'iverilog', 'riviera': 'vsimsa',
            'questa': 'vsim', 'xcelium': 'xrun'}.get(simulator, simulator))),
        cpu_count=env.get('cpu_count') if type(env.get('cpu_count')) is int else None,
        source_digest=sha(env.get('sources', {})),
        flags_digest=sha([env.get('build_flags', []), env.get('test_flags', [])]),
        nondefault_flags=env.get('build_flags', []) != {'icarus': ['-g2012'],
            'verilator': ['--timing', '-Wno-fatal']}.get(simulator, []) or bool(env.get('test_flags')))
    rows = []
    for raw in report.get('rows', []):
        row = {k: raw[k] for k in FIELDS + METRICS if k in raw and number(raw[k])}
        row['variant'] = raw.get('variant') if raw.get('variant') in ('baseline', 'cached') else 'unknown'
        row['gate'] = raw.get('gate') if raw.get('gate') in ('pass', 'failed', 'incomplete', 'infrastructure_error') else 'unavailable'
        row['qualified'] = raw.get('qualified') is True
        row['rtl_load_checked'] = raw.get('rtl_load_checked') is True
        for key in HASHES:
            value = raw.get(key, '')
            if isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value):
                row[key] = value
        row['timing'] = {k: v for k, v in raw.get('timing', {}).items()
                         if k in ('build_seconds', 'test_seconds', 'total_seconds') and number(v)}
        rows.append(row)
    return dict(status='qualified' if report.get('qualified') is True and returncode in (None, 0) and rows and all(r['qualified'] for r in rows) else 'not_qualified',
                returncode=returncode, environment=safe_env, rows=rows)


def validate(data):
    if set(data) != {'schema_version', 'workload', 'profile', 'requested_simulator', 'packager_sha256', 'cases'} or type(data['schema_version']) is not int or data['schema_version'] != 1:
        raise ValueError('invalid submission envelope')
    if data['workload'] != 'public-stream-v1' or data['profile'] not in ('standard', 'smoke', 'custom'):
        raise ValueError('unknown workload/profile')
    if data['requested_simulator'] not in SIMULATORS + ('unknown',):
        raise ValueError('unknown requested simulator')
    if not re.fullmatch('[0-9a-f]{64}', data['packager_sha256']):
        raise ValueError('invalid runner digest')
    if set(data['cases']) != {'positive', 'corruption'}:
        raise ValueError('both case slots required, including unavailable cases')
    for case in data['cases'].values():
        if set(case) != {'status', 'returncode', 'environment', 'rows'} or case['status'] not in ('qualified', 'not_qualified', 'unavailable'):
            raise ValueError('invalid case')
        if case['returncode'] is not None and type(case['returncode']) is not int:
            raise ValueError('invalid returncode')
        env = case['environment']
        if env:
            if set(env) != {'simulator', 'python', 'cocotb', 'simulator_version', 'cpu_count', 'source_digest', 'flags_digest', 'nondefault_flags'}:
                raise ValueError('unexpected environment field')
            if env['simulator'] not in SIMULATORS or type(env['nondefault_flags']) is not bool:
                raise ValueError('invalid simulator/flags')
            if env['cpu_count'] is not None and type(env['cpu_count']) is not int:
                raise ValueError('invalid CPU count')
            for k in ('python', 'cocotb', 'simulator_version'):
                if not re.fullmatch(r'unknown|(?:[A-Z]-)?\d+\.\d+(?:\.\d+)*(?:-SP\d+)?', env[k]):
                    raise ValueError('invalid version token')
            for k in ('source_digest', 'flags_digest'):
                if not re.fullmatch('[0-9a-f]{64}', env[k]):
                    raise ValueError('invalid digest')
        for row in case['rows']:
            if set(row) - set(FIELDS + METRICS + HASHES + ('variant', 'gate', 'qualified', 'rtl_load_checked', 'timing')):
                raise ValueError('unexpected row field')
            for k in FIELDS + METRICS:
                if k in row and not number(row[k]):
                    raise ValueError('invalid numeric metric')
            if row['variant'] not in ('baseline', 'cached', 'unknown') or row['gate'] not in ('pass', 'failed', 'incomplete', 'infrastructure_error', 'unavailable'):
                raise ValueError('invalid row classification')
            if type(row['qualified']) is not bool or type(row['rtl_load_checked']) is not bool:
                raise ValueError('invalid row qualification')
            for k in HASHES:
                if k in row and not re.fullmatch('[0-9a-f]{64}', row[k]):
                    raise ValueError('invalid trace digest')
            if set(row['timing']) - {'build_seconds', 'test_seconds', 'total_seconds'} or not all(number(v) for v in row['timing'].values()):
                raise ValueError('invalid timing')
        if case['status'] == 'qualified' and (not env or not case['rows'] or not all(r['qualified'] for r in case['rows'])):
            raise ValueError('empty or failed case cannot qualify')
    return data


def package(positive, corruption, output, profile='custom', codes=(None, None), requested_simulator='unknown'):
    data = validate(dict(schema_version=1, workload='public-stream-v1', profile=profile,
        requested_simulator=requested_simulator,
        packager_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        cases=dict(positive=public_report(positive, codes[0]), corruption=public_report(corruption, codes[1]))))
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('submission.json', json.dumps(data, indent=2, allow_nan=False) + '\n')
        archive.writestr('README.txt', README)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sim', choices=SIMULATORS, default='vcs')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--smoke', action='store_true', help='short compatibility probe, not a performance baseline')
    parser.add_argument('--export', nargs=2, type=Path, metavar=('POSITIVE_DIR', 'CORRUPTION_DIR'))
    parser.add_argument('--validate', type=Path, metavar='ZIP')
    args = parser.parse_args()
    if args.validate:
        with zipfile.ZipFile(args.validate) as archive:
            if sorted(archive.namelist()) != ['README.txt', 'submission.json'] or sum(i.file_size for i in archive.infolist()) > 10_000_000:
                raise ValueError('unexpected archive contents or size')
            validate(json.loads(archive.read('submission.json')))
        print('Valid submission structure (self-reported results; not independently verified).')
        return 0
    if not args.out:
        parser.error('--out required')
    args.out.mkdir(parents=True, exist_ok=False)
    if args.export:
        directories, codes, profile = args.export, (None, None), 'custom'
    else:
        directories = [args.out / 'positive', args.out / 'corruption']
        codes = []
        profile = 'smoke' if args.smoke else 'standard'
        for i, directory in enumerate(directories):
            command = [sys.executable, str(ROOT / 'scripts/benchmark_simulation.py'), '--sim', args.sim,
                '--out', str(directory.resolve()), '--transactions', '24' if args.smoke else ('1000' if i == 0 else '100'),
                '--repeats', '1' if args.smoke or i else '3', '--lanes', '1']
            if not args.smoke and i == 0:
                command.append('1024')
            command += ['--corrupt', str(i)]
            print('Running', 'positive' if i == 0 else 'corruption', args.sim, flush=True)
            with (args.out / f'local-{i}.log').open('w') as log:
                codes.append(subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode)
    output = args.out / 'submission.zip'
    result = package(*directories, output, profile, codes, args.sim if not args.export else 'unknown')
    print(f'Review and submit only {output}; raw logs stay local. No upload performed.')
    return 0 if all(c['status'] == 'qualified' for c in result['cases'].values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
