# Decisions and open questions

Status labels: baseline = proposed default for implementation; confirmed = supported by owner decision or executable evidence; deferred = intentionally outside current milestone. Baseline choices can be refined with a written rationale.

| ID | Decision | Status / rationale |
| --- | --- | --- |
| ADR-001 | Separate public companion with targeted upstream contributions. | Baseline from discussion; avoids placing the entire workflow in UVM core. |
| ADR-002 | pyuvm first; evidence schema independent of UVM inheritance. | Baseline; enables existing cocotb environments later. |
| ADR-003 | JSON/JSONL artifacts and CLI before databases/UI. | Baseline; inspectable, portable and sufficient for the pilot. |
| ADR-004 | Small APB peripheral as first complete example. | Baseline; exercises state, errors, wait timing and reset. |
| ADR-005 | Linux and Icarus first for RTL pilot. | Baseline; not a gate-level/signoff support claim. |
| ADR-006 | Reuse existing constraints/coverage backend. | Baseline; selection requires M0 probe. |
| ADR-007 | Exact compatibility keys for initial merges. | Baseline; prevents accidental mixing of incompatible evidence. |
| ADR-008 | Recorded-stimulus replay before AI-directed closure. | Baseline; reproducibility is a prerequisite. |
| ADR-009 | No required AI service in runtime. | Baseline; keeps results deterministic and independently usable. |
| ADR-011 | Include selective Icarus SV/native feature implementation with upstream-directed patches. | User-requested expansion; IV0 probes determine priorities; implementation in separate compiler checkout. |
| ADR-010 | Public repository/package name and software license remain undecided. | Owner decisions before publication; local development can proceed. |

## Questions the coding agent should investigate

1. Which stable Python/cocotb/pyuvm combination installs and passes the chosen integration probe?
2. Which constraint backend supports the needed relations, distributions, reproducibility and target platforms with acceptable install/runtime cost?
3. Can the first adapter capture APB acceptance correctly under zero wait and same-edge reset? What sampling shim is needed, if any?
4. What is the narrowest typed core contract that handles correlated multi-event checks and reset epochs?
5. Which generated inputs must be recorded to reproduce response-dependent sequences?
6. Which upstream public APIs are sufficient, and where is a focused upstream proposal justified?

These are engineering investigations, not reasons to block on user clarification.

## Owner decisions to defer until relevant

Public project name and hosting account; licensing/ownership; desired commercial simulator priority; intended deployment platforms; whether a particular real DUT becomes a second pilot; whether historical SV VIP interoperability is required.

## Decision entry template

## Extension decisions — 2026-10-28

- **ADR-025, implemented:** add a narrow public EvidenceRecorder for protocol-independent bookkeeping. Monitors and contract scoreboards retain ownership of observation, prediction, correlation and pending state. Preserve the existing schema and conservative closure rules; use standard pyuvm composition rather than another UVM framework.
- **ADR-026, demonstrated:** use an elastic ready/valid buffer as a second protocol example with source/sink/passive agent roles, shared independent model and both pyuvm and plain-cocotb entry points. Good DUTs close the four declared goals; deliberate data corruption fails ORDER in both styles. The example uses seeded bounded Python random data; solver constraints and recorded replay remain demonstrated by APB. No general AXI VIP or automatic protocol replay is claimed.
- **ADR-027, environment:** qualify Python 3.11.18 and stable Icarus 13.0 from v13_0 in isolated installations, retaining cocotb 1.9.2, pyuvm 5.0.0 and PyVSC 0.9.6.37412289187. Exact final results and source digests belong in evidence/python311-icarus13-summary.json. This expands tested combinations without asserting support for an unavailable external DUT or all simulator features.

## Implementation decisions — 2026-10-26

