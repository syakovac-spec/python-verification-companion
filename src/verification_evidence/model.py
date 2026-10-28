"""Version 1 records and strict JSON decoding; IDs are scoped to their container."""
from dataclasses import asdict, dataclass, field, is_dataclass
import hashlib
import json
from pathlib import Path
from typing import get_args, get_origin, get_type_hints


class EvidenceError(ValueError):
    """Malformed or semantically inconsistent evidence."""


@dataclass
class Requirement:
    id: str
    statement: str
    source_revision: str


@dataclass
class Checker:
    id: str
    version: str
    digest: str
    description: str
    event_types: list[str]
    xz_policy: str


@dataclass
class Bin:
    id: str
    version: str
    digest: str
    description: str
    threshold: int


@dataclass
class Obligation:
    id: str
    requirement_id: str
    bin_id: str
    checker_ids: list[str]
    goal: int
    profiles: list[str]


@dataclass
class Exclusion:
    id: str
    obligation_id: str
    profiles: list[str]
    reason: str
    author: str
    reviewer: str
    revision: str
    provenance: str


@dataclass
class Catalog:
    schema_version: str
    revision: str
    requirements: list[Requirement]
    checkers: list[Checker]
    bins: list[Bin]
    obligations: list[Obligation]
    exclusions: list[Exclusion]


@dataclass
class Compatibility:
    schema_major: int
    catalog_digest: str
    dut_digest: str
    configuration_digest: str
    profile: str
    execution_semantics: str
    checker_digest: str
    adapter_version: str


@dataclass
class Artifact:
    path: str
    sha256: str


@dataclass
class Manifest:
    id: str
    compatibility: Compatibility
    time_resolution_fs: int
    source_digest: str
    dependency_digest: str
    tools: dict[str, str]
    seeds: dict[str, str]
    command: list[str]
    artifacts: list[Artifact]
    replay_of: str


@dataclass
class Intent:
    id: str
    obligation_id: str
    stream_id: str
    payload: dict


@dataclass
class Event:
    id: str
    run_id: str
    interface: str
    epoch: int
    correlation: str
    index: int
    tick: int
    kind: str
    payload: dict


@dataclass
class Check:
    id: str
    checker_id: str
    obligation_id: str
    event_ids: list[str]
    outcome: str
    reason: str
    tick: int
    triggered: bool


@dataclass
class Coverage:
    id: str
    bin_id: str
    event_ids: list[str]
    check_ids: list[str]


@dataclass
class Finalization:
    status: str
    reason: str
    pending: int
    record_counts: dict[str, int]
    pending_by_obligation: dict[str, int] = field(default_factory=dict)


@dataclass
class Run:
    manifest: Manifest
    intents: list[Intent]
    events: list[Event]
    checks: list[Check]
    coverage: list[Coverage]
    finalization: Finalization


@dataclass
class Bundle:
    catalog: Catalog
    runs: list[Run]


def decode(cls, value, path="bundle"):
    """Reject unknown fields and wrong primitive types (including bool as int)."""
    if is_dataclass(cls):
        if type(value) is not dict:
            raise EvidenceError(f"{path}: expected object")
        hints = get_type_hints(cls)
        if set(value) != set(hints):
            raise EvidenceError(f"{path}: missing {sorted(set(hints)-set(value))}; unknown {sorted(set(value)-set(hints))}")
        return cls(**{k: decode(t, value[k], f"{path}.{k}") for k, t in hints.items()})
    origin, args = get_origin(cls), get_args(cls)
    if origin is list:
        if type(value) is not list:
            raise EvidenceError(f"{path}: expected array")
        return [decode(args[0], x, f"{path}[{i}]") for i, x in enumerate(value)]
    if origin is dict:
        if type(value) is not dict:
            raise EvidenceError(f"{path}: expected object")
        return {decode(args[0], k, path): decode(args[1], v, f"{path}.{k}") for k, v in value.items()}
    if type(value) is not cls:
        raise EvidenceError(f"{path}: expected {cls.__name__}")
    return value


def normalized(value):
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, dict):
        return {k: normalized(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        result = [normalized(v) for v in value]
        # Entity collections are unordered. Commands and payload arrays are ordered.
        return result
    return value


def canonical(value):
    return json.dumps(normalized(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def catalog_digest(catalog):
    data = asdict(catalog)
    for key in ("requirements", "checkers", "bins", "obligations", "exclusions"):
        data[key].sort(key=lambda x: x["id"])
    return hashlib.sha256(canonical(data).encode()).hexdigest()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load(path):
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_unique_object,
                         parse_constant=lambda x: (_ for _ in ()).throw(EvidenceError(f"invalid number: {x}")))
        return decode(Bundle, raw)
    except (json.JSONDecodeError, UnicodeError, RecursionError) as exc:
        raise EvidenceError(f"{path}: invalid JSON: {exc}") from exc


def dump(bundle, path):
    Path(path).write_text(json.dumps(normalized(bundle), indent=2, allow_nan=False) + "\n", encoding="utf-8")
