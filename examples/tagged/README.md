# Tagged transformation example

This bounded RTL DUT accepts two requests, XORs their 8-bit data with `0x5a`, and
returns the second request's ID/data first. The plain-cocotb monitor reads HDL
acceptance snapshots and feeds the reusable tagged scoreboard independently of
the driver. It uses one response per unique outstanding ID.

```sh
python examples/tagged/run.py --sim icarus
python examples/tagged/run.py --sim verilator
```

Each command runs permitted reordering, wrong-data, forbidden-reordering and
missing-response cases. The outer command requires positive closure and the
intended negative checker failures; failed raw runs remain failed. Fresh evidence
is under `evidence/tagged/`, or `--out NEW_DIRECTORY`. Each case retains sources,
configuration/dependency/tool identities, logs, simulator XML and evidence.

See [the scoreboard guide](../../docs/27_REUSABLE_SCOREBOARDS.md) for reset,
deadlines, X/Z and stateful-model policies. This is not a general tagged-bus VIP
or a recorded-stimulus replay implementation.
