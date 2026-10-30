# Checked performance and scalability benchmarks

EXT-02 adds a repeatable Linux/WSL benchmark harness and an evidence profiler.
The benchmark uses the active Python/conda interpreter and the shared simulator
adapter. It does not require Icarus and does not change simulator implementations.

## Run

Install the simulation extra and select an available simulator. Use a new output
directory per invocation; Linux-native storage such as `/tmp` avoids mixing WSL
mounted-filesystem overhead into artifact writes.

```sh
python scripts/benchmark_simulation.py --sim icarus --out /tmp/bench-icarus \
  --transactions 1000 --repeats 3 --lanes 1 1024
python scripts/benchmark_simulation.py --sim verilator --out /tmp/bench-verilator \
  --transactions 1000 --repeats 3 --lanes 1 1024
python scripts/benchmark_simulation.py --sim icarus --out /tmp/bench-negative \
  --transactions 100 --repeats 1 --lanes 1 --corrupt 1
```

The 16-bit generated stream carries the same seeded traffic under deterministic
backpressure in every variant. Each added RTL lane contains a 32-bit accumulator;
all lanes contribute to a visible checksum independently checked against the
observed step count. This is synthetic scalable RTL activity, not a customer
design or a proxy for all large designs. Increase transactions for longer runs or
lane count to explore simulator sensitivity; large evidence stays in memory.

Baseline monitor sampling resolves signal handles on every edge. The cached
variant resolves those handles once. Both read the same HDL acceptance snapshots
after ReadOnly and feed the same scoreboard and coverage plan. Neither disables
checks or waves selectively: all runs have checks enabled and waves disabled.
The optimization is a benchmark prototype, not a switch silently applied to every
generated agent. Variant order alternates across repeats. Every sample recompiles
in a fresh directory; operating-system file caches are uncontrolled, so these
are fresh-build measurements, not guaranteed cold-cache measurements.

## Measurements and correctness gates

`report.json` includes individual samples, medians, min/max and relative spread;
`environment.json` records tools and executable digests, dependencies, source
digests, flags, seed and host information. Each run retains stimulus, manifest,
raw bundle, metrics, timing, simulator XML and process log. `partial.json` retains
completed and failed samples as the sequence proceeds.

Measured wall-clock scopes:

- Build time from the shared adapter, including runner setup and compilation.
- Test-process time from the adapter, including startup, simulation and shutdown.
- Simulation-loop wall time, monitor reads, and synchronous checking/recording.
- Finalization/validation, summary calculation, and evidence serialization/write.
- Simulator-process peak RSS in KiB, including Python and evidence processing.

The loop residual contains RTL execution, VPI, cocotb scheduling, driver activity
and measurement overhead. It is **not** pure native RTL execution time. Test time
minus measured body time includes imports/startup/shutdown/runner overhead; these
are not independently traced. VCS currently supplies combined build/test timing.
Peak RSS is not summed process-tree memory and does not measure compiler memory.
Timers and semantic hashing introduce overhead; these are instrumented workloads.

A positive sample must close the coverage gate, pass the synthetic RTL checksum,
and pass exactly one simulator test. A corruption sample must fail ORDER and the
simulator test while still passing the load checksum. Missing artifacts, process
timeouts and infrastructure errors cannot qualify. All repetitions and both
monitor variants must have identical ordered observations, checks, coverage and
finalization after removing only the run ID. Stimulus hashes are also recorded.

## Evidence and constraint profiling

```sh
python scripts/profile_evidence.py /tmp/bench-icarus/lanes-1-repeat-0-baseline/bundle.json \
  --out /tmp/evidence-profile --repeats 5
python scripts/profile_evidence.py /tmp/bench-icarus/lanes-1-repeat-0-baseline/bundle.json \
  --out /tmp/evidence-cprofile --cprofile /tmp/evidence.prof
python scripts/profile_constraints.py --iterations 200 --solver boolector \
  --out /tmp/boolector.json
python scripts/profile_constraints.py --iterations 200 --solver dv-solve \
  --out /tmp/dvsolve.json
```

