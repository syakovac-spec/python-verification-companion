"""DUT contract hook: replace prediction from observed input, never driver intent."""
from interface_config import SPEC


def predict(observed_bits):
    """The demonstration DUT is an ordered identity buffer, flushed on reset."""
    return observed_bits


def legal_values():
    """Half-open legal stimulus interval; sampled with an isolated seeded RNG."""
    return 0, 1 << SPEC['width']
