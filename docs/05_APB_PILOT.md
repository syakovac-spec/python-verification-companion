# APB reference pilot

Use a newly authored small peripheral so public examples contain no employer or proprietary design material. This is a selected APB subset with product-specific register semantics. Consult the relevant Arm APB specification for protocol timing; the contract below does not redefine the protocol.

## Interface and behavior

Single slave, one PCLK domain, 32-bit PADDR/PWDATA/PRDATA, PSEL, PENABLE, PWRITE, PREADY, PSLVERR and active-low PRESETn. Exclude PSTRB/PPROT from the first pilot and label the subset accurately. Support aligned full-word accesses only. PRESETn asynchronously clears peripheral state; the testbench normally releases it away from a sampling edge. Reset dominates a coincident access completion.

Transfers begin with setup and progress to access. A transfer is accepted at a rising PCLK edge with PSEL, PENABLE and PREADY high while reset is inactive. Outputs and side effects must agree with the pre-edge transfer state. Read data and error status must be valid at acceptance. The master holds address, direction and write data stable through wait cycles.

| Address | Register | Contract |
| --- | --- | --- |
| 0x00 | ID | Read-only constant 0x43564301. Writes complete with PSLVERR and no side effect. |
| 0x04 | SCRATCH | 32-bit read/write, reset value zero. |
| 0x08 | STATUS | Bit 0 is sticky; remaining bits read zero. Write-one-to-clear bit 0; writing zero leaves it unchanged. |
| 0x0C | SET_EVENT | Write bit 0 equal to one sets STATUS[0]. Other write bits ignored. Reads return zero. |

Unmapped or misaligned accesses complete with PSLVERR; invalid reads return zero; invalid writes have no state effect. Sample PSLVERR for meaning at transfer completion. Reset suppresses acceptance, clears writable state and discards any in-progress operation. No discarded write may take effect later.

WAIT_CYCLES is an elaboration parameter, initially qualified at 0, 1 and 3. Define it as the exact count of access-phase sampling edges at which PREADY is low before the accepting edge. For zero waits, the first access edge accepts. A maximum-latency checker uses this definition and profile. Different parameter values have separate evidence keys unless explicitly aggregated under a later policy.

## Independent environment

The driver converts transactions into bus cycles. It does not tell the scoreboard that a transfer succeeded. The monitor reconstructs setup, waiting, accepted and reset-aborted operations. A Python model predicts register values and side effects from accepted observed transfers. Scoreboards detect missing/extra responses and compare outcomes. A protocol checker independently verifies stability and phase sequencing. Reset starts a new epoch so old pending operations cannot match new ones.

For negative master-protocol tests, explicitly select an expected-error harness policy. Ordinary regressions must treat those same violations as failures; do not globally suppress checker errors.

## Pilot requirement and scenario matrix

| ID | Required behavior | Scenarios/checks |
| --- | --- | --- |
| APB-001 | Reset restores state and ID. | Startup reset; reset after writes; readback checks. |
| APB-002 | SCRATCH stores all 32 bits. | Zero, all ones, walking ones, alternating patterns and constrained values. |
| APB-003 | Read-only ID rejects writes. | Write/error/readback confirms no change. |
| APB-004 | STATUS follows set and W1C semantics. | Set; clear with zero; clear with one; repeated set/clear. |
| APB-005 | Invalid accesses fail without side effects. | Unmapped/misaligned reads and writes; check affected and unaffected state. |
| APB-006 | Wait-state acceptance is exact. | Zero, one and three wait profiles; read/write and stable controls. |
| APB-007 | Consecutive transfers preserve ordering. | Same/different addresses; read/write combinations; setup between transfers. |
| APB-008 | Reset aborts in-flight operations. | Reset in setup, during wait, and at completion boundary; no stale write/response. |
| APB-009 | Testbench detects bus protocol violations. | Deliberately unstable master control; injected checker self-tests. |
| APB-010 | End-of-run reconciliation detects lost operations. | Pending accepted/uncompleted work cannot be silently dropped. |

Define meaningful functional bins and crosses for direction × register class, wait profile × direction, back-to-back operation pair and reset phase × operation type. Avoid enormous crosses with no requirement rationale. Unreachable combinations need explicit applicability or reviewed exclusion, never quiet deletion.

Random generation chooses legal transactions, values, sequence lengths and idle gaps within a bounded scenario. Use a selected constraint backend for actual constraints, with deterministic directed tests retained for important boundaries. Document intended distributions and collect observed distributions; constrained-random does not mean uniform over all legal assignments.

## Deliberate DUT mutants

| Mutant | Defect | Expected detecting check |
| --- | --- | --- |
| MUT-01 | Drop SCRATCH bit 31 on write. | APB-002 full-width readback. |
| MUT-02 | Accept a write one edge early during waits. | APB-006 side-effect timing check, plus reset-during-wait test. |
| MUT-03 | Treat STATUS write-zero as clear. | APB-004 W1C model comparison. |
| MUT-04 | Suppress PSLVERR on unmapped access. | APB-005 completion error check. |
| MUT-05 | Apply an aborted write after reset. | APB-008 epoch/state check. |
| MUT-06 | Skip a required wait edge. | APB-006 latency check. |

Each mutant is individually enabled and known to compile. Record the intended checker failure, seed, stimulus trace and replay. A compiler error, unrelated timeout or infrastructure crash does not count as detection. Baseline must pass with the same tests. Mutants validate selected failure sensitivity; they do not prove design completeness.
