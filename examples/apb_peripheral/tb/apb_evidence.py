"""Translate independent checker findings into the public evidence schema."""
import hashlib
import json
from pathlib import Path
from verification_evidence.model import (
    Artifact, Bin, Bundle, Catalog, Check, Checker, Coverage, Event, Finalization,
    Intent, Manifest, Obligation, Requirement, Run, catalog_digest, decode, dump,
)
from verification_evidence.core import summarize, validate
from apb_model import obligation_names
from apb_functional import definitions, GOAL

DESCRIPTIONS = ["Reset restores state and ID", "SCRATCH stores all 32 bits", "ID rejects writes",
                "STATUS set and W1C semantics", "Invalid access errors without side effects",
                "Exact wait-state acceptance", "Consecutive transfer ordering", "Reset aborts in-flight work",
                "Protocol checking active (negative sensitivity qualified separately)", "End-of-run reconciliation"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def catalog(functional=False):
    digest = hashlib.sha256("".join(sha(Path(__file__).with_name(name)) for name in
                                   ("apb_model.py", "apb_functional.py", "apb_evidence.py", "test_apb.py")).encode()).hexdigest()
    profiles = [f"rtl-wait-{n}" for n in (0, 1, 3)]
    names = obligation_names()
    result = Catalog("1.0", "apb-directed-m2-v1",
        [Requirement(f"APB-{i:03d}", text, "docs/05_APB_PILOT.md:M2") for i, text in enumerate(DESCRIPTIONS, 1)],
        [Checker("APB-MODEL", "1", digest, "Independent sampled-bus protocol/register model", ["apb"], "relevant X/Z => inconclusive; never coerce")],
        [Bin(name, "1", digest, name, 1) for name in names],
        [Obligation(name, name.split(".")[0], name, ["APB-MODEL"], 1,
                    profiles[1:] if name.startswith("APB-008.wait.") else profiles) for name in names], [])
    if functional:
        result.revision = "apb-constrained-m3-v1"
        result.requirements += [Requirement(f"FC-{i:03d}", text, "M3-functional-plan-v1") for i, text in enumerate(
            ["Direction by register class", "Wait profile by direction", "Back-to-back operation pair",
             "Reset phase by operation", "Scratch readback bit31 by low-two-bit class"], 1)]
        for name, applicable in definitions():
            result.bins.append(Bin(name, "1", digest, name, GOAL))
            result.obligations.append(Obligation(name, name.split(".")[0], name, ["APB-MODEL"], GOAL, applicable))
    return result


class Recorder:
    def __init__(self, directory):
        self.directory = Path(directory)
        manifest = decode(Manifest, json.loads((self.directory / "manifest.json").read_text()))
        functional = json.loads((self.directory / "inputs.json").read_text())["configuration"]["random_generation"]
        self.bundle = Bundle(catalog(functional), [Run(manifest, [], [], [], [], Finalization("error", "not finalized", 0, {}))])
        assert manifest.compatibility.catalog_digest == catalog_digest(self.bundle.catalog)

    @property
    def run(self):
        return self.bundle.runs[0]

    def intent(self, tick, address, write, data):
        self.run.intents.append(Intent(f"I-{len(self.run.intents)}", "APB-006.write" if write else "APB-006.read", "directed-master",
                                       {"tick": tick, "address": f"0x{address:08x}", "write": bool(write), "data": f"0x{data:08x}"}))

    def write(self, finding):
        n = len(self.run.events)
        eid, cid = f"E-{n}", f"C-{n}"
        self.run.events.append(Event(eid, self.run.manifest.id, "apb0", finding.epoch,
                                     finding.correlation, n, finding.tick, "apb", finding.payload))
        self.run.checks.append(Check(cid, "APB-MODEL", finding.obligation, [eid], finding.outcome, finding.reason, finding.tick, True))
        self.run.coverage.append(Coverage(f"V-{n}", finding.obligation, [eid], [cid]))

    def finish(self, analyzer, error=None):
        pending = int(analyzer.pending is not None)
        status = "error" if error else ("fail" if any(f.outcome == "fail" for f in analyzer.findings) else
                                      "aborted" if analyzer.failures else "pass")
        self.run.finalization = Finalization(status, str(error) if error else "directed run finalized", pending,
            {k: len(getattr(self.run, k)) for k in ("intents", "events", "checks", "coverage")},
            {"APB-010.drained": pending} if pending else {})
        for name in ("pins.json", "samples.jsonl", "stimulus.jsonl", "generated.json", "closure_progress.json", "distribution.json"):
            path = self.directory / name
            if path.exists():
                self.run.manifest.artifacts.append(Artifact(name, sha(path)))
        validate(self.bundle)
        dump(self.bundle, self.directory / "bundle.json")
        result = summarize(self.bundle)
        (self.directory / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
