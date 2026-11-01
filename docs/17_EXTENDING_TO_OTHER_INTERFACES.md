# Extend to your DUT and protocol

Use standard pyuvm components for UVM structure and `verification_evidence` for portable, checked coverage evidence. The evidence core is protocol independent. APB is one reference environment, not a required base class. New interfaces do not require changes to the core schema or forks of the APB agent.

For an editable generated starting point, see the [agent generator](21_AGENT_GENERATOR.md). It ships in the wheel and accepts explicit width and signal bindings.

## Start with an executable second protocol

The [ready/valid example](../examples/ready_valid/) verifies an 8-bit elastic buffer with independent input/output observations, randomized legal data, backpressure, an automatic FIFO scoreboard, and checked functional goals. Run from the repository root after installing the simulation dependencies:

```sh
python examples/ready_valid/run.py
```

This runs four qualifications: pyuvm and plain cocotb, each with a good DUT and a deliberately corrupted DUT. Both good runs must close their goals. Both corrupted runs must fail ORDER in the raw evidence and fail the simulator test. The outer command succeeds only when these expectations hold. Artifacts are under `evidence/ready-valid/`; `latest.json` identifies the invocation.

| UVM responsibility | Working implementation | What you replace for a new interface |
| --- | --- | --- |
| Transaction and sequence | `uvm_components.py`: StreamItem, StreamSequence | Fields, legality constraints, scenario generation |
| Sequencer and driver | StreamAgent, StreamDriver | Pin handshake and timeout rules |
| Virtual interface/configuration | `bfm.py`: StreamConfig | Signal handles, clock, reset, widths |
| Monitor and analysis port | StreamMonitor | Independent sampling and transaction reconstruction |
| Active/passive agent | StreamAgent roles source, sink, passive | Protocol roles; passive creates only a monitor |
| Predictor/scoreboard | `model.py`: StreamModel; StreamScoreboard subscriber | DUT contract, outstanding state, matching and comparisons |
| Functional coverage plan | `model.py`: plan | Requirements, bins, checkers, goals, applicable profiles |
| Environment and test | `test_uvm.py` | Instances, connections, reset, stimulus, drain and check phases |
| Evidence/run identity | `evidence.py`, `run.py` | Source/configuration/tool digests and execution artifacts |

The same BFM and model run in [test_plain.py](../examples/ready_valid/test_plain.py) without importing pyuvm. This demonstrates that the evidence boundary does not depend on UVM. Use pyuvm's existing factory, phasing, sequencers and analysis connections when you need them; the companion does not implement another UVM runtime.

## Build a new environment

1. Write the DUT contract first: accepted transfers, response matching, latency bounds, reset cancellation, errors and X/Z policy. Specify which signals are meaningful on idle cycles.
2. Create a new example or a verification directory in your DUT repository. Define transaction fields and an explicit configuration holding HDL handles. `StreamConfig.bind` is only a convenience for this example's names; construct the configuration directly for a different hierarchy. Supply HDL acceptance snapshots through `capture`, or implement and qualify an equivalent sampling adapter. The streaming example rejects a missing capture instead of silently reading the live bus.
3. Implement the driver and monitor separately. Drive on a safe phase. Capture acceptance values in HDL before sequential nonblocking updates, then read those snapshot registers after `RisingEdge` and `ReadOnly`. A RisingEdge callback can already see post-update live pins on VCS and other simulators; ReadOnly makes live outputs settled, not pre-update. Both monitors and driver handshake decisions must use the captured values. Do not infer actual transfers from successful driver calls. See docs/19_SIMULATOR_PORTABILITY.md for the sampling contract and race regressions.
4. Compose agents in the parent environment's build phase, assign configuration/role before child build, and connect each monitor's analysis port to the scoreboard in connect phase. For multiple instances, use distinct logical interface IDs and independent outstanding queues. Share a model only when its contract explicitly spans the channels.
5. Predict from accepted input observations and independently compare observed outputs. Define queues or ID-indexed outstanding maps, timeout handling, and reset epochs. Keep unknown values as bit strings until the checker applies its policy. Never feed the scoreboard only the intended sequence values.
6. Define a catalog of requirements, bins, checkers and obligations with measurable goals. Sample a functional scenario only when the relevant behavior occurs; attach the exact observed event IDs to checker results. Raw hits and generated transactions do not prove closure.
7. Add legal random stimulus, then target uncovered scenarios with bounded sequences. The stream example uses a private seeded Python RNG for legal 8-bit values and deterministic backpressure. For relational constraints and solver-backed randomization, reuse the pattern in `examples/apb_peripheral/tb/apb_random.py`, not APB-specific fields. Give each component a stable seed/stream identity, preserve generated actions, and never promise cross-version seed equivalence.
8. Finalize after a bounded drain. Report pending requests, failed comparisons, exceptions and unknown states. Prove checker sensitivity with deliberate corruption, dropped/extra responses, stall violations, reset interruption and X/Z tests appropriate to your protocol. Require positive tests and intended negative detections before claiming support.

