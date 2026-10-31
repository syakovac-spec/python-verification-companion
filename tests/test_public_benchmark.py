import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location('public_benchmark', Path(__file__).parents[1] / 'scripts/public_benchmark.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PublicSubmissionTests(unittest.TestCase):
    def report(self):
        return dict(qualified=True, environment=dict(tools=dict(simulator='vcs', python='3.11.18',
            cocotb='2.1.0', vcs='VCS V-2023.12-SP2 /private/CANARY'),
            sources={'/private/CANARY': 'a'*64}, dependencies={'CANARY': 'secret'},
            build_flags=['-I/private/CANARY'], test_flags=[], cpu_count=8),
            rows=[dict(qualified=True, variant='baseline', gate='pass', rtl_load_checked=True,
                semantic_sha256='a'*64, stimulus_sha256='b'*64, lanes=1, transactions=24, repeat=0,
                corrupt=0, returncode=0, loop_seconds=.1, error='CANARY', directory='/private/CANARY',
                timing=dict(total_seconds=1., python='/private/CANARY'))])

    def test_export_uses_allowlist_and_preserves_failed_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); positive = root / 'positive'; positive.mkdir()
            (positive / 'report.json').write_text(json.dumps(self.report()))
            archive = root / 'submission.zip'
            result = module.package(positive, root/'missing', archive, codes=(0, 1))
            self.assertEqual(result['cases']['corruption']['status'], 'unavailable')
            with zipfile.ZipFile(archive) as z:
                self.assertEqual(set(z.namelist()), {'submission.json', 'README.txt'})
                contents = z.read('submission.json').decode()
                self.assertNotIn('CANARY', contents)
                self.assertNotIn('/private', contents)
                self.assertIn('V-2023.12-SP2', contents)
                module.validate(json.loads(contents))
            with self.assertRaises(FileExistsError):
                module.package(positive, root/'missing', archive)

    def test_reject_unexpected_strings_and_nonfinite_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'report.json').write_text(json.dumps(self.report()))
            data=module.package(root, root, root/'submission.zip')
            data['cases']['positive']['environment']['private_path']='secret'
            with self.assertRaises(ValueError): module.validate(data)
            del data['cases']['positive']['environment']['private_path']
            data['cases']['positive']['rows'][0]['loop_seconds']=float('nan')
            with self.assertRaises(ValueError): module.validate(data)

    def test_empty_qualified_report_does_not_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); report=self.report(); report['rows']=[]
            (root/'report.json').write_text(json.dumps(report))
            self.assertEqual(module.public_report(root)['status'], 'not_qualified')

    def test_scheduling_metadata_and_legacy_archives(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); report=self.report()
            report['environment'].update(workers=2, cache_enabled=True)
            (root/'report.json').write_text(json.dumps(report))
            data=module.package(root, root, root/'submission.zip')
            env=data['cases']['positive']['environment']
            self.assertEqual(env['workers'], 2)
            self.assertTrue(env['cache_enabled'])
            env['workers']=0
            with self.assertRaises(ValueError): module.validate(data)
            del env['workers']; del env['cache_enabled']
            module.validate(data)

    def test_validator_rejects_extra_archive_members(self):
        with tempfile.TemporaryDirectory() as directory:
            archive=Path(directory)/'unsafe.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('submission.json', '{}')
                z.writestr('README.txt', '')
                z.writestr('private.log', 'CANARY')
            with patch('sys.argv', ['public_benchmark.py', '--validate', str(archive)]):
                with self.assertRaises(ValueError): module.main()
