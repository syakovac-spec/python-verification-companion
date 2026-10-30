"""Reviewed requirements and checked functional goals; customize for your DUT."""
from interface_config import SPEC
PROFILE = SPEC["name"] + "-" + str(SPEC["width"]) + "bit"
from verification_evidence.model import Catalog, Requirement, Checker, Bin, Obligation


def plan(digest):
    names = {"ORDER": ("Output preserves accepted input data and order", 8),
             "HOLD.tx": ("Source holds valid/data under backpressure", 2),
             "HOLD.rx": ("DUT holds valid/data under backpressure", 2),
             "DRAIN": ("No outstanding transfers at shutdown", 1)}
    return Catalog("1.0", SPEC["name"] + "-v1",
        [Requirement(n, desc, "elastic-buffer-contract-v1") for n, (desc, _) in names.items()],
        [Checker("stream-model", "1", digest, "Observed input/output queue and stall stability", ["stream"], "relevant X/Z => inconclusive")],
        [Bin(n, "1", digest, desc, goal) for n, (desc, goal) in names.items()],
        [Obligation(n, n, n, ["stream-model"], goal, [PROFILE]) for n, (_, goal) in names.items()], [])
