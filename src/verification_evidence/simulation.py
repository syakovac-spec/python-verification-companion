"""Optional simulator integration. Imports cocotb only when executing a run.

The evidence core has no dependency on this module or on a particular simulator.
The selected Python executable owns the environment, including conda prefixes.
"""
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


def simulator():
    return os.environ.get("SIM", "icarus").lower()


def build_flags():
    defaults = {"icarus": ["-g2012"], "verilator": ["--timing", "-Wno-fatal"]}
    return defaults.get(simulator(), []) + json.loads(os.environ.get("PVC_BUILD_ARGS", "[]"))


def configure(parser):
    parser.add_argument("--build-cache", help="opt-in local Linux build cache (qualified backends only)")
    parser.add_argument("--sim", default=simulator(), help="cocotb simulator name; defaults to SIM or icarus")
    parser.add_argument("--build-arg", action="append", default=[], help="additional compiler argument (use --build-arg=-flag)")
    parser.add_argument("--test-arg", action="append", default=[], help="additional simulator argument")


def select(args):
    if getattr(args, 'build_cache', None):
        os.environ['PVC_BUILD_CACHE'] = str(Path(args.build_cache).resolve())
    os.environ["SIM"] = args.sim.lower()
    # Workers inherit these values. Do not erase options when reparsing a worker.
    if args.build_arg:
        os.environ["PVC_BUILD_ARGS"] = json.dumps(args.build_arg)
    if args.test_arg:
        os.environ["PVC_TEST_ARGS"] = json.dumps(args.test_arg)


def identity():
    probes = {"icarus": [("iverilog", "-V"), ("vvp", "-V")],
              "verilator": [("verilator", "--version")], "vcs": [("vcs", "-ID")],
              "questa": [("vsim", "-version")], "riviera": [("vsimsa", "-version")],
              "xcelium": [("xrun", "-version")], "ghdl": [("ghdl", "--version")],
              "nvc": [("nvc", "--version")]}
    result = {"simulator": simulator(), "python": sys.version.split()[0], "cocotb": metadata.version("cocotb")}
    for name, flag in probes.get(simulator(), [(simulator(), "--version")]):
        executable = shutil.which(name)
        if executable is None:
            raise RuntimeError(f"{simulator()}: executable {name!r} unavailable in the active environment PATH")
        proc = subprocess.run([executable, flag], text=True, capture_output=True, timeout=30)
        output = (proc.stdout + proc.stderr).strip()
        result[name] = output.splitlines()[0] if output else f"version probe returned {proc.returncode}"
        result[name + "_version_output_sha256"] = hashlib.sha256(output.encode()).hexdigest()
        result[name + "_sha256"] = hashlib.sha256(Path(executable).read_bytes()).hexdigest()
    return result


def vcs_make_command(*, sources, top, parameters, out, module, plusargs):
    """Use cocotb's public Makefile backend: available even in cocotb 1.9."""
    try:
        from cocotb_tools.config import makefiles_dir
        makefiles = Path(makefiles_dir)
    except ImportError:
        import cocotb.config
        makefiles = Path(cocotb.config.share_dir) / "makefiles"
    flags = build_flags() + [f"-pvalue+{top}.{key}={value}" for key, value in parameters.items()]
    return ["make", "-f", str(makefiles / "Makefile.sim"), "SIM=vcs", "TOPLEVEL_LANG=verilog",
            f"TOPLEVEL={top}", f"COCOTB_TOPLEVEL={top}", f"MODULE={module}", f"COCOTB_TEST_MODULES={module}",
            "VERILOG_SOURCES=" + " ".join(str(p) for p in sources), f"SIM_BUILD={out / 'build'}",
            f"COCOTB_RESULTS_FILE={out / 'results.xml'}", "COMPILE_ARGS=" + " ".join(flags),
            "SIM_ARGS=" + " ".join(json.loads(os.environ.get("PVC_TEST_ARGS", "[]"))),
            "PLUSARGS=" + " ".join(plusargs)]


def run(*, sources, top, parameters, out, module, test_dir, extra_env, seed=42, plusargs=(), includes=(), defines=None):
    """Run using the active interpreter; never activate or manufacture an environment."""
    out = Path(out).resolve()
    start = time.perf_counter()
    timing = {"simulator": simulator(), "python": sys.executable}
    defines = dict(defines or {})
    timing['cache'] = {'status': 'disabled'}
    original_path = os.environ.get("PATH")
    # cocotb supplies PYTHONHOME to build tools too. Their `python3` helpers
    # must resolve to this interpreter, not an unrelated system Python.
    os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + (original_path or "")
    try:
        if simulator() == "vcs":
            if includes or defines:
                raise ValueError('VCS includes/defines currently require explicit backend build arguments')
            if os.environ.get('PVC_BUILD_CACHE'):
                timing['cache'] = {'status': 'bypass', 'reason': 'backend not cache-qualified'}
            env = os.environ.copy()
            env.update(extra_env)
            # cocotb-config must come from the same interpreter, including conda.
            env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
            env["PYTHON_BIN"] = sys.executable
            env["PYTHONPATH"] = os.pathsep.join([str(test_dir), *sys.path])
            env["RANDOM_SEED"] = env["COCOTB_RANDOM_SEED"] = str(seed)
            subprocess.run(vcs_make_command(sources=sources, top=top, parameters=parameters,
                           out=out, module=module, plusargs=plusargs), cwd=out, env=env, check=True)
        else:
            try:
                from cocotb_tools.runner import get_runner
            except ImportError:
                from cocotb.runner import get_runner
            runner = get_runner(simulator())
            def build():
                runner.build(sources=sources, hdl_toplevel=top, parameters=parameters,
                             includes=includes, defines=defines,
                             build_args=build_flags(), build_dir=out / "build", always=True)
            cache = os.environ.get('PVC_BUILD_CACHE')
            if cache and sys.platform == 'linux' and simulator() in ('icarus', 'verilator') and build_flags() == {'icarus': ['-g2012'], 'verilator': ['--timing', '-Wno-fatal']}[simulator()] and not os.environ.get('WAVES'):
                from .build_cache import descriptor, materialize, runtime_identity
                tools = identity()
                describe = lambda: descriptor(sources, includes, defines, top, parameters, build_flags(), tools)
                try:
                    tools['native_resources'] = runtime_identity(simulator())
                    describe()
                except (ValueError, UnicodeError) as exc:
                    timing['cache'] = {'status': 'bypass', 'reason': str(exc)}
                    build()
                else:
                    timing['cache'] = materialize(cache, describe, out / 'build', build)
            else:
                if cache:
                    timing['cache'] = {'status': 'bypass', 'reason': 'unqualified backend/platform, custom flags or wave settings'}
                build()
            timing["build_seconds"] = time.perf_counter() - start
            runner.test(hdl_toplevel=top, test_module=module, test_dir=test_dir, seed=seed,
                        build_dir=out / 'build', hdl_toplevel_lang='verilog' if timing['cache']['status'] == 'hit' else None, parameters=parameters,
                        results_xml=str(out / "results.xml"), plusargs=list(plusargs),
                        test_args=json.loads(os.environ.get("PVC_TEST_ARGS", "[]")), extra_env=extra_env)
    finally:
        if original_path is None:
            os.environ.pop("PATH", None)
        else:
            os.environ["PATH"] = original_path
        timing["total_seconds"] = time.perf_counter() - start
        if "build_seconds" in timing:
            timing["test_seconds"] = timing["total_seconds"] - timing["build_seconds"]
        (out / "timing.json").write_text(json.dumps(timing, indent=2) + "\n")
