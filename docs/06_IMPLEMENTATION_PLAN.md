# Implementation plan

Implement sequential milestones. A milestone is complete only when its acceptance evidence exists. Timelines are intentionally omitted until M0 establishes actual tooling and constraints.

## M0 — Establish dependencies and decisions

Inspect existing repository instructions and environment. Choose a provisional import/CLI name. Investigate compatible Python, cocotb and pyuvm versions from real APIs; compare PyVSC and cocotb-coverage using a small representative constraint/coverage probe. Check licenses and redistribution requirements from current upstream files without choosing the project's license for the user.

Record exact versions, solver/platform constraints, install commands, probe results and unresolved limitations in a dependency note. Keep the evidence core free of optional simulation/solver imports. Use stable releases where practical and record an exact tested dependency set; do not hard-code an unverified 'latest' claim.

Acceptance: documented dependency decision with actual probe results or clearly identified blockers, proposed package layout, and explicit distinction between tested and planned compatibility. M1 may proceed when optional solver/simulator probes are blocked.

## IV0 — Icarus capability inventory

Run the IV0 work in docs/11_ICARUS_SV_WORKSTREAM.md alongside M0 before choosing the first native simulator change. Follow IV1–IV3 there for compiler implementation and qualification. M1 does not depend on a completed compiler patch; simulator-dependent milestones must declare the exact native capabilities they require.

## M1 — Evidence core

Implement typed catalog/run/event/check/coverage records, validation, obligation assessment, exact-key compatibility, deterministic merge and a small CLI for validate/summarize/gaps/merge. Include examples showing all key evidence states.

Acceptance: installable package; core import without simulator dependencies; successful fixtures round-trip; invalid references and incompatible merges rejected; duplicate import idempotence; attempted-only and unchecked scenarios cannot close requirements; failures remain visible; CLI errors return nonzero. Record the actual commands and outputs.

## M2 — Complete directed APB slice

Implement the specified peripheral, cocotb driver and independent monitor, Python reference model, pyuvm environment, directed tests and evidence subscribers. Establish race-free sampling experimentally. Capture manifests and artifacts.

Acceptance: baseline directed tests for APB-001 through APB-008 pass on a recorded Icarus/tool combination; monitor/scoreboard self-tests demonstrate APB-009/APB-010; missing/wrong responses cause intended checker failures. Unsupported or blocked simulator combinations remain unqualified.

## M3 — Constrained scenarios and functional coverage

Integrate the selected backend, per-component random streams, planned bins/crosses and structured gap output. Keep observation/check semantics from the core rather than treating a backend hit as automatic requirement closure.

Acceptance: bounded seeded runs exercise defined scenarios, reports identify intentionally left-open obligations, observed distributions are inspected, and changing an unrelated random stream leaves existing streams stable. Include a replayable sequence trace, even before full replay automation.

## M4 — Replay and defect sensitivity

Implement recorded-stimulus replay, input integrity checks, reset/wait scheduling capture and all pilot mutants. Reconcile pending obligations on timeout/error.

Acceptance: all six mutants compile and fail through intended checks, baseline passes, each failing case replays without random generation, manifest mismatches are rejected or explicitly marked as a divergent reproduction. Store a mutation evidence table.

## M5 — Release candidate and independent workflow

Exercise a clean install, produce examples and a support matrix, and add a plain cocotb example writing the same evidence schema. Verify schema migration/error behavior. Prepare contribution guidelines and release notes.

Acceptance: a fresh user can run the full documented pilot; core and both adapter paths work for exercised combinations; public interfaces and limitations are documented; license/package-name decisions are recorded before any publication. Actual publication remains a separate user-requested action.

## M6 — Selective expansion

The prioritized [extension TODO backlog](20_EXTENSION_BACKLOG.md), recorded 2026-10-29, expands this milestone into individually scoped items EXT-01 through EXT-10 with acceptance criteria. Start performance measurement early; the recommended deliverables are a reusable agent/scoreboard kit, performance/scalability improvements backed by measurements, and an AXI-Lite reference environment. Separate Icarus, encrypted-model and SV-UVM interoperability workstreams must not become package prerequisites. This is future work and does not close the remaining M5 criteria.

Prioritize measured gaps: selected UCIS interchange, simulator-native metrics, commercial simulators, register integration, another protocol, gate-level profiles, broader temporal checking, optional AI tool interface. Each capability gets a bounded contract, executable probe and acceptance gate. Do not treat M6 as a single task.

## Follow-on prompts

### After M1

Read AGENTS.md and STATUS.md. Implement M2 only, following docs/05_APB_PILOT.md. Inspect the installed cocotb/pyuvm APIs before writing adapters. Demonstrate correct APB sampling and independent checking. Run the directed baseline and negative checker tests; record the commands, actual results and support limitations. Preserve the evidence semantics and update STATUS.md.

### After M2

Implement M3 using the dependency decision established in M0. Add bounded constrained scenarios and observation-based coverage without weakening existing checks. Show a deliberately uncovered obligation, an observed-but-unchecked case and checked-pass evidence. Verify random-stream independence and document actual backend support.

### After M3

Implement M4. Record and replay stimulus without calling random generation. Add the six specified DUT mutants and verify their intended checker failures against a passing baseline. Detect manifest mismatch and incomplete runs. Report exact reproduction commands and unresolved replay limitations.

### Before release preparation

Implement M5 locally. Verify a clean installation, documentation commands, dependency boundaries and demonstrated support matrix. Prepare public project metadata, contribution guidance and release notes. Identify owner decisions for license/name/publication. Do not publish, upload packages or contact maintainers as part of this task.
