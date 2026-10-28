"""Render a mutation evidence table only from a completed qualification."""
import json
import sys
from pathlib import Path

directory = Path(sys.argv[1])
result = json.loads((directory / "qualification.json").read_text())
assert result["qualified"] and len(result["runs"]) == 15
rows = result["runs"]
text = "# M4 mutation evidence\n\nGenerated from qualification.json. Wait cycles 3; seed 42.\n\n"
text += "| Case | Original gate | Replay gate | Exact pins / samples / checks | Intended check |\n| --- | --- | --- | --- | --- |\n"
checks = {0: "Baseline closure", 1: "APB-002.readback", 2: "APB-006.write (SIDE_EFFECT_BEFORE_ACCEPT)",
          3: "APB-004.readback", 4: "APB-005.unmapped.read", 5: "APB-008.setup.write", 6: "APB-006.read"}
for mutant in range(7):
    original = next(r for r in rows if r["mutant"] == mutant and not r["replay_of"] and r["case"] == "m3")
    replay = next(r for r in rows if r["mutant"] == mutant and r["replay_of"])
    assert all(replay[k] for k in ("same_pin_trace", "same_samples", "same_checker_results"))
    text += f"| {'Baseline' if mutant == 0 else f'MUT-{mutant:02}'} | {original['gate']} | {replay['gate']} | All identical | {checks[mutant]} |\n"
text += "\nAll cases compiled, produced expected test XML and passed artifact integrity checks. Additional consequential failures are retained in qualification.json.\n"
text += "\nThe deliberate interruption has error finalization and one pending APB-010 obligation; it cannot close coverage. Process-loss recovery is separately tested with partial/missing observation logs.\n"
(directory / "MUTATION_RESULTS.md").write_text(text)
print(directory / "MUTATION_RESULTS.md")
