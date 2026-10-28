# Architecture

This document retains the original architectural proposals. The implemented evidence API is documented in docs/14_EVIDENCE_CORE.md; the public EvidenceRecorder and standard pyuvm/plain-cocotb composition are documented in docs/17_EXTENDING_TO_OTHER_INTERFACES.md. Use those executable interfaces when extending the package. Unimplemented layers below remain proposals.

## Layers and ownership

| Layer | Owns | Does not own |
| --- | --- | --- |
| Evidence core | Records, catalogs, validation, compatibility and merge policy | HDL handles, simulation scheduling, random solving |
| Reports/CLI | Gap queries, run summaries, validation and replay orchestration | Independent truth about hardware correctness |
| Execution services | Manifests, artifacts, stimulus traces and isolated run directories | UVM phase implementation |
| cocotb adapter | Time/clock/reset context, task lifecycle and signal access | A replacement HDL simulator |
| pyuvm adapter | Analysis subscribers and binding evidence to existing agents/checkers | Reimplementation of pyuvm core |
| Coverage/constraint adapter | Translation to a selected backend with explicit supported subset | Claims of full SV feature parity |
| Reference environment | APB driver, monitor, contract model, checks and scenario coverage | Generic project requirements |
| Optional AI adapter | Structured discovery, run requests and evidence retrieval | Pass/fail authority or automatic waivers |

Dependencies point inward toward the pure-Python core. An evidence record must not contain a simulator handle or a pyuvm object. Adapters translate live objects into serializable values.

## Proposed source layout

```text
src/<provisional_package>/
    core/           # catalogs, records, validation, aggregation
    reporting/      # JSON and text views
    execution/      # manifests, artifact management, replay
    adapters/       # add cocotb and pyuvm integrations when needed
    cli.py
examples/apb_peripheral/
    rtl/
    tb/
    verification_plan/
tests/
    unit/
    fixtures/
    integration/
docs/
```

Create modules when required by a milestone. This tree describes responsibility, not a demand to create empty files. The final import name is selected in M0; documentation commands use `<tool>` until the CLI exists.

## Execution flow

Before simulation, validate the verification catalog and execution profile, resolve configuration, create an isolated run ID and capture inputs. During simulation, the generator issues stimulus; the interface monitor publishes observed events; reference models/checkers evaluate relevant events; coverage subscribers classify those same observed events. The evidence writer records references between these records.

At shutdown, stop new stimulus, drain or explicitly abort pending operations under a bounded policy, reconcile checkers and scoreboards, and finalize artifacts. An unhandled exception or simulator failure must leave an incomplete/error run record rather than a plausible pass summary.

After simulation, validate referential integrity and artifact digests, then create reports. Aggregation is a separate operation over immutable finalized run artifacts.

## Scheduling boundary

Document the bus sampling point and drive phase once in the APB adapter. Monitor values at a defined stable sampling point consistent with APB's clock-edge semantics and DUT sequential behavior. Validate that this samples the accepted transfer rather than post-edge outputs for the next cycle. Use captured pre-update values or an HDL sampling shim if required; do not assume a generic `RisingEdge` plus `ReadOnly` pattern solves every protocol race.

Simulation tasks follow cocotb's scheduling model. Ordinary asyncio services must not be mixed into live simulation tasks without a documented bridge. Unit tests of the evidence core do not require simulation scheduling.

## Performance boundary

Publish protocol-level events where possible. Do not serialize every gate transition into Python. Capture bounded signal snapshots around failures and keep simulator-native waveforms as artifacts. Measure event throughput and logging overhead before adding concurrency infrastructure.

## Gate-level extension

Keep transaction stimulus/checking reusable through interface contracts. Profile-specific adapters handle latency, reset, cell libraries, SDF, hierarchy/backdoor mappings and simulator flags. Timing violations and annotation diagnostics remain simulator artifacts linked into the run. Functional tests do not substitute for STA, CDC/RDC, formal equivalence or technology characterization.
