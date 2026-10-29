# Python 3.11 and Icarus 13

The additional environment uses Ubuntu 22.04 x86-64 under WSL2, CPython 3.11.18, Icarus Verilog and vvp 13.0 stable, cocotb 1.9.2, pyuvm 5.0.0 and PyVSC 0.9.6.37412289187. Icarus was built from official tag `v13_0`, commit `dfeee909ed9f20b4870dd93423156c0170c0e1ff`, into an isolated prefix. Existing Icarus 11 and Python 3.10 installations were preserved.

Qualification completed on 2026-10-28:

| Check | Result |
| --- | --- |
| Unit tests in simulation environment | 57 passed |
| Fresh core-only wheel installation, optional libraries absent | 57 passed |
| APB directed positive/negative cases | 8/8 qualified |
| APB constrained random closure and deliberate gap | 5/5 qualified |
| APB baseline/replay, six mutant/replay pairs, interruption | 15/15 qualified; all 7 replays exact |
| Ready/valid, pyuvm and plain cocotb, good/corrupt RTL | 4/4 qualified |
| Simulation environment dependency check | No broken requirements |

Use a Python 3.11 interpreter and ensure both `iverilog` and `vvp` resolve to the intended 13.0 installation. A package manager may supply a different version. For a source installation, use the [official Icarus installation instructions](https://github.com/steveicarus/iverilog/blob/master/Documentation/usage/installation.rst) with tag `v13_0`, and put its install prefix's `bin` directory first on PATH.

```sh
python3.11 -m venv .venv-311
. .venv-311/bin/activate
python -m pip install -r requirements-sim.txt
python -m pip install -e .
python -m pip check
python --version
command -v iverilog
command -v vvp
iverilog -V
vvp -V
python -m unittest discover -s tests -v
python examples/apb_peripheral/run_suite.py
python examples/apb_peripheral/run_suite.py --m3
python examples/apb_peripheral/run_suite.py --m4
python examples/ready_valid/run.py
```

Each suite writes fresh artifacts under `evidence/` and a latest.json pointer. Qualification success includes expected failures: negative DUT runs retain failed evidence gates; deliberate coverage gaps retain incomplete gates. Do not read an outer successful exit as a claim that every DUT run passed.

The checked-in `evidence/python311-icarus13-summary.json` records the final results and dependency versions without private machine paths. Raw local artifacts include simulation output, manifests, observations, checks and coverage. The original 3.10/Icarus 11 results remain in `evidence/m4-summary.json`; their 47-test count is historical.

This historical qualification covers the supplied examples on the exact listed versions. It did not test the user's external design, every Python 3.11 patch, native Windows simulation, all Icarus SystemVerilog features, or cocotb 2.x. Later portability work and additional tested combinations are documented in [doc 19](19_SIMULATOR_PORTABILITY.md). Exact dependency pins are now optional reproduction snapshots. The Icarus assertion-feature investigations remain separate from these cocotb-driven testbenches.
