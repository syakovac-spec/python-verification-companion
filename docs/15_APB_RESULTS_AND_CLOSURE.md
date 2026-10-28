# APB verification and functional closure

Updated 2026-10-26. M2 and M3 use Python 3.10.12 on Ubuntu 22.04/WSL, Icarus/vvp 11.0, cocotb 1.9.2, pyuvm 5.0.0, PyVSC 0.9.6.37412289187 and pyboolector 3.2.4.38488416565. Other simulation combinations remain unqualified.

## Contract and independent checking

The APB signaling reference is Arm IHI 0024C, ID042910, AMBA APB Protocol v2.0, sections 3.1, 3.3, 3.4 and 4.1. The pilot uses the APB3 signal subset without PSTRB/PPROT. The four-register map, exact wait counts, invalid-access side effects and reset behavior are project requirements from doc 05. The implementation is in `examples/apb_peripheral`.

The pyuvm environment contains a driver, passive monitor, automatic scoreboard and evidence subscriber. The scoreboard reconstructs accepted bus transactions and register state from sampled signals. It does not use generated requests as expected responses. Relevant X/Z produces inconclusive evidence. Shutdown reconciles pending transfers.

Drivers change signals on falling edges. A positive-edge HDL snapshot captures pre-NBA acceptance values; the Python monitor checks its immediate sample against that snapshot after ReadOnly. The regression also records post-NBA differences, proving that the sampling distinction is exercised. An asynchronous reset watcher handles subcycle reset; reset at an acceptance edge dominates the transfer. Readback checks establish reset and side-effect behavior.

The directed suite covers reset, ID, scratch patterns including 32 walking bits, read-only errors, W1C clear/preserve, invalid/misaligned accesses, exact waits, consecutive operation pairs and reset during setup/wait/completion. Wait-phase resets are explicitly not applicable at zero wait.

## Functional coverage plan

Functional sampling starts after the directed prelude. Every applicable functional bin requires three distinct, correlated checked-pass observations in finalized passing runs. The evidence core supplies bins/crosses and closure semantics; PyVSC supplies constraints and per-object solver state. Backend activity alone is not checked coverage.

| Family | Cross / points | Applicable bins per run |
| --- | --- | --- |
| FC-001 | Read/write × ID, scratch, status, event, unmapped, misaligned | 12 |
| FC-002 | Wait profile × read/write | 2 for the selected profile |
| FC-003 | Consecutive operation pair rr/rw/wr/ww | 4 |
| FC-004 | Reset setup/wait/completion × read/write, with checked abort readback | 4 at wait 0; 6 at wait 1/3 |
| FC-005 | Scratch readback bit 31 × low two bits | 8 |

There are 30 active functional bins at wait 0 and 32 at wait 1/3, in addition to 77/79 directed obligations. Definitions and applicability are explicit in `tb/apb_functional.py`. These finite goals do not establish exhaustive APB verification or signoff.

## Constrained stimulus and closure

`RandomAgent` owns a pyuvm sequencer; `ClosureSequence` issues sequence items through the driver's sequence-item port. PyVSC constrains six address classes, direction, full 32-bit data, and legal reset phases. Scratch addresses have weight three; other address classes have weight one. Separate transaction, reset and idle streams derive 32-bit seeds from SHA-256 of `apb-stream-v1:{root}:{component path}`. PyVSC uses per-object RandState; idle uses a private Python Random instance. This is reproducibility within the recorded dependency set, not cross-version equivalence.

Each normal run starts with 48 randomized iterations, readbacks and periodic randomized resets. Up to 96 further target operations use still-open checked goals to add constraints. Goals and checkers remain unchanged. The final evidence assessment is authoritative; progress checkpoints are provisional.

Each run preserves `generated.json`, `stimulus.jsonl`, `samples.jsonl`, `closure_progress.json`, `distribution.json`, manifest/input identities, simulator logs/XML, VCD, bundle and summary. Generated action arguments preserve the sequence for future replay; executable recorded-stimulus replay belongs to M4.

Distributions count observed accepted transfers, including readbacks and closure targeting. They are not an unbiased sample of the solver's address weights. For wait 3 / seed 42, observed scratch reads/writes were 53/21, status reads 36, and ID reads 27; all twelve direction/region cells had at least three observations. Readback and reset checks explain the read skew. This bounded inspection is not a statistical distribution certification.

## Qualification evidence

- M2: `evidence/m2/df188945-c90c-4abf-a209-6d292e086d30/qualification.json`. Three directed baselines pass at waits 0/1/3; wrong response, missing response, unstable control and truncated transfer all produce their expected failed obligations and failing simulator test XML. Artifact hashes are verified.
- M3: `evidence/m3/7b2c412f-b1d2-4d44-b509-b3208f52c761/qualification.json`. Seeds/profile results are recorded per case. Passing closure cases use seed 42 at waits 0/1/3 and seed 17 at wait 3. The scratch-only gap case deliberately remains incomplete, including uncovered `FC-001.write.unmapped`.
- `evidence/m3/random-streams.json` proves same-seed repeatability, unrelated-stream isolation, changed-root variation, legal constraints, targeted data classes and zero-wait reset applicability.
- `evidence-semantics.json` beside the M3 qualification records a clearly labeled derived reporting experiment: removing a coverage/check link from real observations yields unchecked status, zero eligible credit and an incomplete gate. It is not a new simulation. The same probe verifies compatible two-seed merging and duplicate-run idempotence.
- 43 pure Python semantic/checker tests pass without optional simulator/solver imports; tests include failure propagation, unknown preservation, non-vacuous reset/W1C checks and functional sampling boundaries.

## Reproduction

From the project directory in the recorded WSL environment:

```sh
.venv-core/bin/python scripts/qualify_m2_units.py
.venv-linux/bin/python examples/apb_peripheral/run_suite.py
.venv-linux/bin/python examples/apb_peripheral/run_suite.py --m3
.venv-linux/bin/python probes/random_streams.py
.venv-core/bin/python probes/apb_evidence_semantics.py evidence/m3/7b2c412f-b1d2-4d44-b509-b3208f52c761
```

Each suite invocation writes a unique directory and updates its `latest.json`. Supply the new M3 directory to the last command when qualifying new runs. Native Windows simulation/solver support is not claimed. The outer suite succeeds only when positive and deliberate-negative expectations, XML and artifact integrity agree; the gap run's raw evidence gate remains incomplete.

## Remaining work

M4 has since added recorded replay, integrity rejection and all six DUT mutants; see doc 16 and STATUS.md. Current negatives qualify checker sensitivity using harness faults; they do not substitute for that mutation matrix. HDL structural coverage, Python coverage and native assertion coverage are not collected. Icarus concurrent implication remains unsupported on the exercised path; IV1 compiler changes are separate.
