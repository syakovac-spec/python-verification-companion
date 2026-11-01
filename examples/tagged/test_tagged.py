"""Monitor independently captured request/response values in a bounded RTL run."""
import json
import os
from pathlib import Path
import cocotb
from cocotb.triggers import FallingEdge, RisingEdge, ReadOnly
from verification_evidence import EvidenceRecorder, dump, summarize
from verification_evidence.model import Manifest, decode
from verification_evidence.scoreboard import Scoreboard
from contract import plan, predict, compare


@cocotb.test()
async def tagged_test(dut):
    out = Path(os.environ['TAGGED_OUT'])
    manifest = decode(Manifest, json.loads((out/'manifest.json').read_text()))
    config = json.loads((out/'inputs.json').read_text())['configuration']
    recorder = EvidenceRecorder(plan(manifest.compatibility.checker_digest), manifest)
    board = Scoreboard(recorder, interface='tagged0', obligation='MATCH', drain_obligation='DRAIN',
        checker='tagged-model', mode='tagged', allow_reordering=config['allow_reordering'],
        predictor=predict, comparator=compare)
    error = None
    try:
        # Driving is separate from checking; predictions use only s_tx snapshots.
        for cycle in range(12):
            await FallingEdge(dut.clk)
            dut.rst_n.value = int(cycle >= 2)
            dut.tx_valid.value = int(cycle in (2, 3))
            dut.tx_id.value = 3 if cycle == 2 else 7
            dut.tx_data.value = 0x12 if cycle == 2 else 0x81
            await RisingEdge(dut.clk)
            await ReadOnly()
            if str(dut.s_reset.value) != '1':
                continue
            for port in ('tx', 'rx'):
                accepted = str(getattr(dut, 's_'+port+'_valid').value) == '1'
                if port == 'tx': accepted &= str(dut.s_tx_ready.value) == '1'
                if not accepted: continue
                bits = str(getattr(dut, 's_'+port+'_data').value).lower()
                tag_bits = str(getattr(dut, 's_'+port+'_id').value).lower()
                if any(bit not in '01' for bit in tag_bits):
                    raise ValueError('unknown response/request ID cannot be matched')
                payload = {'data': {'width': 8, 'bits': bits}, 'tag': tag_bits, 'channel': port}
                if port == 'tx':
                    board.request(payload, tick=cycle, tag=int(tag_bits, 2), deadline=9)
                else:
                    board.response(payload, tick=cycle, tag=int(tag_bits, 2))
            board.advance(cycle)
    except Exception as exc:
        error = str(exc)
    bundle = recorder.finish(pending_by_obligation=board.close(12), error=error)
    dump(bundle, out/'bundle.json')
    result = summarize(bundle)
    (out/'summary.json').write_text(json.dumps(result, indent=2)+'\n')
    assert result['gate'] == 'pass', 'TAGGED_CHECK_FAILURE: ' + result['gate']
