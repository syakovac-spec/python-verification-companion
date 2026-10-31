"""UCIS 1.0 checked-functional-coverage projection; evidence remains authoritative."""
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import xml.etree.ElementTree as ET

from .core import merge, summarize
from .model import EvidenceError, canonical, dump, load

NAMESPACE = 'UCIS'
FORMAT = 'verification-evidence-ucis-1'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def projection(bundle):
    bundle = merge([bundle])
    if not bundle.runs:
        raise EvidenceError('UCIS export requires at least one recorded run')
    identity = [asdict(bundle.runs[0].manifest.compatibility), bundle.runs[0].manifest.time_resolution_fs]
    scope = 've_' + sha(canonical(identity).encode())
    summary = summarize(bundle)
    points = {}
    for ob in summary['obligations']:
        if ob['status'] == 'not_applicable':
            continue
        name = 'ob_' + sha(ob['id'].encode())
        points[name] = dict(obligation=ob['id'], count=ob['eligible_checked_pass'], goal=ob['goal'])
    if not points:
        raise EvidenceError('UCIS export requires an applicable functional obligation')
    return scope, points, summary


def xml_bytes(bundle, timestamp):
    scope, points, summary = projection(bundle)
    def node(parent, tag, **attrs):
        return ET.SubElement(parent, '{UCIS}' + tag, {k: str(v) for k, v in attrs.items()})
    def attr(parent, key, value):
        node(parent, 'userAttr', key=key, type='str').text = value
    root = ET.Element('{UCIS}UCIS', ucisVersion='1.0', writtenBy='verification-evidence', writtenTime=timestamp)
    # A logical catalog source, not a fabricated RTL source location.
    node(root, 'sourceFiles', fileName='evidence.json', id=1)
    for index, run in enumerate(bundle.runs):
        history = node(root, 'historyNodes', historyNodeId=index, logicalName=run.manifest.id,
                       kind='test', testStatus='true' if run.finalization.status == 'pass' else 'false',
                       date=timestamp, toolCategory='simulation', ucisVersion='1.0',
                       vendorId='verification-evidence', vendorTool='vevidence', vendorToolVersion='0.1.0',
                       comment='Export time in UTC; original run status and provenance in evidence.json')
        attr(history, 've.finalization', run.finalization.status)
        attr(history, 've.seeds', json.dumps(run.manifest.seeds, sort_keys=True))
        attr(history, 've.replay_of', run.manifest.replay_of)
    instance = node(root, 'instanceCoverages', name=scope, key=scope, instanceId=1, moduleName='verification_evidence')
    node(instance, 'id', file=1, line=1, inlineCount=1)
    coverage = node(instance, 'covergroupCoverage')
    group = node(coverage, 'cgInstance', name='checked_functional', key='checked_functional')
    node(group, 'options', weight=1, goal=100, at_least=1)
    cg_id = node(group, 'cgId', cgName='checked_functional', moduleName='verification_evidence')
    node(cg_id, 'cginstSourceId', file=1, line=1, inlineCount=1)
    node(cg_id, 'cgSourceId', file=1, line=1, inlineCount=1)
    for name, item in sorted(points.items()):
        cp = node(group, 'coverpoint', name=name, key=name, alias=item['obligation'])
        node(cp, 'options', weight=1, goal=100, at_least=item['goal'], comment=item['obligation'])
        bin_node = node(cp, 'coverpointBin', name='checked', key='checked', type='bins')
        contents = node(bin_node, 'range', **{'from': 1, 'to': 1})
        node(contents, 'contents', coverageCount=item['count'])
        attr(cp, 've.obligation', item['obligation'])
    attr(instance, 've.gate', summary['gate'])
    attr(instance, 've.policy', 'checked scenarios from finalized passing runs; raw exclusions retained')
    ET.indent(root)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def read_projection(path, scope):
    """Read our functional subset from a tool's XML; never import it as evidence."""
    data = Path(path).read_bytes()
    try:
        text = data.decode('utf-8-sig')
    except UnicodeError as exc:
        raise EvidenceError('UCIS projection checker requires UTF-8 XML') from exc
    if len(data) > 64 * 1024 * 1024 or '\x00' in text or '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise EvidenceError('UCIS XML must be <=64 MiB and contain no DTD/entities')
    try:
        root = ET.fromstring(text)
        for element in root.iter():
            element.tag = element.tag.split('}')[-1]
        if root.tag != 'UCIS' or root.get('ucisVersion') != '1.0':
            raise EvidenceError('expected UCIS 1.0 XML')
        instances = [n for n in root.findall('instanceCoverages') if n.get('name') == scope]
        if len(instances) != 1:
            raise EvidenceError('expected exactly one compatible evidence scope')
        groups = instances[0].findall('covergroupCoverage/cgInstance')
        if len(groups) != 1 or groups[0].get('name') != 'checked_functional':
            raise EvidenceError('functional covergroup identity changed')
        result = {}
        for cp in groups[0].findall('coverpoint'):
            name = cp.attrib['name']
            options = cp.find('options')
            bins = cp.findall('coverpointBin')
            if name in result or len(bins) != 1 or bins[0].get('name') != 'checked' or bins[0].get('type') != 'bins':
                raise EvidenceError('duplicate coverpoint or changed functional bin identity/type')
            if groups[0].get('excluded', 'false') not in ('false', '0'):
                raise EvidenceError('functional group was excluded')
            for opts in (groups[0].find('options'), options):
                if opts is None or int(opts.get('weight', '1')) != 1 or int(opts.get('goal', '100')) != 100:
                    raise EvidenceError('functional weight or percentage goal changed')
            counts = bins[0].findall('range/contents')
            if len(counts) != 1 or bins[0].find('sequence') is not None:
                raise EvidenceError('unsupported functional bin shape')
            count, goal = int(counts[0].attrib['coverageCount']), int(options.get('at_least', '1'))
            if count < 0 or goal < 1:
                raise EvidenceError('invalid count or hit goal')
            result[name] = dict(count=count, goal=goal)
        if groups[0].find('cross') is not None:
            raise EvidenceError('unexpected cross coverage in evidence projection')
        return result
    except (ET.ParseError, KeyError, ValueError, TypeError) as exc:
        raise EvidenceError(f'invalid UCIS projection: {exc}') from exc


