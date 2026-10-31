# Extension TODO backlog

Recorded 2026-10-29 at the owner's request. All unchecked items below are future work, not implemented capabilities or compatibility claims. Existing agent examples, timing/solver profiles and evidence APIs are starting points; these TODOs describe the additional reusable tooling and qualification needed. Recording this backlog does not mark M5 complete or authorize implementing every item at once.

## Priorities and delivery sequence

| ID | Extension | Priority | Delivery grouping |
| --- | --- | --- | --- |
| EXT-01 | Agent generator and reusable agent kit | Highest | A: agent and scoreboard kit |
| EXT-02 | Performance benchmarks and profiling | Highest | B: performance and scalability |
| EXT-03 | Build caching and parallel regressions | High | B |
| EXT-04 | Reusable scoreboard library | High | A |
| EXT-05 | Functional coverage planning and closure tools | High | A, then C |
| EXT-06 | Portable sampling adapters | High | A |
| EXT-07 | Scalable evidence storage | High | B |
| EXT-08 | Additional protocol agents | Medium | C: AXI-Lite reference, then further protocols |
| EXT-09 | Register abstraction layer | Medium | Follow A and C |
| EXT-10 | Failure triage and replay tools | Medium | Follow B and C |

Recommended sequence: establish the performance baseline early, build the reusable agent/scoreboard/sampling interfaces, optimize measured bottlenecks, and exercise those interfaces with AXI-Lite. Do not defer measurement until after optimization.

| Deliverable | Acceptance criterion |
| --- | --- |
| A: reusable agent and scoreboard kit | Build a new interface environment without modifying the evidence core; generated positive and negative tests execute. |
| B: performance and scalability baseline | Publish reproducible time/memory breakdowns and demonstrate improvements with unchanged verification results. |
| C: AXI-Lite reference environment | Independently monitor all channels, close declared functional goals, and detect deliberate protocol/data defects on available simulators. |

## EXT-01 — Agent generator and reusable agent kit

- [x] Define a versioned interface description for signal bindings, widths, clock/reset, protocol roles and transaction fields.
- [x] Generate transaction, configuration, sequence, sequencer/driver, monitor, active/passive agent, scoreboard, coverage-plan, environment and test files using standard pyuvm composition. Preserve a plain-cocotb integration path.
- [x] Provide explicit implementation points for protocol behavior and the independent DUT reference model. Do not generate a scoreboard that treats the driver's intended values as observed truth.
- [x] Generate executable tests for positive traffic, missing/unexpected responses, reset interruption and malformed traffic where applicable.
- [x] Document the generated files and provide an agent handoff example for integrating a real DUT.

Implemented 2026-10-29 for the bounded ready/valid template: see [generation and real-DUT handoff](21_AGENT_GENERATOR.md). The executable command is `vevidence create-agent --interface interfaces/packet16.json --output verification/packet16` (JSON, schema version 1). A generated 16-bit environment with renamed pins closes positive coverage and detects corrupted data in pyuvm and plain cocotb on Icarus 13 and Verilator 5.052. Six synthetic checker tests separately exercise positive/missing/unexpected/reset/stale/malformed cases. Generation and checker tests also run from an installed core-only wheel outside the checkout. Arbitrary protocol synthesis, general solver generation, and RTL reset/malformed mutation campaigns are not claimed; adapt and qualify the explicit hooks for a real DUT. EXT-04/05/06 remain separate work.

## EXT-02 — Performance benchmarks and profiling

- [x] Add a long-running small DUT benchmark to expose Python callbacks, solver and evidence overhead.
- [x] Add a larger RTL workload to expose simulator execution cost and memory growth.
- [ ] Add a representative real-design benchmark when a suitable design is available.
- [ ] Separate compile/elaboration, startup, RTL execution, Python/VPI callbacks, constraint construction/solving, checking, evidence output and peak memory. Extend the existing timing and constraint-profile tools rather than duplicating them.
- [x] Record exact tools, flags, environment, generated stimulus, check/trace settings and warm/cold build conditions. Use repeated measurements and report variability.
- [ ] Compare supported simulator/dependency/solver combinations on equivalent workloads. Obtain a licensed VCS baseline when available; keep unavailable tools explicitly unqualified.
- [ ] Establish regression thresholds for runtime and memory after measuring stable baselines.
- [ ] If callbacks dominate, prototype transaction batching and HDL or compiled driver/monitor implementations behind the same agent interface. Preserve scoreboards and coverage plans across execution implementations.

Acceptance: publish reproducible breakdowns and demonstrate improvements without removing checks or changing coverage intent. The previously suggested goal of within 2x VCS steady-state runtime is provisional, requires an agreed workload and measured VCS baseline, and is not a performance promise. Report compile time, single-test runtime and regression throughput separately.

