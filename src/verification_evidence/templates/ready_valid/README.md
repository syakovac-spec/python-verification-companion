# Generated ready/valid agent kit

This editable demonstration verifies an ordered elastic buffer. It is not a model
of your DUT until you implement its contract and qualify the adapted environment.

Run from this directory in your own Python/conda environment:

```sh
python -m unittest test_contract -v
python run.py --sim icarus
python run.py --sim verilator
```

Install the companion simulation extra if needed. The runner executes pyuvm and
plain cocotb with both a good buffer and deliberate output corruption. Success
requires closed positive coverage and detected ORDER failure in each negative.
The six pure checker tests exercise positive, missing, unexpected, reset discard,
stale response, and unstable stalled traffic. Synthetic tests do not qualify RTL.

## Files and extension points

- `interface.json` records the versioned generation input; `interface_config.py`
  is the runtime binding configuration. Edit the latter when adapting handles.
- `bfm.py` owns drive/acceptance timing, configuration, independent monitoring,
  seeded bounded stimulus and backpressure. Replace these for a different protocol.
- `uvm_components.py` contains transaction, sequence, driver, monitor, sequencer
  composition, source/sink/passive agents and scoreboard subscriber. Passive
  agents construct only their monitor. Analysis connections carry observations.
- `reference.py` owns prediction from accepted observed inputs and stimulus bounds.
  Implement DUT-specific prediction here; change `model.py` for different ordering,
  latency, reset or matching policies. Never connect driver intent as actual data.
- `coverage_plan.py` defines requirements, checkers, bins and obligations;
  `model.py` implements the automatic scoreboard. Replace goals with reviewed DUT requirements.
- `test_uvm.py` owns environment wiring and test phases. `test_plain.py` uses the
  same protocol/model without pyuvm. `test_contract.py` qualifies checker sensitivity.
- `rtl/stream_top.sv` is demonstration RTL and the sampling harness. Replace its
  buffer with your DUT, retaining or adapting pre-update `s_*` acceptance snapshots.
  Read snapshots after ReadOnly; RisingEdge alone does not guarantee pre-NBA values.
- `run.py` records source/configuration/dependency/tool identity and checks raw
  evidence plus simulator results. Add DUT sources and negative variants here.

The template has one packed data field, active-low reset that discards outstanding
work, one clock, ordered responses, and source/sink roles. Packed subfields, other
buses, asynchronous reset pulses between clocks, and out-of-order responses need
explicit adapter/model work. The RNG enforces a legal interval; general solver
constraints and bounded adaptive coverage closure remain demonstrated by the APB
example, not automatically synthesized here. VCS uses the shared backend adapter;
run local qualification with a licensed installation before claiming support.

The generated model uses `verification_evidence.Scoreboard` for FIFO matching and drain accounting. Edit `reference.predict` for the DUT transformation and retain the monitor-side acceptance and explicit X/Z checks. Reset cancellation follows this kit's declared discard contract. See the repository guide `docs/27_REUSABLE_SCOREBOARDS.md` for tagged matching and stateful callbacks.
