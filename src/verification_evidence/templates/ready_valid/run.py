"""Qualify both composition styles against baseline and deliberate corruption."""
import argparse
from dataclasses import asdict
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from verification_evidence.model import Compatibility, Manifest, Artifact, catalog_digest, load
from verification_evidence.core import validate, summarize
from coverage_plan import PROFILE
from model import plan
from verification_evidence import simulation

HERE = Path(__file__).resolve().parent
ROOT = HERE


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def run_one(directory, mode, corrupt):
    out = directory / f"{mode}-corrupt-{corrupt}"
    out.mkdir()
    sources = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in list(HERE.glob("*.py")) + list((HERE / "rtl").glob("*.sv"))}
    checker = digest(sources)
    config = {"mode": mode, "corrupt": corrupt, "width": __import__("interface_config").SPEC["width"], "seed": 42, "simulator": simulation.simulator(), "build_flags": simulation.build_flags(), "test_flags": json.loads(os.environ.get("PVC_TEST_ARGS", "[]"))}
    dependencies = {d.metadata["Name"]: d.version for d in metadata.distributions()}
    tools = simulation.identity()
    inputs = dict(sources=sources, configuration=config, dependencies=dependencies, tools=tools)
    (out / "inputs.json").write_text(json.dumps(inputs, indent=2))
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--mode", mode,
               "--corrupt", str(corrupt), "--out", str(out)]
    cat = plan(checker)
    manifest = Manifest(str(uuid.uuid4()), Compatibility(1, catalog_digest(cat), sources['rtl/stream_top.sv'],
        digest(config), PROFILE, digest(tools), checker, "ready-valid-v1"), 1000,
        digest(sources), digest(dependencies), tools, {"traffic": "42"}, command,
        [Artifact("inputs.json", hashlib.sha256((out / "inputs.json").read_bytes()).hexdigest())], "")
    (out / "manifest.json").write_text(json.dumps(asdict(manifest), indent=2))
    r = subprocess.run(command, text=True, capture_output=True, timeout=120)
    (out / "stdout.log").write_text(r.stdout)
    (out / "stderr.log").write_text(r.stderr)
    qualified, gate, failed = False, "infrastructure_error", []
    if (out / "bundle.json").exists() and (out / "results.xml").exists():
        bundle = load(out / "bundle.json")
        validate(bundle)
        gate = summarize(bundle)["gate"]
        failed = sorted({c.obligation_id for c in bundle.runs[0].checks if c.outcome == "fail"})
        cases = list(ET.parse(out / "results.xml").getroot().iter("testcase"))
        failures = sum(c.find("failure") is not None or c.find("error") is not None for c in cases)
        qualified = (r.returncode in (0, 1) and len(cases) == 1 and failures == corrupt and
                     (gate == "pass" if not corrupt else gate == "failed" and failed == ["ORDER"]))
        if corrupt:
            qualified &= "STREAM_CHECK_FAILURE" in r.stdout
    row = dict(mode=mode, corrupt=corrupt, qualified=bool(qualified), gate=gate, failed=failed,
               directory=str(out), tools=tools)
    print(json.dumps(row), flush=True)
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--mode", choices=["uvm", "plain"])
    parser.add_argument("--corrupt", type=int, choices=[0, 1], default=0)
    parser.add_argument("--out")
    simulation.configure(parser)
    args = parser.parse_args()
    simulation.select(args)
    if args.worker:
        out = Path(args.out)
        simulation.run(sources=[HERE / "rtl/stream_top.sv"], top="stream_top",
            parameters={"CORRUPT": args.corrupt}, out=out, module="test_" + args.mode,
            test_dir=HERE, extra_env={"STREAM_OUT": str(out)})
        return 0
    out = ROOT / "evidence/ready-valid" / str(uuid.uuid4())
    out.mkdir(parents=True)
    rows = [run_one(out, mode, corrupt) for mode in ([args.mode] if args.mode else ["uvm", "plain"]) for corrupt in (0, 1)]
    result = {"qualified": all(r["qualified"] for r in rows), "runs": rows}
    (out / "qualification.json").write_text(json.dumps(result, indent=2))
    (out.parent / "latest.json").write_text(json.dumps({"path": str(out / "qualification.json")}))
    return 0 if result["qualified"] else 1


if __name__ == "__main__":
    sys.exit(main())
