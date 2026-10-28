from copy import deepcopy
from dataclasses import asdict
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from verification_evidence.model import *
from verification_evidence.core import validate, summarize, merge


def sample():
    catalog = Catalog("1.0", "demo-v1",
        [Requirement("REQ-1", "Readback matches the observed write", "demo:1")],
        [Checker("CHECK-1", "1", "model-v1", "Compare observed readback", ["transfer"], "inconclusive on X/Z")],
        [Bin("BIN-1", "1", "classifier-v1", "Scratch readback", 1)],
        [Obligation("OB-1", "REQ-1", "BIN-1", ["CHECK-1"], 1, ["rtl"])], [])
    key = Compatibility(1, catalog_digest(catalog), "dut-v1", "config-v1", "rtl", "fixture-only", "model-v1", "none")
    run = Run(Manifest("RUN-1", key, 1000, "source-v1", "stdlib-only", {"python": "3.10"}, {"root": "42"}, ["fixture"], [], ""),
        [Intent("I-1", "OB-1", "master", {"data": {"width": 4, "bits": "10xz"}})],
        [Event("E-1", "RUN-1", "apb", 0, "txn-1", 0, 10, "transfer", {"data": {"width": 32, "bits": "0" * 32}})],
        [Check("C-1", "CHECK-1", "OB-1", ["E-1"], "pass", "Expected matches observed", 10, True)],
        [Coverage("V-1", "BIN-1", ["E-1"], ["C-1"])],
        Finalization("pass", "complete", 0, {}))
    recount(run)
    return Bundle(catalog, [run])


def recount(run):
    run.finalization.record_counts = {k: len(getattr(run, k)) for k in ("intents", "events", "checks", "coverage")}


def reseal(bundle):
    for r in bundle.runs:
        r.manifest.compatibility.catalog_digest = catalog_digest(bundle.catalog)


