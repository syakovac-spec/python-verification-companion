# Python Verification Companion

A verification evidence core and working APB example for cocotb and pyuvm. It connects independently observed DUT behavior, checker results, functional coverage, bounded coverage closure, and recorded-stimulus replay.

This is an early source release. M0–M4 are implemented; M5 independent release qualification and the plain-cocotb adapter remain pending. It is not an official cocotb/pyuvm project or a signoff certification.

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

The qualified simulation environment is Ubuntu 22.04 x86-64 (including WSL2), Python 3.10, Icarus Verilog/vvp 11.0. The Python evidence core also has test results on Windows Python 3.10.7. Native Windows simulation/solver support is not qualified.

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
```

The direct simulation dependencies are pinned. The recorded development environment's full version snapshot is `evidence/m0/environment-freeze.txt`; use it instead of `requirements-sim.txt` when reproducing that dependency set. It includes optional investigation tools and is not a hash-locked manifest. Source packaging and a fresh core installation are checked separately from full fresh-machine simulation qualification.

## What runs

- A simulator-independent `verification_evidence` Python package and `vevidence` CLI.
- A four-register APB3-subset DUT, pyuvm agent, independent monitor and automatic register/protocol scoreboard.
- PyVSC constrained sequences with isolated random streams and functional coverage targeting.
- Coverage closure requiring linked checker evidence, not merely generated stimulus or observed hits.
- Recorded pin-level replay, strict input identity checks, and six RTL mutants with intended detection.

M4 local qualification contains 15 cases: baseline/replay, six mutant/replay pairs, and interruption accounting. All seven replays matched pin traces, samples and checker records. 47 unit tests passed on Windows and Linux. These are results from the recorded environment, not guarantees for every platform.

Suite commands return success when their qualification expectations are met. Mutants intentionally retain failed raw evidence gates; deliberate gaps remain incomplete. Each invocation writes a new evidence directory and a latest.json pointer.

## Documentation

- [Evidence core and CLI](docs/14_EVIDENCE_CORE.md)
- [APB checking and functional coverage](docs/15_APB_RESULTS_AND_CLOSURE.md)
- [Replay and mutations](docs/16_REPLAY_AND_MUTATIONS.md)
- [Implementation milestones](docs/06_IMPLEMENTATION_PLAN.md)
- [Support and validation](docs/07_VALIDATION.md)
- [Contributing](CONTRIBUTING.md)

The design documents retain historical milestone context. Raw development logs, waveforms, virtual environments and private machine paths are not included. Historical evidence links may refer to local development artifacts; `evidence/m4-summary.json` is a labeled summary, and the suite commands produce fresh full artifacts.

No AI API key or service is required at runtime. Adapting to another DUT requires its own interface adapter, independent reference model and coverage intent.

## License

MIT; see [LICENSE](LICENSE). Dependencies retain their own licenses. Pending license decisions in historical design notes were resolved for this source release on 2026-10-28.
