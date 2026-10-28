# Coding agent instructions

## Mission

Implement the companion framework described in these documents in small, executable milestones. Preserve verification credibility: a passing test is useful only when its intended hardware behavior was observed and evaluated by an appropriate checker.

## Start each session

Read README.md, STATUS.md, docs/09_DECISIONS_AND_QUESTIONS.md, and the current milestone in docs/06_IMPLEMENTATION_PLAN.md. Inspect existing code and applicable repository instructions before editing. Keep useful existing work. Establish what actually runs before making compatibility claims.

## Engineering rules

- Inspect installed/pinned dependency APIs and official documentation. Every API in this pack is proposed unless explicitly identified as an external library API.
- Use pyuvm for UVM structure. Do not reimplement its factory, phasing or transaction library inside this package.
- Keep evidence types, validation, merging and reporting importable without a simulator or pyuvm installed.
- Use narrow public adapters; avoid monkey patches and private dependency internals.
- Use explicit types, stable IDs, schema versions and actionable validation errors. Small standard-library dataclasses are acceptable initially; select a validation dependency only for a demonstrated need.
- Record random streams, configuration and environment. Never promise cross-version seed equivalence. Preserve generated stimulus for replay.
- Preserve X/Z values until a checker applies an explicit policy. Never silently coerce unknown hardware values to zero.
- Keep scoreboards independent of stimulus intent. Derive actual transactions from sampled interface behavior and expected results from the documented DUT contract.
- Use simulator scheduling correctly. Document driving and sampling phases; validate reset and same-edge behavior with executable checks.
- Record failed, aborted, incomplete and incompatible runs explicitly. Never turn missing evidence into a pass.
- Do not weaken checkers, goals, exclusions or requirements merely to make a test pass. Changes to verification intent must be clearly identified for user review.
- Keep HDL structural coverage, functional coverage, requirements evidence, assertion results and Python coverage separate.
- Do not create empty plugin hierarchies or speculative backends. Start with one working integration.
- Keep runtime independent of AI credentials and network services. AI adapters use the CLI/structured artifacts after those interfaces are stable.

## Icarus/SystemVerilog workstream

Read docs/11_ICARUS_SV_WORKSTREAM.md. Qualify required native features using positive and deliberate-failure probes. Parsing alone is not execution support. Implement demonstrated gaps in an Icarus checkout under its own instructions, with standard-derived semantic tests and upstream regression checks. Keep compiler changes separate from the companion Python package. Record tool commits/patch digests. Do not silently bypass required assertions or timing checks.

## Work and handoff

Proceed through the requested milestone without asking about routine choices covered by defaults. If a dependency is unavailable, complete independent work, preserve the exact failure, and state the blocked acceptance criterion. Do not substitute fake simulator evidence. Do not claim a milestone complete when required checks were skipped.

For each milestone, update STATUS.md with implemented scope, commands actually executed, outcomes, limitations and the next task. Add consequential changes to the decision log. Report the result succinctly with exact reproduction commands.

Do not publish a repository, upload a package, contact maintainers, or apply a public license merely because public release is planned. Prepare those steps locally until the user requests them. When editing an existing repository, follow its established tools and license.
