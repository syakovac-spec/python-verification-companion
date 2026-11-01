"""Execute real RTL with native coverage, export UCIS and optionally round-trip PyUCIS."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from importlib import metadata

from verification_evidence.regression import Processes
from verification_evidence.structural import export_structural,validate_structural
from verification_evidence.ucis import sha

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--verilator',default='verilator')
    parser.add_argument('--pyucis',action='store_true')
    args=parser.parse_args(); out=args.out.resolve(); out.mkdir(parents=True,exist_ok=False)
    report=dict(qualified=False,commercial_tools='not_executed',commands=[],runs=[])
    processes=Processes()
    try:
        report['tool_version']=subprocess.check_output([args.verilator,'--version'],text=True,timeout=30).strip()
        sources=[ROOT/'examples/structural/probe.sv',ROOT/'examples/structural/main.cpp']
        report['source_sha256']={p.name:sha(p.read_bytes()) for p in sources}
        command=[args.verilator,'--cc','--exe','--build','--coverage-line','--coverage-toggle',
                 '--top-module','probe','--Mdir',str(out/'build'),*[str(p) for p in sources]]
        report['commands'].append(command)
        result=processes.run(command,out/'build.log',900)
        if result['returncode']!=0: raise RuntimeError(f'build failed: {result}')
        for name,selections in [('partial',2),('full',4)]:
            native=out/(name+'.dat')
            command=[str(out/'build/Vprobe'),str(selections),str(native)]
            report['commands'].append(command)
            result=processes.run(command,out/(name+'.log'),30)
            if result['returncode']!=0: raise RuntimeError(f'RTL checker failed: {result}')
            exported=out/name
            row=export_structural(native,exported,source_root=ROOT,run_id=name,run_status='pass',tool_version=report['tool_version'])
            row['case']=name
            if args.pyucis:
                from ucis.xml import validate_ucis_xml
                from ucis.xml.xml_factory import XmlFactory
                report['pyucis']=metadata.version('pyucis')
                validate_ucis_xml(str(exported/'coverage.xml'))
                XmlFactory.write(XmlFactory.read(str(exported/'coverage.xml')),str(exported/'roundtrip.xml'))
                validate_ucis_xml(str(exported/'roundtrip.xml'))
                row['roundtrip']=validate_structural(exported,exported/'roundtrip.xml')
            report['runs'].append(row)
        partial,full=report['runs']
        if partial['metrics']['line']['hit']>=full['metrics']['line']['hit']:
            raise RuntimeError('additional RTL stimulus did not improve native line coverage')
        if full['metrics']['toggle']['zero']==0:
            raise RuntimeError('expected constant-bit toggle holes were lost')
        report['qualified']=True
    except Exception as exc:
        report['error']=str(exc)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    return 0 if report['qualified'] else 1


if __name__=='__main__': sys.exit(main())
