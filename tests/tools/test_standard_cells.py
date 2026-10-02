"""Check UI example netlists against independently specified Boolean truth tables."""
import os
from pathlib import Path

import pytest

from mock_virtuoso.circuit import check_circuit
from mock_virtuoso.pdk import installed
from mock_virtuoso.simulation import find_ngspice, read_raw, simulate

ROOT = Path(__file__).resolve().parents[2]
TRUTH = {
    'INV': lambda a,b,c: not a, 'BUF': lambda a,b,c: a,
    'NAND2': lambda a,b,c: not (a and b), 'NOR2': lambda a,b,c: not (a or b),
    'AND2': lambda a,b,c: a and b, 'OR2': lambda a,b,c: a or b,
    'XOR2': lambda a,b,c: a != b, 'XNOR2': lambda a,b,c: a == b,
    'MUX2': lambda a,b,c: b if c else a,
    'AOI21': lambda a,b,c: not ((a and b) or c),
    'OAI21': lambda a,b,c: not ((a or b) and c),
}


@pytest.mark.skipif(not os.environ.get('VERIFICATION_BROWSER') or not find_ngspice(), reason='Requires browser and ngspice')
@pytest.mark.parametrize('profile',['generic','sky130'])
def test_every_standard_cell_input_combination(profile,tmp_path):
    if profile == 'sky130' and not installed():
        pytest.skip('Requires installed SKY130')
    playwright=pytest.importorskip('playwright.sync_api')
    with playwright.sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ['VERIFICATION_BROWSER'],headless=True)
        page=browser.new_page()
        source=(ROOT/'floor/circuit.js').read_text(encoding='utf-8').split('// Circuit editor.')[0]
        page.add_script_tag(content=source)
        examples=page.evaluate('standardCellExamples()')
        browser.close()
    assert {e['name'] for e in examples} == set(TRUTH)
    for example in examples:
        circuit=example['circuit'];circuit['model_profile']=profile
        assert check_circuit(circuit)['status']=='pass',example['name']
        result=simulate(circuit,output=tmp_path,executable=find_ngspice(ROOT))
        assert result['status']=='pass',(example['name'],result)
        data=read_raw(tmp_path/result['run_id']/'result.raw',full=True)
        columns={c['name']:c['real'] for c in data['columns']}
        for pattern in range(2**len(example['inputs'])):
            target=20e-9*pattern+10e-9
            sample=min(range(len(columns['time'])),key=lambda i:abs(columns['time'][i]-target))
            bits=[bool(pattern & (1<<bit)) for bit in range(3)]
            for i,name in enumerate(example['inputs']):
                assert abs(columns['v('+name.lower()+')'][sample]-(1.8 if bits[i] else 0))<.05
            expected=1.8 if TRUTH[example['name']](*bits) else 0
            assert abs(columns['v(vout)'][sample]-expected)<.18,(profile,example['name'],pattern,columns['v(vout)'][sample],expected)