Local implementation (2026-10-30): [benchmark harness and profiling guide](22_PERFORMANCE_BENCHMARKS.md). Repeated Icarus/Verilator runs compare handle lookup versus cached sampling, plus a measured core canonicalization optimization with identical evidence and summary hashes. Native RTL/VPI attribution and compiler/process-tree memory remain unmeasured; licensed VCS and customer RTL baselines remain unavailable. Conditional HDL batching is deferred because the larger workload is dominated by RTL/scheduler residual rather than monitor reads. Thresholds are provisional and reject noisy/incompatible comparisons. EXT-02 is not fully externally qualified.

## EXT-03 — Build caching and parallel regression execution

- [x] Cache compiled designs by source/include content, parameters, defines, tool identity, backend and relevant build options.
- [x] Reuse compatible builds across seeds and replay runs; reject stale/incompatible entries and handle concurrent cache access safely.
- [x] Schedule independent tests/seeds in bounded parallel processes with isolated artifacts and configurable CPU, memory and commercial-license limits.
- [x] Retain individual failed, aborted, timed-out and incomplete runs in aggregate reports.
- [x] Evaluate Linux-native build/artifact storage versus Windows-mounted WSL paths as a measured environment option.

Acceptance: prove cache invalidation and concurrent-run isolation, then measure turnaround/throughput improvement. Do not describe regression parallelism as faster execution of an individual simulation.

Bounded implementation: see [EXT-03 guide](24_BUILD_CACHE_AND_REGRESSIONS.md) and `evidence/cache-regression-summary.json`. Linux/WSL default-build caching qualifies Icarus 13 and Verilator 5.052; other backends/custom options bypass reuse. Budgets govern admission, not hard resource enforcement. Commercial cache relocation/dependency qualification remains follow-up.

## EXT-04 — Reusable scoreboard library

- [ ] Implement ordered/FIFO matching from accepted input observations to observed outputs.
- [ ] Implement tagged matching with ID-indexed outstanding requests and explicitly permitted response reordering.
- [ ] Implement stateful prediction hooks for register files, memories, counters and architectural state.
- [ ] Support transformation callbacks so users can express behavior without rewriting matching machinery.
- [ ] Standardize deadlines, duplicate/unexpected response detection, reset epochs/cancellation, pending-work accounting and final drain checks.
- [ ] Automatically link predictions, observed event groups, checker outcomes and coverage evidence using valid schema correlations.

Acceptance: reusable implementations pass model tests and simulator examples, and detect missing, duplicate, wrong, reordered-when-forbidden, late and cross-reset responses. Expected behavior must remain independent of stimulus intent. Preserve X/Z until an explicit checker policy applies.

## EXT-05 — Functional coverage planning and closure tools

- [ ] Simplify declarations of bins, crosses, applicability and coverage-to-requirement/checker mappings.
- [ ] Report whether an open requirement lacks stimulus, observed behavior, checker evidence or a passing check.
- [ ] Associate targeting sequences with open goals and execute bounded, reproducible closure campaigns.
- [ ] Attribute simulation and solver time to the goals/scenarios being pursued.
- [ ] Explain why a bin remains open and preserve failed, excluded and incomplete states in reports.

Acceptance: demonstrate absent-stimulus, observed-but-unchecked, failed-check and satisfied cases, plus targeted closure and an intentionally unreachable/uncovered goal. Never lower thresholds, silently waive obligations or count generated transactions as checked coverage.

## EXT-06 — Reusable portable sampling adapters

- [ ] Package the HDL acceptance-snapshot pattern as reusable sampling components and documented bindings for generated agents.
- [ ] Define clock/reset, acceptance phase, sampled values and settled-state observations separately; support protocol-specific edge/framing adapters when a single clocked handshake is insufficient.
- [ ] Require a qualified adapter instead of silently falling back to live RisingEdge values.
- [ ] Add early/late callback, same-edge update, reset and backpressure regressions across available simulators; run licensed VCS qualification when accessible.

Acceptance: identical intended transactions are reconstructed despite callback timing differences, and protocol violations remain detectable. Preserve the VCS race fix described in [the portability guide](19_SIMULATOR_PORTABILITY.md); do not assume ReadOnly makes live pins represent pre-update values.

## EXT-07 — Scalable evidence storage

- [ ] Stream evidence and use compact/buffered records where measurement justifies them.
- [ ] Bound memory for long runs while retaining enough outstanding state for correct matching, timeout and drain checks.
- [ ] Define chunk finalization, integrity, crash recovery and incomplete-tail behavior before reducing flush frequency.
- [ ] Add indexed queries over large regressions while preserving inspectable export and exact compatibility checks.
- [ ] Measure memory, write/query throughput and recovery behavior on long runs. Select a database or binary format only after demonstrating the need.

