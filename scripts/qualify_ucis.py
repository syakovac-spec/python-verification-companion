"""Validate exported UCIS through optional PyUCIS; retain external merge losses."""
import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import sys

from verification_evidence.core import merge
from verification_evidence.ucis import check_projection, load_export


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exports',nargs='+',type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--external-merge',action='store_true',help='Also test PyUCIS merge; return failure on semantic loss')
    args=parser.parse_args()
    from ucis.xml import validate_ucis_xml
    from ucis.xml.xml_factory import XmlFactory
    from ucis.mem.mem_factory import MemFactory
    from ucis.merge.db_merger import DbMerger
    args.out.mkdir(parents=True,exist_ok=False)
    report=dict(pyucis=metadata.version('pyucis'),python=sys.version.split()[0],
                commercial_tools='not_executed',roundtrips=[],external_merge='not_requested')
    databases=[]; bundles=[]
    for i,path in enumerate(args.exports):
        row={'index':i,'qualified':False}
        try:
            bundle=load_export(path)
            xml=path/'coverage.xml'
            row['input_sha256']=hashlib.sha256(xml.read_bytes()).hexdigest()
            validate_ucis_xml(str(xml))
            db=XmlFactory.read(str(xml))
            target=args.out/f'roundtrip-{i}.xml'
            XmlFactory.write(db,str(target))
            validate_ucis_xml(str(target))
            row.update(check_projection(bundle,target))
            row['qualified']=True
            databases.append(db); bundles.append(bundle)
        except Exception as exc:
            row['error']=str(exc)
        report['roundtrips'].append(row)
    qualified=all(r['qualified'] for r in report['roundtrips'])
    if args.external_merge and qualified:
        row={'qualified':False}
        try:
            # Enforce compatibility and disjoint runs before any external sum.
            bundle=merge(bundles)
            if len(bundle.runs)!=sum(len(b.runs) for b in bundles):
                raise ValueError('external merge inputs overlap; use vevidence merge-ucis for deduplication')
            db=MemFactory.create(); DbMerger().merge(db,databases)
            target=args.out/'external-merged.xml'; XmlFactory.write(db,str(target))
            validate_ucis_xml(str(target))
            row.update(check_projection(bundle,target)); row['qualified']=True
        except Exception as exc:
            row['error']=str(exc)
        report['external_merge']=row
        qualified &= row['qualified']
    report['qualified']=qualified
    (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    return 0 if qualified else 1


if __name__=='__main__':
    sys.exit(main())
