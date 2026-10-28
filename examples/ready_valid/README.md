# Ready/valid extension example

From the repository root, with the simulation dependencies installed:

```sh
python examples/ready_valid/run.py
```

The runner qualifies pyuvm and plain-cocotb versions against both the correct elastic-buffer RTL and a deliberately corrupted variant. It returns success only when the correct DUT closes the declared goals and the corrupt DUT fails ORDER. Select one composition style with `--mode uvm` or `--mode plain`.

Read [the extension guide](../../docs/17_EXTENDING_TO_OTHER_INTERFACES.md) before adapting this example. Start at `test_uvm.py` for environment composition, `uvm_components.py` for agents and analysis connections, `bfm.py` for handle configuration and scheduling, and `model.py` for independent checking and the functional plan. `test_plain.py` reuses the same BFM and model without importing pyuvm.

The example exercises legal seeded data, deterministic backpressure, observed FIFO data/order, stable valid/data during stalls, and final drain. It is an 8-bit elastic-buffer example, not complete AXI-Stream VIP. Python-only counterexamples in `tests/test_stream_model.py` additionally exercise corruption, unexpected/missing output, stall violations, unknown values and reset accounting. Protocol-specific random constraints, reset campaigns, packet semantics and replay must be added for a new DUT.