Use separate unprofiled runs for speed comparisons: cProfile changes timing.
The evidence profiler preserves an exact input digest, canonical evidence and
summary hashes, and verifies serialization round-trip equality. The existing
constraint profiler measures import/construction, randomize calls (including
native solver work), legality and an expected unsatisfiable rejection. These
solver timings are separate from the stream benchmark's simple bounded RNG;
they must not be added together as if measured in one testbench.

Profiling identified repeated whole-tree dataclass copies in canonicalization.
The core now traverses dataclass fields directly while retaining canonical JSON,
unknown-value preservation, validation, and closure semantics. The old behavior
can be reproduced from commit `69ae7fe` in a separate checkout and run against the
same input bundle. Do not mix two installed package copies unknowingly; the
profiler records the loaded model source digest.

## Local regression gate

```sh
python scripts/compare_benchmarks.py /tmp/baseline/report.json /tmp/candidate/report.json
```

The initial investigation thresholds are 25% median loop/process-time regression
or 15% simulator peak-RSS regression. These are configurable in the comparison
function and are local investigation triggers, not universal performance SLAs.
The gate requires at least three samples and relative spread at most 20% for each
compared metric. Noisy runs, different environments, or different checked
observations return incomplete (exit 3); a regression/qualification failure exits
1; pass exits 0. Re-run noisy samples on an idle, consistent host before changing
thresholds. Source changes remain auditable in both reports and are allowed when
the workload, stimulus, and checked semantic output remain identical.

## Remaining qualification

A licensed VCS baseline and a representative customer RTL design are unavailable
locally. No claim of being within 2x VCS follows from these measurements. Exact
native RTL versus VPI attribution and compiler/process-tree peak memory need
backend-specific tracing. HDL transaction batching is deferred until measurements
justify its complexity; cached handles test the cheaper option first. Build-cache
reuse and regression parallelism remain EXT-03, separate from single-test speed.

## Recorded results - 2026-10-30

All 28 main simulation qualifications passed their expected outcomes: 24 positive
samples and four deliberate-corruption cases across Icarus 13 and Verilator 5.052,
Python 3.11.18 and cocotb 2.1.0. The 71-test unit suite passed on Windows Python
3.10.7 and Linux Python 3.11.18. Full samples and source/tool identities are in
[evidence/performance-summary.json](../evidence/performance-summary.json).

| Workload (1,000 transfers) | Icarus baseline loop | Verilator baseline loop |
| --- | ---: | ---: |
| 1 active RTL lane | 0.554 s | 0.434 s |
| 1,024 active RTL lanes | 19.095 s | 0.503 s |

These are three-repeat medians, not general simulator rankings. Full process
medians include build/startup/evidence costs: respectively 13.61/14.66 seconds for
one lane and 33.37/14.41 seconds for 1,024 lanes. Cached handles reduced Icarus
small-workload monitor time from 0.119 to 0.069 seconds, but large-workload loop
time changed only from 19.095 to 18.903 seconds. The RTL-heavy case needs a different
optimization than Python handle lookup.

On the exact same 1,000-transfer evidence bundle, five unprofiled before/after
repeats measured validation at 1.546/1.123 seconds, summary at 2.209/1.770 seconds,
and writing at 0.647/0.430 seconds: reductions of 27.4%, 19.9%, and 33.6%.
Load time was effectively unchanged (0.433/0.439 seconds). Both core versions
produced identical canonical evidence and summary hashes and round-trip results.

Solver median milliseconds per draw (200 draws per class): Boolector versus
dv-solve was 1.703/0.769 for weighted addresses, 3.112/1.093 for targeted bits,
and 0.942/0.248 for reset constraints. Both passed legality and rejected the
unsatisfiable case. Startup/import and first-call costs are retained separately;
these results do not select a universally fastest solver.

Both simulation reports contain a loop-time group with more than 20% spread.
Consequently the performance regression gate returns **incomplete**, even when
comparing a report with itself. Correctness qualification passed; a stable
performance regression baseline has not yet been established. The descriptive
medians above must not be treated as guaranteed speedups or relaxed thresholds.
