"""Observed-transaction matching with explicit prediction and comparison policies.

No simulator or UVM dependency. Feed accepted monitor observations, never driver
intent. One instance represents one logical interface and owns its reset epochs.
"""
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable

from .model import EvidenceError


@dataclass(frozen=True)
class Comparison:
    outcome: str
    reason: str


@dataclass(frozen=True)
class Prediction:
    token: int
    tag: Any
    epoch: int
    event_id: str
    correlation: str
    expected: Any
    deadline: int | None


class Scoreboard:
    """FIFO or unique-tag matching, optionally allowing tagged reordering.

    predictor(payload) runs once per accepted input and can own architectural
    state. comparator(expected, actual) must return Comparison, including an
    explicit policy for unknown values. reset_predictor() resets model state.
    Deadlines are inclusive absolute ticks; advance() reports overdue requests
    without deleting them. close() checks drain and returns pending counts for
    EvidenceRecorder.finish(), which the environment owns.
    """

    def __init__(self, recorder, *, interface, obligation, checker, predictor: Callable,
                 comparator: Callable, drain_obligation, kind="transfer",
                 mode="ordered", allow_reordering=False, reset_predictor=None):
        if mode not in ("ordered", "tagged") or (allow_reordering and mode != "tagged"):
            raise EvidenceError("reordering requires tagged matching")
        if type(allow_reordering) is not bool or not callable(predictor) or not callable(comparator):
            raise EvidenceError("explicit reordering boolean and callable prediction/comparison policies required")
        if reset_predictor is not None and not callable(reset_predictor):
            raise EvidenceError("reset_predictor must be callable")
        if drain_obligation == obligation:
            raise EvidenceError("drain and matching require distinct obligations")
        for name in (obligation, drain_obligation):
            found = next((o for o in recorder.bundle.catalog.obligations if o.id == name), None)
            if found is None or checker not in found.checker_ids:
                raise EvidenceError("scoreboard checker/obligation binding is invalid")
        definition = next(c for c in recorder.bundle.catalog.checkers if c.id == checker)
        if kind not in definition.event_types:
            raise EvidenceError("scoreboard event kind is not supported by checker")
        self.recorder, self.interface = recorder, interface
        self.obligation, self.checker = obligation, checker
        self.drain_obligation = drain_obligation or obligation
        self.predictor, self.comparator = predictor, comparator
        self.reset_predictor = reset_predictor
        self.kind, self.mode, self.allow_reordering = kind, mode, allow_reordering
        self.epoch = 0
        self._pending = OrderedDict()
        self._tags = {}
        self._expired = set()
        self._serial = 0
        self._tick = -1
        self._closed = False

    @property
    def pending(self):
        """Detached snapshot; callers cannot mutate matching state."""
        return tuple(deepcopy(list(self._pending.values())))

    def _time(self, tick):
        if self._closed:
            raise EvidenceError("scoreboard already closed")
        if type(tick) is not int or tick < 0 or tick < self._tick:
            raise EvidenceError("scoreboard ticks must be nonnegative and monotonic")
        self._tick = tick

    def _event(self, tick, correlation, payload):
        return self.recorder.observe(interface=self.interface, epoch=self.epoch,
            correlation=correlation, tick=tick, kind=self.kind, payload=payload)

    def _check(self, ids, tick, outcome, reason, obligation=None):
        self.recorder.evaluate(obligation_id=obligation or self.obligation,
            checker_id=self.checker, event_ids=ids, tick=tick,
            outcome=outcome, reason=reason)

    def _issue(self, payload, tick, reason):
        correlation = f"scoreboard-issue-{self._serial}"
        self._serial += 1
        event = self._event(tick, correlation, payload)
        self._check([event], tick, "fail", reason)

    def _tag(self, tag):
        if self.mode == "tagged" and (type(tag) not in (int, str) or tag == ""):
            raise EvidenceError("tagged matching requires an integer or nonempty string ID")
        if self.mode == "ordered" and tag is not None:
            raise EvidenceError("ordered matching does not accept tags")

    def request(self, payload, *, tick, tag=None, deadline=None):
        self._tag(tag)
        if deadline is not None and (type(deadline) is not int or deadline < tick):
            raise EvidenceError("deadline must be an absolute tick at or after acceptance")
        self._time(tick)
        if self.mode == "tagged" and tag in self._tags:
            self._issue(payload, tick, "duplicate outstanding request ID")
            return None
        token = self._serial
        self._serial += 1
        correlation = f"scoreboard-request-{token}"
        event = self._event(tick, correlation, payload)
        try:
            expected = deepcopy(self.predictor(deepcopy(payload)))
        except Exception:
            self._check([event], tick, "inconclusive", "prediction callback failed")
            raise
        item = Prediction(token, tag, self.epoch, event, correlation, expected, deadline)
        self._pending[token] = item
        if self.mode == "tagged":
            self._tags[tag] = token
        return token

    def response(self, payload, *, tick, tag=None, epoch=None):
        self._tag(tag)
        self._time(tick)
        if epoch is not None and (type(epoch) is not int or epoch != self.epoch):
            self._issue(payload, tick, "response from another reset epoch")
            return
        token = (self._tags.get(tag) if self.mode == "tagged"
                 else next(iter(self._pending), None))
        if token is None:
            self._issue(payload, tick, "unexpected or duplicate response without outstanding input")
            return
        item = self._pending[token]
        event = self._event(tick, item.correlation, payload)
        ids = [item.event_id, event]
        try:
            comparison = self.comparator(deepcopy(item.expected), deepcopy(payload))
            if (not isinstance(comparison, Comparison) or
                    comparison.outcome not in ("pass", "fail", "inconclusive") or
                    not isinstance(comparison.reason, str) or not comparison.reason):
                raise EvidenceError("comparator must return Comparison with an explicit outcome and reason")
        except Exception:
            self._check(ids, tick, "inconclusive", "comparison callback failed")
            raise
        if not self.allow_reordering and token != next(iter(self._pending)):
            comparison = Comparison("fail", "response reordered when forbidden")
        if item.deadline is not None and tick > item.deadline:
            comparison = Comparison("fail", "response after deadline")
        self._check(ids, tick, comparison.outcome, comparison.reason)
        del self._pending[token]
        self._expired.discard(token)
        if self.mode == "tagged":
            del self._tags[tag]

    def advance(self, tick):
        """Report missing responses after their deadline; retain pending work."""
        self._time(tick)
        for token, item in self._pending.items():
            if item.deadline is not None and tick > item.deadline and token not in self._expired:
                self._check([item.event_id], tick, "fail", "response deadline expired")
                self._expired.add(token)

    def reset(self, tick, *, cancel=True):
        """Start an epoch; explicit cancellation is allowed only by DUT contract.

        cancel=False reports missing responses before retiring the old epoch.
        No cancelled request receives functional matching credit.
        """
        if type(cancel) is not bool:
            raise EvidenceError("reset cancellation must be an explicit boolean")
        self._time(tick)
        if not cancel:
            for item in self._pending.values():
                self._check([item.event_id], tick, "fail", "reset interrupted required response")
        self._event(tick, f"scoreboard-reset-{self.epoch}",
                    {"action": "reset", "cancelled": len(self._pending), "cancellation_allowed": cancel})
        if self.reset_predictor is not None:
            try:
                self.reset_predictor()
            except Exception:
                self._issue({"action": "reset"}, tick, "predictor reset failed")
                raise
        self._pending.clear()
        self._tags.clear()
        self._expired.clear()
        self.epoch += 1

    def close(self, tick):
        self.advance(tick)
        for item in self._pending.values():
            self._check([item.event_id], tick, "fail", "missing response at final drain",
                        self.drain_obligation)
        event = self._event(tick, "scoreboard-drain", {"pending": len(self._pending)})
        self._check([event], tick, "fail" if self._pending else "pass",
                    "outstanding observed requests at final drain", self.drain_obligation)
        self._closed = True
        return {self.drain_obligation: len(self._pending)} if self._pending else {}
