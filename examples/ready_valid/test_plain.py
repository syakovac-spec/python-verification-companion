"""Same BFM, checker and evidence API with no pyuvm import or dependency."""
import sys
import cocotb
from cocotb.utils import get_sim_time
from bfm import StreamConfig, observe, send, sink, reset, drain, data_sequence
from evidence import session, finish


@cocotb.test(timeout_time=20, timeout_unit="us")
async def stream_test(dut):
    assert "pyuvm" not in sys.modules
    directory, model = session()
    tx, rx = StreamConfig.bind(dut, "tx", "tx"), StreamConfig.bind(dut, "rx", "rx")
    def publish(observed):
        model.sample(*observed)
    tasks = [cocotb.start_soon(observe(tx, publish)), cocotb.start_soon(observe(rx, publish)),
             cocotb.start_soon(sink(rx))]
    error = None
    try:
        await reset(tx)
        for value in data_sequence():
            await send(tx, value)
        await drain(tx)
    except Exception as exc:
        error = str(exc)
    finally:
        for task in tasks:
            try:
                if task.done():
                    task.result()
            except Exception as exc:
                error = str(exc)
            task.kill()
        result = finish(directory, model, int(get_sim_time(units="ps")), error)
    assert result["gate"] == "pass", "STREAM_CHECK_FAILURE: " + str(result["requirements"])
