"""Conservative evidence recovery after a simulator process fails to finalize."""
import json
from pathlib import Path
from apb_model import Analyzer
from apb_evidence import Recorder


def recover(directory, wait, reason):
    recorder = Recorder(directory)
    model = Analyzer(wait, recorder.write)
    last_tick = 0
    uncertain = False
    path = Path(directory) / "samples.jsonl"
    lines = path.read_text().splitlines() if path.exists() else []
    for line in lines:
        try:
            row = json.loads(line)
            last_tick = row["tick"]
            if row["kind"] == "reset":
                model.reset(last_tick, row["signals"])
            elif row["kind"] == "sample":
                model.sample(row["signals"], last_tick)
        except (ValueError, KeyError, TypeError):
            uncertain = True
            break
    # This sentinel is conservative bookkeeping, not an observed transfer.
    if (not lines or uncertain) and model.pending is None:
        model.pending = {"recovery_unknown": True}
        reason += "; incomplete observation log: pending state unknown"
    model.finish(last_tick)
    recorder.finish(model, reason)
    return recorder.bundle
