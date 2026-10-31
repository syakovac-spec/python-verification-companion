from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from test_evidence import sample, recount, reseal
from verification_evidence.model import EvidenceError, Exclusion, dump
from verification_evidence.core import merge, summarize
from verification_evidence.cli import main
from verification_evidence.ucis import export_ucis, load_export, projection, read_projection, check_projection


class UcisTests(unittest.TestCase):
    def test_failed_run_survives_covered_bins(self):
        good,bad=sample(),self.second()
        bad.runs[0].checks[0].outcome='fail'
        bad.runs[0].finalization.status='fail'
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'export'; export_ucis([good,bad],p)
            restored=load_export(p)
            scope,_,summary=projection(restored)
            self.assertEqual(summary['gate'],'failed')
            self.assertEqual(list(read_projection(p/'coverage.xml',scope).values()),[dict(count=1,goal=1)])
            self.assertEqual(restored.runs[1].checks[0].outcome,'fail')
            statuses=[n.get('testStatus') for n in ET.parse(p/'coverage.xml').findall('{UCIS}historyNodes')]
            self.assertEqual(statuses,['true','false'])

    def second(self):
        b=sample(); b.runs[0].manifest.id='RUN-2'; b.runs[0].events[0].run_id='RUN-2'
        return b

    def test_merge_dedup_goals_and_integrity(self):
        a,b=sample(),self.second()
        for item in (a,b):
            item.catalog.obligations[0].goal=3; reseal(item)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            export_ucis([a],p/'a'); export_ucis([b],p/'b')
            self.assertEqual(main(['merge-ucis',str(p/'a'),str(p/'b'),str(p/'a'),'--output',str(p/'merged')]),0)
            merged=load_export(p/'merged')
            self.assertEqual(len(merged.runs),2)
            scope,points,_=projection(merged)
            self.assertEqual(list(read_projection(p/'merged/coverage.xml',scope).values()),[dict(count=2,goal=3)])
            self.assertEqual(summarize(merged)['gate'],'incomplete')
            with self.assertRaises(EvidenceError): export_ucis([a],p/'a')
            (p/'a/coverage.xml').write_text('<UCIS/>')
            with self.assertRaises(EvidenceError): load_export(p/'a')

    def test_nonpassing_unchecked_and_excluded(self):
        for status in ('fail','error','aborted','timeout','unchecked'):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as tmp:
                b=sample()
                if status=='unchecked':
                    b.runs[0].checks=[]; b.runs[0].coverage[0].check_ids=[]; recount(b.runs[0])
                else:
                    b.runs[0].finalization.status=status
                b.catalog.exclusions=[Exclusion('EX','OB-1',['rtl'],'reason','author','reviewer','1','issue')]
                reseal(b)
                p=Path(tmp)/'export'; export_ucis([b],p)
                scope,_,summary=projection(load_export(p))
                self.assertEqual(list(read_projection(p/'coverage.xml',scope).values())[0]['count'],0)
                self.assertNotEqual(summary['gate'],'pass')
                self.assertTrue(summary['obligations'][0]['exclusions'])

    def test_roundtrip_detects_changed_counts_and_goals(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=sample(); p=Path(tmp)/'export'; export_ucis([b],p)
            for tag,attribute,value in [('contents','coverageCount','8'),('options','at_least','9'),('coverpointBin','type','ignore')]:
                tree=ET.parse(p/'coverage.xml')
                matches=tree.findall('.//{UCIS}coverpoint/{UCIS}'+tag) if tag=='options' else tree.findall('.//{UCIS}'+tag)
                matches[0].set(attribute,value); tree.write(p/'roundtrip.xml')
                with self.assertRaises(EvidenceError): check_projection(b,p/'roundtrip.xml')
            (p/'roundtrip.xml').write_text('<!DOCTYPE UCIS><UCIS/>')
            with self.assertRaises(EvidenceError): check_projection(b,p/'roundtrip.xml')
            (p/'roundtrip.xml').write_bytes('<!DOCTYPE UCIS><UCIS/>'.encode('utf-16'))
            with self.assertRaises(EvidenceError): check_projection(b,p/'roundtrip.xml')

    def test_incompatible_and_empty_rejected(self):
        a,b=sample(),self.second(); b.runs[0].manifest.compatibility.dut_digest='different'
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(EvidenceError): export_ucis([a,b],Path(tmp)/'bad')
            a.runs=[]
            with self.assertRaises(EvidenceError): export_ucis([a],Path(tmp)/'empty')

    def test_cli_export_and_validate(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); dump(sample(),p/'bundle.json')
            self.assertEqual(main(['export-ucis',str(p/'bundle.json'),'--output',str(p/'export')]),0)
            self.assertEqual(main(['validate-ucis',str(p/'export'),'--roundtrip',str(p/'export/coverage.xml')]),0)

    @unittest.skipUnless(importlib.util.find_spec('ucis'), 'optional PyUCIS qualification dependency')
    def test_independent_pyucis_schema_reader_writer(self):
        from ucis.xml import validate_ucis_xml
        from ucis.xml.xml_factory import XmlFactory
        from ucis.mem.mem_factory import MemFactory
        from ucis.merge.db_merger import DbMerger
        with tempfile.TemporaryDirectory() as tmp:
            b=sample(); b.catalog.obligations[0].goal=3; reseal(b)
            p=Path(tmp)/'export'; export_ucis([b],p)
            self.assertTrue(validate_ucis_xml(str(p/'coverage.xml')))
            db=XmlFactory.read(str(p/'coverage.xml'))
            XmlFactory.write(db,str(p/'roundtrip.xml'))
            self.assertTrue(validate_ucis_xml(str(p/'roundtrip.xml')))
            check_projection(b,p/'roundtrip.xml')
            second=self.second(); second.catalog.obligations[0].goal=3; reseal(second)
            export_ucis([second],p/'second')
            target=MemFactory.create()
            DbMerger().merge(target,[db,XmlFactory.read(str(p/'second/coverage.xml'))])
            XmlFactory.write(target,str(p/'external-merged.xml'))
            actual=read_projection(p/'external-merged.xml',projection(b)[0])
            self.assertEqual(next(iter(actual.values()))['count'],2)
            # This installed merger loses at_least > 1. Detect, never repair silently.
            if next(iter(actual.values()))['goal'] != 3:
                with self.assertRaises(EvidenceError): check_projection(merge([b,second]),p/'external-merged.xml')
            else:
                check_projection(merge([b,second]),p/'external-merged.xml')
            export_ucis([b,second],p/'safe-merged')
            XmlFactory.write(XmlFactory.read(str(p/'safe-merged/coverage.xml')),str(p/'safe-roundtrip.xml'))
            check_projection(merge([b,second]),p/'safe-roundtrip.xml')
