"""Qualify installed PyVSC stream isolation; not simulator evidence."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples/apb_peripheral/tb"))
from apb_random import Streams


def trace(root, perturb=False):
    streams = Streams(root, 3)
    unrelated = Streams(root, 3, "env.unrelated")
    rows = []
    for _ in range(32):
        if perturb:
            unrelated.draw()
            streams.draw_reset()
            streams.idle.randrange(100)
        rows.append(streams.draw())
    return rows


baseline = trace(42)
assert baseline == trace(42), "same-seed repeatability failed"
assert baseline == trace(42, True), "unrelated streams perturbed transaction stream"
assert baseline != trace(17), "different seeds produced identical trace"
assert all(r["address"] in (0, 4, 8, 12, 16, 6) and 0 <= r["data"] < 2**32 for r in baseline)
targeted = Streams(42, 0)
for high in (0, 1):
    for low in range(4):
        row = targeted.draw(address=4, write=1, high=high, low=low)
        assert row["address"] == 4 and row["write"] and row["data"] >> 31 == high and row["data"] & 3 == low
assert all(targeted.draw_reset()["phase"] != "wait" for _ in range(32))
result = {"passed": True, "scope": "installed backend stream and constraint probe", "seeds": targeted.seeds,
          "checks": ["repeatability", "stream isolation", "different root", "legality", "target constraints", "zero-wait reset applicability"],
          "trace": baseline}
out = ROOT / "evidence/m3/random-streams.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2) + "\n")
print(out)
