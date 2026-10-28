"""Explicit functional cross definitions; no solver or simulator dependency."""
REGIONS = {"id": 0, "scratch": 4, "status": 8, "event": 12, "unmapped": 16, "misaligned": 6}
GOAL = 3


def region(address):
    return {0: "id", 4: "scratch", 8: "status", 12: "event"}.get(address, "misaligned" if address % 4 else "unmapped")


def definitions():
    profiles = [f"rtl-wait-{w}" for w in (0, 1, 3)]
    rows = [(f"FC-001.{d}.{r}", profiles) for d in ("read", "write") for r in REGIONS]
    rows += [(f"FC-002.wait_{w}.{d}", [f"rtl-wait-{w}"]) for w in (0, 1, 3) for d in ("read", "write")]
    rows += [(f"FC-003.{pair}", profiles) for pair in ("rr", "rw", "wr", "ww")]
    rows += [(f"FC-004.{phase}.{d}", profiles[1:] if phase == "wait" else profiles)
             for phase in ("setup", "wait", "completion") for d in ("read", "write")]
    rows += [(f"FC-005.h{high}.l{low}", profiles) for high in (0, 1) for low in range(4)]
    return rows


def active_names(wait):
    return [name for name, profiles in definitions() if f"rtl-wait-{wait}" in profiles]
