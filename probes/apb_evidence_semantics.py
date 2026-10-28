"""Derived reporting experiment on real runs; does not create simulator evidence."""
import copy
import json
import sys
from pathlib import Path
from verification_evidence.model import load
from verification_evidence.core import merge, summarize

directory = Path(sys.argv[1])
first = load(directory / "m3-wait-3-seed-42/bundle.json")
second = load(directory / "m3-wait-3-seed-17/bundle.json")
merged = merge([first, second, first])
assert len(merged.runs) == 2
assert summarize(merged)["gate"] == "pass"
derived = copy.deepcopy(first)
target = "FC-001.write.unmapped"
for coverage in derived.runs[0].coverage:
    if coverage.bin_id == target:
        coverage.check_ids = []
summary = summarize(derived)
row = next(r for r in summary["obligations"] if r["id"] == target)
assert row["status"] == "unchecked" and row["counts"]["observed"] >= 3
assert row["eligible_checked_pass"] == 0 and summary["gate"] == "incomplete"
result = {"passed": True, "scope": "Derived reporting counterexample, not a new simulation or replay",
          "source": str(directory), "transformation": "Remove coverage-to-check links for " + target,
          "unchecked": row, "derived_gate": summary["gate"],
          "merge": {"unique_runs": len(merged.runs), "gate": summarize(merged)["gate"]}}
(directory / "evidence-semantics.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
