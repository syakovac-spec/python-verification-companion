"""Example-specific plan/manifest binding; the recorder itself is reusable."""
import json
import os
from pathlib import Path
from verification_evidence.model import Manifest, decode, dump
from verification_evidence.recording import EvidenceRecorder
from verification_evidence.core import summarize
from model import plan, StreamModel


def session():
    directory = Path(os.environ["STREAM_OUT"])
    manifest = decode(Manifest, json.loads((directory / "manifest.json").read_text()))
    recorder = EvidenceRecorder(plan(manifest.compatibility.checker_digest), manifest)
    return directory, StreamModel(recorder)


def finish(directory, model, tick, error=None):
    bundle = model.finish(tick, error)
    dump(bundle, directory / "bundle.json")
    result = summarize(bundle)
    (directory / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
