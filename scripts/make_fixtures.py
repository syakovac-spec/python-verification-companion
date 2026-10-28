"""Generate explicitly synthetic evidence, never simulator qualification evidence."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from test_evidence import sample, recount
from verification_evidence.model import dump

root = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
root.mkdir(exist_ok=True)
for name in ("passing", "attempted", "unchecked", "failing", "incomplete", "incompatible", "invalid_reference"):
    b = sample(); r = b.runs[0]
    if name == "attempted":
        r.events = []; r.checks = []; r.coverage = []
    elif name == "unchecked":
        r.checks = []; r.coverage[0].check_ids = []
    elif name == "failing":
        r.checks[0].outcome = "fail"; r.checks[0].reason = "Readback mismatch"; r.finalization.status = "fail"
    elif name == "incomplete":
        r.finalization.status = "timeout"; r.finalization.pending = 1
    elif name == "incompatible":
        r.manifest.id = "RUN-other"; r.events[0].run_id = "RUN-other"
        r.manifest.compatibility.configuration_digest = "different-config"
    elif name == "invalid_reference":
        r.coverage[0].event_ids = ["missing"]
    recount(r); dump(b, root / (name + ".json"))
