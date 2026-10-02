"""Measured combinational-cell review; never inferred from simulator exit alone."""
from bisect import bisect_right
from copy import deepcopy
from datetime import datetime, timezone
from itertools import product
import hashlib
import json
import math
from pathlib import Path
import uuid

from .circuit import fields, identifier, number, validate_circuit
from .pdk import CORNERS
from .simulation import read_raw, simulate

INPUTS = {'INV': 1, 'BUF': 1, 'NAND2': 2, 'NOR2': 2, 'AND2': 2,
          'OR2': 2, 'XOR2': 2, 'XNOR2': 2, 'MUX2': 3, 'AOI21': 3, 'OAI21': 3}


def truth(kind, bits):
    a, b, c = (list(bits) + [False, False])[:3]
    return bool({'INV': lambda: not a, 'BUF': lambda: a,
                 'NAND2': lambda: not (a and b), 'NOR2': lambda: not (a or b),
                 'AND2': lambda: a and b, 'OR2': lambda: a or b,
                 'XOR2': lambda: a != b, 'XNOR2': lambda: a == b,
                 'MUX2': lambda: b if c else a,
                 'AOI21': lambda: not ((a and b) or c),
                 'OAI21': lambda: not ((a or b) and c)}[kind]())


def aggregate(statuses):
    statuses = list(statuses)
    for state in ('error', 'fail', 'not_run', 'unsupported', 'stale'):
        if state in statuses:
            return state
    return 'pass' if statuses and all(s == 'pass' for s in statuses) else 'not_run'


def validate_plan(value):
    fields(value, ('circuit', 'logic', 'inputs', 'output', 'supply', 'corners',
                   'temperatures', 'voltages', 'limits', 'settle_ns', 'slew_ns'), 'design review')
    circuit = validate_circuit(value.get('circuit'))
    logic = value.get('logic')
    if not isinstance(logic, str) or logic not in INPUTS:
        raise ValueError('Choose a supported combinational logic function; sequential characterization is unsupported')
    inputs = value.get('inputs')
    if not isinstance(inputs, list) or len(inputs) != INPUTS[logic]:
        raise ValueError('Input source order must match the logic function (MUX2: A,B,S)')
    inputs = [identifier(v, 'input source') for v in inputs]
    supply = identifier(value.get('supply'), 'supply source')
    sources = {d['id']: d for d in circuit['devices'] if d['kind'] == 'V'}
    if len(set(inputs + [supply])) != len(inputs) + 1 or any(s not in sources for s in inputs + [supply]):
        raise ValueError('Select distinct existing voltage sources for supply and inputs')
    if any(sources[s]['nodes'][1] != '0' for s in inputs + [supply]):
        raise ValueError('Review sources must be ground referenced')
    nodes = [sources[s]['nodes'][0] for s in inputs + [supply]]
    output = identifier(value.get('output', 'vout'), 'output', node=True).lower()
    if len(set(nodes)) != len(nodes) or '0' in nodes or output in nodes + ['0']:
        raise ValueError('Supply, input and output nodes must be distinct')
    corners = value.get('corners', [circuit.get('corner', 'tt')])
    if not isinstance(corners, list) or not corners or any(c not in CORNERS for c in corners):
        raise ValueError('Select supported process corners')
    if circuit.get('model_profile', 'generic') == 'generic' and corners != ['tt']:
        raise ValueError('Process corner sweeps require SKY130 models')
    def values(key, default, low, high):
        raw = value.get(key, default)
        if not isinstance(raw, list) or not raw or len(raw) > 30:
            raise ValueError(f'{key}: provide 1–30 values')
        return list(dict.fromkeys(number(v, key, low, high) for v in raw))
    temps = values('temperatures', [27], -100, 250)
    volts = values('voltages', [sources[supply]['value']], 0.1, 1.98)
    corners = list(dict.fromkeys(corners))
    if len(corners) * len(temps) * len(volts) > 30:
        raise ValueError('Review is limited to 30 PVT combinations')
    limits = value.get('limits', {})
    fields(limits, ('delay_ns', 'transition_ns', 'power_uw'), 'acceptance limits')
    limits = {k: number(limits.get(k), k, 1e-9, 1e9) for k in ('delay_ns', 'transition_ns', 'power_uw')}
    settle = number(value.get('settle_ns', 20), 'settle_ns', 1, 1000)
    slew = number(value.get('slew_ns', 0.1), 'slew_ns', 0.01, settle / 10)
    if settle * (2**len(inputs)+1) / (slew / 4) > 10000:
        raise ValueError('Reduce settling time or increase slew: review exceeds 10,000 time steps')
    return dict(circuit=circuit, logic=logic, inputs=inputs, supply=supply, output=output,
                corners=corners, temperatures=temps, voltages=volts, limits=limits,
                settle_ns=settle, slew_ns=slew)


