# Evidence core v1.0

The local package is `verification-evidence` 0.1.0, import `verification_evidence`, command `vevidence`. It has no runtime dependencies. Python 3.10 is the tested baseline. The typed dataclasses in `src/verification_evidence/model.py` define the serialized contract; `tests/fixtures` provides complete JSON examples.

## Install and use

```sh
python -m pip install .
vevidence validate tests/fixtures/passing.json --json
vevidence summarize tests/fixtures/passing.json
vevidence gaps tests/fixtures/unchecked.json --json
vevidence merge tests/fixtures/passing.json tests/fixtures/passing.json --output merged.json
```

`python -m verification_evidence.cli` is equivalent to the installed command. `gaps` deliberately exits 3 for the unchecked example. `validate` checks structure and internal consistency; valid failing evidence may pass validation. `merge` checks compatibility and writes evidence, without asserting coverage closure. `summarize` and `gaps` enforce the raw qualification gate.

| Exit | Meaning |
| --- | --- |
| 0 | Requested operation/gate succeeds |
| 1 | Relevant checker failure or failed run |
| 2 | Invalid input, schema/reference conflict, incompatible merge, or CLI usage error |
| 3 | Uncovered/unchecked/incomplete evidence or unfinished execution |
| 4 | Infrastructure error, unreadable file, or recorded error run |

The summary preserves individual runs even if a failed run takes precedence over another run's infrastructure error. JSON errors go to stderr. No `run` or `replay` commands exist yet.

## Records and validation

A bundle contains one catalog and zero or more runs. Catalogs include version/revision, requirements, bin definitions, checker definitions with explicit X/Z policy, mandatory obligations with explicit profile lists, and reviewed exclusion metadata. IDs are unique within each entity collection. Every requirement needs at least one obligation. A checker pass always names an obligation and its observed event group.

Runs include manifests, generated intents, observed events, checks, coverage records, and finalization. All schema fields are required in JSON, including empty collections. Unknown fields, unsupported schema majors, duplicate JSON keys/IDs/references, nonfinite numbers, wrong primitive types, and dangling references are rejected. An integer field cannot be supplied as a Boolean. Record counts detect simple truncation; they are not tamper-proof signatures.

Simulation time is integer ticks plus positive `time_resolution_fs`; event indices order same-time samples. Events carry interface, reset epoch, correlation ID, kind, and payload. Checks and coverage cannot cross interface/reset/correlation boundaries. Each checker must support the event kinds it evaluates. A coverage record's check must name exactly its event set and the mapped bin's obligation. This conservative restriction handles correlated multi-event groups but intentionally does not infer subset/superset equivalence.

Hardware vectors use `{"width": 4, "bits": "10xz"}`. Payload objects containing width or bits are reserved for this form; validation checks width and the four-state alphabet and never converts X/Z. Other payload structure is application-defined JSON. The core records a checker's X/Z policy; it does not implement hardware checking or enforce the checker's truthfulness.

`triggered=false` records an untriggered evaluation and earns no checked-pass credit. Finalization contains a total pending count and optional-in-Python/default-empty `pending_by_obligation` mapping (serialized explicitly). The mapping can account for a subset of pending work; unmapped pending work still prevents a passing run. A `pass` run cannot have pending, failed, inconclusive, or aborted checks. Temporal engines and adapters remain later work; they must supply correlated events, trigger flags, and pending counts.

## Assessment and merging

An observation counts once per `(run, bin, interface, reset epoch, correlation)`, even if multiple coverage records describe subsets of the same transaction. Exact event groups accumulate checker links. Every required checker must pass on a qualifying group and be triggered; a generic run-level pass is insufficient. The goal is the maximum of the bin threshold and obligation goal.

Checked-pass counts include diagnostic evidence from failed/unfinished runs; **eligible** closure credit comes only from fully passing runs. Any relevant failure in the selected evidence set stays failed. Pending/inconclusive/aborted evidence stays visible. Requirement assessment includes every applicable obligation and lists missing obligations even when another obligation has failed. Empty evidence cannot pass. Explicit profile membership supplies applicability; arbitrary executable predicates are outside v1.

Merge requires exact compatibility keys and time resolution. Keys include schema major, computed catalog digest, DUT/configuration identities, profile, execution semantics, checker identity, and adapter version. Identical run ID/content is idempotent; conflicting content is rejected. Run and catalog entity ordering is normalized; record-array ordering within a run remains part of its content. Raw counts are summed and goals assessed afterward. Different replay run IDs remain separate executions, with `replay_of` visible; diversity analysis is deferred.

Exclusions expose reason, scope, author/reviewer, revision, and provenance. Reports show raw and adjusted obligation totals; exclusions do not silently change the raw success gate. Unavailable HDL structural coverage, Python coverage, and native assertion metrics are explicitly `not_collected`.

Manifest digest fields are caller-supplied identities except the catalog digest, which is recomputed. Artifact SHA256 syntax is checked; external file contents are not opened or verified by M1. Input/artifact hashing, replay integrity, and trusted provenance collection belong to later execution services. This package is not an authenticity or tamper-resistance system.

## Validation

```sh
python -m unittest discover -s tests -v
python scripts/qualify_core.py
```

The qualification script records exact commands, output, status, platform, and optional-module absence in `evidence/m1/core-<platform>.json`. It checks the fixtures and all four CLI operations, including deliberate invalid and incompatible inputs. The semantic tests target false closure, correlation mistakes, duplicate imports, thresholds, resets, schema corruption, and failure retention.

## Protocol-independent recording API

`from verification_evidence import EvidenceRecorder` exposes the standard-library-only recording boundary for new interfaces. Construct it with a declared Catalog and Manifest, call `observe` from independently sampled activity, call `evaluate` from the scoreboard with exact event IDs, and call `finish` with pending obligation counts or an execution error. The recorder validates the finalized bundle and does not allow a caller to override failed checks with a pass. Monitoring alone does not earn checked closure. See [the extension guide](17_EXTENDING_TO_OTHER_INTERFACES.md) and `examples/ready_valid` for complete working integration in pyuvm and plain cocotb.
