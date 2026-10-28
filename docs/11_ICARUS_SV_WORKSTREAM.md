# Icarus Verilog and required SystemVerilog capabilities

## Expanded objective

The project includes selective implementation of needed SystemVerilog and simulator capabilities in Icarus Verilog. The goal is an end-to-end open verification flow: Python methodology and evidence management above a trustworthy simulator, with native HDL features where they add necessary semantics, compatibility or performance.

This is an additional engineering workstream, not merely a fallback if Python encounters a problem. Its first deliverable is an executable capability matrix and ranked patch backlog. Actual simulator features are implemented as bounded, separately tested changes in an Icarus checkout, targeting upstream contribution.

## Current-source grounding

Icarus documents language-generation selection and separately controlled assertion/specify behavior. Its command-line guide explicitly describes configurations in which assertions or specify constructs are parsed but ignored. Therefore parsing or successful compilation alone is insufficient qualification. Consult the exact release/build documentation and test runtime behavior. Do not assume a language-year flag means full implementation of that standard.

Sources: [Icarus source](https://github.com/steveicarus/iverilog), [compiler flags](https://steveicarus.github.io/iverilog/usage/command_line_flags.html), [documented quirks](https://steveicarus.github.io/iverilog/usage/icarus_verilog_quirks.html). These were inspected while preparing the pack. No listed candidate feature below has been experimentally classified by this pack.

## Allocation principle

For each capability, ask where its semantics must execute and what existing code needs it. Python can provide transactions, random stimulus, reference models and functional coverage. Native HDL support is valuable for existing DUT assertions, precise sampled timing, bound monitors, unmodified RTL/library compatibility and performance close to the event engine.

A Python equivalent may be useful while a native feature is developed, but label its supported semantics honestly. A Python temporal checker is not automatically a conforming SVA implementation. An HDL source translator is another implementation strategy with its own correctness burden, not proof that the simulator supports the original feature.

## Candidate backlog — investigate before declaring missing

| Candidate family | Why it may matter | Initial action / priority |
| --- | --- | --- |
| Required DUT SV types, arrays, packages and elaboration constructs | Compile representative modern RTL unchanged | P0: probe actual pilot/next-DUT constructs; reduce any failure to a minimal case |
| Four-state semantics, event ordering and VPI visibility/callbacks | Correct cocotb observation, driving, force/release and X handling | P0: behavior probes; fixes may be simulator/VPI work rather than SV syntax |
| Immediate assertion/action behavior and diagnostics | Local checks must execute and failures must reach regression status | P0: test true/false/unknown expressions, flags, severity and exit/report behavior |
| Concurrent assertions: a bounded useful subset | Preserve HDL-local protocol and temporal checks | P1: evaluate clocked implication, bounded delays, reset disable and sampled-value functions as individually scoped features |
| `bind` for modules/checkers used by the project | Add checks without editing DUT source | P1: probe target forms and hierarchy; define a narrow supported form first |
| Interfaces and modports required by actual RTL | Reuse existing interface-based designs | P1 when demonstrated need; separate elaboration, access and behavioral issues |
| Clocking blocks / sampled driving mechanisms | Race-free SV testbench interoperability | P1 if required; assess scheduling implications before patching |
| Specify paths, SDF, timing checks and notifier behavior | Gate-level timing profiles | P1 for gate objectives; probe each independently, using known cell models and explicit expected violations |
| Native coverage instrumentation and export hooks | HDL structural metrics and low-overhead native observations | P2: identify useful public interface; instrumentation is simulator tooling, not automatically an SV language feature |
| Native SV covergroups/crosses | Reuse existing SV coverage models | P2 unless a concrete use case promotes it; compare benefit against existing Python coverage |
| SV classes, randomize/constraints, virtual interfaces and full SV UVM execution | Existing SV VIP/testbench reuse | Deferred broad scope; promote only for a specific required workflow and explicit feature subset |

P0 = needed for a credible initial flow; P1 = targeted next capability; P2 = investigate when evidence justifies it. These priorities are proposals and can be revised. A feature that already works needs qualification, not reimplementation. Full SV-UVM compatibility is not an implied requirement of this workstream.

## Capability matrix contract

For every probe record: feature ID, exact language construct/subset, motivating requirement/use case, standard document/revision/clause, installed release version, upstream commit if tested, compiler/runtime commands and flags, expected behavior, actual output, parse/elaboration/runtime classification, VPI observability, pass/fail/unsupported/ignored state and source references.

Keep 'not investigated' distinct from 'unsupported'. Test packaged release and a recorded upstream commit for high-priority failures when feasible. A failure fixed upstream should normally be addressed through an updated supported version, not a duplicate patch.

Use tiny positive, negative and boundary cases. Each assertion probe must include a deliberate violation whose detection is externally verified, plus a passing case. An assertion-disabled build must not be credited as an assertion-covered run. Document how active features are detected, rather than trusting only compiler flags.

## First bounded native-assertion target

After probing, consider a single-clock bounded response property used by APB checks. Define the accepted syntax and semantics before implementation: overlapped versus non-overlapped implication; finite delay bounds; simultaneous triggers; sampled signals; reset disable; end-of-run pending obligations; X/Z behavior; diagnostic identity. If sampled-value functions are required, specify clock history and insufficient-history behavior separately.

Validate overlapping obligations, reset at/between sample points, NBA-updated signals, never-triggered properties, a response at each allowed boundary and a response just outside the window. Reference the standard for actual SVA semantics, including asynchronous disable behavior; do not replace it with an easier Python interpretation.

Native engine outcome, non-vacuous exercise and evidence-package credit are distinct. Preserve assertion results and activation counts through an explicit adapter; do not infer a pass merely from absent simulator error text. General SVA support can require substantial parser, elaborator and scheduling/runtime work; bounded syntax still needs precise semantics.

## Compiler contribution process

1. Inspect the target checkout's AGENTS/contribution/build/regression guidance and current issues/patches.
2. Add a minimal failing test with a standard-derived expectation before changing semantics.
3. Diagnose the responsible layer: preprocessing/parser, elaboration/type system, intermediate representation, vvp code generation, runtime scheduling or VPI.
4. Design the smallest coherent implementation. Document unsupported forms and emit explicit diagnostics; never silently accept and ignore required behavior.
5. Implement parser-to-runtime behavior as needed, with positive, negative and boundary regression cases.
6. Run targeted tests and the required upstream regression suite; record pre-existing failures separately.
7. Run the companion integration probe and one real use case against both baseline and patched binaries.
8. Prepare an upstream patch with motivation, standard reference, semantic scope, tests, compatibility and measured overhead where relevant.

Use differential simulation against another implementation where available, but resolve disagreements using the applicable standard. Agreement between two tools is useful evidence, not a substitute for specified semantics.

Changes belong in an Icarus checkout with its existing license/contribution rules. Keep compiler patches separate from the Python package repository. The companion repository holds probe sources, tested commit references, build recipes and integration contracts. A development branch is acceptable; avoid requiring a permanent proprietary or divergent simulator fork. Do not copy compiler code into a differently licensed companion package.

## Milestones

### IV0 — Feature inventory and minimal probes

Alongside M0, create the matrix and execute at least three probes: immediate assertion true/false detection, a representative concurrent-property case, and callback/sampling behavior under NBA updates. Classify results honestly. Expand the matrix to required DUT syntax and later gate-level features as needed. If tools are unavailable, preserve runnable probe sources and mark execution blocked; do not invent support results.

Acceptance: exact tool identity/commands; expected and actual behavior for each executed case; ranked genuine gaps; proposed upstream destination and rationale for the first patch. M1 evidence-core work can continue independently.

### IV1 — One useful upstream-ready change

Select one demonstrated high-value gap after IV0. Establish its exact feature contract and implement the smallest complete slice in an Icarus checkout. It may be a native assertion semantic slice, VPI defect or an RTL compatibility fix; do not choose solely because a syntax feature is easy to parse.

Acceptance: failing-before/passing-after probe, deliberate failure still detected, applicable upstream regressions run, explicit unsupported forms, reproducible patch/build and companion integration evidence. 'Upstream-ready' does not claim maintainer acceptance.

### IV2 — Integration and support profile

Provide machine-readable required capabilities for execution profiles. Fail preflight if required features are unavailable/disabled. Record baseline/patched simulator revision, patch digest and feature-probe results in manifests. Publish exercised subsets. Evidence collected under different simulator semantics does not merge by default.

### IV3 — Demand-led expansion

Implement subsequent ranked features, each with its own semantic specification and regression suite. Native SVA, gate timing and SV VIP reuse may become distinct multi-release efforts. Preserve the ability to use stock Icarus for profiles whose capabilities it already supplies.

## Prompt for the Icarus workstream

Read AGENTS.md, STATUS.md and docs/11_ICARUS_SV_WORKSTREAM.md. Implement IV0: inspect current Icarus documentation/source and actual tool versions, create a versioned capability matrix and executable probes, and rank gaps based on the companion verification needs. Do not label parsing as execution support. Identify one bounded IV1 change with standard-derived acceptance tests and affected compiler/runtime layers. Do not begin a broad SV implementation or publish/send upstream messages. Preserve exact commands/results and update STATUS.md. Continue independent M0/M1 work if simulator execution is blocked.
