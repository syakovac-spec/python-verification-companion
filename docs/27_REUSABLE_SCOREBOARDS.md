# Reusable observed-transaction scoreboards

`verification_evidence.Scoreboard` provides FIFO and tagged matching without a
simulator or pyuvm dependency. The ready/valid example and newly generated kits
use it for data/order and drain checks; their monitors still own handshake and
stall checking. `examples/tagged` exercises a second DUT that transforms data
and returns two responses in reverse request order.

Feed **accepted monitor observations** to the scoreboard. The predictor derives
expected results from those inputs and the independent DUT contract. Driving a
transaction is not evidence that the DUT accepted it.

## Bind the verification plan

```python
from verification_evidence import Scoreboard, Comparison

def predict(observed):
    return observed['data']['bits']  # Identity-buffer contract; preserve X/Z.

def compare(expected, observed):
    actual = observed['data']['bits']
    if any(bit not in '01' for bit in expected + actual):
        return Comparison('inconclusive', 'unknown active data')
    return Comparison('pass' if expected == actual else 'fail',
                      'independently predicted data')

board = Scoreboard(
    recorder, interface='pipe0', obligation='MATCH', drain_obligation='DRAIN',
    checker='model', predictor=predict, comparator=compare,
    mode='tagged', allow_reordering=True)

# Called by monitors using accepted, sampled values, not sequence intent:
board.request(input_payload, tick=10, tag=7, deadline=30)
board.response(output_payload, tick=20, tag=7)
board.advance(31)
bundle = recorder.finish(pending_by_obligation=board.close(40))
```

The snippet assumes the declared catalog and recorder exist. Bind matching and
drain to **distinct obligations** with the selected checker and event kind
(`transfer` by default). A successful empty drain must never count as a matched
transaction. See `examples/tagged/contract.py` for a complete catalog and explicit
four-state comparison policy.

`request` returns a monotonically assigned prediction token. `pending` returns
detached `Prediction` records with the expected result, request event ID,
correlation, epoch, tag and optional deadline. Predictions and comparisons receive
copies, so subsequent input/model mutations cannot rewrite outstanding expectations.
The serialized evidence retains actual input/output payloads and checker reasons;
predictions are runtime state, not a separate persisted replay format.

## Matching, time and finalization

| Policy | Behavior |
| --- | --- |
| `mode='ordered'` | Compare each output against the oldest accepted request; omit tags. |
| `mode='tagged'` | Match integer or nonempty string IDs; reject a duplicate outstanding request ID without replacing its prediction. |
| `allow_reordering=False` | A response for a later outstanding ID fails, even if its data is correct. |
| `allow_reordering=True` | Different IDs may complete in any order; only valid with tagged mode. |
| `deadline=N` | Response at tick N is on time; response after N fails. |
| `advance(tick)` | Report expired deadlines once per request and retain pending work. Call on monitor clock/time progress, including idle intervals. |
| `close(tick)` | Report missing responses and check final drain; return pending counts for recorder finalization. Further use is rejected. |

Ticks must be nonnegative integers in one consistent unit and must not move
backward. Same-tick input/output observations are allowed; the adapter determines
their protocol-defined processing order. No background timer is started. A
deadline detects lateness at response or explicit `advance`; shutdown always
detects remaining work even without deadlines.

Unexpected/duplicate responses fail. After an ID has completed it may be reused,
but a protocol cannot distinguish an old duplicate from the new response solely
from the reused ID and identical data. Supply additional generation identity in
the monitor's tag when the protocol provides it. FIFO matching likewise cannot
detect permutations of indistinguishable identical transactions.

Every successful match links the accepted-input event and actual output event
under the same logical interface, epoch and correlation. Checker and coverage
records use that exact event group. Missing/deadline failures retain the request
event; unexpected outputs retain their own event. Failed or inconclusive checks
and pending work cannot be overridden by a later pass.

## Reset and stateful prediction

`reset(tick, cancel=True)` records how many requests were cancelled, clears the
matching state and starts a new epoch. Use cancellation only when the DUT contract
permits it. Cancelled requests earn no matching credit. With `cancel=False`, each
interrupted request gets a failed check before the new epoch begins. Existing
failures are never erased by reset.

An optional `reset_predictor()` callback resets architectural model state. A
stateful predictor can be a callable object or closure implementing a register
file, memory, counter or other architectural model. For example:

```python
class MemoryPredictor:
    def __init__(self):
        self.words = {}

    def __call__(self, observed):
        # The adapter has already applied its explicit unknown-address policy.
        address = observed['address']
        if observed['op'] == 'write':
            self.words[address] = observed['data']['bits']
        return self.words.get(address, '00000000')

    def reset(self):
        self.words.clear()
```

Pass the object as `predictor` and its `reset` method as `reset_predictor`.
This example assumes each write acknowledges its resulting value and each read
returns the predicted word; define the actual access policies for your DUT.
The library supplies hooks, not a register-map or memory semantics package.
Prediction runs in accepted-input order, even when responses may reorder.

If a monitor can identify the originating epoch, pass it to
`response(..., epoch=observed_epoch)`. A stale-epoch response fails without consuming
a current request. Without an on-wire generation marker, stale responses after
reset and reuse of the same ID may be indistinguishable. The adapter must establish
reset flushing/quiescence or provide a protocol-specific identity; the library
does not infer an epoch from output data.

The comparator must return `Comparison('pass'|'fail'|'inconclusive', reason)`.
There is no default equality that could accidentally certify X/Z values. Callback
exceptions record nonpassing evidence and propagate to the environment, which
should finalize with the execution error. Prediction rollback is not automatic;
stop a run after a callback exception.

## Executable qualification

From an installed checkout in the active Python environment:

```sh
python -m unittest discover -s tests -q
python examples/ready_valid/run.py --sim icarus
python examples/tagged/run.py --sim icarus
python examples/ready_valid/run.py --sim verilator
python examples/tagged/run.py --sim verilator
```

The tagged runner accepts `--out NEW_DIRECTORY`. Its positive case permits the
DUT's reversal and checks its XOR transformation. Negative cases corrupt data,
forbid the observed reordering, and drop a response. The missing case must retain
both deadline and drain failures. The outer qualification succeeds only when
the intended raw failures and simulator-test failures occur. HDL snapshots capture
acceptance at the active edge; Python reads them after `ReadOnly`.

Model tests separately qualify duplicate IDs/outputs, unexpected responses,
deadline boundaries, stale epochs, permitted/forbidden cancellation, X/Z,
stateful memory/reset, callback failures, mutation isolation and empty-run
nonclosure. These synthetic checks are not presented as RTL defect evidence.
Recorded executed combinations and results are in `evidence/scoreboard-summary.json`.

## Boundaries

The library matches one response to each accepted request. It does not implement
burst assembly, multiple outstanding requests with the same ID, speculative
rollback, cross-interface schema groups, arbitrary out-of-order architectural
prediction, or protocol-specific temporal assertions. The tagged example is a
bounded demonstration, not AXI VIP. Commercial simulator execution remains
unqualified locally. Existing generated kits are user-owned; regenerate into a
new directory to adopt the shared matcher.
