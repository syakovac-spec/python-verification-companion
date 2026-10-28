# IV0 results and bounded IV1 proposal — 2026-10-23

## Observed capability matrix

Commands, stdout/stderr, binary SHA256 identities, versions, and classifications are preserved in [matrix.json](../evidence/iv0/matrix.json). The installed compiler/runtime is Icarus 11.0 stable on Ubuntu 22.04/WSL2. No compiler patches were applied; no upstream build is qualified.

| Probe | Compile/elaboration | Runtime | Observation |
| --- | --- | --- | --- |
| Immediate assert, `-g2012 -gassertions` | Succeeds | True passes; false/X/Z each execute `$fatal`, exit 1 | Expected unique failure marker captured |
| Same, `-gno-assertions` | Succeeds | All modes exit 0; action blocks absent | Classified ignored, never assertion-qualified |
| `@(posedge clk) req |=> ack`, assertions enabled | Syntax/property-spec error | Not reached | Tested subset compile-rejected |
| Same, assertions disabled | Same compile rejection | Not reached | Disabling checks does not make this syntax parse |
| NBA callback sampling | Succeeds | Four clock edges checked | RisingEdge sees 0..3; ReadOnly sees 1..4; HDL capture retains 0..3 |
| pyuvm public integration | Succeeds | Build/connect/run/check phases and analysis port/subscriber pass | Expected transaction received |
| Deliberate cocotb negative | Succeeds | NBA test fails with sentinel; pyuvm test still passes | XML contains exactly the intended failed test |

The positive cocotb/pyuvm run has 2 passes. The negative run has 1 intentional failure and 1 pass; the probe harness succeeds only after inspecting the XML failure. A simulator process exit alone is insufficient qualification. [nba.xml](../evidence/iv0/nba.xml) and [nba-negative.xml](../evidence/iv0/nba-negative.xml) retain the individual test results.

Source files are in `probes/icarus`. Run `.venv-linux/bin/python probes/icarus/run.py` in Ubuntu from the package root. Expected failed simulations are evidence, not defects in the probe harness. Matrix generation records unsupported capabilities without claiming all capabilities passed. Missing tools are classified blocked.

The NBA experiment is deliberately small. It does not establish arbitrary APB acceptance sampling or all simulator scheduling combinations. M2 must validate pre-edge read/error/acceptance state, reset, and zero-wait transitions; use an HDL capture shim if needed. Native SVA sampling is distinct from cocotb callbacks.

## Standard and source grounding

Use IEEE 1800-2017 clause 16.3 (immediate assertions), 16.5.1 (sampling), 16.12.7 (implication), 16.14 (concurrent assertions), and clause 4 (scheduling). The [IEEE standard text hosted by MIT](https://fpga.mit.edu/6205/_static/F25/documentation/1800-2017.pdf) was available through indexed excerpts; the full PDF exceeded the browsing tool's size limit. Full clause review is required before implementing native semantics. The immediate assertion probe uses the specified treatment of 0/X/Z as failure. The implication probe supplies the response on the following clock, with an otherwise identical absent-response case.

The [Icarus flag documentation](https://steveicarus.github.io/iverilog/usage/command_line_flags.html) distinguishes assertion controls from language generation. The inspected [upstream parser](https://github.com/steveicarus/iverilog/blob/master/parse.y) contains explicit unsupported concurrent-assertion branches; parsing alone does not imply a runtime engine. A remote HEAD lookup returned `1a663cb33a9d8e70f6f3f5e9077120c60dcb6e06`. That revision was not built or regression-tested here. Reproduce the gap on a pinned upstream checkout before coding; do not attribute the installed 11.0 result to current HEAD.

## Ranked backlog

1. **P1 demonstrated gap:** the tested single-clock non-overlapped implication cannot compile on installed 11.0. Investigate a native bounded response slice on current upstream.
2. **P0 qualification to retain:** immediate assertion execution/failure propagation and pre/post-NBA VPI observation work in these probes. No simulator fix is justified by these results.
3. **P0 next integration investigation:** actual APB constructs and same-edge/reset behavior in M2; no defect has yet been demonstrated.
4. **Not investigated:** bind, interface/modport forms, clocking blocks, specify/SDF/timing checks/notifiers, native structural coverage. Keep these out of the supported matrix until probed.

## IV1 proposal: one-cycle native response assertion

Proposed first target: `assert property (@(posedge clk) request |=> response) else $fatal(...)`, with scalar four-state Boolean operands and a single clock. First reproduce on current upstream and review its contribution/build/regression instructions. The compiler contribution destination is Icarus Verilog, in a separate checkout. This is a proposal, not an implemented patch or promise of general SVA support.

Define acceptance before editing: sampled antecedent at cycle n, consequent at n+1; consecutive triggers; true/false/X/Z operands; never-triggered vacuity; consequent just early/on-time/late; NBA-updated operands; separate concurrent properties; correct failure action timing/identity. End-of-run pending obligations must remain visible in the evidence adapter, without changing the standard's native property semantics. Initially reject ranges, multiclock forms, sequences, sampled-value functions, and `disable iff` explicitly. Reset-aware properties are a subsequent slice after asynchronous disable semantics are reviewed; do not advertise this first slice as the full APB temporal checker.

Likely affected layers: grammar/property representation, elaboration, vvp lowering, sampled-value storage and scheduling, and assertion action scheduling. Parser acceptance alone is not completion. Require failing-before/passing-after positive and deliberate-negative probes, targeted standard-derived boundary tests, applicable upstream regressions, and companion integration. If the feature is already implemented upstream, qualify the newer version and select another demonstrated gap instead. Native engine results, non-vacuous activation, and companion closure credit remain separate.
