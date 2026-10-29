"""Reproduce a late RisingEdge callback without requiring a VCS license.

The fake edge changes live pins before resuming Python; captured pins retain
the accepted transaction. These are scheduling counterexamples, not VCS runs.
"""
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


class Signal:
    def __init__(self, value):
        self.value = value

    def __len__(self):
        return 8


class SamplingRaceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.edges = 0
        self.live = SimpleNamespace(reset=Signal("1"), valid=Signal("1"), ready=Signal("1"), data=Signal("10100101"))
        async def edge(clock):
            self.edges += 1
            self.live.reset.value = "0"
            self.live.valid.value = "0"
            self.live.ready.value = "0"
            self.live.data.value = "11111111"
        async def noop(*args, **kwargs):
            pass
        triggers = ModuleType("cocotb.triggers")
        triggers.RisingEdge = edge
        triggers.FallingEdge = triggers.ReadOnly = triggers.Timer = noop
        utils = ModuleType("cocotb.utils")
        utils.get_sim_time = lambda **kwargs: 100
        source = Path(__file__).resolve().parents[1] / "examples/ready_valid/bfm.py"
        spec = importlib.util.spec_from_file_location("sampling_bfm", source)
        self.bfm = importlib.util.module_from_spec(spec)
        with patch.dict("sys.modules", {"sampling_bfm": self.bfm, "cocotb": ModuleType("cocotb"), "cocotb.triggers": triggers, "cocotb.utils": utils}):
            spec.loader.exec_module(self.bfm)
        capture = SimpleNamespace(s_reset=Signal("1"), s_tx_valid=Signal("1"),
                                  s_tx_ready=Signal("1"), s_tx_data=Signal("10100101"))
        self.config = self.bfm.StreamConfig(None, self.live.reset, self.live.valid,
            self.live.ready, self.live.data, "tx", capture)

    async def test_monitor_uses_accepted_values_when_callback_sees_post_update(self):
        seen = []
        class StopMonitor(Exception):
            pass
        def publish(item):
            seen.append(item)
            raise StopMonitor()
        with self.assertRaises(StopMonitor):
            await self.bfm.observe(self.config, publish)
        self.assertEqual(seen[0][2], dict(reset="1", valid="1", ready="1", data="10100101"))
        self.assertEqual(self.live.data.value, "11111111")

    async def test_driver_recognizes_acceptance_even_when_ready_drops_at_edge(self):
        await self.bfm.send(self.config, 0xA5)
        self.assertEqual(self.edges, 1)
        self.assertEqual(self.live.valid.value, 0)

    def test_missing_capture_cannot_silently_fall_back_to_live_bus(self):
        self.config.capture = None
        with self.assertRaisesRegex(ValueError, "HDL edge snapshots"):
            self.bfm.captured_signals(self.config)