def testbench(plan, corner, temperature, voltage, *, external=False):
    circuit = deepcopy(plan['circuit'])
    circuit.update(corner=corner, temperature_c=temperature)
    if external:
        circuit['devices'] = [d for d in circuit['devices'] if d['kind'] in ('R', 'C', 'L', 'V', 'I')]
        circuit['model_profile'] = 'sky130'
    by_id = {d['id']: d for d in circuit['devices']}
    by_id[plan['supply']].update(value=voltage, ac=0)
    by_id[plan['supply']].pop('pulse', None)
    for bit, source in enumerate(plan['inputs']):
        half = plan['settle_ns'] * 1e-9 * 2**bit
        edge = plan['slew_ns'] * 1e-9
        by_id[source].update(value=0, ac=0, pulse=dict(low=0, high=voltage, delay=half,
            rise=edge, fall=edge, width=half-edge, period=2*half))
    circuit['analysis'] = dict(type='tran', step=plan['slew_ns'] * 1e-9 / 4,
                               stop=plan['settle_ns'] * 1e-9 * (2**len(plan['inputs'])+1))
    return validate_circuit(circuit)


def interpolate(times, values, time):
    if time < times[0] or time > times[-1]:
        raise ValueError('Waveform does not cover the measurement window')
    i = min(max(bisect_right(times, time)-1, 0), len(times)-2)
    return values[i] + (values[i+1]-values[i]) * (time-times[i]) / (times[i+1]-times[i])


def crossing(times, values, level, rising, start, stop):
    for i in range(max(1, bisect_right(times, start)), min(len(times), bisect_right(times, stop)+1)):
        a, b = values[i-1], values[i]
        if (a < level <= b) if rising else (a > level >= b):
            time = times[i-1] + (level-a) / (b-a) * (times[i]-times[i-1])
            if start <= time <= stop:
                return time
    return None


def time_mean(times, values, start, stop):
    interior = [i for i, t in enumerate(times) if start < t < stop]
    ts = [start] + [times[i] for i in interior] + [stop]
    ys = [interpolate(times, values, start)] + [values[i] for i in interior] + [interpolate(times, values, stop)]
    return math.fsum((b-a)*(x+y)/2 for a, b, x, y in zip(ts, ts[1:], ys, ys[1:])) / (stop-start)


