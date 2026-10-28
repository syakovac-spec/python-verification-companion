import sys
import unittest
import json
import tempfile
from dataclasses import asdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples/apb_peripheral/tb"))
from apb_replay import validate_trace
from apb_recovery import recover
from apb_evidence import catalog
from verification_evidence.model import load, catalog_digest
from test_apb_model import frame


class ReplayTests(unittest.TestCase):
    def test_process_failure_preserves_pending_and_unknown_state(self):
        for rows in ([], [{"kind": "sample", "tick": 10, "signals": frame(sel=1, addr=4, write=1)}]):
            with self.subTest(rows=rows), tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                fixture = Path(__file__).parent / "fixtures/passing.json"
                manifest = load(fixture).runs[0].manifest
                manifest.compatibility.catalog_digest = catalog_digest(catalog())
                manifest.compatibility.profile = "rtl-wait-3"
                manifest.artifacts = []
                (directory / "manifest.json").write_text(json.dumps(asdict(manifest)))
                (directory / "inputs.json").write_text(json.dumps({"configuration": {"random_generation": False}}))
                (directory / "samples.jsonl").write_text("\n".join(json.dumps(row) for row in rows))
                bundle = recover(directory, 3, "process timeout")
                final = bundle.runs[0].finalization
                self.assertEqual(final.status, "error")
                self.assertEqual(final.pending_by_obligation, {"APB-010.drained": 1})
                self.assertTrue(any(c.obligation_id == "APB-010.drained" and c.outcome == "fail" for c in bundle.runs[0].checks))

    def test_same_timestamp_order_is_allowed(self):
        validate_trace({"version": 1, "end_tick": 11, "drives": [
            {"tick": 10, "name": "PADDR", "value": 4}, {"tick": 10, "name": "PSEL", "value": 1}]})

    def test_invalid_schedule_or_drive_rejected(self):
        for row in ({"tick": -1, "name": "PSEL", "value": 1},
                    {"tick": 1, "name": "PREADY", "value": 1},
                    {"tick": 1, "name": "PADDR", "value": 2**32},
                    {"tick": 1, "name": "PRESETn", "value": True}):
            with self.subTest(row=row), self.assertRaises(ValueError):
                validate_trace({"version": 1, "end_tick": 2, "drives": [row]})

    def test_finalization_cannot_precede_drive(self):
        with self.assertRaises(ValueError):
            validate_trace({"version": 1, "end_tick": 0, "drives": [{"tick": 1, "name": "PSEL", "value": 1}]})
