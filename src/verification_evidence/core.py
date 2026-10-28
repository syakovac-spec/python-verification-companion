"""Validation, exact-key aggregation and conservative closure assessment."""
from dataclasses import asdict
import re
from .model import Bundle, EvidenceError, canonical, catalog_digest, decode


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def indexed(items, name):
    result = {}
    for item in items:
        require(bool(item.id.strip()) and item.id not in result, f"{name}: empty or duplicate ID {item.id!r}")
        result[item.id] = item
    return result


def refs(values, table, context, nonempty=True):
    require(not nonempty or bool(values), f"{context}: empty references")
    require(len(values) == len(set(values)), f"{context}: duplicate references")
    for value in values:
        require(value in table, f"{context}: unknown reference {value!r}")


def payload_vectors(value, context):
    """Validate reserved width/bits objects while preserving every X and Z."""
    if isinstance(value, dict):
        if "width" in value or "bits" in value:
            require(set(value) == {"width", "bits"}, f"{context}: vector requires exactly width and bits")
            width, bits = value["width"], value["bits"]
            require(type(width) is int and width > 0 and type(bits) is str and len(bits) == width
                    and bool(re.fullmatch(r"[01xXzZ]+", bits)), f"{context}: invalid four-state vector")
        else:
            for v in value.values():
                payload_vectors(v, context)
    elif isinstance(value, list):
        for v in value:
            payload_vectors(v, context)


