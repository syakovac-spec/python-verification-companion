import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from verification_evidence.scaffold import create_agent, validate_spec


class ScaffoldTests(unittest.TestCase):
    def spec(self):
        return json.loads((Path(__file__).parents[1] / 'interfaces/packet16.json').read_text())

    def test_reject_invalid_and_unsupported_contracts(self):
        for key, value in [('width', True), ('width', 0), ('schema_version', 2),
                           ('protocol', 'axi'), ('clock', '../escape'), ('reset_policy', 'retain')]:
            spec = self.spec(); spec[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_spec(spec)
        spec = self.spec(); spec['channels']['tx']['signals']['data'] = spec['clock']
        with self.assertRaises(ValueError):
            validate_spec(spec)

    def test_generation_is_deterministic_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            interface = root / 'spec.json'; interface.write_text(json.dumps(self.spec()))
            a, b = root / 'a', root / 'b'
            create_agent(interface, a); create_agent(interface, b)
            self.assertEqual({str(p.relative_to(a)): p.read_bytes() for p in a.rglob('*') if p.is_file()},
                             {str(p.relative_to(b)): p.read_bytes() for p in b.rglob('*') if p.is_file()})
            with self.assertRaises(ValueError):
                create_agent(interface, a)
            self.assertIn('[15:0] request_payload', (a / 'rtl/stream_top.sv').read_text())
            result = subprocess.run([sys.executable, '-m', 'unittest', 'test_contract', '-v'],
                                    cwd=a, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
