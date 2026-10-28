# Python Verification Companion

A protocol-independent verification evidence core with working APB and ready/valid examples for cocotb and pyuvm. It connects independently observed DUT behavior, checker results, functional coverage, bounded coverage closure, and recorded-stimulus replay.

This is an early source release. M0–M4 are implemented; M5 release hardening remains pending. A plain-cocotb example now shares the streaming scoreboard and evidence schema with the pyuvm example. It is not an official cocotb/pyuvm project or a signoff certification.

## Use with your own DUT

Read [Extending to other buses and interfaces](docs/17_EXTENDING_TO_OTHER_INTERFACES.md) for the UVM component map, implementation steps, protocol-specific considerations, and a copyable coding-agent prompt. Start with `examples/ready_valid` for reusable source/sink/passive agents and monitor-to-scoreboard connections. Use the APB example for solver-backed constraints, bounded coverage targeting and recorded replay. The public `EvidenceRecorder` API lets either approach write checked evidence without changing the core.

## Install

Download this repository as a ZIP and extract it, or clone it:

```sh
git clone https://github.com/syakovac-spec/python-verification-companion.git
cd python-verification-companion
```

The evidence core alone can also be installed directly from the public URL into an activated Python environment:

```sh
python -m pip install "git+https://github.com/syakovac-spec/python-verification-companion.git"
```

Clone the repository for the full RTL examples, simulation runners, tests and documentation; the installed Python package contains the evidence core.

The original qualified simulation environment is Ubuntu 22.04 x86-64 (including WSL2), Python 3.10, Icarus Verilog/vvp 11.0. See [Python 3.11 / Icarus 13 qualification](docs/18_TOOLCHAIN_QUALIFICATION.md) for the additional toolchain and exact results. The Python evidence core also has test results on Windows Python 3.10.7. Native Windows simulation/solver support is not qualified.

Install Python's venv support and Icarus if needed:

```sh
sudo apt-get update
sudo apt-get install python3-venv iverilog
python3 --version
iverilog -V
```

Check versions against the qualified environment rather than assuming the package manager supplies the same version on every OS release.

For the evidence core only:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/vevidence summarize tests/fixtures/passing.json
```

For the full simulation workflow:

```sh
python3 -m venv .venv-linux
.venv-linux/bin/python -m pip install -r requirements-sim.txt
.venv-linux/bin/python -m pip install -e .
.venv-linux/bin/python -m pip check
.venv-linux/bin/python -m unittest discover -s tests -v
.venv-linux/bin/python examples/apb_peripheral/run_suite.py
.venv-linux/bin/python examples/apb_peripheral/run_suite.py --m3
.venv-linux/bin/python examples/apb_peripheral/run_suite.py --m4
.venv-linux/bin/python examples/ready_valid/run.py
```

The direct simulation dependencies are pinned. The recorded development environment's full version snapshot is `evidence/m0/environment-freeze.txt`; use it instead of `requirements-sim.txt` when reproducing that dependency set. It includes optional investigation tools and is not a hash-locked manifest. Source packaging and a fresh core installation are checked separately from full fresh-machine simulation qualification.

## What runs

- A simulator-independent `verification_evidence` Python package and `vevidence` CLI.
- A four-register APB3-subset DUT, pyuvm agent, independent monitor and automatic register/protocol scoreboard.
- PyVSC constrained sequences with isolated random streams and functional coverage targeting.
- Coverage closure requiring linked checker evidence, not merely generated stimulus or observed hits.
- Recorded pin-level replay, strict input identity checks, and six RTL mutants with intended detection.

M4 local qualification contains 15 cases: baseline/replay, six mutant/replay pairs, and interruption accounting. All seven replays matched pin traces, samples and checker records. 47 unit tests passed on Windows and Linux. These are results from the recorded environment, not guarantees for every platform.

The additional Python 3.11.18 / Icarus 13.0 run qualified all 32 simulation cases across APB and ready/valid, including intended negative detections. All 57 current unit tests passed in both the simulation environment and a fresh core-only installation. See the [qualification report](docs/18_TOOLCHAIN_QUALIFICATION.md) for scope and reproduction.

Suite commands return success when their qualification expectations are met. Mutants intentionally retain failed raw evidence gates; deliberate gaps remain incomplete. Each invocation writes a new evidence directory and a latest.json pointer.

## Documentation

- [Evidence core and CLI](docs/14_EVIDENCE_CORE.md)
- [Extend to another bus or interface](docs/17_EXTENDING_TO_OTHER_INTERFACES.md)
- [Python 3.11 / Icarus 13 qualification](docs/18_TOOLCHAIN_QUALIFICATION.md)
- [APB checking and functional coverage](docs/15_APB_RESULTS_AND_CLOSURE.md)
- [Replay and mutations](docs/16_REPLAY_AND_MUTATIONS.md)
- [Implementation milestones](docs/06_IMPLEMENTATION_PLAN.md)
- [Support and validation](docs/07_VALIDATION.md)
- [Contributing](CONTRIBUTING.md)

The design documents retain historical milestone context. Raw development logs, waveforms, virtual environments and private machine paths are not included. Historical evidence links may refer to local development artifacts; `evidence/m4-summary.json` is a labeled summary, and the suite commands produce fresh full artifacts.

No AI API key or service is required at runtime. Adapting to another DUT requires its own interface adapter, independent reference model and coverage intent.

## License

MIT; see [LICENSE](LICENSE). Dependencies retain their own licenses. Pending license decisions in historical design notes were resolved for this source release on 2026-10-28.
