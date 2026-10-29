"""Qualify the user's active environment without installing or changing it."""
import argparse
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
from verification_evidence import simulation

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    simulation.configure(parser)
    parser.add_argument("--full", action="store_true", help="include full directed, closure and replay/mutation suites")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    simulation.select(args)
    out = (args.out or ROOT / "evidence/compatibility" / str(uuid.uuid4())).resolve()
    out.mkdir(parents=True, exist_ok=False)
    result = dict(python=sys.version, executable=sys.executable, prefix=sys.prefix,
                  conda_prefix=os.environ.get("CONDA_PREFIX"), virtual_env=os.environ.get("VIRTUAL_ENV"),
                  dependencies={d.metadata["Name"]: d.version for d in metadata.distributions()},
                  full=args.full, qualified=False, runs=[])
    try:
        result["tools"] = simulation.identity()
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        result["unavailable"] = str(exc)
        (out / "qualification.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result))
        return 2
    apb = "examples/apb_peripheral/run_suite.py"
    commands = [["-m", "unittest", "discover", "-s", "tests", "-q"],
                ["examples/ready_valid/run.py"]]
    commands += ([[apb], [apb, "--m3"], [apb, "--m4"]] if args.full else [
        [apb, "--single", "--case", "baseline", "--wait", "3"],
        [apb, "--single", "--case", "wrong_response", "--wait", "3"],
        [apb, "--single", "--case", "m3", "--wait", "3"]])
    for index, command in enumerate(commands):
        start = time.perf_counter()
        proc = subprocess.run([sys.executable, *command], cwd=ROOT, text=True, capture_output=True)
        (out / f"{index}.stdout.log").write_text(proc.stdout)
        (out / f"{index}.stderr.log").write_text(proc.stderr)
        row = dict(command=command, returncode=proc.returncode, seconds=time.perf_counter() - start)
        result["runs"].append(row)
        print(json.dumps(row), flush=True)
        (out / "qualification.json").write_text(json.dumps(result, indent=2))
    result["qualified"] = all(row["returncode"] == 0 for row in result["runs"])
    (out / "qualification.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({"qualified": result["qualified"], "report": str(out / "qualification.json")}))
    return 0 if result["qualified"] else 1


if __name__ == "__main__":
    sys.exit(main())