def validate(bundle):
    # Re-validate objects built directly through the Python API as well as JSON.
    decode(Bundle, asdict(bundle))
    canonical(bundle)  # payload must be finite JSON
    cat = bundle.catalog
    require(bool(re.fullmatch(r"1\.\d+", cat.schema_version)), "catalog: unsupported schema version")
    require(bool(cat.revision.strip()), "catalog: missing revision")
    requirements = indexed(cat.requirements, "requirements")
    checkers = indexed(cat.checkers, "checkers")
    bins = indexed(cat.bins, "bins")
    obligations = indexed(cat.obligations, "obligations")
    indexed(cat.exclusions, "exclusions")
    require(bool(requirements), "catalog: no requirements")
    for checker in checkers.values():
        require(all((checker.version, checker.digest, checker.description, checker.event_types, checker.xz_policy)), f"{checker.id}: incomplete checker definition")
    for bin_ in bins.values():
        require(bin_.threshold > 0 and all((bin_.version, bin_.digest, bin_.description)), f"{bin_.id}: invalid bin")
    for ob in obligations.values():
        refs([ob.requirement_id], requirements, ob.id)
        refs([ob.bin_id], bins, ob.id)
        refs(ob.checker_ids, checkers, ob.id)
        require(ob.goal > 0 and bool(ob.profiles) and all(ob.profiles), f"{ob.id}: invalid goal/profiles")
    for req in requirements.values():
        require(bool(req.statement) and bool(req.source_revision), f"{req.id}: missing requirement metadata")
        require(any(o.requirement_id == req.id for o in obligations.values()), f"{req.id}: no obligations")
    for ex in cat.exclusions:
        refs([ex.obligation_id], obligations, ex.id)
        require(all((ex.profiles, ex.reason, ex.author, ex.reviewer, ex.revision, ex.provenance)), f"{ex.id}: incomplete exclusion metadata")
        require(set(ex.profiles) <= set(obligations[ex.obligation_id].profiles), f"{ex.id}: exclusion outside applicability")
    seen_runs = {}
    digest = catalog_digest(cat)
    for run in bundle.runs:
        m, f = run.manifest, run.finalization
        key = m.compatibility
        require(bool(m.id.strip()), "empty run ID")
        if m.id in seen_runs:
            require(canonical(run) == seen_runs[m.id], f"{m.id}: conflicting run content")
        seen_runs[m.id] = canonical(run)
        require(key.schema_major == 1 and key.catalog_digest == digest, f"{m.id}: catalog/schema compatibility mismatch")
        require(all(str(v).strip() for v in asdict(key).values()), f"{m.id}: incomplete compatibility key")
        require(m.time_resolution_fs > 0, f"{m.id}: invalid time resolution")
        require(all((m.source_digest, m.dependency_digest, m.tools, m.command)), f"{m.id}: incomplete manifest")
        for artifact in m.artifacts:
            require(bool(artifact.path) and bool(re.fullmatch(r"[0-9a-f]{64}", artifact.sha256)), f"{m.id}: invalid artifact metadata")
        intents = indexed(run.intents, m.id + ": intents")
        events = indexed(run.events, m.id + ": events")
        checks = indexed(run.checks, m.id + ": checks")
        indexed(run.coverage, m.id + ": coverage")
        for intent in intents.values():
            refs([intent.obligation_id], obligations, intent.id)
            require(bool(intent.stream_id), f"{intent.id}: missing stream")
            payload_vectors(intent.payload, intent.id)
        indices = set()
        last_tick = -1
        for event in sorted(events.values(), key=lambda e: e.index):
            require(event.run_id == m.id, f"{event.id}: wrong run")
            require(event.index >= 0 and event.index not in indices and event.tick >= last_tick and event.epoch >= 0, f"{event.id}: invalid event ordering/time/epoch")
            require(all((event.interface, event.correlation, event.kind)), f"{event.id}: incomplete event context")
            indices.add(event.index)
            last_tick = event.tick
            payload_vectors(event.payload, event.id)
        for check in checks.values():
            refs([check.checker_id], checkers, check.id)
            refs([check.obligation_id], obligations, check.id)
            refs(check.event_ids, events, check.id)
            require(check.checker_id in obligations[check.obligation_id].checker_ids, f"{check.id}: checker not mapped to obligation")
            require(check.outcome in {"pass", "fail", "inconclusive", "aborted"}, f"{check.id}: invalid outcome")
            require(bool(check.reason) and check.tick >= max(events[e].tick for e in check.event_ids), f"{check.id}: missing reason or invalid time")
            group = [events[e] for e in check.event_ids]
            require(len({(e.interface, e.epoch, e.correlation) for e in group}) == 1, f"{check.id}: crosses correlation/reset/interface boundary")
            require(all(e.kind in checkers[check.checker_id].event_types for e in group), f"{check.id}: unsupported event type")
        for cov in run.coverage:
            refs([cov.bin_id], bins, cov.id)
            refs(cov.event_ids, events, cov.id)
            refs(cov.check_ids, checks, cov.id, nonempty=False)
            require(len({(events[e].interface, events[e].epoch, events[e].correlation) for e in cov.event_ids}) == 1, f"{cov.id}: mixed event group")
            for cid in cov.check_ids:
                check = checks[cid]
                require(set(check.event_ids) == set(cov.event_ids), f"{cov.id}: wrong checker/event association")
                require(obligations[check.obligation_id].bin_id == cov.bin_id, f"{cov.id}: wrong checker/bin association")
        require(f.status in {"pass", "fail", "error", "timeout", "aborted"}, f"{m.id}: invalid run status")
        require(f.pending >= 0 and bool(f.reason), f"{m.id}: invalid finalization")
        refs(list(f.pending_by_obligation), obligations, m.id + ": pending", nonempty=False)
        require(all(n >= 0 for n in f.pending_by_obligation.values()) and sum(f.pending_by_obligation.values()) <= f.pending,
                f"{m.id}: invalid pending obligation counts")
        require(f.record_counts == {name: len(getattr(run, name)) for name in ("intents", "events", "checks", "coverage")}, f"{m.id}: record counts mismatch (truncated evidence)")
        if f.status == "pass":
            require(f.pending == 0 and all(c.outcome == "pass" for c in run.checks), f"{m.id}: passing run contains unresolved checks")
    return bundle


def merge(bundles):
    require(bool(bundles), "merge: no inputs")
    catalogs, keys, runs = set(), set(), {}
    for bundle in bundles:
        validate(bundle)
        catalogs.add(catalog_digest(bundle.catalog))
        for run in bundle.runs:
            keys.add(canonical([asdict(run.manifest.compatibility), run.manifest.time_resolution_fs]))
            rid = run.manifest.id
            require(rid not in runs or canonical(runs[rid]) == canonical(run), f"{rid}: conflicting run content")
            runs[rid] = run
    require(len(catalogs) == 1 and len(keys) <= 1, "merge: incompatible catalog or execution key")
    # Canonicalize catalog entity ordering even for empty bundles.
    cat = asdict(bundles[0].catalog)
    for field in ("requirements", "checkers", "bins", "obligations", "exclusions"):
        cat[field].sort(key=lambda x: x["id"])
    return decode(Bundle, {"catalog": cat, "runs": [asdict(runs[k]) for k in sorted(runs)]})


