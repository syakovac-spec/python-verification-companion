# Recorded replay and mutation qualification

M4 adds timestamped pin-level replay and six individually selected RTL mutations. Qualification results and the final evidence directory are recorded in STATUS.md.

## Replay contract

`pins.json` records ordered input assignments in integer picoseconds, including reset, completion-edge reset control, idle/phase transitions, addresses and data. It also records the functional-sampling boundary and finalization time. Assignments with the same timestamp retain their order. Replay consumes these assignments directly; it does not rerun response-dependent driver methods or solve constraints. The same HDL clock and sampling shim remain in use.

The source bundle must validate, and every listed artifact must match its SHA-256 digest. Replay requires inputs, manifest and pin-trace artifacts. Source/configuration/dependency/tool identities must match the current environment exactly. Unknown pin names, out-of-range values, backward time and unsupported trace versions are rejected. Changed identities are rejected rather than silently labeled a reproduction. Hashes detect accidental changes; they are not cryptographic signatures authenticating a third party.

Replay runs get fresh IDs and preserve the source ID in `manifest.replay_of`. Solver/agent imports are explicitly blocked in the replay simulator process. Cocotb may initialize its own random infrastructure, but no stimulus generator or constraint backend is used by replay. Qualification compares original/replay pin traces, sampled bus traces and checker records exactly. A matching failure alone is insufficient.

## Mutations

Select one elaboration parameter MUTANT, with zero selecting the baseline. Mutations are in the peripheral RTL, not substituted expected values or checker suppressions.

| Mutant | RTL defect | Required detection |
| --- | --- | --- |
| MUT-01 | Mask SCRATCH bit 31 on write | APB-002.readback |
| MUT-02 | Commit a write on the last waiting edge | APB-006.write, SIDE_EFFECT_BEFORE_ACCEPT |
| MUT-03 | Clear STATUS even when bit 0 is written zero | APB-004.readback |
| MUT-04 | Suppress errors for aligned unmapped accesses | APB-005.unmapped.read |
| MUT-05 | Save an aborted scratch write through reset and apply it after release | APB-008.setup.write |
| MUT-06 | Reduce nonzero programmed wait count by one | APB-006.read |

MUT-02 needs an explicit architectural-state observation because a correct later read can conceal a premature write. The monitor observes SCRATCH around the waiting edge and checks that state does not change before acceptance. This is a pilot-specific white-box timing probe; the protocol/register scoreboard otherwise derives expectations from sampled bus transactions. It does not use the driver's expected data.

Compilation must succeed, the simulator must reach the named checker failure, and the XML result must contain the expected test failure. Compilation errors, infrastructure exceptions and unrelated timeouts do not qualify a mutant. Additional consequent failures remain visible. The finite mutation set demonstrates selected checker sensitivity, not exhaustive fault detection.

## Commands

From the project directory in the qualified Ubuntu-22.04/WSL environment:

```sh
.venv-linux/bin/python examples/apb_peripheral/run_suite.py --m4
```

For an individual source run and its replay:

```sh
.venv-linux/bin/python examples/apb_peripheral/run_suite.py --single --case m3 --wait 3 --seed 42 --mutant 1
.venv-linux/bin/python examples/apb_peripheral/run_suite.py --single --case m3 --wait 3 --seed 42 --mutant 1 --replay /absolute/path/to/source-run
.venv-core/bin/python probes/replay_integrity.py /absolute/path/to/source-run
```

The replay command must match the original case, wait profile and mutant. Use the same recorded source and dependency versions. Earlier M2/M3 bundles without pin traces remain valid historical evidence but cannot be replayed by this interface. Each suite writes a new directory and updates `evidence/m4/latest.json`.

## Boundaries

An injected exception after setup exercises in-simulator error finalization: the run retains one pending APB-010 obligation. If a subprocess exits or times out without finalizing, the runner reconstructs evidence from the flushed observation log and marks finalization as error. Missing or malformed observation history retains an explicitly unknown pending state conservatively. Unit counterexamples exercise this recovery path; they are not presented as simulator timeout runs.

The complete M4 suite comprises the baseline and its replay, six mutants and their replays, and the deliberate interruption: 15 qualified cases. `scripts/report_m4.py` generates a mutation evidence table from the resulting qualification JSON. The final suite ID is recorded in STATUS.md. The directed regression is also rerun at waits 0/1/3 with its checker negatives.

Replay is qualified on the recorded Icarus/cocotb/pyuvm environment and timing resolution. It is not a portable waveform player for arbitrary DUTs or simulators. M5 remains responsible for clean installation, an independent user workflow, plain-cocotb integration and release preparation. Native concurrent-assertion/compiler work remains separate.
