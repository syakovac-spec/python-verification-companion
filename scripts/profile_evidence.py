"""Profile public evidence operations on the same recorded workload."""
import argparse
import cProfile
import hashlib
import json
from pathlib import Path
import platform
import statistics
import time
from verification_evidence.model import load, dump, canonical
from verification_evidence.core import validate, summarize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--cprofile', type=Path)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error('repeats must be positive')
    args.out.mkdir(parents=True, exist_ok=False)
    samples = []
    profile = cProfile.Profile() if args.cprofile else None
    if profile:
        profile.enable()
    for _ in range(args.repeats):
        row = {}
        start = time.perf_counter(); bundle = load(args.bundle)
        row['load_seconds'] = time.perf_counter() - start
        start = time.perf_counter(); validate(bundle)
        row['validate_seconds'] = time.perf_counter() - start
        start = time.perf_counter(); summary = summarize(bundle)
        row['summarize_seconds'] = time.perf_counter() - start
        start = time.perf_counter(); dump(bundle, args.out / 'roundtrip.json')
        row['write_seconds'] = time.perf_counter() - start
        samples.append(row)
    if profile:
        profile.disable(); profile.dump_stats(str(args.cprofile))
    assert canonical(load(args.out / 'roundtrip.json')) == canonical(bundle)
    import verification_evidence.model as model
    result = dict(python=platform.python_version(), samples=samples,
        median={k: statistics.median(r[k] for r in samples) for k in samples[0]},
        input_sha256=hashlib.sha256(args.bundle.read_bytes()).hexdigest(),
        model_source_sha256=hashlib.sha256(Path(model.__file__).read_bytes()).hexdigest(),
        semantic_sha256=hashlib.sha256(canonical(bundle).encode()).hexdigest(),
        summary_sha256=hashlib.sha256(json.dumps(summary, sort_keys=True).encode()).hexdigest(),
        gate=summary['gate'], profiled=bool(profile), roundtrip_equal=True)
    (args.out / 'report.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
