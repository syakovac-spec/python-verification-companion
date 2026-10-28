# Publication candidate status

Prepared 2026-10-28. M0–M4 complete in the recorded development environment; see README and evidence/m4-summary.json. Raw historical evidence is retained locally, not included in this source release.

The owner selected MIT and personal GitHub hosting on 2026-10-28. Public repository: https://github.com/syakovac-spec/python-verification-companion.

## Python 3.11 / Icarus 13 and extension support — 2026-10-28

Qualified CPython 3.11.18 and Icarus/vvp 13.0 stable (official v13_0 commit dfeee909ed9f20b4870dd93423156c0170c0e1ff) on Ubuntu 22.04 x86-64 under WSL2, retaining the declared simulation dependency pins. An isolated fresh simulation virtual environment ran all three APB suites and the new streaming suite. All 32 qualifications met expectations: 8 directed APB cases, 5 constrained closure/gap cases, 15 replay/mutation/interruption cases, and 4 ready/valid cases. All six APB mutants were detected and all seven replays matched pin traces, observations and checks. Deliberate failures and gaps retain failed/incomplete raw gates.

Added the public protocol-independent EvidenceRecorder, a ready/valid source/sink/passive pyuvm agent example, independent observed-input/output scoreboard and checked coverage goals, plus a plain-cocotb test sharing the model and BFM. Both composition styles close the good DUT and detect deliberate data corruption. The extension guide maps UVM concepts to executable code and describes adapting other interfaces. Streaming randomization is seeded legal Python data; APB remains the solver-backed constrained-random and recorded-replay demonstration.

Executed commands: `python scripts/qualify_m2_units.py python311-icarus13`; `python examples/apb_peripheral/run_suite.py` with default, `--m3` and `--m4`; `python examples/ready_valid/run.py`; `python -m pip check`. All 57 unit tests passed in the simulation environment and again after a fresh wheel installation into a core-only Python 3.11 environment with cocotb, pyuvm and vsc absent. See evidence/python311-icarus13-summary.json for sanitized results, dependencies and source digests; full raw artifacts remain local. Reproduction commands are in docs/18_TOOLCHAIN_QUALIFICATION.md.

M5 is partially advanced, not declared complete. Schema migration policy, independent fresh-machine release qualification and broader release hardening remain. No external user DUT, complete AXI VIP, native Windows simulator/solver environment, or general new-protocol replay is qualified by these results.
