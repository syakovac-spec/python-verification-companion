# UCIS functional coverage interchange

The companion exports a bounded UCIS 1.0 XML functional-coverage projection.
It also retains the complete original evidence, its closure summary and an
integrity manifest. Export and safe merging use only the Python standard library;
they need no simulator, PyUCIS, solver or license. Use your active Python/conda.

## Export and merge

```sh
vevidence export-ucis run1/bundle.json --output ucis-run1
vevidence export-ucis run2/bundle.json --output ucis-run2
vevidence merge-ucis ucis-run1 ucis-run2 --output ucis-regression
vevidence validate-ucis ucis-regression
```

Alternatively export several compatible evidence bundles together:

```sh
vevidence export-ucis run1/bundle.json run2/bundle.json --output ucis-regression
```

Every output is a new directory; existing directories are never overwritten:

| File | Purpose |
| --- | --- |
| `coverage.xml` | UCIS functional counts, thresholds and run history |
| `evidence.json` | Full authoritative event/check/coverage evidence and provenance |
| `summary.json` | Original failed/incomplete/pass gate, exclusions and closure assessment |
| `export.json` | Mapping, compatibility scope, content hashes and limitations |

Merge validates artifact hashes, reloads evidence, enforces the existing catalog
and execution compatibility contract, deduplicates identical run IDs and rejects
conflicting duplicates. It then recomputes counts and writes fresh UCIS. It does
not sum potentially overlapping XML databases. A replay with a different run ID
remains a distinct run, matching the core's existing semantics.

All three commands return zero for a successful artifact operation, **not a
passing verification gate**. Inspect the exported `gate` or run
`vevidence summarize ucis-regression/evidence.json --json` for closure. Invalid
data returns 2; filesystem errors return 4. Empty runs and profiles with no
applicable functional obligations are rejected rather than inventing coverage.

## Mapping and preserved meaning

- One stable instance scope encodes the full evidence compatibility identity.
  Incompatible designs/configurations/profiles/tool semantics cannot accidentally
  share a scope. Cross-simulator equivalence is not inferred or forced.
- Each applicable obligation gets a stable hashed coverpoint name and a single
  `checked` bin. The original ID is in aliases/comments, metadata and the manifest.
  These are abstract checked-scenario indicators, not reconstructed signal ranges,
  native SV covergroups or inferred cross definitions.
- `coverageCount` is the core's `eligible_checked_pass`: independently observed,
  checked scenarios from finalized passing runs, with the core's deduplication.
  Failed, errored, aborted and timed-out runs contribute no eligible hit counts.
- `options.at_least` is `max(obligation.goal, bin.threshold)`; percentage goal is
  100 and weight is 1. A separate coverpoint for each obligation avoids collapsing
  different checker requirements that refer to the same evidence bin.
- Non-applicable obligations are omitted from the UCIS denominator but remain in
  evidence. Exclusions stay visible in evidence and **are not automatically applied
  as UCIS ignore bins or waivers**, preserving the core's raw closure policy.
- Run history retains run IDs and a boolean completed-pass status. Exact status,
  seeds and replay links are also metadata and remain in the evidence sidecar.
  XML dates describe export time in UTC, not invented simulation start times;
  timezone-free formatting accommodates the qualified PyUCIS reader.
- The schema's required source location refers to the logical `evidence.json`
  catalog. It is not an RTL coverage source location.

A UCIS coverage percentage is not our verification gate. For example, passing
runs can fill all bins while another run fails a checker. The sidecar preserves
that failure even if an external tool displays 100% functional coverage. Do not
discard the evidence/summary when using UCIS dashboards for signoff decisions.

## Independent validation and tool round trips

The optional qualification dependency is separate from the core:

```sh
python -m pip install -e '.[ucis]'
python scripts/qualify_ucis.py ucis-regression --out ucis-check
```

This checks PyUCIS's UCIS 1.0 XSD, imports the database using its public reader,
re-exports it through its writer, validates again and compares functional bin
identity, counts, thresholds, weights and percentage goals against evidence.
`report.json` records the exact Python/PyUCIS versions and any failures. This
script operates on local data and does not upload anything.

To qualify a commercial importer, import `coverage.xml` using that installed
tool's documented UCIS import/API route, then export UCIS XML and run:

```sh
vevidence validate-ucis ucis-regression --roundtrip vendor-reexport.xml
```

The comparison accepts namespace-qualified or unqualified UTF-8 XML, rejects
DTD/entities, and checks our one compatible functional scope. Other unrelated
vendor coverage scopes may coexist. This is a subset semantic check, not a
general XML schema validator or import of vendor XML into authoritative evidence.
It does not prove preservation of history/user metadata by the external tool.
If the tool cannot re-export UCIS XML, its database API must independently query
the same named bins/goals before compatibility can be claimed.

Record the vendor, version, import/merge commands, diagnostics, counts/goals and
round-trip result. There are no fabricated generic VCS/Questa/Xcelium import
commands: their installed workflows must be qualified. Native commercial binary
database writing and arbitrary vendor-database import are not implemented.

## Reproducible merge probe

Two **synthetic** evidence fixtures have distinct run IDs and one hit each with
a goal of three. They test interoperability, not RTL correctness:

```sh
vevidence export-ucis tests/fixtures/ucis-run-1.json --output probe-one
vevidence export-ucis tests/fixtures/ucis-run-2.json --output probe-two
vevidence merge-ucis probe-one probe-two probe-one --output probe-safe
python scripts/qualify_ucis.py probe-safe --out probe-safe-check
python scripts/qualify_ucis.py probe-one probe-two --external-merge --out probe-external-check
```

Safe merge must retain two runs and count 2 with goal 3 despite duplicate input.
The last command deliberately tests the independent merger and exits nonzero on
loss. In PyUCIS **0.2.0.22787133465**, reader/writer round trips preserve goal 3,
but `DbMerger` changes it to 1 while correctly summing the count to 2. Our check
detects this; no dependency monkey patch or silent goal repair is applied. Use
`merge-ucis` followed by reader/writer import for the qualified path. Future
PyUCIS versions are accepted if they preserve the same semantics.

Local qualification also exports existing plain-cocotb/pyuvm positive and
deliberately corrupt Icarus stream evidence. All four schema/read/write round
trips preserve their counts/goals; the two corrupt runs retain failed evidence
gates. See `evidence/ucis-summary.json` for recorded results. Commercial tool
execution remains **not qualified**; requirement INT-003's commercial round-trip
acceptance remains open.

This feature does not collect HDL code/toggle/FSM coverage or native assertions,
and does not convert them into functional coverage. Full event/checker links,
waiver provenance and detailed failure state are outside this UCIS projection.

References: [Accellera UCIS 1.0](https://www.accellera.org/downloads/standards/ucis),
[PyUCIS XML interoperability](https://fvutils.github.io/pyucis/reference/formats/xml-interchange.html).
