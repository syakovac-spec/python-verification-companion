# Simulator, Python environment and solver portability

The evidence core is simulator independent. The example runners select a cocotb backend through `--sim NAME` or `SIM=NAME`; Icarus is only the default when neither is set. No other backend needs an Icarus installation. Simulator-specific compiler arguments stay in the optional `verification_evidence.simulation` integration module. The DUT language and the installed cocotb backend determine which simulators can execute a particular example; this is not a claim that every simulator supports every HDL feature.

## Executed compatibility matrix — 2026-10-29

| Simulator | Python/environment | cocotb / pyuvm / PyVSC | Result |
| --- | --- | --- | --- |
| Icarus 13.0 | 3.11.18, venv | 2.1.0 / 5.0.0 / 1.0.0 | 32/32 full qualifications |
| Icarus 11.0 | 3.11.18, venv | 1.9.2 / 5.0.0 / 0.9.6.37412289187 | 7/7 compatibility cases |
| Icarus 11.0 | 3.12.16, conda-format environment created with micromamba | 2.0.1 / 4.0.1 / 1.0.0 | 7/7 compatibility cases |
| Verilator 5.052 | 3.11.18, venv | 2.1.0 / 5.0.0 / 1.0.0 | 7/7 compatibility cases plus 15/15 mutation/replay cases |
| VCS | Tool/license unavailable locally | VCS command construction tested | Licensed execution not run |

All 65 unit tests passed in these Linux environments and on Windows Python 3.10. The installed core also passed with simulator and solver libraries absent. The Icarus 13 and Verilator mutation suites detected all six deliberate defects and reproduced all seven replay traces/check records. Results are recorded in [the public summary](../evidence/portability-summary.json); full raw artifacts remain local. Different simulator results are separately identified and are not merged as equivalent execution profiles.

## Use your existing conda environment

```sh
conda activate my-verification-env
python -m pip install -e .
python -m pip install -r requirements-sim.txt
python -m pip check
python scripts/qualify_compatibility.py --sim vcs
```

The scripts use `sys.executable` for child Python processes and the active interpreter's cocotb integration. They do not create an environment, activate another environment, set VIRTUAL_ENV, or replace CONDA_PREFIX. License and simulator environment variables are inherited. Build helper Python commands resolve to the active interpreter's bin directory during execution; the caller's PATH is restored afterward. This prevents a simulator helper from using system Python with a different Python's standard library.

If the environment already supplies compatible dependencies, skip the requirements installation. The evidence core itself needs no cocotb, pyuvm or solver installation. Alternatively `python -m pip install -e '.[simulation]'` installs the simulation extra. Do not use a bare `pip` from a different environment.

Installation requirements are minimum versions, not exact pins: cocotb >=1.9, pyuvm >=4, PyVSC >=0.9.6. PyVSC selects its solver dependencies. This permits other releases; it does not certify untested releases. The previous exact set is retained in `requirements-sim-qualified-20261028.txt` for historical reproduction. New manifests continue to record actual versions and tool identities.

## Select a simulator

```sh
python examples/apb_peripheral/run_suite.py --sim vcs --single --case m3 --wait 3
python examples/ready_valid/run.py --sim verilator
SIM=questa python examples/ready_valid/run.py
python scripts/qualify_compatibility.py --sim icarus --full
```

`--build-arg=-flag` and `--test-arg=-flag` are repeatable and pass additional arguments to the selected tool. The runner adds `-g2012` only for Icarus and `--timing` for Verilator. VCS uses cocotb's supported Makefile integration (including on cocotb 1.9, whose Python runner lacks VCS support), VPI read/write access and VCS `-pvalue+TOP.PARAM=VALUE` parameter overrides. It does not receive Icarus compiler flags. GNU make and the selected simulator must be available. Cocotb's Makefile interface uses whitespace-separated source lists; use a checkout/build path without spaces for that path.

Other selected backends are passed to the installed cocotb Python runner. Missing executables are reported for the selected simulator only. The shipped examples are Verilog/SystemVerilog; VHDL-only tools need a suitable VHDL DUT/harness. The core, catalog and scoreboard patterns are not restricted by the example's HDL language.

`qualify_compatibility.py` checks unit tests, both stream styles with corruption, APB positive/negative checking and constrained closure. `--full` adds all directed, closure-gap, replay/mutation and interruption cases. It saves failures and exact environment metadata under `evidence/compatibility`. A missing commercial simulator is unavailable, not passed. VCS execution requires the user's installed tool and license; a command-generation test alone is not VCS qualification.

