"""Design review adapter and paired simulation of an LVS reference and its PEX."""
from pathlib import Path
import hashlib
import json
import math
import re
import uuid

from mock_virtuoso.circuit import fields, identifier
from mock_virtuoso.design_review import aggregate, run_review, validate_plan
from mock_virtuoso.simulation import find_ngspice

ROOT = Path(__file__).resolve().parents[1]
NODE = re.compile(r'[A-Za-z0-9_./#!<>\[\]:-]+\Z')
MODELS = {'sky130_fd_pr__nfet_01v8', 'sky130_fd_pr__pfet_01v8', 'sky130_fd_pr__pfet_01v8_hvt'}


def spice_number(value):
    match = re.fullmatch(r'([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?)(meg|[tgkmunpf]?)', value, re.I)
    if not match:
        raise ValueError('Only finite numeric SPICE parameters are supported')
    result = float(match[1]) * {'':1, 't':1e12, 'g':1e9, 'meg':1e6, 'k':1e3, 'm':1e-3,
                               'u':1e-6, 'n':1e-9, 'p':1e-12, 'f':1e-15}[match[2].lower()]
    if not math.isfinite(result) or result < 0:
        raise ValueError('Invalid SPICE parameter')
    return result


def safe_subcircuit(text, top, mapping, *, units='micron'):
    """Rebuild a flat numeric X/R/C subcircuit; never execute uploaded directives."""
    lines, ports, inside, ended, names = [], None, False, False, set()
    # Continuations are common in native Magic device records.
    logical = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('*'):
            continue
        if line.startswith('+') and logical:
            logical[-1] += ' ' + line[1:]
        else:
            logical.append(line)
    for line in logical:
        tokens = line.split()
        if tokens[0].lower() == '.subckt':
            if ports is not None or len(tokens) < 3 or tokens[1].lower() != top.lower():
                raise ValueError('Comparison supports one flat top-level X/R/C subcircuit')
            ports = tokens[2:]
            if len({p.lower() for p in ports}) != len(ports) or not all(NODE.fullmatch(p) for p in ports):
                raise ValueError('Invalid or duplicate subcircuit ports')
            lines.append('.subckt REVIEW_DUT ' + ' '.join(ports))
            inside = True
            continue
        if tokens[0].lower() == '.ends':
            if not inside or len(tokens) > 2 or (len(tokens) == 2 and tokens[1].lower() != top.lower()):
                raise ValueError('Invalid subcircuit end')
            inside, ended = False, True
            lines.append('.ends REVIEW_DUT')
            continue
        if not inside or ended or not re.fullmatch(r'[XRC][A-Za-z0-9_]+', tokens[0], re.I):
            raise ValueError('Unsupported SPICE statement in comparison reference')
        if tokens[0].lower() in names:
            raise ValueError('Duplicate SPICE device')
        names.add(tokens[0].lower())
        kind = tokens[0][0].upper()
        count = 4 if kind == 'X' else 2
        if len(tokens) < count+2 or not all(NODE.fullmatch(p) for p in tokens[1:count+1]):
            raise ValueError('Invalid SPICE device nodes')
        if kind == 'X':
            if tokens[5].lower() not in MODELS:
                raise ValueError('Comparison supports SKY130 1.8 V nfet/pfet/pfet_hvt devices')
            params = {}
            for token in tokens[6:]:
                pair = token.split('=')
                if len(pair) != 2 or pair[0].lower() not in ('w', 'l', 'ad', 'as', 'pd', 'ps', 'm', 'nf') or pair[0].lower() in params:
                    raise ValueError('Unsupported or duplicate device parameter')
                key = pair[0].lower()
                value = spice_number(pair[1])
                if units == 'si' and key in ('w', 'l', 'ad', 'as', 'pd', 'ps'):
                    value *= 1e12 if key in ('ad', 'as') else 1e6
                params[key] = value
            if not all(params.get(k, 0) > 0 for k in ('w', 'l')):
                raise ValueError('Positive W and L are required')
            lines.append(' '.join(tokens[:6]) + ' ' + ' '.join(f'{k}={v:.15g}' for k, v in params.items()))
        else:
            if len(tokens) != 4:
                raise ValueError('Only numeric resistors and capacitors are supported')
            lines.append(' '.join(tokens[:3]) + f' {spice_number(tokens[3]):.15g}')
    if not ended or not names or not ports:
        raise ValueError('Complete nonempty subcircuit required')
    if not isinstance(mapping, dict) or set(mapping) != set(ports):
        raise ValueError('Map every reference/extracted port exactly: ' + ', '.join(ports))
    nodes = [identifier(mapping[p], 'port node', node=True).lower() for p in ports]
    return '\n'.join(lines) + '\nX_REVIEW ' + ' '.join(nodes) + ' REVIEW_DUT\n'