def evaluate(data, plan, circuit, voltage):
    cols = {c['name'].lower(): c['real'] for c in data['columns']}
    times = cols['time']
    if len(times) < 2 or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError('Transient time samples must be strictly increasing')
    by_id = {d['id']: d for d in circuit['devices']}
    inputs = [cols['v('+by_id[s]['nodes'][0]+')'] for s in plan['inputs']]
    output = cols['v('+plan['output']+')']
    period = plan['settle_ns'] * 1e-9
    count = 2**len(inputs)
    truth_rows, arcs = [], []
    # Repeat the initial vector so wraparound edges and a complete energy cycle
    # are measured, rather than reporting energy returned on just a falling edge.
    for pattern in range(count+1):
        bits = [bool(pattern & (1 << i)) for i in range(len(inputs))]
        sample = (pattern + .5) * period
        expected = truth(plan['logic'], bits)
        actual = interpolate(times, output, sample)
        observed = [interpolate(times, values, sample) for values in inputs]
        def matches(v, bit):
            return .8*voltage <= v <= 1.2*voltage if bit else -.2*voltage <= v <= .2*voltage
        ok = matches(actual, expected) and all(matches(v, b) for v, b in zip(observed, bits))
        if pattern < count:
            truth_rows.append(dict(inputs=[int(b) for b in bits], expected=int(expected),
                                   output_v=actual, input_v=observed, time_s=sample, status='pass' if ok else 'fail'))
        if not pattern:
            continue
        previous = [bool((pattern-1) & (1 << i)) for i in range(len(inputs))]
        changed = [i for i in range(len(bits)) if bits[i] != previous[i]]
        if len(changed) != 1 or truth(plan['logic'], previous) == expected:
            continue  # Multi-input transitions cannot identify a timing arc.
        bit = changed[0]
        start, stop = pattern*period, sample
        trigger = crossing(times, inputs[bit], .5*voltage, bits[bit], start, stop)
        target = crossing(times, output, .5*voltage, expected, start, stop)
        low = crossing(times, output, (.1 if expected else .9)*voltage, expected, start, stop)
        high = crossing(times, output, (.9 if expected else .1)*voltage, expected, start, stop)
        complete = all(v is not None for v in (trigger, target, low, high))
        arcs.append(dict(input=plan['inputs'][bit], edge='rise' if expected else 'fall',
            pattern=pattern, status='pass' if complete else 'fail',
            delay_ns=(target-trigger)*1e9 if complete else None,
            transition_ns=(high-low)*1e9 if complete else None))
    metrics = {}
    for name in ('delay_ns', 'transition_ns'):
        values = [a[name] for a in arcs if a[name] is not None]
        value = max(values) if values else None
        metrics[name] = dict(value=value, limit=plan['limits'][name],
            status='not_run' if not arcs else 'pass' if len(values) == len(arcs) and value <= plan['limits'][name] else 'fail')
    supply = cols['v('+by_id[plan['supply']]['nodes'][0]+')']
    current = cols['i(v_'+plan['supply'].lower()+')']
    power = [-v*i for v, i in zip(supply, current)]
    # Exclude initial operating-point settling; integrate adaptive samples in time.
    average = time_mean(times, power, period*.5, (count+.5)*period)*1e6
    steady = max(time_mean(times, power, (i+.8)*period, (i+.9)*period) for i in range(count))*1e6
    metrics['power_uw'] = dict(value=average, limit=plan['limits']['power_uw'],
                               status='pass' if 0 <= average <= plan['limits']['power_uw'] else 'fail')
    return dict(functional=dict(status=aggregate(r['status'] for r in truth_rows), vectors=truth_rows),
                timing=dict(status=aggregate(metrics[k]['status'] for k in ('delay_ns', 'transition_ns')), arcs=arcs),
                power=dict(status=metrics['power_uw']['status'], steady_supply_uw=steady), metrics=metrics)


def run_review(value, *, executable=None, output='simulation-runs', dut=None):
    plan = validate_plan(value)
    directory = Path(output).resolve() / ('review-' + uuid.uuid4().hex)
    directory.mkdir(parents=True)
    report = dict(run_id=directory.name, created_at=datetime.now(timezone.utc).isoformat(),
                  plan=plan, plan_sha256=hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest(),
                  foundry_qualified=False, runs=[], status='running',
                  scope='Combinational sampled truth table; observed single-input timing arcs; supply energy. Not a Liberty characterization or STA.')
    def save():
        (directory/'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    save()
    for corner, temperature, voltage in product(plan['corners'], plan['temperatures'], plan['voltages']):
        circuit = testbench(plan, corner, temperature, voltage, external=dut is not None)
        result = simulate(circuit, executable=executable, output=directory, extracted_dut=dut)
        measured = {}
        status = result['status'] if result['status'] != 'blocked' else 'fail'
        if status == 'pass':
            try:
                measured = evaluate(read_raw(directory/result['run_id']/'result.raw', full=True), plan, circuit, voltage)
                status = aggregate(measured[k]['status'] for k in ('functional', 'timing', 'power'))
            except (OSError, ValueError, KeyError, IndexError, StopIteration) as exc:
                status = 'error'
                measured = {'reason': f'Cannot measure complete raw waveform: {exc}'}
        report['runs'].append(dict(corner=corner, temperature_c=temperature, voltage=voltage,
                                   status=status, simulation=result, **measured))
        save()
    report['checks'] = {k: aggregate(r.get(k, {}).get('status', r['status']) for r in report['runs'])
                        for k in ('functional', 'timing', 'power')}
    report['status'] = aggregate(report['checks'].values())
    save()
    return report
