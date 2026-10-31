# Build reuse and bounded regressions

EXT-03 adds an opt-in local build cache and parallel subprocess scheduling. The
evidence core remains independent of both. Cache hits save compilation; parallel
workers improve regression throughput, not the execution speed of one simulation.

## Run

```sh
python scripts/benchmark_simulation.py --sim icarus --out /tmp/regression-first \
  --transactions 100 --repeats 2 --lanes 1 --seeds 42 43 \
  --jobs 2 --cpu-slots 2 --memory-budget-mb 2048 --job-memory-mb 512 \
  --build-cache /tmp/pvc-build-cache

python scripts/benchmark_simulation.py --sim icarus --out /tmp/regression-next \
  --kit /tmp/regression-first/kit --transactions 100 --repeats 2 --lanes 1 \
  --seeds 44 45 --jobs 2 --build-cache /tmp/pvc-build-cache
```

Use `--kit` to reuse the generated source location across invocations. Absolute
source paths are intentionally part of the build key, so moving a generated kit
does not silently reuse a binary containing different embedded source paths.
Each seed has separate manifests, logs, XML, evidence and output directories.
The default remains one worker and no cache. `--timeout-seconds` bounds each
worker process group. SIGINT/SIGTERM stop active groups and retain aborted rows;
queued jobs are marked aborted instead of being launched.

`report.json` reports regression wall time, tests per second, worker budgets and
individual outcomes. `partial.json` is updated as results are collected. Timeouts,
aborts, launch failures, missing artifacts and failed/incomplete qualification are
retained and cannot pass the aggregate gate. Expected negative tests retain their
failed raw evidence gate while qualifying only if the intended checker fires.

## Resource budgets

The worker count is the minimum of requested jobs, CPU slots and the integer
memory-budget/per-job-estimate ratio. For commercial backends it is also bounded
by `--license-slots`, defaulting to one. These are admission budgets, not OS CPU
affinity, RSS enforcement or a query to the vendor license server. Account for
compiler/simulator internal threads and actual peak memory when setting estimates.
For example, `--jobs 8 --cpu-slots 4 --memory-budget-mb 2048
--job-memory-mb 1024 --license-slots 1` admits one commercial-simulator job.

The reusable `verification_evidence.regression.worker_limit` and `Processes`
helpers can also support application-specific command schedules. `Processes.run`
returns distinct launch-error, timed-out, aborted and finished outcomes; the
application must assess its simulator XML and evidence, not equate exit zero with
verification success. Linux process groups include the simulator's descendants.

## Cache identity and integrity

The shared simulation adapter accepts `--build-cache DIR` through its CLI helpers,
or `PVC_BUILD_CACHE=DIR`. This applies to the existing APB and stream runners too.
Python callers can supply explicit `includes` and `defines` to `simulation.run`.

Cache keys include ordered source paths/content, recursively resolved literal
Verilog includes, include paths, defines, top, parameters, backend/build flags,
tool versions and executable digests, Python identity, native build resources,
and an environment digest. Seeds are excluded from the build identity. The
environment digest avoids storing environment values in the cache descriptor.
Transient WSL connection and shell bookkeeping (`WSL_INTEROP`, `SHLVL`, `_`) are
also excluded; build-relevant environment changes still invalidate reuse.
Cocotb native resources, Icarus target libraries, and Verilator native resources
and C++ compiler are fingerprinted. Keep tool installations stable during a run.

A process lock serializes writers for one key. Successful builds are copied into
a staging entry and published only after artifact hashing; failed builds never
publish. Every hit verifies file hashes and copies the build into that run's
private directory. Simulation never writes into the shared cached build. Changed
sources/parameters/tools/options invalidate entries, and corrupted artifacts are
rebuilt. Changed source inputs during compilation prevent publication. Cache
entries with symlinks are rejected. Lock ownership ends if a process dies.

Use a trusted, user-owned cache on a local Linux filesystem. Network filesystems,
untrusted shared caches and concurrently patched tool installations are not
qualified. Cache binaries and descriptors may contain design information; they
are local artifacts, not public submission attachments. There is no automatic
eviction; remove a cache only while no jobs use it. Interrupted staging directories
are ignored and can be cleaned at that time.

## Supported boundary

Build reuse is initially qualified for Icarus and Verilator on Linux/WSL with the
adapter's default build flags, explicit defines/includes and no wave setting.
Verilator cache use requires `VERILATOR_ROOT` so native resources can be identified.
Macro-generated/unresolved include paths, additional raw compiler flags, unknown
native resources, wave settings and other backends bypass reuse and perform a
normal build. Bypass reasons are recorded in `timing.json`. This conservative
boundary avoids treating untracked file lists, libraries or response files as
unchanged inputs. Other simulator execution remains available; commercial build
reuse requires its own relocation and dependency qualification.

`timing.json.cache` records hit/miss/bypass/disabled and the cache key when used.
Its build time includes identity hashing, lock wait and artifact copying, so a hit
is not free and may cost more than compiling a tiny design. Do not infer savings
from hit count alone. Benchmark comparison rejects differing worker/cache settings;
public submission archives retain those settings without exposing cache paths.

## Storage and measurement

Use Linux-native output/cache directories to measure their effect separately from
Windows-mounted WSL directories. Keep source paths, seed, simulator and workload
fixed; change only the output location. OS file cache state and host contention
still vary. Record complete regression throughput alongside build and test times.
This work does not establish a universal cache speedup or change the EXT-02 noise
gate. Exact measured results and qualification limits are recorded in STATUS.md
and evidence/cache-regression-summary.json.

Local qualification on 2026-10-30 used Python 3.11.18, Icarus 13 and cocotb 2.1.0.
Each main batch contains four 100-transaction tests with identical semantic hashes:

| Batch | Workers | Cache results | Batch seconds |
| --- | ---: | --- | ---: |
| Linux-native output, no cache | 1 | disabled | 40.73 |
| Cold cache | 1 | 1 miss, 3 hits | 50.70 |
| Warm cache | 1 | 4 hits | 69.46 |
| Warm cache | 2 | 4 hits | 19.73 |
| Windows-mounted output, no cache | 1 | disabled | 47.81 |

Host variability was substantial; these are descriptive batches, not a stable
speedup ratio. Cache hashing/copying did not pay off for this tiny Icarus design.
The storage comparison moves build/artifact outputs only: source and Python
environment remain on the Windows mount. A larger representative design and
repeated quiet-host measurements are needed before making deployment predictions.

Additional qualification includes four seed-43/44 cache hits, Verilator 5.052
concurrent builds (one miss/three hits), parameter-corruption invalidation with
ORDER detection, two retained forced timeouts, cocotb 1.9.2 plain/pyuvm positive
and negative stream cases, and an APB cache-hit replay reproducing pins, samples
and checker records exactly. Unit tests cover include/parameter/tool invalidation,
corrupt entries, failed builds, concurrent publication, isolated copies, admission
budgets and process cancellation. Both platforms pass 82 tests (three Linux-only
tests skipped on Windows). Commercial simulator execution remains unqualified here.
