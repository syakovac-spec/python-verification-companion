"""Strict recorded-pin replay validation, independent of simulator and solver."""
import json
from dataclasses import asdict
from pathlib import Path
from apb_evidence import sha
from verification_evidence.model import load
from verification_evidence.core import validate

WIDTHS = {"PRESETn": 1, "PSEL": 1, "PENABLE": 1, "PWRITE": 1, "PADDR": 32, "PWDATA": 32,
          "fault_read": 1, "fault_stall": 1, "reset_at_edge": 1, "functional": 1}


def validate_trace(trace):
    if set(trace) != {"version", "end_tick", "drives"} or trace["version"] != 1:
        raise ValueError("unsupported replay schema")
    previous = 0
    for row in trace["drives"]:
        if set(row) != {"tick", "name", "value"} or row["name"] not in WIDTHS:
            raise ValueError("invalid replay drive")
        if type(row["tick"]) is not int or row["tick"] < previous:
            raise ValueError("nonmonotonic replay time")
        if type(row["value"]) is not int or not 0 <= row["value"] < 2**WIDTHS[row["name"]]:
            raise ValueError("invalid replay value")
        previous = row["tick"]
    if type(trace["end_tick"]) is not int or trace["end_tick"] < previous:
        raise ValueError("invalid replay finalization time")


def verify_source(directory, current_inputs):
    directory = Path(directory).resolve()
    bundle = load(directory / "bundle.json")
    validate(bundle)
    if len(bundle.runs) != 1:
        raise ValueError("replay requires one source run")
    run = bundle.runs[0]
    names = set()
    for artifact in run.manifest.artifacts:
        path = (directory / artifact.path).resolve()
        if not path.is_relative_to(directory) or sha(path) != artifact.sha256:
            raise ValueError("replay artifact integrity mismatch: " + artifact.path)
        names.add(artifact.path)
    if not {"inputs.json", "pins.json", "manifest.json"} <= names:
        raise ValueError("source lacks required replay artifacts")
    saved_manifest = json.loads((directory / "manifest.json").read_text())
    actual_manifest = asdict(run.manifest)
    for key in saved_manifest:
        if key != "artifacts" and saved_manifest[key] != actual_manifest[key]:
            raise ValueError("source manifest identity mismatch: " + key)
    saved = json.loads((directory / "inputs.json").read_text())
    if saved != current_inputs:
        raise ValueError("replay input identity mismatch (sources/configuration/dependencies/tools)")
    trace = json.loads((directory / "pins.json").read_text())
    validate_trace(trace)
    return run.manifest.id