def review(payload):
    return run_review(payload, executable=find_ngspice(ROOT), output=ROOT/'simulation-runs')


def compare(payload):
    fields(payload, ('plan', 'run_id', 'ports'), 'PEX comparison')
    plan = validate_plan(payload.get('plan'))
    if plan['circuit'].get('model_profile') != 'sky130':
        raise ValueError('PEX comparison requires SKY130 models')
    if len(plan['corners'])*len(plan['temperatures'])*len(plan['voltages']) > 15:
        raise ValueError('Paired comparison is limited to 15 PVT combinations (30 simulations)')
    run_id = payload.get('run_id')
    if not isinstance(run_id, str) or not re.fullmatch('[a-f0-9]{32}', run_id):
        raise ValueError('Select a completed physical verification run ID')
    directory = (ROOT/'verification-runs'/run_id).resolve()
    if not directory.is_relative_to((ROOT/'verification-runs').resolve()):
        raise ValueError('Invalid verification directory')
    physical = json.loads((directory/'result.json').read_text(encoding='utf-8'))
    if any(physical.get(k, {}).get('status') != 'pass' for k in ('lvs', 'pex')):
        raise ValueError('Comparison requires successful LVS and PEX from the same run')
    reference = directory/'reference.spice'
    source = reference.read_bytes()
    if hashlib.sha256(source).hexdigest() != physical['inputs']['netlist']['sha256']:
        raise ValueError('Reference snapshot hash mismatch; rerun verification')
    if physical['extraction']['input_sha256'] != physical['inputs']['gds']['sha256']:
        raise ValueError('PEX and LVS layout hashes differ; rerun verification')
    schematic = safe_subcircuit(source.decode('utf-8'), physical['top'], payload.get('ports'),
                                units=physical['settings']['spice_units'])
    extracted = physical['pex']['netlist']
    post = safe_subcircuit(extracted, 'extracted', payload.get('ports'))
    # Same source/load testbench for both sides. Editor transistors are excluded.
    baseline = run_review(plan, executable=find_ngspice(ROOT), output=ROOT/'simulation-runs', dut=schematic)
    postlayout = run_review(plan, executable=find_ngspice(ROOT), output=ROOT/'simulation-runs', dut=post)
    deltas = []
    for before, after in zip(baseline['runs'], postlayout['runs']):
        metrics = {}
        for key in ('delay_ns', 'transition_ns', 'power_uw'):
            a = before.get('metrics', {}).get(key, {}).get('value')
            b = after.get('metrics', {}).get(key, {}).get('value')
            metrics[key] = dict(before=a, after=b, delta=b-a if a is not None and b is not None else None)
        deltas.append(dict(corner=before['corner'], temperature_c=before['temperature_c'], voltage=before['voltage'], metrics=metrics))
    report = dict(run_id='comparison-'+uuid.uuid4().hex, verification_run_id=run_id,
        status=aggregate([baseline['status'], postlayout['status']]), baseline=baseline, postlayout=postlayout,
        deltas=deltas, physical_checks=physical['signoff']['checklist'], foundry_qualified=False,
        reference_sha256=hashlib.sha256(source).hexdigest(), extracted_sha256=hashlib.sha256(extracted.encode()).hexdigest(),
        layout_sha256=physical['inputs']['gds']['sha256'],
        scope='LVS reference versus RC extraction, using identical sources/loads/PVT. Editor transistors are excluded.')
    target = ROOT/'simulation-runs'/report['run_id']
    target.mkdir(parents=True)
    (target/'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report
