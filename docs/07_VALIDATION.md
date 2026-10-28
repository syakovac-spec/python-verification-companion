# Validation and release evidence

## Core semantic checks

Use small counterexamples that expose false confidence. Include attempted-but-not-observed, observed-without-check, wrong checker/event association, pass plus unresolved failure, multi-obligation partial completion, untriggered temporal properties, reset-aborted checks, pending-at-exit operations, unavailable metrics and explicit exclusions.

Exercise merge permutations, repeated identical input, conflicting content under one run ID, changed bin/checker definitions, malformed/corrupt/truncated artifacts and configuration mismatch. Require exact expected assessment outcomes. Tests should validate semantics rather than mirror every helper function.

## Integration checks

Confirm drivers hold APB control stable, monitors sample the actual acceptance values, same-address consecutive accesses remain distinct and reset epochs isolate operations. Test zero-wait and delayed transfers. Introduce monitor/checker harness faults so the testbench itself has observable failure modes. Ensure simulator errors cannot produce passing evidence.

Measure runtime and artifact size on a named machine/workload. Record whether tracing is enabled. Do not claim performance superiority over SV/UVM without a controlled comparison.

## Compatibility table to populate

| Capability | Planned initial target | Evidence required | Current status |
| --- | --- | --- | --- |
| Pure Python core | Python 3.10.7 Windows / 3.10.12 Linux | Clean install and semantic test results | M1 clean install; 47 current tests pass |
| APB RTL pilot | Icarus 11.0, cocotb 1.9.2, pyuvm 5.0.0 on WSL | Directed, constrained and mutation runs | M2–M4 qualified, including six mutants and exact replay; see docs 15/16 |
| Constraint backend | PyVSC 0.9.6.37412289187 / pyboolector 3.2.4.38488416565 | Seeded legality/coverage probe | M3 closure and stream isolation qualified on WSL |
| Plain cocotb evidence | Same schema, no pyuvm requirement | M5 example | Planned |
| Second simulator | Select after pilot works | Same functional scenarios; differences documented | Deferred |
| Gate timing | Named simulator, cell library and SDF profile | Annotation, timing-check, reset and X/Z probes | Deferred |
| UCIS exchange | Named tool/version and supported subset | Round-trip semantic comparison | Deferred |

Replace planned labels with exact versions only after execution. A row may be experimental without being supported. CI should run pure-Python semantic tests independently of simulator jobs; integration jobs must make missing required simulators visible rather than silently skipping them.

## Release checklist

- All first-release MUST requirements have evidence or explicitly identified outstanding blockers.
- Core installs independently; optional extras install on exercised platforms.
- Baseline passes; each pilot mutant is detected by its intended check.
- Replay reproduces a failing case with matching input identities.
- Documentation commands work from a clean environment.
- Support matrix, schema version, known limitations and compatibility policy are accurate.
- Coverage claims state denominators, applicability, exclusions and collection availability.
- Project ownership, license and public package name are decided before publication.

No single aggregate percentage establishes signoff. The package supplies inspectable evidence; the engineering team defines adequacy for its design and application.
