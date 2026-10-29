"""Profile the actual APB constraints independently of simulator and I/O cost."""
import argparse
import cProfile
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples/apb_peripheral/tb"))


def measure(count, operation, check):
    durations = []
    for index in range(count):
        start = time.perf_counter_ns()
        result = operation(index)
        durations.append((time.perf_counter_ns() - start) / 1e6)
        if not check(result, index):
            raise AssertionError(f"solver produced an illegal result at draw {index}: {result}")
    ordered = sorted(durations)
    return dict(draws=count, total_ms=sum(durations), first_ms=durations[0],
                median_ms=statistics.median(durations), p95_ms=ordered[min(count - 1, int(count * .95))],
                maximum_ms=max(durations), legality_passed=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--solver", choices=["boolector", "dv-solve"], help="explicit PyVSC backend; dv-solve requires PyVSC 1.0+")
    parser.add_argument("--out", type=Path, default=ROOT / "evidence/constraints/profile.json")
    parser.add_argument("--cprofile", type=Path, help="optional Python profile; native solver time appears at its call boundary")
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be positive")
    if args.solver:
        os.environ["VSC_SOLVER"] = args.solver
    start = time.perf_counter()
    from apb_random import Streams
    import vsc
    from vsc.model.solve_failure import SolveFailure
    backend = vsc.get_solver_backend() if hasattr(vsc, "get_solver_backend") else "boolector"
    if args.solver and args.solver != backend:
        parser.error(f"installed PyVSC cannot select {args.solver}; effective backend is {backend}")
    import_seconds = time.perf_counter() - start
    start = time.perf_counter()
    streams = Streams(args.seed, 3)
    construction_seconds = time.perf_counter() - start
    profile = cProfile.Profile() if args.cprofile else None
    if profile:
        profile.enable()
    legal = lambda r, i: r["address"] in (0, 4, 8, 12, 16, 6) and 0 <= r["data"] < 2**32
    rows = {"weighted_address": measure(args.iterations, lambda i: streams.draw(), legal),
            "targeted_bit_constraints": measure(args.iterations,
                lambda i: streams.draw(address=4, write=1, high=i % 2, low=i % 4),
                lambda r, i: legal(r, i) and r["address"] == 4 and r["write"] and r["data"] >> 31 == i % 2 and r["data"] & 3 == i % 4),
            "reset_constraints": measure(args.iterations, lambda i: streams.draw_reset(i % 3, i % 2),
                lambda r, i: r["phase"] == ("setup", "wait", "completion")[i % 3] and r["write"] == bool(i % 2))}
    start = time.perf_counter()
    unsat = False
    try:
        streams.draw(address=3)  # forbidden by the permanent legal-address constraint
    except SolveFailure as exc:
        unsat = True
        unsat_type = type(exc).__name__
    if not unsat:
        raise AssertionError("inconsistent constraints unexpectedly succeeded")
    unsat_seconds = time.perf_counter() - start
    if profile:
        profile.disable()
        args.cprofile.parent.mkdir(parents=True, exist_ok=True)
        profile.dump_stats(args.cprofile)
    dependencies = {}
    for name in ("pyvsc", "pyboolector", "dv-solve"):
        try:
            dependencies[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            pass
    result = dict(python=platform.python_version(), dependencies=dependencies, seed=args.seed,
                  solver=backend, cprofile_enabled=bool(profile),
                  import_seconds=import_seconds, construction_seconds=construction_seconds,
                  cases=rows, unsatisfiable=dict(rejected=unsat, exception=unsat_type, seconds=unsat_seconds),
                  scope="PyVSC randomize calls including constraint construction and native solver; not simulator time")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
