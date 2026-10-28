"""Negative replay validation on copies; source simulation artifacts stay intact."""
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples/apb_peripheral/tb"))
from apb_replay import verify_source

source = Path(sys.argv[1]).resolve()
inputs = json.loads((source / "inputs.json").read_text())
verify_source(source, inputs)
results = {}


def rejected(name, directory, expected):
    try:
        verify_source(directory, expected)
    except (ValueError, OSError) as exc:
        results[name] = str(exc)
    else:
        raise AssertionError(name + " was accepted")


for name in ("sources", "dependencies", "configuration", "tools"):
    changed = copy.deepcopy(inputs)
    changed[name]["mismatch"] = "deliberate probe"
    rejected(name, source, changed)
with tempfile.TemporaryDirectory() as tmp:
    target = Path(tmp) / "copy"
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("build"))
    original = (target / "pins.json").read_bytes()
    (target / "pins.json").write_bytes(original + b" ")
    rejected("corrupt_trace", target, inputs)
    (target / "pins.json").write_bytes(original)
    bundle = json.loads((target / "bundle.json").read_text())
    bundle["runs"][0]["manifest"]["source_digest"] = "0" * 64
    (target / "bundle.json").write_text(json.dumps(bundle))
    rejected("manifest_identity", target, inputs)
out = source.parent / "replay-integrity.json"
out.write_text(json.dumps({"passed": True, "rejections": results}, indent=2) + "\n")
print(out)
