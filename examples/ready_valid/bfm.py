"""Signal binding and coroutine BFM; no pyuvm dependency."""
from dataclasses import dataclass
import random
from cocotb.triggers import FallingEdge, RisingEdge, ReadOnly, Timer
from cocotb.utils import get_sim_time


@dataclass
class StreamConfig:
    clock: object
    reset: object
    valid: object
    ready: object
    data: object
    channel: str
    capture: object = None  # required HDL acceptance snapshot; see sampling contract

    @classmethod
    def bind(cls, dut, prefix, channel):
        return cls(dut.clk, dut.rst_n, getattr(dut, prefix + "_valid"),
                   getattr(dut, prefix + "_ready"), getattr(dut, prefix + "_data"), channel, dut)


def captured_signals(config):
    """Read the HDL's edge snapshot after ReadOnly, never the live bus.

    An adapter must supply equivalent sampling registers/clocking semantics.
    Falling back to live handles would reintroduce simulator-dependent races.
    """
    if config.capture is None:
        raise ValueError("StreamConfig.capture must provide HDL edge snapshots (s_reset, s_<channel>_{valid,ready,data})")
    return {name: str(getattr(config.capture,
            "s_reset" if name == "reset" else f"s_{config.channel}_{name}").value).lower()
            for name in ("reset", "valid", "ready", "data")}


async def observe(config, publish):
    while True:
        await RisingEdge(config.clock)
        await ReadOnly()
        signals = captured_signals(config)
        publish((config.channel, int(get_sim_time(units="ps")), signals))


async def send(config, value):
    if not 0 <= value < 2**len(config.data):
        raise ValueError("transaction data exceeds interface width")
    await FallingEdge(config.clock)
    config.valid.value = 1
    config.data.value = value
    for _ in range(100):
        await RisingEdge(config.clock)
        await ReadOnly()
        signals = captured_signals(config)
        accepted = all(signals[name] == "1" for name in ("reset", "valid", "ready"))
        if accepted:
            await FallingEdge(config.clock)
            config.valid.value = 0
            return
    raise TimeoutError("ready/valid source timed out")


async def sink(config):
    cycle = 0
    while True:
        await FallingEdge(config.clock)
        config.ready.value = int(cycle % 7 >= 4)
        cycle += 1


async def reset(config):
    config.reset.value = 0
    for _ in range(3):
        await RisingEdge(config.clock)
    await FallingEdge(config.clock)
    config.reset.value = 1


def data_sequence(seed=42, count=24):
    stream = random.Random(seed)
    return [stream.randrange(256) for _ in range(count)]


async def drain(config):
    for _ in range(20):
        await RisingEdge(config.clock)
    await Timer(1, units="ns")