The [reusable scoreboard library](27_REUSABLE_SCOREBOARDS.md) supplies FIFO/unique-tag matching, transformation and stateful prediction callbacks, deadlines, reset epochs and linked checker evidence. The protocol adapter still reconstructs accepted observations and defines the independent DUT contract.

## Public evidence boundary

`EvidenceRecorder(catalog, manifest)` is a standard-library-only writer. Build these schema objects using your versioned verification plan and run identity; see [model.py](../src/verification_evidence/model.py) and the complete [stream session](../examples/ready_valid/evidence.py). Its methods are:

```python
from verification_evidence import EvidenceRecorder, dump, summarize

# catalog and manifest are the project's declared plan and current run identity.
recorder = EvidenceRecorder(catalog, manifest)
event_id = recorder.observe(
    interface="port0", epoch=0, correlation="request-7", tick=100,
    kind="transfer", payload={"data": {"width": 8, "bits": "10100101"}})
# The independent scoreboard computes outcome from actual observations/model state.
recorder.evaluate(
    obligation_id=obligation_id, checker_id=checker_id, event_ids=[event_id],
    outcome=outcome, reason=reason, tick=100)
bundle = recorder.finish(pending_by_obligation=pending_counts)
dump(bundle, output_path)
report = summarize(bundle)
```

The snippet shows the API boundary, not a standalone test: the identifiers, outcome, reason, pending counts and output path come from your environment. See the executable examples for complete construction. Recorder bookkeeping does not decide hardware correctness. `finish(error=...)` records an execution error; failures and pending work cannot be overridden with a passing finalization. An empty run cannot earn closure.

For multiple required checkers, call evaluate once per checker using the same exact event-ID group. In schema v1, a group must share one logical interface, reset epoch and correlation. The stream example represents input and output as channels of logical interface `pipe0` and records the channel in payload. Do not link unrelated interface IDs into one group; use separate obligations or explicitly design a common logical observation boundary. Reset invalidates old associations according to the DUT contract.

## Adapting common protocols

| Interface | Required protocol-specific work |
| --- | --- |
| AXI-Lite | Independently reconstruct AW and W handshakes, pair them according to the interface contract, match B responses, and separately handle AR/R. Test independent channel stalls. |
| AXI | Add burst/beat metadata, ID-indexed outstanding state, ordering rules, response errors and backpressure. A FIFO-only matcher is insufficient for permitted reordering. |
| SPI | Define mode, clock edge/bit order, chip-select framing and multi-slave configuration; reconstruct words from observed edges. |
| UART | Define baud tolerance, start/stop/parity rules, framing errors and reset behavior; reconstruct received frames independently. |
| Packet streaming | Add packet boundaries, byte enables, sideband semantics and packet-level predictions; test stalls at boundaries and partial packets. |

These are extension requirements, not shipped VIP claims. The ready/valid example is an elastic-buffer teaching environment, not complete AXI-Stream VIP. Its reset policy discards pending transfers. Qualification covers its normal traffic and corruption case; add protocol-specific reset and error campaigns for your DUT.

APB's recorded pin replay and bounded closure campaign are implemented in its runner. They are not automatically provided to every new agent. A new interface must record its own drive schedule, seeds, compatibility identity and finalization policy before claiming replay or coverage closure. The small stream runner also does not provide APB's process-interruption recovery.

## Prompt for another coding agent

> Clone https://github.com/syakovac-spec/python-verification-companion and read AGENTS.md, README.md and docs/17_EXTENDING_TO_OTHER_INTERFACES.md. Integrate it with my DUT using standard pyuvm agents, or plain cocotb if requested. Start from the ready/valid composition pattern, not by forcing my interface into APB. First derive a versioned interface/DUT contract and coverage plan. Implement independently sampled monitors, a contract-based predictor and automatic scoreboard, constrained legal randomized sequences with isolated seeds, explicit pending/reset/XZ handling, and linked checked coverage. Demonstrate closure with bounded targeting and deliberate checker-negative tests. Record exact tool versions and reproduce on my Python/simulator combination. Clearly identify protocol features and replay/closure capabilities that remain unimplemented.
