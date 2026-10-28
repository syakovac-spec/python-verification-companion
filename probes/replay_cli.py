"""Verify public runner rejects divergent replay requests before simulation."""
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
source = Path(sys.argv[1]).resolve()
rows = []
for label, wait, seed in (("configuration", "1", "42"), ("seed", "3", "17")):
    command = [sys.executable, str(root / "examples/apb_peripheral/run_suite.py"), "--single", "--case", "m3",
               "--wait", wait, "--seed", seed, "--replay", str(source)]
    process = subprocess.run(command, capture_output=True, text=True, timeout=60)
    assert process.returncode == 2, process.stdout + process.stderr
    assert "mismatch" in process.stderr
    rows.append(dict(case=label, command=command, exit=process.returncode, stderr=process.stderr))
(source.parent / "replay-cli.json").write_text(json.dumps({"passed": True, "rejections": rows}, indent=2) + "\n")
print("Replay CLI mismatch rejection passed")