def summarize(bundle):
    bundle = merge([bundle])
    cat = bundle.catalog
    profile = bundle.runs[0].manifest.compatibility.profile if bundle.runs else None
    bins = {b.id: b for b in cat.bins}
    assessed = []
    for ob in sorted(cat.obligations, key=lambda o: o.id):
        counts = dict.fromkeys(("attempted", "observed", "checked_pass", "checked_fail", "inconclusive", "aborted", "untriggered", "pending"), 0)
        eligible = 0
        applicable = profile is None or profile in ob.profiles
        for run in bundle.runs:
            counts["pending"] += run.finalization.pending_by_obligation.get(ob.id, 0)
            counts["attempted"] += sum(i.obligation_id == ob.id for i in run.intents)
            checks = {c.id: c for c in run.checks}
            relevant = [c for c in run.checks if c.obligation_id == ob.id]
            for outcome, name in (("fail", "checked_fail"), ("inconclusive", "inconclusive"), ("aborted", "aborted")):
                counts[name] += sum(c.outcome == outcome for c in relevant)
            counts["untriggered"] += sum(not c.triggered for c in relevant)
            groups = {}
            events = {e.id: e for e in run.events}
            for cov in run.coverage:
                if cov.bin_id == ob.bin_id:
                    groups.setdefault(tuple(sorted(cov.event_ids)), set()).update(cov.check_ids)
            observed_scenarios, passed_scenarios = set(), set()
            for event_ids, ids in groups.items():
                event = events[event_ids[0]]
                scenario = (event.interface, event.epoch, event.correlation)
                observed_scenarios.add(scenario)
                group_checks = [checks[c] for c in ids if checks[c].obligation_id == ob.id]
                passing = {c.checker_id for c in group_checks if c.outcome == "pass" and c.triggered}
                if set(ob.checker_ids) <= passing and all(c.outcome == "pass" for c in group_checks):
                    passed_scenarios.add(scenario)
            counts["observed"] += len(observed_scenarios)
            counts["checked_pass"] += len(passed_scenarios)
            if run.finalization.status == "pass":
                eligible += len(passed_scenarios)
        goal = max(ob.goal, bins[ob.bin_id].threshold)
        if not applicable:
            status = "not_applicable"
        elif counts["checked_fail"]:
            status = "failed"
        elif not counts["observed"]:
            status = "uncovered"
        elif counts["inconclusive"] or counts["aborted"] or counts["pending"]:
            status = "incomplete"
        elif not counts["checked_pass"]:
            status = "unchecked"
        elif eligible < goal:
            status = "incomplete"
        else:
            status = "satisfied"
        exclusions = [asdict(ex) for ex in cat.exclusions if ex.obligation_id == ob.id and profile in ex.profiles]
        assessed.append(dict(id=ob.id, requirement_id=ob.requirement_id, status=status, counts=counts,
                             eligible_checked_pass=eligible, goal=goal, exclusions=exclusions))
    precedence = ("failed", "uncovered", "incomplete", "unchecked", "satisfied")
    requirements = []
    for req in sorted(cat.requirements, key=lambda r: r.id):
        items = [a for a in assessed if a["requirement_id"] == req.id and a["status"] != "not_applicable"]
        status = next((s for s in precedence if any(a["status"] == s for a in items)), "not_applicable")
        requirements.append(dict(id=req.id, status=status, missing_obligations=[a["id"] for a in items if a["status"] != "satisfied"]))
    active = [a for a in assessed if a["status"] != "not_applicable"]
    adjusted = [a for a in active if not a["exclusions"]]
    def totals(items):
        return dict(satisfied=sum(a["status"] == "satisfied" for a in items), total=len(items))
    statuses = [r.finalization.status for r in bundle.runs]
    if "fail" in statuses or any(a["status"] == "failed" for a in assessed):
        gate = "failed"
    elif "error" in statuses:
        gate = "infrastructure_error"
    elif not statuses or any(s != "pass" for s in statuses) or any(a["status"] != "satisfied" for a in active):
        gate = "incomplete"
    else:
        gate = "pass"
    return dict(gate=gate, requirements=requirements, obligations=assessed,
                coverage=dict(raw=totals(active), adjusted=totals(adjusted)),
                runs=[dict(id=r.manifest.id, status=r.finalization.status, pending=r.finalization.pending,
                           replay_of=r.manifest.replay_of) for r in bundle.runs],
                metrics={"hdl_structural": "not_collected", "python_coverage": "not_collected", "native_assertions": "not_collected"})
