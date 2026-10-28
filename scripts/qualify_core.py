"""Run semantic and CLI checks in whichever installed Python invokes this script."""
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
out = root / "evidence" / "m1"
out.mkdir(parents=True, exist_ok=True)
results = {"python": platform.python_version(), "platform": platform.platform(),
           "optional_modules": {m: importlib.util.find_spec(m) is not None for m in ("cocotb", "pyuvm", "vsc", "pytest")}, "commands": []}


def check(args, expected=0):
    proc = subprocess.run([sys.executable] + args, cwd=root, capture_output=True, text=True)
    results["commands"].append(dict(command=[sys.executable] + args, expected=expected, returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr))
    return proc.returncode == expected


ok = check(["-m", "unittest", "discover", "-s", "tests", "-v"])
for fixture, expected in (("passing", 0), ("attempted", 3), ("unchecked", 3), ("failing", 1), ("incomplete", 3), ("invalid_reference", 2)):
    ok &= check(["-m", "verification_evidence.cli", "summarize", f"tests/fixtures/{fixture}.json", "--json"], expected)
ok &= check(["-m", "verification_evidence.cli", "merge", "tests/fixtures/passing.json", "tests/fixtures/passing.json", "--output", "evidence/m1/merged.json", "--json"])
ok &= check(["-m", "verification_evidence.cli", "merge", "tests/fixtures/passing.json", "tests/fixtures/incompatible.json", "--output", "evidence/m1/should-not-exist.json", "--json"], 2)
ok &= check(["-m", "verification_evidence.cli", "gaps", "tests/fixtures/unchecked.json", "--json"], 3)
ok &= check(["-m", "verification_evidence.cli", "validate", "tests/fixtures/passing.json", "--json"])
results["passed"] = bool(ok)
name = "windows" if sys.platform == "win32" else "linux"
(out / f"core-{name}.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: v for k,v in results.items() if k != "commands"}, indent=2))
sys.exit(0 if ok else 1)