Acceptance: process a declared large workload with bounded memory; reproduce summaries and failure evidence from persisted records; never convert a truncated or missing tail into a pass. Recording only completed transactions must not hide stalled-control violations or missing responses.

## EXT-08 — Additional protocol agents

- [ ] Build AXI-Lite next as the reference for independently arriving address/data channels, channel-specific backpressure, response matching and multiple monitors.
- [ ] Extend ready/valid to packet streaming with packet boundaries, byte enables, sideband rules and packet-level prediction.
- [ ] Add SPI and UART examples with protocol-specific edge/bit sampling, framing, configuration and error checks.
- [ ] Add full AXI only after tagged matching, bursts, outstanding IDs and ordering/reordering rules are established and independently tested.

Acceptance for each protocol: publish its supported subset and contract, configurable agent roles, independent scoreboard, legal constrained stimulus, checked functional goals and deliberate negative tests. Qualify on available simulators and identify unsupported features. Do not label an elastic-buffer example as complete AXI-Stream VIP.

## EXT-09 — Register abstraction layer

- [ ] Define register maps, fields, reset values and access policies, including read-only and write-one-to-clear behavior.
- [ ] Add reusable frontdoor sequences through protocol agents and independent prediction from monitored bus activity.
- [ ] Provide optional backdoor access with explicit capabilities and distinct evidence semantics; backdoor success must not count as frontdoor protocol verification.
- [ ] Exercise reserved fields, aliases, errors, side effects and reset behavior in a complete example.

Acceptance: reuse one register model through more than one frontdoor adapter, demonstrate access-policy checks and deliberately faulty DUT detection, and distinguish predicted state from observed/readback state.

## EXT-10 — Failure triage and replay tooling

- [ ] Group equivalent failures by meaningful checker signatures while preserving every original run and distinct root-cause evidence.
- [ ] Minimize failing generated stimulus while preserving legal dependencies, reset history and the intended checker failure.
- [ ] Link events/checks to waveform timestamps and relevant signals; keep useful diagnostics available without waveforms.
- [ ] Extend recorded replay beyond the APB-specific runner through explicit per-protocol drive/sampling contracts.
- [ ] Distinguish exact replay from intentional reproduction under changed tools/configuration.

Acceptance: reproduce and minimize a known defect without consulting the original random generator, preserve the failure identity, and reject incompatible exact-replay inputs. Do not merge unrelated failures simply because their final pass/fail statuses match.

## Independent workstreams

- [ ] **Icarus improvements:** retain Icarus as a first-class backend; profile VVP scheduling, vector operations and VPI costs on representative workloads. Develop only justified upgrades in a separate compiler checkout with semantic and performance regressions. Follow [the Icarus workstream](11_ICARUS_SV_WORKSTREAM.md). No Icarus patch may become a prerequisite for using other simulators.
- [ ] **Encrypted-model support:** investigate vendor-authorized unencrypted/compiled models, supported commercial-simulator execution and any feasible IEEE 1735 integration. Document required keys, vendor cooperation, language support and licensing boundaries. Parsing an encryption envelope is not demonstrated encrypted-IP execution. Keep this separate from the core package.
- [ ] **Full SV-UVM interoperability:** define a concrete coexistence/bridge use case and qualify simulator capabilities before implementing it. Do not reimplement pyuvm or imply that the current Python agents execute arbitrary SV-UVM VIP.

These workstreams are optional extensions, not prerequisites for agent creation, evidence collection or simulator portability.

## Completion and handoff rules

Keep M5's outstanding schema-migration and independent release-hardening work visible in [STATUS](../STATUS.md). This backlog expands M6; it does not replace existing acceptance criteria. For each selected item, record scope, dependencies, commands, measurements, positive/negative tests, supported combinations and limitations. Check off an item only after its acceptance evidence exists, and link that evidence here or from STATUS. Preserve the active Python/conda environment, backend selection, independent checking and conservative evidence semantics throughout.


## UCIS interoperability - owner-prioritized 2026-10-31

- [x] UCIS 1.0 functional XML export with authoritative evidence sidecars.
- [x] Compatible evidence-aware merge, run deduplication, threshold preservation and external round-trip checker.
- [x] Independent PyUCIS schema/read/write qualification and detection of external merge goal loss.
- [ ] Qualify named commercial importer/database versions and document their native merge routes.
- [ ] Add further UCIS metrics only with separate semantics and validation.

See [UCIS interchange](25_UCIS_INTERCHANGE.md); this does not replace EXT-04 or declare commercial qualification complete.
