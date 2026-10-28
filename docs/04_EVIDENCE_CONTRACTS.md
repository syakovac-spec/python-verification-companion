# Evidence contracts

These are normative semantic proposals, not existing package APIs. M1 should translate them into typed records and a documented serialized format. JSON and JSON Lines are reasonable initial formats. Use a versioned catalog plus immutable per-run records.

## Minimum entities

| Entity | Required information |
| --- | --- |
| Catalog | Schema version, revision/hash, requirements, checkers, bin definitions, obligation mappings and exclusion records |
| Requirement | Stable ID, statement, source/revision, applicability and mandatory obligations |
| Obligation | Stable ID, requirement ID, scenario/bin ID, checker IDs, hit goal and applicable configuration/profile |
| Bin definition | Stable ID, version, description, classifier/definition digest and threshold |
| Checker definition | Stable ID, version, semantic/code digest, description and applicable event types |
| Run manifest | Run ID, profile, compatibility key, source/dependency/configuration digests, tool versions, seeds, invocation and artifacts |
| Intent record | Intent ID, sequence/stream ID, planned transaction and scheduling parameters |
| Observed event | Event ID, run ID, interface, reset epoch, transaction/correlation key, integer time and payload |
| Check outcome | Evaluation ID, checker ID, event references, obligation references, outcome, reason and time |
| Coverage evidence | Bin ID, observed event references, qualifying check evaluation references |
| Run finalization | Status, termination reason, pending counts, record counts and artifact integrity metadata |

Use explicit integer simulation ticks with a declared resolution, e.g. `time_resolution_fs: 1000`; an event at tick 123 means 123 ps in that run. Use monotonically assigned event indices to distinguish same-time events. Store hardware vectors as width plus four-state text when unknowns are possible. Store potentially large hardware integers as width-qualified strings for cross-language consumers.

## Meaning of evidence

An intent record documents an attempt. It cannot create observed coverage. An event may satisfy a bin classifier but remain unchecked. A checker pass refers to specified events and a specific obligation. A generic pass somewhere in the same run cannot qualify every observed bin.

For an obligation to receive checked-pass credit, the event must match the obligation's scenario/bin; the required checker evaluations must pass and refer to the relevant correlated event group; the evidence must meet the hit goal; and the run must be finalized and eligible under the aggregation policy. Correlation is explicit for multi-event and temporal checks. A timeout has its own synthesized observation/evaluation record with the originating request reference.

Report distinct counts: attempted, observed, checked-pass, checked-fail, inconclusive and aborted. These counts need not form a simple disjoint partition: one scenario can be exercised multiple times with different outcomes. Explain denominators and deduplicate evidence by stable IDs.

## Requirement assessment

Assess a requirement using every applicable mandatory obligation. Suggested statuses:

- `not_applicable`: explicit applicability predicate is false for this configuration.
- `uncovered`: no qualifying observed evidence for one or more required scenarios.
- `unchecked`: relevant observations exist but required checker evidence is absent.
- `incomplete`: pending, inconclusive, aborted or insufficient-threshold evidence remains.
- `satisfied`: every required obligation has enough eligible checked-pass evidence and no unresolved relevant failure exists in the selected evidence set.
- `failed`: a relevant checker failure exists in the selected evidence set.

Expose missing obligations even when the top-level status is failed. Do not hide holes behind one precedence label. A passing check from a failed run can remain visible diagnostically; default closure credit comes from eligible fully passing runs. Failure evidence is always preserved. Revised DUT/checker catalogs create a new evidence baseline; do not silently erase earlier failures or merge them into a different revision.

## Temporal semantics

Each bounded temporal obligation tracks trigger count, completed-pass count, failed count, pending count and reset-aborted count. An untriggered property may have no failures but has no scenario credit. Define whether reset cancels or fails each pending operation. End-of-test pending obligations are incomplete or failures according to their contract, never implicit passes.

## Compatibility and merge

The compatibility key includes schema major version, catalog/definition digests, DUT source/build identity, parameter/configuration profile, execution semantics, checker revisions and relevant adapter versions. For M1 require exact key equality. Later aggregation across declared compatible configuration dimensions must preserve separate denominators and applicability.

Identical run ID plus identical content is a no-op. Identical run ID with different content is an error. Different run IDs from an exact replay are separate executions; record replay lineage and report distinct scenario diversity separately from execution counts. Merge order must not change normalized results. Sum raw compatible hit counts; compute goals and percentages afterward. Never average run percentages.

An exclusion has stable ID, obligation/bin scope, reason, identity, review metadata and revision. The initial package validates and exposes this metadata; it does not authenticate a reviewer or provide tamper-proof approval. Show raw and adjusted coverage and excluded obligations. AI-generated tests cannot silently introduce exclusions.

## Reproducibility and replay

A manifest captures source revision plus dirty-tree/input digests, HDL files/build flags, top module, parameters, timescale, simulator version/command, Python version, exact package set, catalog/checker digests, root seed, component stream derivation and artifact hashes. Do not capture credentials or the entire process environment; record an allowlisted set of relevant variables.

Derive per-component seeds from a documented stable hash of root seed plus component path and algorithm version. Python's process-dependent `hash()` is unsuitable. A seed is reproducible only within the documented generation environment.

Record the actual issued transaction stream, pauses, reset actions, clock settings, synchronization conditions and response-dependent decisions needed by the supported replay mode. Replay disables random generation. Validate expected inputs before running and identify divergence at the first mismatching observation. Same-tool replay is the first target; cross-simulator identical event scheduling is not promised.

## CLI contract to implement

Proposed operations: `validate`, `summarize`, `gaps`, `merge`, `run`, `replay`. M1 implements only the first four. Require JSON output for automation and useful text output for people. Return zero only when the operation and requested acceptance gate succeed. Distinguish evidence failure, invalid input, infrastructure error and incomplete execution through documented exit codes and structured status fields. Never call an infrastructure error a detected DUT defect.
