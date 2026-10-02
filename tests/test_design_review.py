import json
import os
from pathlib import Path

import pytest

from mock_virtuoso.design_review import aggregate, run_review, time_mean, validate_plan
from mock_virtuoso.simulation import find_ngspice
from toolkit.review_service import safe_subcircuit


def plan(profile='generic'):
    return dict(circuit=dict(name='REVIEW_INV', model_profile=profile, devices=[
        dict(id='VDD', kind='V', nodes=['vdd','0'], value=1.8),
        dict(id='VA', kind='V', nodes=['a','0'], value=0),
        dict(id='MN', kind='NMOS', nodes=['vout','a','0','0'], width=.65e-6, length=.15e-6),
        dict(id='MP', kind='PMOS', nodes=['vout','a','vdd','vdd'], width=1.3e-6, length=.15e-6),
        dict(id='CL', kind='C', nodes=['vout','0'], value=5e-15)], analysis=dict(type='op')),
        logic='INV', inputs=['VA'], supply='VDD', output='vout', corners=['tt'],
        temperatures=[27], voltages=[1.8], limits=dict(delay_ns=2, transition_ns=2, power_uw=100))


def test_adaptive_time_power_is_integrated_not_sample_averaged():
    assert time_mean([0, .01, 1], [0, .01, 1], 0, 1) == pytest.approx(.5)
    assert aggregate([]) == 'not_run'
    assert aggregate(['pass', 'unsupported']) == 'unsupported'
    assert aggregate(['pass', 'error']) == 'error'


@pytest.mark.parametrize('changes', [dict(logic='DFF'), dict(inputs=['VDD']),
    dict(corners=['ff']), dict(voltages=[float('nan')]), dict(limits={}),
    dict(temperatures=list(range(30)), voltages=[1.6, 1.8]), dict(slew_ns=.01)])
def test_invalid_review_rejected(changes):
    with pytest.raises(ValueError):
        validate_plan({**plan(), **changes})


@pytest.mark.skipif(not find_ngspice(), reason='Requires ngspice')
def test_truth_timing_power_and_changed_function(tmp_path):
    p = plan()
    p['voltages'] = [1.62, 1.8]
    report = run_review(p, output=tmp_path)
    assert report['status'] == 'pass', report
    assert len(report['runs']) == 2
    for run in report['runs']:
        assert [v['expected'] for v in run['functional']['vectors']] == [1, 0]
        assert run['functional']['vectors'][1]['input_v'][0] == pytest.approx(run['voltage'])
        assert run['metrics']['power_uw']['value'] > 0
        assert run['metrics']['delay_ns']['value'] > 0
        assert run['timing']['arcs']
    p['logic'] = 'BUF'
    p['voltages'] = [1.8]
    wrong = run_review(p, output=tmp_path)
    assert wrong['checks']['functional'] == 'fail'
    assert not wrong['foundry_qualified']
    assert json.loads((tmp_path / wrong['run_id'] / 'result.json').read_text())['status'] == 'fail'


def test_missing_engine_is_not_a_functional_pass(tmp_path):
    report = run_review(plan(), executable=tmp_path/'absent.exe', output=tmp_path)
    assert report['checks'] == dict(functional='not_run', timing='not_run', power='not_run')


@pytest.mark.parametrize('injection', ['.control\nshell echo bad\n.endc', '.include other.spice',
    'X1 y a 0 0 evil w=1 l=1', 'R1 y 0 {system(1)}', 'R1 y 0 1\n.ends\n.control',
    '.subckt nested x y', 'R1 y 0 1\nR1 y 0 2'])
def test_reference_parser_rejects_programs_and_unknown_models(injection):
    with pytest.raises(ValueError):
        safe_subcircuit('.subckt inv a y\n'+injection+'\n.ends', 'inv', {'a':'a','y':'vout'})


def test_reference_units_and_port_order():
    source = '.subckt inv y a\nX0 y a 0 0 sky130_fd_pr__nfet_01v8 w=650000u l=150000u\n.ends'
    converted = safe_subcircuit(source, 'inv', {'a':'a', 'y':'vout'})
    assert 'w=0.65 l=0.15' in converted
    assert 'X_REVIEW vout a REVIEW_DUT' in converted
    with pytest.raises(ValueError, match='Map every'):
        safe_subcircuit(source, 'inv', {'a':'a'})


@pytest.mark.skipif(not os.environ.get('RUN_MAGIC_TESTS') or not os.environ.get('KLAYOUT_EXE'), reason='Requires real physical engines')
def test_paired_lvs_reference_and_pex(tmp_path, monkeypatch):
    import base64
    from toolkit import review_service, verification_service
    root = Path.cwd()
    monkeypatch.setenv('SKY130_DECKS', str(root/'.tools/sky130'))
    monkeypatch.setenv('NGSPICE_EXE', str(find_ngspice(root)))
    monkeypatch.setattr(review_service, 'ROOT', tmp_path)
    monkeypatch.setattr(verification_service, 'ROOT', tmp_path)
    fixture = root/'.tools/sky130-fixture/sky130_fd_sc_hd__inv_1'
    physical = verification_service.verify_upload(dict(top=fixture.name, substrate='VNB', physical_checks=True,
        gds_base64=base64.b64encode(fixture.with_suffix('.gds').read_bytes()).decode(),
        netlist=fixture.with_suffix('.spice').read_text()))
    payload = dict(plan=plan('sky130'), run_id=physical['run_id'],
        ports={'A':'a','Y':'vout','VPWR':'vdd','VGND':'0','VPB':'vdd','VNB':'0'})
    report = review_service.compare(payload)
    assert report['status'] == 'pass', report
    assert report['baseline']['checks']['functional'] == report['postlayout']['checks']['functional'] == 'pass'
    assert report['deltas'][0]['metrics']['delay_ns']['delta'] is not None
    assert report['layout_sha256'] == physical['inputs']['gds']['sha256']
    assert report['reference_sha256'] == physical['inputs']['netlist']['sha256']
    reference = tmp_path/'verification-runs'/physical['run_id']/'reference.spice'
    reference.write_text('* changed')
    with pytest.raises(ValueError, match='hash mismatch'):
        review_service.compare(payload)
