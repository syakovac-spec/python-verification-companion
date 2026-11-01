"""VCS-owned native database creation; never synthesize or rename binary formats."""
import json
from pathlib import Path
import shutil
import subprocess

from .model import EvidenceError
from .ucis import load_export, projection, sha
from .regression import Processes


def instrumentation(metrics, directory):
    names=metrics.split('+')
    if not names or len(names)!=len(set(names)) or set(names)-{'line','cond','fsm','tgl','branch'}:
        raise EvidenceError('VCS coverage metrics: distinct line+cond+fsm+tgl+branch names')
    return ['-cm','+'.join(names),'-cm_dir',str(Path(directory).resolve())]


def database_inventory(directory):
    directory=Path(directory)
    if not directory.is_dir(): raise EvidenceError('VCS did not produce the requested VDB directory')
    result={}
    for p in sorted(directory.rglob('*')):
        if p.is_symlink(): raise EvidenceError('VDB symlinks are not supported by artifact inventory')
        if p.is_file(): result[str(p.relative_to(directory))]=sha(p.read_bytes())
    if not result: raise EvidenceError('VCS produced an empty VDB directory')
    return result


def sampler(bundle, max_samples=1_000_000):
    """Replay checked counts into native covergroups, not the original DUT stimulus."""
    scope,points,_=projection(bundle)
    total=sum(p['count'] for p in points.values())
    if total>max_samples or any(p['goal']>2147483647 for p in points.values()):
        raise EvidenceError('native sampler count budget or SV at_least integer range exceeded')
    lines=[f'module {scope};','  integer selected;','  bit value;',
           '  covergroup checked_functional_type;', '    option.per_instance = 1;']
    for i,(name,point) in enumerate(sorted(points.items())):
        lines += [f'    {name}: coverpoint value iff (selected == {i}) {{',
                  f"      option.at_least = {point['goal']};",'      bins checked = {1};','    }']
    lines += ['  endgroup','  checked_functional_type checked_functional;',
              '  initial begin','    checked_functional = new;',
              '    checked_functional.set_inst_name("checked_functional");','    value = 1;']
    for i,(_,point) in enumerate(sorted(points.items())):
        lines += [f'    selected = {i};',f"    repeat (64'd{point['count']}) checked_functional.sample();"]
    lines += ['    #1; $finish;','  end','endmodule','']
    return '\n'.join(lines),scope,total


def write_vcs_vdb(export, output, *, prepare_only=False, timeout=600, max_samples=1_000_000):
    bundle=load_export(export)
    source,top,total=sampler(bundle,max_samples)
    output=Path(output).resolve(); output.mkdir(parents=True,exist_ok=False)
    shutil.copytree(export,output/'evidence')
    (output/'coverage_sampler.sv').write_text(source,encoding='utf-8')
    database=output/'functional.vdb'
    # No -cm structural metrics: this sampler is not the user's DUT.
    commands=[['vcs','-full64','-sverilog','-top',top,'-cm_dir',str(database),
               str(output/'coverage_sampler.sv'),'-o',str(output/'simv')],
              [str(output/'simv'),'-cm_dir',str(database),'-cm_name','evidence_projection']]
    report=dict(status='prepared',vendor='Synopsys VCS',samples=total,commands=commands,
                original_gate=projection(bundle)[2]['gate'],
                qualification='native writer not locally qualified; verify bins using vendor UCIS re-export/API',
                semantics='aggregate count conversion; original test outcomes remain in evidence sidecars')
    try:
        if not prepare_only:
            vcs=shutil.which('vcs')
            if not vcs:
                raise EvidenceError('VCS unavailable: source/commands prepared, no native VDB created')
            version=subprocess.run([vcs,'-ID'],capture_output=True,text=True,timeout=30)
            report['version_output']=version.stdout+version.stderr
            processes=Processes()
            for i,command in enumerate(commands):
                # A child Python process changes cwd without mutating the caller's cwd.
                import sys
                wrapped=[sys.executable,'-c','import os,sys; os.chdir(sys.argv[1]); os.execvp(sys.argv[2],sys.argv[2:])',str(output),*command]
                execution=processes.run(wrapped,output/f'stage-{i}.log',timeout)
                if execution['execution_status']!='finished' or execution['returncode']!=0:
                    raise EvidenceError(f'VCS stage {i} failed: {execution}; see retained log')
            report['files']=database_inventory(database)
            report['status']='native_created_unverified'
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        report['status']='not_created_or_unverified'; report['error']=str(exc)
        raise EvidenceError(str(exc)) from exc
    finally:
        (output/'native-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report
