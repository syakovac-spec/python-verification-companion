"""Strict Verilator line/basic-block and directional-toggle UCIS export."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET

from .model import EvidenceError, canonical
from .ucis import sha


def parse_verilator(path):
    lines=Path(path).read_text(encoding='utf-8').splitlines()
    if not lines or lines[0] != '# SystemC::Coverage-3':
        raise EvidenceError('expected Verilator SystemC::Coverage-3 file')
    rows=[]; seen=set()
    for number,line in enumerate(lines[1:],2):
        if not line.strip(): continue
        match=re.fullmatch(r"C '([^']*)' ([0-9]+)",line)
        if not match: raise EvidenceError(f'unsupported coverage record at line {number}')
        attrs={}
        if not match[1].startswith('\x01'): raise EvidenceError('unsupported Verilator key encoding')
        for field in match[1].split('\x01')[1:]:
            if not field: continue
            parts=field.split('\x02')
            if len(parts)!=2 or not parts[0] or parts[0] in attrs:
                raise EvidenceError('malformed or duplicate Verilator attribute')
            attrs[parts[0]]=parts[1]
        if not all(attrs.get(k) for k in ('f','l','t','h','o')):
            raise EvidenceError('coverage record missing source/type/hierarchy/comment')
        if not attrs['l'].isdigit() or int(attrs['l'])<1:
            raise EvidenceError('invalid source line')
        if attrs['t'] not in ('line','toggle'):
            raise EvidenceError(f"unsupported native metric {attrs['t']!r}; no records silently discarded")
        if attrs['t']=='toggle' and not re.fullmatch(r'.+:[01]->[01]',attrs['o']):
            raise EvidenceError('toggle record lacks explicit binary transition direction')
        if attrs['t']=='toggle' and attrs['o'][-4]==attrs['o'][-1]:
            raise EvidenceError('toggle transition must change value')
        key=sha(canonical(attrs).encode())
        if key in seen: raise EvidenceError('duplicate coverage point; merge native runs explicitly first')
        seen.add(key); rows.append(dict(id=key,attributes=attrs,count=int(match[2])))
    if not rows: raise EvidenceError('empty native coverage file')
    return rows


def structural_xml(rows, run_id, run_status, source_hashes):
    def node(parent,tag,**attrs):
        return ET.SubElement(parent,'{UCIS}'+tag,{k:str(v) for k,v in attrs.items()})
    root=ET.Element('{UCIS}UCIS',ucisVersion='1.0',writtenBy='verification-evidence',
                    writtenTime=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S'))
    files={name:i+1 for i,name in enumerate(sorted(source_hashes))}
    for name,index in files.items(): node(root,'sourceFiles',fileName=name,id=index)
    node(root,'historyNodes',historyNodeId=0,logicalName=run_id,kind='test',
         testStatus='true' if run_status=='pass' else 'false',date=root.get('writtenTime'),
         toolCategory='simulation',ucisVersion='1.0',vendorId='verification-evidence',
         vendorTool='Verilator import',vendorToolVersion='1',comment='Export time UTC; native structural hits are not checked functional coverage')
    for index,hierarchy in enumerate(sorted({r['attributes']['h'] for r in rows}),1):
        selected=[r for r in rows if r['attributes']['h']==hierarchy]
        identity=sha(canonical([hierarchy,source_hashes]).encode())
        inst=node(root,'instanceCoverages',name='hdl_'+identity,key=identity,instanceId=index,moduleName=hierarchy)
        first=selected[0]['attributes']
        node(inst,'id',file=files[first['f']],line=first['l'],inlineCount=1)
        toggles=[r for r in selected if r['attributes']['t']=='toggle']
        if toggles:
            coverage=node(inst,'toggleCoverage')
            # One object per instrumented bit; each original transition has its own count.
            objects={}
            for row in toggles:
                a=row['attributes']; signal,direction=a['o'].rsplit(':',1)
                key=(a['f'],a['l'],a.get('n',''),signal)
                if key not in objects:
                    name='signal_'+sha(canonical(key).encode())
                    obj=node(coverage,'toggleObject',name=name,key=name,alias=signal)
                    node(obj,'id',file=files[a['f']],line=a['l'],inlineCount=1)
                    objects[key]=node(obj,'toggleBit',name='bit0',key='0')
                toggle=node(objects[key],'toggle',**{'from':direction[0],'to':direction[-1]})
                bin_node=node(toggle,'bin',alias=row['id'])
                node(bin_node,'contents',coverageCount=row['count'])
        blocks=[r for r in selected if r['attributes']['t']=='line']
        if blocks:
            coverage=node(inst,'blockCoverage')
            for row in blocks:
                a=row['attributes']; statement=node(coverage,'statement',alias=row['id'])
                node(statement,'id',file=files[a['f']],line=a['l'],inlineCount=1)
                node(node(statement,'bin'),'contents',coverageCount=row['count'])
    ET.indent(root)
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)


def export_structural(native, output, *, source_root, run_id, run_status, tool_version):
    """Keep unfiltered native counts and explicit status; never infer a passing run."""
    if run_status not in ('pass','fail','incomplete') or not run_id or not tool_version:
        raise EvidenceError('explicit run ID/status and simulator version required')
    rows=parse_verilator(native)
    hashes={}
    for name in {r['attributes']['f'] for r in rows}:
        source=Path(source_root)/name
        hashes[name]=sha(source.read_bytes())
    output=Path(output)
    if output.exists(): raise EvidenceError('structural output already exists')
    output.parent.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix='.structural-',dir=output.parent))
    try:
        shutil.copyfile(native,staging/'native.dat')
        (staging/'coverage.xml').write_bytes(structural_xml(rows,run_id,run_status,hashes))
        projected=structural_projection(staging/'coverage.xml')
        if len(projected)!=len(rows) or sum(projected.values())!=sum(r['count'] for r in rows):
            raise EvidenceError('structural mapping lost native counters')
        metrics={}
        for metric in sorted({r['attributes']['t'] for r in rows}):
            counts=[r['count'] for r in rows if r['attributes']['t']==metric]
            metrics[metric]=dict(points=len(counts),hit=sum(n>0 for n in counts),zero=sum(n==0 for n in counts),hits=sum(counts))
        report=dict(format='verification-structural-1',run_id=run_id,run_status=run_status,
                    simulator='verilator',tool_version=tool_version,source_sha256=hashes,metrics=metrics,points=rows,
                    artifacts={p.name:sha(p.read_bytes()) for p in staging.iterdir()},
                    limitations=['Line counters represent Verilator basic-block instrumentation, not every physical source line.',
                                 'Structural hits do not imply functional checking or closure.',
                                 'Only line and explicitly directional toggle records supported; other records are rejected.',
                                 'Source hashes describe supplied files; caller must ensure these are the compiled revisions.'])
        (staging/'structural.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        staging.rename(output)
    finally:
        if staging.exists(): shutil.rmtree(staging)
    return dict(status='exported',output=str(output),run_status=run_status,metrics=metrics)


def structural_projection(path):
    text=Path(path).read_text(encoding='utf-8-sig')
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper() or '\x00' in text:
        raise EvidenceError('DTD/entities are not supported')
    try:
        root=ET.fromstring(text)
    except ET.ParseError as exc:
        raise EvidenceError(f'invalid structural XML: {exc}') from exc
    for element in root.iter(): element.tag=element.tag.split('}')[-1]
    if root.tag!='UCIS': raise EvidenceError('expected UCIS XML')
    files={n.attrib['id']:n.attrib['fileName'] for n in root.findall('sourceFiles')}
    points={}
    def add(key,contents):
        if key in points: raise EvidenceError('duplicate structural counter')
        count=int(contents.attrib['coverageCount'])
        if count<0: raise EvidenceError('negative coverage count')
        points[key]=count
    for inst in root.findall('instanceCoverages'):
        scope=inst.attrib['name']
        for statement in inst.findall('blockCoverage/statement'):
            loc=statement.find('id')
            add((scope,'line',statement.get('alias'),files[loc.attrib['file']],loc.attrib['line']),statement.find('bin/contents'))
        for obj in inst.findall('toggleCoverage/toggleObject'):
            loc=obj.find('id')
            for bit in obj.findall('toggleBit'):
                for toggle in bit.findall('toggle'):
                    add((scope,'toggle',obj.attrib['name'],bit.attrib['name'],toggle.attrib['from'],toggle.attrib['to'],
                         files[loc.attrib['file']],loc.attrib['line']),toggle.find('bin/contents'))
    if not points: raise EvidenceError('no supported structural counters')
    return points


def validate_structural(directory, roundtrip=None):
    directory=Path(directory)
    report=json.loads((directory/'structural.json').read_text(encoding='utf-8'))
    if report.get('format')!='verification-structural-1' or set(report.get('artifacts',{}))!={'native.dat','coverage.xml'}:
        raise EvidenceError('invalid structural manifest')
    for name,digest in report['artifacts'].items():
        if sha((directory/name).read_bytes())!=digest: raise EvidenceError('structural artifact integrity mismatch')
    if parse_verilator(directory/'native.dat')!=report['points']:
        raise EvidenceError('structural manifest disagrees with native records')
    expected=structural_projection(directory/'coverage.xml')
    if roundtrip and expected!=structural_projection(roundtrip):
        raise EvidenceError('structural round trip changed source locations, identities, directions or counts')
    return dict(status='valid_structural_projection',points=len(expected),run_status=report['run_status'])
