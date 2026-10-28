# Project brief

## Problem

Python testbenches can be easy to create and extend, including with AI assistance. A collection of passing tests does not automatically provide reusable agents, independent checking, coverage closure, or evidence suitable for engineering review. Traditional UVM environments provide useful structure, but their broader workflow also depends on language features, simulator instrumentation, verification IP and team practice.

The project makes that workflow explicit for cocotb/pyuvm. Its value is a reliable connection between what was required, what was exercised, what was checked and what remains uncertain.

## Users and jobs

- Verification engineer: reuse an environment and explain remaining verification gaps.
- RTL designer: run a fast local regression and reproduce a failure.
- Technical lead: inspect evidence across configurations without confusing metrics.
- AI coding assistant: discover valid stimulus operations, target a documented coverage hole and obtain deterministic results.

## Product boundary

Build an installable public companion package with an evidence core, execution adapters, regression artifacts and a useful CLI. pyuvm provides the initial UVM methodology integration. Existing libraries provide constraint solving and functional coverage where suitable. The HDL simulator remains responsible for HDL execution and its supported structural coverage/timing/assertion facilities.

The package does not establish complete IEEE UVM compliance, replace formal verification or static timing analysis, or certify an ASIC signoff flow. Support claims require explicit qualification evidence.

## First release scope

1. Versioned requirement/checker/coverage catalogs and run evidence.
2. Separate records for generated intent, observed events and checker outcomes.
3. Deterministic result aggregation with compatibility checks.
4. Manifest-based reproducibility and recorded-stimulus replay.
5. A complete APB peripheral example using cocotb and pyuvm.
6. Directed tests and constrained stimulus through an evaluated library backend.
7. Text/JSON reports identifying uncovered and unchecked obligations.
8. Deliberate DUT defects proving representative checkers detect errors.

## Native simulator workstream

Selectively implement key required SystemVerilog and simulator capabilities in Icarus Verilog. Establish capability probes first, then deliver focused upstream-ready changes with semantic and regression tests. The first planning tranche includes IV0; implementation milestones IV1 onward are scoped from demonstrated gaps. Native SV assertions, interface compatibility and gate-timing capabilities are investigated independently of Python substitutes. See doc 11.

## Later work

Simulator-native coverage adapters, selected UCIS interchange, additional protocols, register model generation/integration, richer temporal checking, gate-level execution profiles, performance optimization, optional AI tool interfaces and a UI. Later features should be driven by demonstrated needs from the pilot.

## Success measures

- A fresh environment can install and execute the documented pilot.
- A seeded failure can be replayed with recorded stimulus and a matching checker failure.
- A generated-but-unobserved scenario receives no observed coverage credit.
- An observed-but-unchecked event is visible and cannot satisfy a checked obligation.
- All listed pilot mutants are detected by their intended checks.
- Duplicate run imports do not inflate coverage.
- Reports preserve failures and incomplete runs while showing valid evidence from other runs.
- The evidence core works without cocotb, pyuvm or a simulator installed.

Public availability should make the method inspectable and reusable. It adds maintenance obligations: support matrix, schema evolution, releases, documentation and issue handling.
