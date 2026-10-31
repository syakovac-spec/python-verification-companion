# Submit public benchmark results

Exports retain worker count, cache-enabled status and per-row seeds when available.
Version 1 archives without these optional fields remain valid. Use the harness in
[build reuse and regressions](24_BUILD_CACHE_AND_REGRESSIONS.md) for custom parallel
or cached runs, then export those directories. Compare like-for-like settings.

Commercial simulator users can help improve backend compatibility and performance
by running the same public synthetic RTL and submitting a small results archive.
No customer RTL, encrypted IP, account credentials or network service is required.
Use your existing Linux/WSL Python or conda environment and licensed simulator.

## Run and submit

From an updated checkout, install `python -m pip install -e '.[simulation]'`, then:

```sh
python scripts/public_benchmark.py --sim vcs --out /tmp/pvc-public-vcs
python scripts/public_benchmark.py --validate /tmp/pvc-public-vcs/submission.zip
```

Select `questa`, `xcelium`, `riviera`, `icarus` or `verilator` instead as appropriate.
The wrapper uses the existing backend adapter; naming a backend does not imply it
has been locally qualified. Keep required license and tool environment settings
in your shell. Existing PVC_BUILD_ARGS/PVC_TEST_ARGS JSON arrays are inherited.
VCS's current backend records combined build/test time; missing split metrics are
not treated as zero. The benchmark remains Linux/WSL-only for RSS measurement.

The standard run executes 12 positive samples (1,000 transfers, three repetitions,
one/1,024 RTL lanes, two monitor variants) and two deliberate-corruption cases.
For a quick installation/compatibility probe:

```sh
python scripts/public_benchmark.py --sim vcs --smoke --out /tmp/pvc-vcs-smoke
```

Smoke mode executes four short cases and labels the submission `smoke`; it is not
a performance baseline. A missing simulator, failed compile, or failed checker
still produces a results ZIP when the wrapper completes. Exit 1 means some cases
did not qualify; retain and submit that result to help diagnose incompatibilities.
An interrupted wrapper may require the export command below.

Open `submission.zip` and review `submission.json`. Then attach **only that ZIP**
to a [Benchmark results issue](https://github.com/syakovac-spec/python-verification-companion/issues/new/choose).
Include the repository commit, CPU model/RAM, OS, virtualization and host-load
context requested by the form. Make sure your organization and simulator terms
permit public sharing of the measurements. Nothing uploads automatically.

## Existing results and data boundary

Existing benchmark directories can be packaged without rerunning simulation:

```sh
python scripts/public_benchmark.py --export /tmp/bench-positive /tmp/bench-negative \
  --out /tmp/pvc-export
```

These archives are labeled `custom`. Each ZIP contains exactly `submission.json`
and `README.txt`. The version-1 allowlist retains numeric timing/memory/case data,
qualification status, selected tool-version tokens, CPU count, workload/source,
stimulus and semantic hashes. Flags are represented by a digest and a non-default
indicator; share their relevant meaning manually after review. It excludes raw
logs, error text, paths, commands, full dependency inventories, environment
variables, hostnames and license-server settings. No proprietary design is needed
for this workload. Sanitization is deliberately restrictive, but review the archive
before sharing it. Keep the raw directory locally for follow-up investigation.

## Maintainer triage

1. Validate the archive with `--validate`; this checks structure, bounded archive
   size and allowed fields, not authenticity or correctness of user claims. Do not
   execute submitted files; the validator reads JSON without extracting the ZIP.
2. Separate standard, smoke and custom profiles. Preserve unavailable/failed cases;
   inspect sanitized failure details separately. A fully failed startup can have
   no tool identity, so use the issue's simulator/version description.
3. Group by workload/source digest, flags digest, simulator/version, Python and
   cocotb version, plus hardware/context from the issue. Do not rank unlike hosts
   or combine VCS total time with another backend's loop-only time.
4. Compare individual repetitions, semantic/stimulus hashes, gates and expected
   corruption results before examining timing medians. Require three stable
   repetitions for performance claims; preserve noise/incomplete status as in
   [the benchmark guide](22_PERFORMANCE_BENCHMARKS.md).
5. Reproduce a compatibility issue on an available licensed setup before claiming
   a commercial backend fix. Public submissions provide useful evidence but are
   self-reported and do not replace local qualification.

The current synthetic workload targets plain-cocotb sampling, independent checking
and evidence costs. It does not benchmark all pyuvm features, customer designs,
encrypted models or native simulator assertions. Constraint-solver profiling
remains available separately in the benchmark guide.
