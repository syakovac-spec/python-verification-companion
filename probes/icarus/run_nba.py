from pathlib import Path
import os
import sys
import xml.etree.ElementTree as ET
from cocotb.runner import get_runner

here = Path(__file__).resolve().parent
out = here.parents[1] / "evidence" / "iv0"
out.mkdir(parents=True, exist_ok=True)
negative = "--negative" in sys.argv
os.environ["VIRTUAL_ENV"] = sys.prefix
runner = get_runner("icarus")
runner.build(verilog_sources=[here / "nba.sv"], hdl_toplevel="nba", build_args=["-g2012"], build_dir=here / "sim_build", always=True)
xml = out / ("nba-negative.xml" if negative else "nba.xml")
try:
    runner.test(hdl_toplevel="nba", test_module="test_nba", test_dir=here,
                results_xml=str(xml), seed=42, extra_env={"NBA_NEGATIVE": "1" if negative else "0"})
except SystemExit:
    # Inspect the actual result artifact below; runner exits on failed tests.
    pass
root = ET.parse(xml).getroot()
cases = list(root.iter("testcase"))
failures = [c for c in cases if c.find("failure") is not None or c.find("error") is not None]
assert len(cases) == 2, f"Expected both cocotb and pyuvm probes, got {len(cases)}"
if negative:
    assert len(failures) == 1 and failures[0].get("name") == "observe_nba", "Deliberate cocotb failure not detected"
else:
    assert not failures, "Integration probe failed"
print("NBA_NEGATIVE_DETECTED" if negative else "NBA_AND_PYUVM_PASS")
