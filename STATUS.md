# Publication candidate status

## Planned extensions — 2026-10-29

The owner-requested [extension TODO backlog](docs/20_EXTENSION_BACKLOG.md) records agent generation, reusable scoreboards and sampling adapters, coverage planning/closure, performance benchmarks, build caching/parallel regressions, scalable evidence, additional protocols, register abstraction and failure triage/replay. It includes priorities, dependencies and acceptance criteria, plus separate Icarus, encrypted-model and SV-UVM interoperability workstreams. All are recorded as future work; no implementation or qualification status is changed by this documentation update. Recommended deliverables are the agent/scoreboard kit, a measured performance/scalability baseline, and an AXI-Lite reference environment. Existing M5 release-hardening work remains open.

## Portability and VCS sampling race — 2026-10-29

Fixed the VCS-reported RisingEdge race: monitors read HDL acceptance snapshots after ReadOnly, the streaming driver uses captured valid/ready/reset, and APB captures pre-update SCRATCH state for early-side-effect checks. Missing stream capture handles are rejected. Three scheduler counterexamples exercise post-update live pins and missing capture. The full 65-test unit suite passes on Windows Python 3.10 and Linux Python 3.11/3.12, including a fresh core-only installation without optional simulator/solver packages.

Both example runners now honor --sim/SIM and the active interpreter, including a conda-format environment created with micromamba. Removed forced VIRTUAL_ENV and unconditional Icarus probes/flags. VCS uses cocotb's supported Makefile integration, including on cocotb 1.9. Exact simulation pins are optional historical snapshots; default requirements use minimum versions. Other simulators require an appropriate installed cocotb backend and DUT-language support.

Executed 68 simulator qualifications across four combinations: Icarus 13 + Python 3.11.18/cocotb 2.1.0/pyuvm 5/PyVSC 1.0 (full 32 cases); Icarus 11 + Python 3.11.18/cocotb 1.9.2/pyuvm 5/PyVSC 0.9.6 (7 cases); conda Python 3.12.16 + Icarus 11/cocotb 2.0.1/pyuvm 4.0.1/PyVSC 1.0 (7 cases); Verilator 5.052 + Python 3.11.18/cocotb 2.1.0/pyuvm 5/PyVSC 1.0 (7 cases plus 15 mutation/replay cases). All met qualification expectations. Both full mutation suites detected all six defects and reproduced all seven replay traces/check records exactly. Negative runs retain failed gates; the coverage gap remains incomplete.

VCS is unavailable locally. Its command construction and the reported race counterexamples are tested; a licensed VCS execution remains to be run in the user's environment. This is not a universal simulator qualification or a VCS performance claim.

Added scripts/qualify_compatibility.py and scripts/profile_constraints.py, per-run solver call profiles and build/test timing. Profiled Boolector and dv-solve on 200 draws each of weighted-address, targeted-bit and reset constraints, with legality checks and an expected unsatisfiable rejection. Publish exact results in evidence/portability-summary.json. Reproduce with docs/19_SIMULATOR_PORTABILITY.md. Potential Icarus engine improvements remain separate, measured follow-up work; no compiler patch is required by the package.

Prepared 2026-10-28. M0–M4 complete in the recorded development environment; see README and evidence/m4-summary.json. Raw historical evidence is retained locally, not included in this source release.

The owner selected MIT and personal GitHub hosting on 2026-10-28. Public repository: https://github.com/syakovac-spec/python-verification-companion.

## Python 3.11 / Icarus 13 and extension support — 2026-10-28

Qualified CPython 3.11.18 and Icarus/vvp 13.0 stable (official v13_0 commit dfeee909ed9f20b4870dd93423156c0170c0e1ff) on Ubuntu 22.04 x86-64 under WSL2, retaining the declared simulation dependency pins. An isolated fresh simulation virtual environment ran all three APB suites and the new streaming suite. All 32 qualifications met expectations: 8 directed APB cases, 5 constrained closure/gap cases, 15 replay/mutation/interruption cases, and 4 ready/valid cases. All six APB mutants were detected and all seven replays matched pin traces, observations and checks. Deliberate failures and gaps retain failed/incomplete raw gates.

Added the public protocol-independent EvidenceRecorder, a ready/valid source/sink/passive pyuvm agent example, independent observed-input/output scoreboard and checked coverage goals, plus a plain-cocotb test sharing the model and BFM. Both composition styles close the good DUT and detect deliberate data corruption. The extension guide maps UVM concepts to executable code and describes adapting other interfaces. Streaming randomization is seeded legal Python data; APB remains the solver-backed constrained-random and recorded-replay demonstration.

Executed commands: `python scripts/qualify_m2_units.py python311-icarus13`; `python examples/apb_peripheral/run_suite.py` with default, `--m3` and `--m4`; `python examples/ready_valid/run.py`; `python -m pip check`. All 57 unit tests passed in the simulation environment and again after a fresh wheel installation into a core-only Python 3.11 environment with cocotb, pyuvm and vsc absent. See evidence/python311-icarus13-summary.json for sanitized results, dependencies and source digests; full raw artifacts remain local. Reproduction commands are in docs/18_TOOLCHAIN_QUALIFICATION.md.

M5 is partially advanced, not declared complete. Schema migration policy, independent fresh-machine release qualification and broader release hardening remain. No external user DUT, complete AXI VIP, native Windows simulator/solver environment, or general new-protocol replay is qualified by these results.