- **ADR-022, M4:** replay ordered timestamped pin drives rather than rerun response-dependent sequences. Preserve functional-sampling boundaries and finalization time; reject changed source/configuration/dependency/tool/seed identities and corrupt artifacts. Fresh replay run IDs reference their originals. Import guards prevent use of the stimulus solver/agent during replay, and qualification requires exact pin, observation and checker-record matches.
- **ADR-023, M4:** individually parameterized RTL mutants exercise all six doc 05 defects. MUT-02 requires a pilot-specific architectural SCRATCH observation across waiting edges because later readback can hide premature effects. Compare pre/post-edge observed state; keep this timing check separate from data correctness. Include the simulator checker adapter in the checker identity digest.
- **ADR-024, M4:** an interrupted simulator cannot imply a drained run. Finalize pending work on exceptions; when the process cannot finalize, reconstruct from flushed observations and retain error status. Missing/malformed history keeps an explicitly unknown pending state. Qualification records distinguish simulator interruption evidence from unit recovery counterexamples.

- **ADR-018, demonstrated:** APB3 signal subset referenced to Arm IHI 0024C; register/reset policies remain doc 05 requirements. Falling-edge drive, pre-NBA acceptance with checked HDL snapshot, and asynchronous reset observation are qualified on the recorded Icarus combination.
- **ADR-019, demonstrated:** PyVSC public constraint/RandState APIs feed a pyuvm agent/sequencer. SHA-256-derived seeds isolate transaction, reset and idle streams. Installed-version repeatability/isolation probes pass; generated actions are preserved for M4. Cross-version equivalence and executable replay are not claimed.
- **ADR-020, qualified:** evidence-core functional bins/crosses require three checked observations after the directed prelude. PyVSC solves constraints; bounded sequences target open goals without changing checkers or thresholds. Catalog revision apb-constrained-m3-v1 records this intent. Explicit applicability omits wait-phase reset at zero wait.
- **ADR-021, demonstrated:** outer qualification verifies raw evidence gates, simulator XML and artifact hashes. Expected negative/gap cases retain failed/incomplete raw gates. Derived unchecked reporting experiments are labeled as such. Full six-DUT-mutant sensitivity remains M4.

## Template

ID and date; question; options considered; decision; evidence/experiment; affected requirements; compatibility consequences; follow-up. Record the final reason rather than a transcript of discarded debugging steps.

## Implementation decisions — 2026-10-23

- **ADR-012, confirmed locally:** provisional distribution `verification-evidence`, import `verification_evidence`, CLI `vevidence`. Standard-library dataclasses/JSON; no runtime dependencies. Wheel installed and semantic tests pass on Python 3.10 Windows/Linux. Public name availability and license remain undecided. CORE-001/002.
- **ADR-013, confirmed for probes:** Ubuntu 22.04 in existing WSL, Python 3.10.12, Icarus 11.0, cocotb 1.9.2, pyuvm 5.0.0. cocotb-coverage 1.2.0 constrains cocotb below 2; retain this exercised set for M2. Exact metadata/freeze under evidence/m0. INT-001/002, VAL-002. This does not qualify the APB pilot.
- **ADR-014, baseline selection with probe evidence:** PyVSC for the M3 adapter; both backends passed bounded legality/coverage/repeatability experiments. Per-object random state and bit-vector constraints favor PyVSC; large optional dependency footprint and unqualified platforms remain explicit. cocotb-coverage remains an evaluated alternative. See doc 12; RUN-002 and INT-002.
- **ADR-015, implemented:** v1 applicability uses explicit profile membership; each check names exactly one obligation and a correlated event group within one interface/reset epoch. Coverage checker links require the exact same event set. Count a scenario once per run/bin/interface/epoch/correlation, preventing overlapping subsets from inflating thresholds. Future cross-interface correlation requires a schema revision. CORE-003/005, COV-001/003/004.
- **ADR-016, implemented:** raw qualification gate remains conservative in the presence of exclusions; display adjusted totals without silently waiving open obligations. `validate` and `merge` judge their requested operation; `summarize` and `gaps` judge closure. Exit codes documented in doc 14. COV-006, RUN-004.
- **ADR-017, confirmed probe scope:** Icarus immediate assertions and sampled NBA/VPI behavior work in tested cases; one-cycle implication is compile-rejected on 11.0. Propose a bounded native one-cycle assertion slice for IV1, with explicit rejection of unsupported syntax and upstream requalification before coding. No compiler implementation in this tranche. IV-001/002/003.
