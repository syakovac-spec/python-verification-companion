"""Capture compile/runtime results separately; unsupported is not a pass."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

here = Path(__file__).resolve().parent
out = here.parents[1] / "evidence" / "iv0"
out.mkdir(parents=True, exist_ok=True)


def call(command):
    try:
        p = subprocess.run(command, capture_output=True, text=True, timeout=90)
        return dict(command=command, returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return dict(command=command, returncode=None, error=str(exc))


results = {"schema_version": "1.0", "tool": call(["iverilog", "-V"]), "runtime": call(["vvp", "-V"]), "binary_sha256": {}, "probes": []}
for binary in ("iverilog", "vvp"):
    path = shutil.which(binary)
    if path:
        results["binary_sha256"][binary] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
for source in ("immediate", "concurrent"):
    for enabled in (True, False):
        target = out / f"{source}-{enabled}.vvp"
        compile_ = call(["iverilog", "-g2012", "-gassertions" if enabled else "-gno-assertions", "-s", source, "-o", str(target), str(here / (source + ".sv"))])
        row = dict(feature=source, enabled=enabled, compile=compile_, runtime=[])
        if compile_["returncode"] == 0:
            for mode in range(4 if source == "immediate" else 2):
                result = call(["vvp", str(target), f"+mode={mode}"])
                detected = result["returncode"] not in (None, 0) and "FAIL" in result.get("stdout", "")
                result.update(mode=mode, deliberate_failure_detected=detected)
                row["runtime"].append(result)
            positive = row["runtime"][0]
            negatives = row["runtime"][1:]
            row["classification"] = "executed" if enabled and positive["returncode"] == 0 and all(x["deliberate_failure_detected"] for x in negatives) else "not_qualified"
            if not enabled and all(x["returncode"] == 0 for x in row["runtime"]):
                row["classification"] = "ignored"
        else:
            row["classification"] = "compile_rejected" if compile_["returncode"] is not None else "blocked"
        results["probes"].append(row)
for negative in (False, True):
    result = call([sys.executable, str(here / "run_nba.py")] + (["--negative"] if negative else []))
    results["probes"].append(dict(feature="nba-negative" if negative else "nba-pyuvm", result=result,
                                  classification="executed" if result["returncode"] == 0 else "not_qualified"))
(out / "matrix.json").write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps([{"feature": p["feature"], "enabled": p.get("enabled"), "classification": p["classification"]} for p in results["probes"]], indent=2))
