"""Retain M2's pure-Python test transcript without rewriting historical M1 evidence."""
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
result = subprocess.run(command, cwd=root, capture_output=True, text=True)
record = dict(command=command, python=platform.python_version(), platform=platform.platform(),
              returncode=result.returncode, stdout=result.stdout, stderr=result.stderr,
              optional_modules={name: importlib.util.find_spec(name) is not None for name in ("cocotb", "pyuvm", "vsc")})
out = root / "evidence" / (sys.argv[1] if len(sys.argv) > 1 else "m2")
out.mkdir(parents=True, exist_ok=True)
(out / ("unit-windows.json" if sys.platform == "win32" else "unit-linux.json")).write_text(json.dumps(record, indent=2) + "\n")
print(result.stderr)
sys.exit(result.returncode)