def check_projection(bundle, path):
    scope, points, _ = projection(bundle)
    expected = {k: dict(count=v['count'], goal=v['goal']) for k, v in points.items()}
    if read_projection(path, scope) != expected:
        raise EvidenceError('UCIS round-trip changed functional bin counts, identities or goals')
    return dict(status='compatible_projection', coverpoints=len(points),
                qualification='functional counts/goals only; evidence sidecar remains authoritative')


def export_ucis(bundles, output):
    bundle = merge(bundles)
    scope, points, summary = projection(bundle)
    output = Path(output)
    if output.exists():
        raise EvidenceError('UCIS output already exists; choose a new directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.ucis-', dir=output.parent))
    try:
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
        dump(bundle, staging / 'evidence.json')
        (staging / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
        (staging / 'coverage.xml').write_bytes(xml_bytes(bundle, timestamp))
        check_projection(bundle, staging / 'coverage.xml')
        manifest = dict(format=FORMAT, scope=scope, mapping=points,
                        files={p.name: sha(p.read_bytes()) for p in staging.iterdir()},
                        limitations=['Functional obligation counts only; no native structural/assertion coverage.',
                                     'Exclusions are retained as evidence, not silently applied as UCIS waivers.',
                                     'XML alone cannot reconstruct checker/event evidence or closure status.',
                                     'Commercial importer qualification requires a named tool/version.'])
        (staging / 'export.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
        if output.exists():
            raise EvidenceError('UCIS output appeared during export')
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return dict(status='exported', output=str(output), runs=len(bundle.runs), gate=summary['gate'], coverpoints=len(points))


def load_export(directory):
    directory = Path(directory)
    manifest = json.loads((directory / 'export.json').read_text(encoding='utf-8'))
    names = {'coverage.xml', 'evidence.json', 'summary.json'}
    if manifest.get('format') != FORMAT or set(manifest.get('files', {})) != names:
        raise EvidenceError('invalid UCIS export manifest')
    for name in names:
        if sha((directory / name).read_bytes()) != manifest['files'][name]:
            raise EvidenceError(f'UCIS artifact integrity mismatch: {name}')
    bundle = merge([load(directory / 'evidence.json')])
    scope, points, summary = projection(bundle)
    if scope != manifest.get('scope') or points != manifest.get('mapping') or summary != json.loads((directory / 'summary.json').read_text(encoding='utf-8')):
        raise EvidenceError('UCIS manifest or summary does not match evidence')
    check_projection(bundle, directory / 'coverage.xml')
    return bundle
