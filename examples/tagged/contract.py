"""Two-request tagged transform contract; not general AXI VIP."""
from verification_evidence.model import Catalog, Requirement, Checker, Bin, Obligation
from verification_evidence.scoreboard import Comparison


def plan(digest):
    names = {'MATCH': 2, 'DRAIN': 1}
    return Catalog('1.0', 'tagged-transform-v1',
        [Requirement(n, n, 'two-request-transform-v1') for n in names],
        [Checker('tagged-model', '1', digest, 'Observed tagged XOR transformation',
                 ['transfer'], 'X/Z gives inconclusive; no integer coercion')],
        [Bin(n, '1', digest, n, goal) for n, goal in names.items()],
        [Obligation(n, n, n, ['tagged-model'], goal, ['tagged']) for n, goal in names.items()], [])


def predict(observed):
    bits = observed['data']['bits']
    if any(bit not in '01' for bit in bits):
        return None
    return format(int(bits, 2) ^ 0x5a, '08b')


def compare(expected, observed):
    bits = observed['data']['bits']
    if expected is None or any(bit not in '01' for bit in bits):
        return Comparison('inconclusive', 'unknown active data')
    return Comparison('pass' if bits == expected else 'fail', 'observed input XOR 0x5a')
