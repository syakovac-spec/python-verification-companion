# Generate and adapt an agent kit

EXT-01 provides a dependency-free generator packaged in the installed wheel.
Its first template is an ordered ready/valid stream with one packed data field,
active-low reset, and reset-discard semantics. Other protocols require explicit
BFM/model implementation; this command does not infer a protocol from pin names.

From a checkout, using your active Python or conda environment:

```sh
python -m pip install -e '.[simulation]'
vevidence create-agent --interface interfaces/packet16.json --output verification/packet16
cd verification/packet16
python -m unittest test_contract -v
python run.py --sim icarus
python run.py --sim verilator
```

`python -m verification_evidence.cli create-agent` is equivalent. Core-only
installation suffices for generation and pure checker tests. Simulation requires
cocotb, pyuvm for the UVM path, and an installed supported simulator. Use
`python run.py --mode plain --sim vcs` for a plain-cocotb commercial-backend run;
VCS execution still needs local licensed qualification. Existing backend flags
and environment behavior are described in [portability](19_SIMULATOR_PORTABILITY.md).

## Interface schema version 1

The JSON example [packet16.json](../interfaces/packet16.json) declares every
required field: `schema_version`, `name`, `protocol`, `width`, `clock`, `reset`,
`reset_policy`, `fields`, and `channels`. Unknown keys and unsupported versions
are rejected. Width is an integer from 1 to 4096; this is an input bound, not a
qualification claim at every width. `fields` contains one packed `data` field
with that width. `tx` is the source role and `rx` the sink role, each binding
`valid`, `ready`, and `data` to distinct top-level HDL identifiers. Passive mode
is selected on a generated agent instance and creates no driver/sequencer.

Generation is deterministic and refuses an existing output directory. The
generated files are user-owned editable source, not runtime plugin stubs. A
staging directory prevents partial output on a generation failure. The generated
README maps configuration, transaction/sequence, agents, protocol BFM, reference
prediction, coverage plan, scoreboard, environment, tests and runner to files.

## Real DUT handoff

Give another coding agent this prompt with the DUT specification and source paths:

> Read the generated README and interface.json. Integrate the supplied DUT into
> rtl/stream_top.sv and update run.py sources/parameters. Preserve HDL acceptance
> snapshots read after ReadOnly; do not use live RisingEdge values as pre-update
> truth. Implement reference.py prediction from independently observed accepted
> inputs. Review model.py ordering, reset, outstanding and timeout policies against
> the specification; replace bfm.py behavior if this is not ready/valid. Update
> coverage_plan.py with traceable requirements and meaningful checked goals.
> Connect monitor analysis ports to the scoreboard, never driver intent. Retain
> source/sink/passive composition and plain-cocotb support. Extend test_contract.py
> and RTL negative variants to detect missing, unexpected, malformed and reset
> failures. Run positive closure and negative qualification on the available
> simulators. Report exact commands, gates and any unqualified behavior.

The stock predictor is identity, not a general DUT reference model. The generated
traffic uses an isolated seeded RNG constrained to a legal integer interval.
General constraint solvers, adaptive closure and replay remain in the APB example;
they are not automatically synthesized by this template. Full AXI/APB generation,
out-of-order matching and subcycle asynchronous reset observation remain follow-up
work. Missing/unexpected/reset/malformed cases in `test_contract.py` are synthetic
checker tests, explicitly separate from simulator evidence. The RTL runner tests
positive closure and deliberate data corruption in both composition styles.
