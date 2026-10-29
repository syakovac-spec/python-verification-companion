"""Run isolated M2 simulations; qualify deliberate failures outside DUT evidence."""
import argparse
from dataclasses import asdict
import hashlib
import importlib.metadata as md
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE / "tb"))
from apb_evidence import catalog, sha
from verification_evidence.model import Compatibility, Manifest, Artifact, Bundle, Run, Finalization, catalog_digest, dump, load
from verification_evidence.core import validate, summarize
from verification_evidence import simulation


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def prepare(out, wait, case, command, seed=42, mutant=0, replay=None):
    sources = sorted(list((HERE / "rtl").glob("*.sv")) + list((HERE / "tb").glob("*.py")) + [Path(__file__)])
    sources += sorted((ROOT / "src" / "verification_evidence").glob("*.py"))
    source_hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in sources}
    dependencies = {d.metadata["Name"]: d.version for d in md.distributions()}
    tools = simulation.identity()
    tools["platform"] = platform.platform()
    for name in ("cocotb", "pyuvm"):
        tools[name] = md.version(name)
    functional = case.startswith("m3")
    config = {"wait_cycles": wait, "case": case, "mutant": mutant, "timescale": "1ns/1ps", "top": "apb_top",
              "simulator": simulation.simulator(), "build_flags": simulation.build_flags(), "test_flags": json.loads(os.environ.get("PVC_TEST_ARGS", "[]")), "clock_period_ns": 10, "random_generation": functional,
              "solver_selection": os.environ.get("VSC_SOLVER", "library-default"),
              "solver_fallback": os.environ.get("VSC_DVSOLVE_FALLBACK", "library-default"),
              "native_assertions_required": False, "checker": "Python observed-bus model"}
    inputs = dict(sources=source_hashes, dependencies=dependencies, configuration=config, tools=tools)
    (out / "inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
    cat = catalog(functional)
    seeds = {"root": str(seed), "stimulus": "directed-no-random"}
    if functional:
        seeds = {"root": str(seed), "algorithm": "apb-stream-v1"}
        for component in ("transactions", "resets", "idle"):
            seeds[component] = str(int.from_bytes(hashlib.sha256(f"apb-stream-v1:{seed}:env.random.{component}".encode()).digest()[:4], "big"))
    manifest = Manifest(str(uuid.uuid4()), Compatibility(1, catalog_digest(cat),
        digest({k:v for k,v in source_hashes.items() if k.endswith(".sv")}), digest(config), f"rtl-wait-{wait}",
        digest({"tools": tools, "sampling": "HDL-pre-NBA-v1"}), cat.checkers[0].digest, "apb-m2-v1"),
        1000, digest(source_hashes), digest(dependencies), tools, seeds,
        command, [Artifact("inputs.json", sha(out / "inputs.json"))], "")
    (out / "manifest.json").write_text(json.dumps(asdict(manifest), indent=2) + "\n")
    return manifest


def worker(args):
    out = Path(args.out).resolve()
    simulation.run(sources=[HERE / "rtl" / "apb_peripheral.sv", HERE / "rtl" / "apb_top.sv"],
        top="apb_top", parameters={"WAIT_CYCLES": args.wait, "MUTANT": args.mutant}, out=out,
        module="test_apb", test_dir=HERE / "tb", seed=args.seed,
        plusargs=["+wavefile=" + str(out / "waves.vcd")],
        extra_env={"APB_OUT": str(out), "APB_WAIT": str(args.wait), "APB_CASE": args.case,
            "APB_SEED": str(args.seed), "APB_REPLAY": str(Path(args.replay).resolve() / "pins.json") if args.replay else ""})



EXPECTED = {"wrong_response": {"APB-001.id", "APB-001.startup.id"},
            "missing_response": {"APB-006.read", "APB-010.drained"},
            "unstable_control": {"APB-009.clean"}, "truncated": {"APB-010.drained"}, "interrupted": {"APB-010.drained"}}


def run_one(directory, wait, case, seed=42, mutant=0, replay=None):
    out = directory / f"{case}-wait-{wait}-seed-{seed}-mut-{mutant}{'-replay' if replay else ''}"
    out.mkdir(parents=True)
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--wait", str(wait), "--case", case, "--seed", str(seed), "--out", str(out)]
    command += ["--mutant", str(mutant)]
    if replay:
        command += ["--replay", str(replay)]
    manifest = prepare(out, wait, case, command, seed, mutant)
    if replay:
        from apb_replay import verify_source
        manifest.replay_of = verify_source(replay, json.loads((out / "inputs.json").read_text()))
        if load(Path(replay) / "bundle.json").runs[0].manifest.seeds != manifest.seeds:
            raise ValueError("replay seed identity mismatch")
        (out / "manifest.json").write_text(json.dumps(asdict(manifest), indent=2) + "\n")
    try:
        p = subprocess.run(command, capture_output=True, text=True, timeout=240)
        stdout, stderr, code = p.stdout, p.stderr, p.returncode
    except subprocess.TimeoutExpired as exc:
        stdout, stderr, code = str(exc.stdout or ""), str(exc.stderr or ""), None
    (out / "stdout.log").write_text(stdout)
    (out / "stderr.log").write_text(stderr)
    infrastructure_error = None
    if not (out / "bundle.json").exists():
        infrastructure_error = "simulation did not finalize evidence"
        from apb_recovery import recover
        bundle = recover(out, wait, infrastructure_error)

    else:
        bundle = load(out / "bundle.json")
    for name in ("stdout.log", "stderr.log", "results.xml", "waves.vcd", "manifest.json", "solver-profile.json", "timing.json"):
        if (out / name).exists():
            bundle.runs[0].manifest.artifacts.append(Artifact(name, sha(out / name)))
    validate(bundle)
    dump(bundle, out / "bundle.json")
    result = summarize(bundle)
    (out / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    try:
        cases = list(ET.parse(out / "results.xml").getroot().iter("testcase"))
        failures = [c for c in cases if c.find("failure") is not None or c.find("error") is not None]
        xml_ok = len(cases) == 1 and len(failures) == (0 if not mutant and (case == "baseline" or case.startswith("m3")) else 1)
    except (OSError, ET.ParseError):
        xml_ok = False
    failed_ids = {c.obligation_id for c in bundle.runs[0].checks if c.outcome == "fail"}
    sampling_changes = 0
    if (out / "samples.jsonl").exists():
        for line in (out / "samples.jsonl").read_text().splitlines():
            item = json.loads(line)
            if item["kind"] == "sample" and item["signals"]["rdata"] != item["post_nba_rdata"]:
                sampling_changes += 1
    qualified = xml_ok and not infrastructure_error
    if mutant:
        target = {1: "APB-002.readback", 2: "APB-006.write", 3: "APB-004.readback",
                  4: "APB-005.unmapped.read", 5: "APB-008.setup.write", 6: "APB-006.read"}[mutant]
        qualified &= code in (0, 1) and result["gate"] == "failed" and target in failed_ids
        qualified &= "APB_CHECK_FAILURES" in stdout
        if mutant == 2:
            qualified &= any(c.reason == "SIDE_EFFECT_BEFORE_ACCEPT" and c.outcome == "fail" for c in bundle.runs[0].checks)
    elif case == "interrupted":
        qualified &= bundle.runs[0].finalization.status == "error" and bundle.runs[0].finalization.pending == 1
        qualified &= failed_ids == {"APB-010.drained"} and "DELIBERATE_INTERRUPTION" in stdout
    elif case in ("baseline", "m3"):
        qualified &= code == 0 and result["gate"] == "pass" and sampling_changes > 0
    elif case == "m3-gap":
        qualified &= code == 0 and result["gate"] == "incomplete" and not failed_ids
        qualified &= any(o["id"] == "FC-001.write.unmapped" and o["status"] == "uncovered" for o in result["obligations"])
    else:
        qualified &= code in (0, 1) and result["gate"] == "failed" and failed_ids == EXPECTED[case]
        # Require named checker failure in the simulator log; a crash is not detection.
        qualified &= "APB_CHECK_FAILURES" in stdout
    row = dict(mutant=mutant, replay_of=manifest.replay_of, case=case, seed=seed, wait_cycles=wait, qualified=bool(qualified), process_returncode=code,
               gate=result["gate"], failed_obligations=sorted(failed_ids), xml_expected=xml_ok,
               pre_post_nba_changes=sampling_changes, directory=str(out), infrastructure_error=infrastructure_error)
    # Validate what was captured, independently of the in-simulator writer.
    artifact_integrity = all(sha(out / artifact.path) == artifact.sha256 for artifact in bundle.runs[0].manifest.artifacts)
    row["artifact_integrity"] = artifact_integrity
    row["qualified"] &= artifact_integrity
    if replay and (out / "samples.jsonl").exists() and (out / "pins.json").exists():
        original = load(Path(replay) / "bundle.json")
        row["same_checker_results"] = asdict(bundle.runs[0])["checks"] == asdict(original.runs[0])["checks"]
        row["same_samples"] = (out / "samples.jsonl").read_bytes() == (Path(replay) / "samples.jsonl").read_bytes()
        row["same_pin_trace"] = json.loads((out / "pins.json").read_text()) == json.loads((Path(replay) / "pins.json").read_text())
        row["qualified"] &= row["same_checker_results"] and row["same_samples"] and row["same_pin_trace"]
    print(json.dumps(row), flush=True)
    return row


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--worker", action="store_true")
    p.add_argument("--wait", type=int, choices=[0, 1, 3], default=0)
    p.add_argument("--case", choices=["baseline", "m3", "m3-gap"] + list(EXPECTED), default="baseline")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--mutant", type=int, choices=range(7), default=0)
    p.add_argument("--replay")
    p.add_argument("--m4", action="store_true")
    p.add_argument("--m3", action="store_true", help="Constrained closure suite and deliberate coverage gap")
    p.add_argument("--out")
    p.add_argument("--single", action="store_true", help="Run one selected case for debugging")
    simulation.configure(p)
    args = p.parse_args()
    simulation.select(args)
    if args.replay and not args.worker and (not args.single or args.m4 or args.m3):
        p.error("--replay requires --single and cannot be combined with suite flags")
    if args.worker:
        worker(args)
        return 0
    directory = ROOT / "evidence" / ("m4" if args.m4 or args.replay or args.mutant else "m3" if args.m3 or args.case.startswith("m3") else "m2") / str(uuid.uuid4())
    directory.mkdir(parents=True)
    selection = [(args.wait, args.case, args.seed)] if args.single else ([(n, "m3", 42) for n in (0, 1, 3)] + [(3, "m3", 17), (0, "m3-gap", 42)] if args.m3 else
                [(n, "baseline", 42) for n in (0, 1, 3)] + [(3, name, 42) for name in EXPECTED])
    if args.m4:
        rows = []
        for mutant in range(7):
            first = run_one(directory, 3, "m3", 42, mutant)
            rows.append(first)
            rows.append(run_one(directory, 3, "m3", 42, mutant, first["directory"]))
        rows.append(run_one(directory, 3, "interrupted"))
    else:
        rows = [run_one(directory, wait, case, seed, args.mutant, args.replay) for wait, case, seed in selection]
    result = dict(qualified=all(r["qualified"] for r in rows), runs=rows, complete_suite=not args.single)
    (directory / "qualification.json").write_text(json.dumps(result, indent=2) + "\n")
    (directory.parent / "latest.json").write_text(json.dumps({"path": str(directory / "qualification.json")}) + "\n")
    return 0 if result["qualified"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc), "qualified": False}), file=sys.stderr)
        sys.exit(2)
