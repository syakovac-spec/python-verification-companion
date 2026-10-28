# Framework requirements

IDs are stable; use them in tests and implementation notes. MUST items are first-release obligations unless a milestone is specified. SHOULD items may be deferred with a recorded reason. A coverage percentage is not sufficient acceptance evidence by itself.

| ID | Requirement | Acceptance evidence |
| --- | --- | --- |
| CORE-001 | MUST provide versioned records for catalogs, runs, events, checker outcomes and coverage evidence. | Round-trip fixtures; reject unsupported major versions and malformed records. |
| CORE-002 | MUST separate simulator-independent data/reporting from execution adapters. | Import and test core in an environment without simulation dependencies. |
| CORE-003 | MUST distinguish generated intent, observed behavior and evaluated outcomes. | Attempted/unobserved and observed/unchecked fixtures stay open. |
| CORE-004 | MUST preserve simulation time as integers plus explicit resolution and retain clock/reset context where meaningful. | No floating-point loss; multi-event ordering and reset-epoch tests. |
| CORE-005 | MUST reject dangling requirement, event, checker and bin references. | Invalid-link fixtures fail with useful diagnostics. |
| COV-001 | MUST support explicit functional bin definitions, thresholds and narrowly scoped requirement mappings. | A multi-bin requirement stays open until every mandatory obligation is satisfied. |
| COV-002 | MUST define functional coverage sampling from observed events. | Driver intent alone does not increment observed bins. |
| COV-003 | MUST report passing checked evidence separately from observed hits. | Failed checks do not receive checked-pass credit. |
| COV-004 | MUST merge compatible runs deterministically and deduplicate identical run imports. | Reordering inputs gives identical normalized results; repeat imports do not inflate counts. |
| COV-005 | MUST reject incompatible catalog/schema/configuration evidence by default. | Changed bin definitions and incompatible profiles cannot be silently merged. |
| COV-006 | MUST preserve exclusions with reason, scope, author/reviewer identity and evidence provenance. | Exclusions are visible; raw and adjusted denominators are reported separately. |
| COV-007 | MUST identify unavailable metrics explicitly and keep coverage families separate. | Missing HDL coverage is 'not collected', never 100% or 0% exercised. |
| CHK-001 | MUST derive actual transactions from an independent interface monitor. | A driver falsely reporting success cannot fool the checker. |
| CHK-002 | MUST support checker outcomes pass, fail, inconclusive and aborted. | Reset cancellation and end-of-run pending checks are handled explicitly. |
| CHK-003 | MUST record whether a temporal trigger occurred and whether obligations remain pending. | An untriggered implication does not satisfy a required non-vacuous scenario. |
| CHK-004 | MUST maintain explicit X/Z policies at checking boundaries. | Unknown control/data fixtures produce the documented result without silent coercion. |
| RUN-001 | MUST record source digests, dependency/tool versions, configuration, seeds, commands and artifact digests. | Manifest inspection and input-change detection. |
| RUN-002 | MUST use per-component random streams with a stable derivation method. | Adding an unrelated component does not perturb an existing stream. |
| RUN-003 | MUST preserve issued transactions and scheduling inputs for supported replay. | Failing pilot stimulus replays without random generation or AI access. |
| RUN-004 | MUST report pass, fail, error, timeout and aborted runs distinctly. | Negative execution fixtures; nonzero CLI status for invalid/failed/unfinished qualification. |
| RUN-005 | MUST detect outstanding scoreboard entries and unfinished obligations at shutdown. | Lost-response and truncated-run fixtures cannot pass. |
| INT-001 | MUST demonstrate one cocotb/pyuvm adapter using public APIs. | APB pilot integration run with pinned versions. |
| INT-002 | MUST evaluate existing constraint/coverage backends before choosing one. | Small executable probe and decision record; no speculative feature claims. |
| INT-003 | SHOULD provide selected UCIS exchange after the initial internal format is stable. | Later: round-trip into a named tool/version with documented losses. |
| GLS-001 | MUST label execution profiles as RTL, zero-delay gate or timing-annotated gate where applicable. | Profile in manifests; reports do not imply interchangeability. |
| GLS-002 | SHOULD qualify gate-level support separately, including SDF and cell libraries. | Later: explicit timing/unknown/reset probe, log evidence and profile limitations. |
| AI-001 | MUST run the first release without AI services or credentials. | Offline execution of core and pilot. |
| AI-002 | MUST expose machine-readable gaps and evidence references through ordinary CLI artifacts. | Structured output consumed without parsing human prose. |
| AI-003 | MUST record verification-intent changes separately from generated tests. | Catalog/checker/exclusion changes create a visible revision boundary. |
| VAL-001 | MUST detect the documented pilot DUT mutants with intended checkers. | Mutation matrix with exact test, failure ID and replay artifact. |
| VAL-002 | MUST publish only exercised compatibility combinations as supported. | Versioned support table linked to actual run evidence. |

## Icarus workstream requirements

| ID | Requirement | Acceptance evidence |
| --- | --- | --- |
| IV-001 | MUST distinguish parsing, elaboration, execution and observation support for needed native features. | IV0 matrix and positive/negative probes, exact tool identity and flags. |
| IV-002 | MUST scope each selected compiler change against standard-derived semantics. | Explicit subset, clause references, boundary and deliberate-failure tests. |
| IV-003 | MUST implement demonstrated high-value native gaps in an Icarus checkout with upstream-oriented patches. | IV1 before/after reproducer and applicable upstream regression results. |
| IV-004 | MUST fail or visibly reject profiles requiring disabled/unsupported checks. | IV2 preflight and intentionally disabled-assertion tests. |
| IV-005 | MUST record simulator commit/patch identity and active feature-probe results. | Manifests and merge rejection across incompatible execution semantics. |

IV-001 is part of the initial investigation; IV-002/003 apply when IV1 is selected, IV-004/005 at IV2. See doc 11 for acceptance scope.

Trace tests to requirements at a useful granularity. A single broad test marked against every requirement is not adequate traceability.
