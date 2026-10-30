"""Dependency-free, versioned agent scaffolding. Generated files belong to the user."""
import json
import re
import shutil
import tempfile
from pathlib import Path
from importlib.resources import files


def validate_spec(spec):
    required = {'schema_version', 'name', 'protocol', 'width', 'clock', 'reset',
                'reset_policy', 'fields', 'channels'}
    if not isinstance(spec, dict) or set(spec) != required:
        raise ValueError('interface must contain exactly: ' + ', '.join(sorted(required)))
    if type(spec['schema_version']) is not int or spec['schema_version'] != 1:
        raise ValueError('unsupported interface schema_version; expected 1')
    if spec['protocol'] != 'ready_valid' or spec['reset_policy'] != 'discard':
        raise ValueError('v1 supports ready_valid with reset_policy=discard')
    width = spec['width']
    if type(width) is not int or not 1 <= width <= 4096:
        raise ValueError('width must be an integer in 1..4096')
    if spec['fields'] != [{'name': 'data', 'width': width}]:
        raise ValueError('v1 requires one packed data field matching width')
    names = [spec['name'], spec['clock'], spec['reset']]
    channels = spec['channels']
    if not isinstance(channels, dict) or set(channels) != {'tx', 'rx'}:
        raise ValueError('channels must contain tx and rx')
    for channel, role in [('tx', 'source'), ('rx', 'sink')]:
        item = channels[channel]
        if not isinstance(item, dict) or set(item) != {'role', 'signals'} or item['role'] != role:
            raise ValueError(f'{channel} requires role={role} and signals')
        signals = item['signals']
        if not isinstance(signals, dict) or set(signals) != {'valid', 'ready', 'data'}:
            raise ValueError('signals must contain valid, ready, data')
        names.extend(signals.values())
    reserved = {'module', 'endmodule', 'wire', 'reg', 'input', 'output', 'always', 'begin', 'end',
                'full', 'stored', 'CORRUPT', 'stream_top'}
    reserved.update('alias always_comb always_ff always_latch and assert assign assume automatic '
        'before bind bit break buf byte case casex casez cell chandle checker class clocking '
        'config const constraint context continue cover covergroup coverpoint cross deassign '
        'default defparam design disable dist do edge else endcase endchecker endclass endclocking '
        'endconfig endfunction endgenerate endgroup endinterface endpackage endprimitive '
        'endprogram endproperty endsequence endspecify endtable endtask enum event expect export '
        'extends extern final first_match for force foreach forever fork forkjoin function '
        'generate genvar highz0 highz1 if iff ifnone ignore_bins illegal_bins implements implies '
        'import incdir include initial inout inside int integer interconnect interface intersect '
        'join join_any join_none large let liblist library local localparam logic longint '
        'macromodule medium modport nand negedge nettype new nmos nor not notif0 notif1 null '
        'or output package packed parameter pmos posedge primitive priority program property '
        'protected pull0 pull1 pulldown pullup pure rand randc randcase randsequence real realtime '
        'ref release repeat restrict return rnmos rpmos rtran rtranif0 rtranif1 scalared sequence '
        'shortint shortreal showcancelled signed small soft solve specify specparam static string '
        'strong strong0 strong1 struct super supply0 supply1 table tagged task this throughout '
        'time timeprecision timeunit tran tranif0 tranif1 tri tri0 tri1 triand trior trireg type '
        'typedef union unique unique0 unsigned use uwire var vectored virtual void wait wait_order '
        'wand weak weak0 weak1 while wildcard with within wor xnor xor'.split())
    for name in names:
        if not isinstance(name, str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_]*', name) or name in reserved or name.startswith('s_'):
            raise ValueError(f'unsupported identifier: {name!r}')
    if len(set(names[1:])) != len(names[1:]):
        raise ValueError('signal bindings must be distinct')
    return spec


def create_agent(interface, output):
    spec = validate_spec(json.loads(Path(interface).read_text(encoding='utf-8-sig')))
    output = Path(output).absolute()
    if output.exists():
        raise ValueError('output already exists; generation never overwrites user files')
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.agent-', dir=output.parent))
    try:
        def copy_tree(source, destination):
            for entry in source.iterdir():
                target = destination / entry.name
                if entry.is_dir():
                    target.mkdir()
                    copy_tree(entry, target)
                else:
                    target.write_bytes(entry.read_bytes())
        copy_tree(files('verification_evidence').joinpath('templates/ready_valid'), staging)
        encoded = json.dumps(spec, indent=2, sort_keys=True)
        (staging / 'interface.json').write_text(encoded + '\n', encoding='utf-8')
        (staging / 'interface_config.py').write_text('SPEC = ' + repr(spec) + '\n', encoding='utf-8')
        rtl = staging / 'rtl/stream_top.sv'
        text = rtl.read_text().replace('[7:0]', f'[{spec["width"]-1}:0]').replace("8'h01", "1").replace("8'h00", "0")
        bindings = {'clk': spec['clock'], 'rst_n': spec['reset']}
        for channel in ('tx', 'rx'):
            bindings.update({channel + '_' + key: value for key, value in spec['channels'][channel]['signals'].items()})
        text = re.sub(r'\b(?:' + '|'.join(bindings) + r')\b', lambda m: bindings[m.group()], text)
        rtl.write_text(text, encoding='utf-8')
        # Rename is atomic within this filesystem; never merge into existing output.
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {'status': 'created', 'output': str(output), 'protocol': spec['protocol'], 'schema_version': 1}
