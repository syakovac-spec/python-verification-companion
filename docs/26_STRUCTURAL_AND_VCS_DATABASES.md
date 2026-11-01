# HDL structural coverage and VCS databases

There are three separate capabilities:

| Capability | Status |
| --- | --- |
| Export real Verilator line/basic-block and directional-toggle counters to UCIS XML | Executed and round-trip tested locally |
| Instrument DUT runs to let VCS create native structural VDB data | Implemented command path; VCS execution unavailable locally |
| Convert checked functional counts into a VCS-owned native VDB using generated SV covergroups | Implemented source generator/runner; native compilation/database content unqualified locally |

No SQLite/ZIP/XML file is relabeled as a vendor database. Only VCS may create the
`.vdb` outputs. A created directory alone does not establish correct native bin
contents: writer results remain `native_created_unverified` until checked with
the installed vendor API or UCIS re-export. VCS, its license and coverage tools
must be available in the user's environment. Other vendor binary writers are
not implemented.

## Structural UCIS export

Use real Verilator `SystemC::Coverage-3` output, produced with line and toggle
instrumentation. Pass the root against which its source filenames resolve:

```sh
vevidence export-structural coverage.dat --output structural-export \
  --source-root . --run-id regression-42 --run-status pass \
  --tool-version 'Verilator 5.052'
vevidence validate-structural structural-export
```

The caller supplies the recorded run status; native hit counts cannot prove that
the test passed. Failed/incomplete tests retain their structural hits and explicit
status. No structural counter earns checked functional coverage credit.

The output contains `coverage.xml`, the untouched `native.dat`, and
`structural.json` with original attributes, source hashes, run status, metric
totals and artifact hashes. Source hashes describe the supplied source files;
keep them matched to the compiled revision. Existing outputs are never overwritten.

Mapping:

- Verilator `line` records become UCIS block/statement counters. They measure
  instrumented basic blocks, not every physical source line. Separate records on
  the same line remain distinct. The native source span/column and full metadata
  remain in the companion JSON.
- Explicit `signal:0->1` and `signal:1->0` records become separate UCIS toggle
  transition counts for the instrumented bit. Zero-hit directions remain present.
  Directionless aggregate toggles are rejected; the converter never invents
  directional counts.
- Unknown records/metrics, malformed lines, empty inputs and duplicate identities
  are rejected. Branch, condition/expression, FSM, assertion and covergroup records
  are not silently converted into line coverage. Collect only supported metrics
  for this exporter; other native metrics require a separate qualified adapter.
- Structural hierarchy is kept separate from functional scopes. Identity includes
  source content hashes. Raw hierarchy and signal names remain in source metadata.

For external-tool verification:

```sh
vevidence validate-structural structural-export --roundtrip vendor-reexport.xml
```

This compares structural counter identities, source file/line locations, toggle
directions and counts. It is not a vendor binary reader or full general UCIS
validator. Run status and the native source metadata remain authoritative in the
sidecar. There is no automatic cross-tool structural merge: instrumentation points
from different simulators need an explicit equivalence mapping.

## Reproduce the executed RTL qualification

```sh
python -m pip install -e '.[ucis]'
python scripts/qualify_structural.py --out /tmp/structural-probe --pyucis
```

Use `--verilator /path/to/verilator` if needed. With a source-tree tool installation,
set its `VERILATOR_ROOT` normally. Linux/WSL is required by the bounded process
runner. The optional `--pyucis` checks XSD validity and an independent reader/writer
round trip; native execution/export does not otherwise require PyUCIS.

The probe compiles `examples/structural/probe.sv`, checks its actual output in C++,
and writes native coverage after resetting counters following initialization.
Two stimulus schedules produce different coverage while preserving constant-bit
holes. Local Verilator 5.052 results:

| Schedule | Line/block points hit | Directional toggle points hit |
| --- | ---: | ---: |
| Two selector values | 4 / 6 | 13 / 24 |
| Four selector values | 6 / 6 | 19 / 24 |

This installed version rejects `--coverage-branch`; the working probe deliberately
uses `--coverage-line --coverage-toggle`. No separate branch coverage claim is
made. `tests/fixtures/structural-verilator.dat` is the real full-schedule output,
retained for parser/export regression tests. See `evidence/structural-summary.json`.

## Native structural VDB from the actual DUT

On a licensed VCS host, existing runners accept:

```sh
python examples/ready_valid/run.py --sim vcs \
  --hdl-coverage line+cond+fsm+tgl+branch
```

The shared adapter adds the same `-cm` selection at compilation and simulation,
and supplies a private `-cm_dir <run-output>/coverage.vdb`. Worker processes inherit
the selection via `PVC_HDL_COVERAGE`. Unset that variable when switching backends.
After successful simulation, `timing.json` inventories the VDB files and records
the metric selection. A missing/empty VDB is an error. Failed simulations retain
their local artifacts; they are not relabeled passing because coverage exists.

Use VCS's matching installed URG/coverage tooling for those native databases.
This path collects the DUT's real structure; it does not manufacture structural
coverage from functional evidence. Exact metric availability and command behavior
still require qualification on the user's VCS version. Binary file content has not
been validated locally because neither VCS nor URG is installed.

## Native functional VDB from our evidence

```sh
vevidence export-ucis run/bundle.json --output checked-export
vevidence write-vcs-vdb checked-export --output vcs-functional
```

To inspect generated source and commands without running VCS:

```sh
vevidence write-vcs-vdb checked-export --output vcs-prepared --prepare-only
```

The writer validates the original export, preserves its sidecars, generates a
small SystemVerilog sampler and invokes VCS to compile and execute it. One
coverpoint per obligation retains `option.at_least`; `iff` guards ensure sampling
one obligation never increments others. Zero-count bins are declared but not
sampled. No DUT structural instrumentation is enabled on this generated sampler.

This replays **aggregate eligible counts**, not the original DUT stimulus or test
history. The conversion simulation may finish normally even when the original
evidence gate failed. The original gate, exclusions and provenance remain in the
copied `evidence/` directory and `native-report.json`; they must not be replaced
by the conversion run's status. Sampling is bounded to one million calls by
default (`--max-samples` overrides it); `--timeout` bounds each compiler/simulator
process group. SV hit thresholds must fit a signed 32-bit integer.

Outputs include `coverage_sampler.sv`, stage logs, commands/version information,
the original evidence and, if VCS succeeds, `functional.vdb`. Missing tools and
failed compilation/simulation leave a failure report and never report successful
native creation. `--prepare-only` reports `prepared`, not a binary database.

Before using the generated VDB for analysis, inspect its bins and thresholds in
the target tool. If it supports UCIS re-export, run:

```sh
vevidence validate-ucis vcs-functional/evidence --roundtrip vcs-reexport.xml
```

Native VCS hierarchy/naming and covergroup persistence may need version-specific
adjustment; this command detects differences rather than treating the VDB as
qualified. Combining this functional VDB with DUT structural VDBs through URG is
also a licensed-host qualification step. No native merge compatibility is claimed
merely because both inputs use the `.vdb` suffix.

References: [Verilator coverage collection](https://verilator.org/guide/latest/simulating.html),
[Verilator coverage tooling](https://verilator.org/guide/latest/exe_verilator_coverage.html).
