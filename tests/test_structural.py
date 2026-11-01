import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_evidence import sample
from verification_evidence.model import EvidenceError
from verification_evidence.structural import export_structural,parse_verilator,validate_structural
from verification_evidence.ucis import export_ucis
from verification_evidence.vcs_coverage import sampler,instrumentation,write_vcs_vdb,database_inventory

ROOT=Path(__file__).parents[1]
FIXTURE=ROOT/'tests/fixtures/structural-verilator.dat'


class StructuralTests(unittest.TestCase):
    def test_native_records_export_and_zero_bins(self):
        rows=parse_verilator(FIXTURE)
        self.assertTrue(any(r['count']==0 for r in rows))
        self.assertEqual({r['attributes']['t'] for r in rows},{'line','toggle'})
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'export'
            result=export_structural(FIXTURE,output,source_root=ROOT,run_id='fixture',run_status='fail',tool_version='5.052')
            self.assertEqual(result['run_status'],'fail')
            self.assertEqual(validate_structural(output)['points'],len(rows))
            with self.assertRaises(EvidenceError): export_structural(FIXTURE,output,source_root=ROOT,run_id='fixture',run_status='pass',tool_version='5.052')
            (output/'native.dat').write_text('corrupt')
            with self.assertRaises(EvidenceError): validate_structural(output)

    def test_unknown_or_directionless_metrics_rejected(self):
        data=FIXTURE.read_text()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bad.dat'
            for value in (data.replace('\x02toggle','\x02fsm',1),data.replace('clk:0->1','clk',1),data+'bad record\n'):
                p.write_text(value)
                with self.assertRaises(EvidenceError): parse_verilator(p)

    @unittest.skipUnless(importlib.util.find_spec('ucis'),'optional PyUCIS')
    def test_schema_and_independent_roundtrip(self):
        from ucis.xml import validate_ucis_xml
        from ucis.xml.xml_factory import XmlFactory
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'export'
            export_structural(FIXTURE,p,source_root=ROOT,run_id='fixture',run_status='pass',tool_version='5.052')
            self.assertTrue(validate_ucis_xml(str(p/'coverage.xml')))
            XmlFactory.write(XmlFactory.read(str(p/'coverage.xml')),str(p/'roundtrip.xml'))
            validate_structural(p,p/'roundtrip.xml')


class VcsCoverageTests(unittest.TestCase):
    def test_native_flags_and_sampler_budget(self):
        self.assertEqual(instrumentation('line+tgl','out')[:2],['-cm','line+tgl'])
        with self.assertRaises(EvidenceError): instrumentation('line+bogus','out')
        with self.assertRaises(EvidenceError): sampler(sample(),0)
        source,top,total=sampler(sample())
        self.assertEqual(total,1)
        self.assertIn('repeat (64\'d1)',source)
        self.assertIn('iff (selected == 0)',source)
        self.assertIn('option.at_least = 1',source)
        self.assertIn('module '+top,source)

    def test_missing_vendor_never_claims_binary_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); export_ucis([sample()],p/'export')
            with patch('verification_evidence.vcs_coverage.shutil.which',return_value=None):
                with self.assertRaises(EvidenceError): write_vcs_vdb(p/'export',p/'native')
            result=json.loads((p/'native/native-report.json').read_text())
            self.assertEqual(result['status'],'not_created_or_unverified')
            self.assertFalse((p/'native/functional.vdb').exists())
            self.assertEqual(write_vcs_vdb(p/'export',p/'prepared',prepare_only=True)['status'],'prepared')
            with self.assertRaises(EvidenceError): database_inventory(p/'missing')
