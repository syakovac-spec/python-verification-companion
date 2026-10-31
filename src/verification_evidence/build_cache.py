"""Opt-in local build cache. Never share writable simulation directories."""
from contextlib import contextmanager
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def dependencies(sources, includes=()):
    """Resolve literal Verilog includes; reject unknown preprocessing dependencies."""
    found = {}
    def visit(path):
        path = Path(path).resolve()
        if str(path) in found:
            return
        data = path.read_bytes()
        found[str(path)] = hashlib.sha256(data).hexdigest()
        text = data.decode('utf-8')
        for match in re.finditer(r'`include\s+([^\r\n]+)', text):
            literal = re.match(r'"([^"\r\n]+)"', match[1])
            if not literal:
                raise ValueError('cache requires literal include paths')
            candidates = [path.parent / literal[1]] + [Path(p) / literal[1] for p in includes]
            target = next((p for p in candidates if p.is_file()), None)
            if target is None:
                raise ValueError(f'cache cannot resolve include {literal[1]}')
            visit(target)
    for source in sources:
        visit(source)
    return found


def inventory(directory):
    result = {}
    for path in sorted(Path(directory).rglob('*')):
        if path.is_symlink():
            raise ValueError('symlinks are not supported in cached builds')
        if path.is_file():
            result[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


@contextmanager
def lock(path, timeout=300):
    import fcntl
    with Path(path).open('a') as handle:
        started = time.monotonic()
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() - started > timeout:
                    raise TimeoutError('timed out waiting for build-cache lock')
                time.sleep(.05)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def materialize(root, descriptor, destination, build):
    """Build once under a process lock, hash artifacts, copy to each private run."""
    if sys.platform != 'linux':
        raise ValueError('build cache currently requires Linux/WSL file locking')
    root = Path(root).resolve(); root.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = Path(destination)
    if destination.exists():
        raise ValueError('cached run requires a fresh build directory')
    initial = descriptor()
    key = digest(initial)
    entry = root / key
    with lock(root / (key + '.lock')):
        valid = False
        if entry.exists():
            if entry.is_symlink():
                raise ValueError('cache entry cannot be a symlink')
            try:
                metadata = json.loads((entry / 'entry.json').read_text())
                valid = (metadata['descriptor'] == initial and bool(metadata['artifacts'])
                         and inventory(entry / 'build') == metadata['artifacts'])
            except (OSError, ValueError, KeyError):
                valid = False
        if valid:
            shutil.copytree(entry / 'build', destination)
            return dict(status='hit', key=key)
        build()
        if descriptor() != initial:
            raise RuntimeError('build inputs changed during compilation; cache not published')
        artifacts = inventory(destination)
        if not artifacts:
            raise RuntimeError('build produced no cacheable artifacts')
        staging = Path(tempfile.mkdtemp(prefix=key + '-', dir=root))
        try:
            shutil.copytree(destination, staging / 'build')
            (staging / 'entry.json').write_text(json.dumps(dict(descriptor=initial, artifacts=artifacts)))
            if entry.exists():
                # entry is a validated digest-named direct child of resolved root.
                shutil.rmtree(entry)
            staging.rename(entry)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
        return dict(status='miss', key=key)


def descriptor(sources, includes, defines, top, parameters, flags, tools):
    return dict(format=1, sources=dependencies(sources, includes), order=[str(Path(p).resolve()) for p in sources],
        includes=[str(Path(p).resolve()) for p in includes], defines=defines, top=top,
        parameters=parameters, flags=flags, tools=tools, python=sys.executable,
        # Conservative invalidation without storing credentials/environment values.
        environment_digest=digest({k: v for k, v in os.environ.items() if k not in
            {'COCOTB_RANDOM_SEED', 'RANDOM_SEED', 'PVC_BUILD_CACHE',
             'WSL_INTEROP', 'SHLVL', '_'}}))


def runtime_identity(backend):
    """Fingerprint native build resources, not just a compiler launcher script."""
    resources = {}
    dist = metadata.distribution('cocotb')
    for item in dist.files or ():
        path = Path(dist.locate_file(item))
        if path.is_file() and path.suffix in ('.so', '.dll', '.dylib', '.vpi', '.cpp', '.h'):
            resources[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    if backend == 'verilator':
        root = os.environ.get('VERILATOR_ROOT')
        if not root or not (Path(root) / 'include').is_dir():
            raise ValueError('Verilator caching requires VERILATOR_ROOT to fingerprint native resources')
        paths = [Path(root) / 'include', Path(root) / 'bin/verilator_bin']
        compiler = shutil.which(os.environ.get('CXX', 'g++'))
        if not compiler:
            raise ValueError('cannot identify C++ compiler for cache')
        paths.append(Path(compiler))
    else:
        prefix = Path(shutil.which('iverilog')).resolve().parent.parent
        paths = [p for p in [prefix/'lib/ivl', *list((prefix/'lib').glob('*/ivl'))] if p.is_dir()]
        if not paths:
            raise ValueError('cannot identify Icarus target libraries for cache')
    for path in paths:
        if path.is_dir():
            resources[str(path)] = digest(inventory(path))
        elif path.is_file():
            resources[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            raise ValueError(f'missing build resource: {path}')
    return digest(resources)