class EvidenceTests(unittest.TestCase):
    def test_roundtrip_preserves_four_state_and_large_time(self):
        b = sample()
        b.runs[0].events[0].tick = 2**70
        b.runs[0].checks[0].tick = 2**70
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "e.json"
            dump(b, p)
            self.assertEqual(validate(load(p)), b)

    def test_pass(self):
        result = summarize(sample())
        self.assertEqual(result["gate"], "pass")
        self.assertEqual(result["obligations"][0]["eligible_checked_pass"], 1)

    def test_attempt_only(self):
        b = sample(); r = b.runs[0]
        r.events = []; r.checks = []; r.coverage = []; recount(r)
        result = summarize(b)
        self.assertEqual(result["requirements"][0]["status"], "uncovered")
        self.assertEqual(result["obligations"][0]["counts"]["attempted"], 1)

    def test_unchecked(self):
        b = sample(); r = b.runs[0]
        r.checks = []; r.coverage[0].check_ids = []; recount(r)
        self.assertEqual(summarize(b)["requirements"][0]["status"], "unchecked")

    def test_untriggered(self):
        b = sample(); b.runs[0].checks[0].triggered = False
        self.assertEqual(summarize(b)["obligations"][0]["eligible_checked_pass"], 0)

    def test_partial_obligations_remain_open(self):
        b = sample()
        b.catalog.bins.append(Bin("BIN-2", "1", "other", "Other scenario", 1))
        b.catalog.obligations.append(Obligation("OB-2", "REQ-1", "BIN-2", ["CHECK-1"], 1, ["rtl"]))
        reseal(b)
        self.assertEqual(summarize(b)["requirements"][0]["missing_obligations"], ["OB-2"])

    def test_threshold(self):
        b = sample(); b.catalog.bins[0].threshold = 2; reseal(b)
        self.assertEqual(summarize(b)["requirements"][0]["status"], "incomplete")

    def test_failure_survives_pass(self):
        b = sample(); r = deepcopy(b.runs[0]); r.manifest.id = "RUN-2"; r.events[0].run_id = "RUN-2"
        r.checks[0].outcome = "fail"; r.finalization.status = "fail"; b.runs.append(r)
        result = summarize(b)
        self.assertEqual(result["gate"], "failed")
        self.assertEqual(result["obligations"][0]["counts"]["checked_pass"], 1)

    def test_unfinished_runs_no_credit(self):
        for status in ("fail", "error", "timeout", "aborted"):
            with self.subTest(status=status):
                b = sample(); b.runs[0].finalization.status = status
                b.runs[0].finalization.pending = 1
                self.assertEqual(summarize(b)["obligations"][0]["eligible_checked_pass"], 0)

    def test_reset_abort(self):
        b = sample(); r = b.runs[0]
        r.checks[0].outcome = "aborted"; r.finalization.status = "aborted"
        self.assertEqual(summarize(b)["requirements"][0]["status"], "incomplete")

    def test_wrong_event_association(self):
        b = sample(); r = b.runs[0]
        e = deepcopy(r.events[0]); e.id = "E-2"; e.index = 1; r.events.append(e)
        r.checks[0].event_ids = ["E-2"]; recount(r)
        with self.assertRaisesRegex(EvidenceError, "association"):
            validate(b)

    def test_cross_reset_group(self):
        b = sample(); r = b.runs[0]
        e = deepcopy(r.events[0]); e.id = "E-2"; e.index = 1; e.epoch = 1; r.events.append(e)
        r.checks[0].event_ids.append("E-2"); recount(r)
        with self.assertRaisesRegex(EvidenceError, "boundary"):
            validate(b)

    def test_duplicate_coverage_no_inflation(self):
        b = sample(); r = b.runs[0]
        c = deepcopy(r.coverage[0]); c.id = "V-2"; r.coverage.append(c); recount(r)
        self.assertEqual(summarize(b)["obligations"][0]["eligible_checked_pass"], 1)

    def test_same_transaction_subsets_do_not_inflate_goal(self):
        b = sample(); r = b.runs[0]
        e = deepcopy(r.events[0]); e.id = "E-2"; e.index = 1; r.events.append(e)
        c = deepcopy(r.checks[0]); c.id = "C-2"; c.event_ids = ["E-1", "E-2"]; r.checks.append(c)
        r.coverage.append(Coverage("V-2", "BIN-1", ["E-1", "E-2"], ["C-2"])); recount(r)
        result = summarize(b)["obligations"][0]
        self.assertEqual(result["counts"]["observed"], 1)
        self.assertEqual(result["eligible_checked_pass"], 1)

    def test_merge_order_and_idempotence(self):
        a = sample(); b = sample(); b.runs[0].manifest.id = "RUN-2"; b.runs[0].events[0].run_id = "RUN-2"
        results = {canonical(merge(list(p))) for p in itertools.permutations([a, b, a])}
        self.assertEqual(len(results), 1)
        self.assertEqual(len(merge([a, a]).runs), 1)

    def test_conflicting_run(self):
        a = sample(); b = sample(); b.runs[0].manifest.seeds["root"] = "43"
        with self.assertRaisesRegex(EvidenceError, "conflicting"):
            merge([a, b])

    def test_incompatible_keys(self):
        for field in ("dut_digest", "configuration_digest", "execution_semantics", "checker_digest", "adapter_version"):
            a = sample(); b = sample(); b.runs[0].manifest.id = "RUN-2"; b.runs[0].events[0].run_id = "RUN-2"
            setattr(b.runs[0].manifest.compatibility, field, "changed")
            with self.subTest(field=field), self.assertRaisesRegex(EvidenceError, "incompatible"):
                merge([a, b])

    def test_catalog_change_rejected(self):
        b = sample(); b.catalog.bins[0].digest = "changed"
        with self.assertRaisesRegex(EvidenceError, "mismatch"):
            validate(b)

    def test_invalid_links_and_counts(self):
        for mutate in (lambda r: r.checks[0].event_ids.append("missing"),
                       lambda r: setattr(r.events[0], "run_id", "wrong"),
                       lambda r: setattr(r.finalization, "pending", 1),
                       lambda r: r.events.clear()):
            b = sample(); mutate(b.runs[0])
            with self.assertRaises(EvidenceError): validate(b)

    def test_exclusion_visible_not_automatic_waiver(self):
        b = sample(); b.catalog.obligations[0].goal = 2
        b.catalog.exclusions = [Exclusion("EX-1", "OB-1", ["rtl"], "Demonstration", "author", "reviewer", "1", "issue:1")]
        reseal(b); result = summarize(b)
        self.assertEqual(result["gate"], "incomplete")
        self.assertEqual(result["coverage"], {"raw": {"satisfied": 0, "total": 1}, "adjusted": {"satisfied": 0, "total": 0}})

    def test_not_applicable(self):
        b = sample(); b.catalog.obligations[0].profiles = ["gate"]; reseal(b)
        self.assertEqual(summarize(b)["requirements"][0]["status"], "not_applicable")

    def test_empty_runs_no_pass(self):
        b = sample(); b.runs = []
        self.assertEqual(summarize(b)["gate"], "incomplete")

    def test_strict_json(self):
        for text in ('{"catalog":{},"catalog":{}}', '{', '{"x":NaN}'):
            with tempfile.TemporaryDirectory() as td:
                p = Path(td) / "bad.json"; p.write_text(text)
                with self.assertRaises(EvidenceError): load(p)
        raw = asdict(sample()); raw["runs"][0]["events"][0]["tick"] = True
        with self.assertRaises(EvidenceError): decode(Bundle, raw)

    def test_malformed_vector_rejected(self):
        b = sample(); b.runs[0].events[0].payload = {"data": {"width": 2, "bits": "10xz"}}
        with self.assertRaisesRegex(EvidenceError, "four-state"):
            validate(b)

    def test_pending_obligation_survives_other_pass(self):
        b = sample(); r = deepcopy(b.runs[0]); r.manifest.id = "RUN-2"; r.events[0].run_id = "RUN-2"
        r.finalization.status = "timeout"; r.finalization.pending = 1
        r.finalization.pending_by_obligation = {"OB-1": 1}; b.runs.append(r)
        self.assertEqual(summarize(b)["obligations"][0]["status"], "incomplete")

    def test_resolution_mismatch(self):
        a = sample(); b = sample(); b.runs[0].manifest.id = "RUN-2"; b.runs[0].events[0].run_id = "RUN-2"
        b.runs[0].manifest.time_resolution_fs = 1
        with self.assertRaisesRegex(EvidenceError, "incompatible"):
            merge([a, b])

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "e.json"
            for status, code in (("pass", 0), ("fail", 1), ("timeout", 3), ("error", 4)):
                b = sample(); b.runs[0].finalization.status = status; dump(b, p)
                result = subprocess.run([sys.executable, "-m", "verification_evidence.cli", "summarize", str(p), "--json"], capture_output=True, text=True)
                self.assertEqual(result.returncode, code, result.stderr)
                json.loads(result.stdout)
            p.write_text("{}")
            result = subprocess.run([sys.executable, "-m", "verification_evidence.cli", "validate", str(p)], capture_output=True)
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
