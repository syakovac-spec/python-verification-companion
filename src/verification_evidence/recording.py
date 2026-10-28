"""Protocol-independent writer for observations and independently evaluated checks.

This module owns evidence bookkeeping only. A user's monitor owns sampling,
and their scoreboard owns predictions, matching, reset epochs and pending work.
"""
from copy import deepcopy
from .model import Bundle, Run, Event, Check, Coverage, Finalization, EvidenceError
from .core import validate


class EvidenceRecorder:
    def __init__(self, catalog, manifest):
        self.bundle = Bundle(deepcopy(catalog), [Run(deepcopy(manifest), [], [], [], [],
            Finalization("error", "not finalized", 0, {k: 0 for k in ("intents", "events", "checks", "coverage")}))])
        self.run = self.bundle.runs[0]
        self._closed = False
        self._obligations = {o.id: o for o in self.bundle.catalog.obligations}
        validate(self.bundle)

    def _writable(self):
        if self._closed:
            raise EvidenceError("recorder already finalized")

    def observe(self, *, interface, epoch, correlation, tick, kind, payload):
        """Record actual monitored activity; this alone never earns checked credit."""
        self._writable()
        index = len(self.run.events)
        event_id = f"event-{index}"
        self.run.events.append(Event(event_id, self.run.manifest.id, interface, epoch,
            correlation, index, tick, kind, deepcopy(payload)))
        return event_id

    def evaluate(self, *, obligation_id, checker_id, event_ids, outcome, reason, tick, triggered=True):
        """Link one checker result and its coverage to an exact observed event group.

        For multi-checker obligations call this once per required checker with
        the same event IDs. Core aggregation requires every checker to pass.
        """
        self._writable()
        if obligation_id not in self._obligations:
            raise EvidenceError(f"unknown obligation: {obligation_id}")
        obligation = self._obligations[obligation_id]
        if checker_id not in obligation.checker_ids:
            raise EvidenceError(f"checker {checker_id} is not assigned to {obligation_id}")
        check_id = f"check-{len(self.run.checks)}"
        self.run.checks.append(Check(check_id, checker_id, obligation_id, list(event_ids),
            outcome, reason, tick, triggered))
        self.run.coverage.append(Coverage(f"coverage-{len(self.run.coverage)}",
            obligation.bin_id, list(event_ids), [check_id]))
        return check_id

    def finish(self, *, pending_by_obligation=None, error=None):
        """Finalize conservatively; callers cannot override failures with 'pass'."""
        self._writable()
        pending = dict(pending_by_obligation or {})
        outcomes = {check.outcome for check in self.run.checks}
        status = ("error" if error is not None else "fail" if "fail" in outcomes else
                  "aborted" if outcomes & {"inconclusive", "aborted"} or sum(pending.values()) else "pass")
        self.run.finalization = Finalization(status, str(error) if error is not None else "checker finalization",
            sum(pending.values()), {key: len(getattr(self.run, key)) for key in ("intents", "events", "checks", "coverage")}, pending)
        validate(self.bundle)
        self._closed = True
        return self.bundle
