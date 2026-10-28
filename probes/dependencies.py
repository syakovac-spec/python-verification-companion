"""Record installed API signatures, package constraints and actual license files."""
import hashlib
import importlib.metadata as md
import inspect
import json
from pathlib import Path
import platform

out = Path(__file__).resolve().parents[1] / "evidence" / "m0"
out.mkdir(parents=True, exist_ok=True)
packages = {}
for name in ("cocotb", "pyuvm", "cocotb-coverage", "pyvsc", "pyboolector", "python-constraint"):
    try:
        dist = md.distribution(name)
    except md.PackageNotFoundError:
        packages[name] = {"status": "not installed"}
        continue
    licenses = []
    for file in dist.files or []:
        if "license" in str(file).lower() or "copying" in str(file).lower():
            data = dist.locate_file(file).read_bytes()
            licenses.append({"path": str(file), "sha256": hashlib.sha256(data).hexdigest(), "text": data.decode(errors="replace")})
    packages[name] = {"version": dist.version, "requires": dist.requires, "license_metadata": dist.metadata.get("License-Expression") or dist.metadata.get("License"), "license_files": licenses}

apis = {}
import cocotb
from cocotb.triggers import Timer, RisingEdge, ReadOnly
from cocotb.runner import get_runner
import pyuvm
from cocotb_coverage.crv import Randomized
from cocotb_coverage.coverage import CoverPoint
for obj in (Timer, RisingEdge, ReadOnly, get_runner, pyuvm.uvm_test, pyuvm.uvm_analysis_port, pyuvm.uvm_subscriber, Randomized.add_rand, Randomized.add_constraint, CoverPoint):
    apis[obj.__module__ + "." + obj.__qualname__] = {"signature": str(inspect.signature(obj)), "source": inspect.getfile(obj)}
try:
    import vsc
    for obj in (vsc.randobj, vsc.covergroup, vsc.coverpoint, vsc.RandState.mkFromSeed):
        apis[obj.__module__ + "." + obj.__qualname__] = {"signature": str(inspect.signature(obj)), "source": inspect.getfile(obj)}
except ImportError:
    pass
result = {"python": platform.python_version(), "platform": platform.platform(), "packages": packages, "apis": apis}
(out / "dependencies.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: v.get("version", v.get("status")) for k,v in packages.items()}, indent=2))