## Race-free acceptance sampling

`await RisingEdge(clk)` does not guarantee that Python sees pre-update live signals. The VCS-reported race occurred because a monitor compared live values read in this callback with HDL pre-NBA snapshots. The streaming driver also used the live ready/reset values to decide whether a transfer completed.

The examples now capture acceptance values in HDL and read only those captured registers after `RisingEdge` followed by `ReadOnly`:

```systemverilog
always @(posedge clk) begin
    s_valid <= valid;
    s_ready <= ready;
    s_data  <= data;
end
```

The right-hand values are evaluated before the synchronous DUT's nonblocking state updates; the snapshot registers become readable after the NBA region. DUT sequential state must follow the nonblocking-update contract, and inputs must be driven away from the acceptance edge. A DUT that races blocking assignments against this sampling process needs a separately defined sampling adapter; this pattern cannot repair a race inside the RTL.

Both the stream monitor and driver use this snapshot. Missing stream capture handles produce an error rather than a live-signal fallback. APB already used captured handshake values in its driver; its monitor now uses captured pre-update SCRATCH state as well as bus values. The early-write-side-effect check still compares pre-update state with the settled post-update architectural state. The reset edge observer remains independent so short reset pulses are not lost.

`tests/test_sampling_race.py` forces live pins to change before resuming Python and verifies monitor data, driver acceptance and missing-capture rejection. Those are deterministic scheduler counterexamples, not a claim of a licensed VCS execution. Simulator qualifications also require observed pre/post data changes, coverage closure and deliberate defect detection. Do not fix the race by adding ReadOnly and then reading live acceptance pins: those are settled next-state values.

## Constraint-solver profiling

```sh
python scripts/profile_constraints.py --iterations 100 --solver boolector --out evidence/constraints/boolector.json
python scripts/profile_constraints.py --iterations 100 --solver dv-solve --out evidence/constraints/dvsolve.json
VSC_SOLVER=dv-solve python examples/apb_peripheral/run_suite.py --sim icarus --single --case m3 --wait 3
```

Selecting dv-solve requires a PyVSC release exposing that backend (tested with 1.0.0); old PyVSC is checked rather than silently ignoring the selection. Profiles separate import time, object construction, first solve, median/p95/max solve latency and expected unsatisfiable rejection. Every generated result is checked for the requested constraints. `--cprofile PATH` optionally records Python call costs; its instrumentation overhead makes those timings unsuitable for direct comparison with uninstrumented runs.

Each APB constrained run also writes `solver-profile.json` with solve call counts, failures, cumulative wall time and maximum latency. These measure complete randomize calls, including Python constraint construction and the native solver boundary; they do not isolate native solver CPU time. `timing.json` separates build and test wall time for the Python-runner backends; VCS Makefile execution currently reports combined wall time. Compare repeated runs on an otherwise idle machine before making speed claims. The two solvers need not produce identical stimulus from the same seed.

An uninstrumented 200-draw profile on PyVSC 1.0.0 measured these median milliseconds per draw:

| Constraint workload | Boolector | dv-solve |
| --- | ---: | ---: |
| Weighted legal address | 1.926 | 0.684 |
| Targeted address/direction/data bits | 2.858 | 0.969 |
| Reset phase/direction | 0.826 | 0.255 |

All generated values satisfied the checked constraints and both rejected the deliberately unsatisfiable address. These single-machine measurements are specific to these workloads, include wrapper overhead, and are not a general solver ranking. First-call/setup and p95 values are preserved in the summary. The profile does not establish simulator speed or a VCS comparison.

Permissive installation does not relax replay identity. A changed simulator, dependency set, compiler flags or solver selection requires a new qualification. HDL four-state/XZ and scheduling capabilities also differ between backends; two-state runs cannot establish four-state behavior.

## Icarus improvements remain an independent workstream

Keep Icarus as a first-class tested backend. Use the timings and solver profiles to separate Python/constraint costs from VVP runtime before modifying the compiler. Candidate experiments are reduced VPI traffic, compact observation buffering, build reuse, and profiling VVP scheduling/vector operations on a representative large design. Any Icarus patch requires an isolated checkout, performance evidence and positive/negative semantic regressions under docs/11_ICARUS_SV_WORKSTREAM.md. No compiler patch is required to use this package with VCS or another simulator, and this change does not claim a VVP engine speedup.
