# M0 dependency investigation — 2026-10-23

## Exercised environment

Development host: Windows, Python 3.10.7. Simulation environment: installed Ubuntu 22.04 under WSL2, x86_64, Python 3.10.12, glibc 2.35, Icarus/vvp 11.0 stable. No Git repository existed in the supplied folder. Work preserves the starter documents and adds an ordinary `src/verification_evidence` package. The provisional distribution name is `verification-evidence`, CLI `vevidence`; public availability has not been checked.

The evidence core uses only the Python standard library. Simulation and solver packages are installed in `.venv-linux`, separately from clean core validation environments. All test fixtures are synthetic, clearly separate from simulator probe output.

| Dependency | Installed version | Actual probe |
| --- | --- | --- |
| cocotb | 1.9.2 | Runner build/test, RisingEdge/ReadOnly sampling, explicit negative test |
| pyuvm | 5.0.0 | `uvm_test` phases, objections, analysis port and subscriber in simulation |
| cocotb-coverage | 1.2.0 | 128 constrained transactions, weighted address choice, four coverage bins, repeated seed |
| PyVSC | 0.9.6.37412289187 | Same finite relation/distribution, per-object random state, covergroup sampling |
| pyboolector | 3.2.4.38488416565 | Used by the PyVSC solver probe on this Linux/glibc combination |
| python-constraint | 1.4.0 | Used by cocotb-coverage probe |

Exact transitive versions are in [environment-freeze.txt](../evidence/m0/environment-freeze.txt). Installed public signatures, dependency constraints, and license file contents/digests are in [dependencies.json](../evidence/m0/dependencies.json). `pip check` reported no broken requirements. This is a tested combination, not a claim about all releases or platforms.

The resolver initially considered cocotb 2.1.0, then selected 1.9.2 because cocotb-coverage 1.2.0 declares `cocotb ~=1.8`. pyuvm 5.0.0 declares `cocotb >=1.6.0,<3.0`. Keep the exercised combination for M2; qualify newer cocotb separately. The 1.9.2 Python runner emits an experimental-API warning, so probe scripts pin its use; it is not imported by the evidence core.

## Backend decision

Select **PyVSC** for the initial M3 adapter. Both candidates passed the bounded probe. PyVSC offers per-object random state and bit-vector constraints suited to the planned 32-bit data scenarios. Its solver wheel and substantial transitive dependency set remain optional. Installation/import and this tiny experiment do not qualify all constraint forms, platform wheels, performance, or UVM integration.

The experiment chooses addresses {0,4,8,12}, data 0..15, requires data=0 at address=0, and requests address weights 1:3:1:1. For 128 draws with seed 42:

| Backend | Address 0 | Address 4 | Address 8 | Address 12 | Repeat trace |
| --- | ---: | ---: | ---: | ---: | --- |
| cocotb-coverage | 2 | 71 | 29 | 26 | Identical on second generation |
| PyVSC | 23 | 62 | 25 | 18 | Identical after restoring seed-derived object state |

Both sampled every bin and obeyed the hard relation. The finite-domain backend's distribution is affected by the number of legal combinations; do not infer marginal uniformity or exact requested proportions. The measured PyVSC distribution is closer to the requested marginal weights in this one sample; this is not a statistical qualification. The cocotb-coverage source uses module-global Python random state; M3 stream independence would require isolation if that backend were selected. PyVSC's per-object API is a more direct fit. Native Windows solver support and 32-bit performance are not qualified here.

Actual traces, measured elapsed times, and results: [backends.json](../evidence/m0/backends.json). These timings include different initialization costs and are not a performance comparison. Generation did not increment cocotb-coverage bins until explicit sampling. Backend hits remain observations; only the companion's linked checker evidence can close an obligation.

## License/source inspection

Installed source/license files identify cocotb as BSD-3-Clause, cocotb-coverage as BSD-2-Clause, pyuvm and PyVSC as Apache-2.0. Their notices are preserved in the inspection artifact; no library implementation was copied into the package. Icarus reports GPL-2.0-or-later. Compiler changes belong in its separate checkout. The pyboolector wheel license is captured verbatim for review; a complete redistribution audit of all transitive dependencies remains a release task. python-constraint wheel metadata says UNKNOWN and has no separate license file in its installed file list; do not treat that metadata as a license grant. No license has been chosen for this project.

## Reproduction

Run these commands from this directory's parent in Ubuntu (WSL host path `<project-directory>`):

```sh
python3 -m venv .venv-linux
.venv-linux/bin/python -m pip install -r evidence/m0/environment-freeze.txt
.venv-linux/bin/python -m pip install -e .
.venv-linux/bin/python -m pip check
.venv-linux/bin/python probes/dependencies.py
.venv-linux/bin/python probes/coverage_backends.py
.venv-linux/bin/python probes/icarus/run.py
```

The initial installs were `pip install cocotb pyuvm cocotb-coverage pytest setuptools wheel`, followed by `pip install pyvsc` and `pip install -e .`. Use the saved versions for reproduction, not unpinned resolution. The freeze is an environment snapshot, not a hash-locked supply-chain manifest. Rebuild tools are defined separately in `pyproject.toml`.

## Primary sources and limitations

Installed source takes precedence for API signatures. Background references: [cocotb timing model](https://docs.cocotb.org/en/stable/timing_model.html), [pyuvm source](https://github.com/pyuvm/pyuvm), [cocotb-coverage tutorials](https://cocotb-coverage.readthedocs.io/en/latest/tutorials.html), [PyVSC quickstart](https://pyvsc.readthedocs.io/en/latest/quickstart.html). The live cocotb stable documentation resolved to a newer development version; it was not used to claim 1.9.2 API compatibility. The exercised installed source and simulator output provide that evidence.

APB specification revision and full protocol qualification are still M2 work. There is no APB RTL implementation yet, no cross-version seed promise, and no public release.
