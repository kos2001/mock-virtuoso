import json
import io
import zipfile
from types import SimpleNamespace

import pytest

db = pytest.importorskip('klayout.db')
from mock_virtuoso.db.geometry import transform_bbox
from mock_virtuoso.layout_snapshot import snapshot
from mock_virtuoso.session import Session
from mock_virtuoso.skill.errors import SkillError
from toolkit import layout_verification as service


@pytest.fixture
def design(tmp_path, monkeypatch):
    session = Session(artifact_dir=tmp_path)
    session.evaluate('cv = dbOpenCellViewByType("LIB" "TOP" "layout" "maskLayout" "a")')
    session.evaluate('dbCreateRect(cv list("met1" "drawing") list(0:0 2:1))')
    class Client:
        def execute_skill(self, source):
            try:
                return SimpleNamespace(status=SimpleNamespace(value='success'), output=json.dumps(session.evaluate(source)))
            except SkillError as exc:
                return SimpleNamespace(status=SimpleNamespace(value='error'), errors=[str(exc)])
    monkeypatch.setattr(service, 'ROOT', tmp_path)
    return session, Client(), {'library':'LIB','cell':'TOP'}


def test_readonly_snapshot_and_gds_capture_current_cell(design):
    session, client, target = design
    cv = session.design.find_cellview('LIB', 'TOP', 'layout')
    windows = list(session.windows)
    report = service.verify(client, target)
    assert cv.mode == 'a' and session.windows == windows
    assert report['roundtrip']['status'] == 'pass'
    assert report['external']['status'] == 'not_run'
    assert report['renderer']['status'] == 'not_run'
    assert not report['stale']
    layout = db.Layout()
    layout.read(report['directory']+'/layout.gds')
    assert layout.cell('TOP').dbbox() == db.DBox(0,0,2,1)
    assert not service.status(client, {**target, 'snapshot_sha256':report['snapshot_sha256']})['stale']
    session.evaluate('dbCreateRect(cv list("met1" "drawing") list(3:0 4:1))')
    assert service.status(client, {**target, 'snapshot_sha256':report['snapshot_sha256']})['stale']


def test_master_and_connectivity_edits_invalidate_snapshot(design):
    session, client, target = design
    session.evaluate('m = dbOpenCellViewByType("LIB" "M" "layout" "maskLayout" "a")')
    session.evaluate('dbCreateRect(m list("met1" "drawing") list(0:0 2:1))')
    session.evaluate('dbCreateInst(cv m "I0" 4:0 "MY")')
    first = service.read_snapshot(client, target)
    session.evaluate('dbCreateRect(m list("met2" "drawing") list(0:0 1:1))')
    second = service.read_snapshot(client, target)
    assert first['snapshot_sha256'] != second['snapshot_sha256']
    session.evaluate('n = dbCreateNet(m "VDD") dbCreateTerm(n "VDD" "inputOutput")')
    third = service.read_snapshot(client, target)
    assert second['snapshot_sha256'] != third['snapshot_sha256']
    assert third['cells']['LIB/M/layout']['nets'][0]['terminals'][0]['name'] == 'VDD'


@pytest.mark.parametrize('orient', list(service.ORIENTS))
def test_export_preserves_rotations_and_mirrors(design, orient):
    session, client, target = design
    session.evaluate('m = dbOpenCellViewByType("LIB" "M" "layout" "maskLayout" "a")')
    session.evaluate('dbCreatePolygon(m list("met2" "drawing") list(0:0 2:0 2:1 1:1 1:3 0:3))')
    session.evaluate(f'dbCreateInst(cv m "I0" 7:9 "{orient}")')
    report = service.verify(client, target)
    layout = db.Layout()
    layout.read(report['directory']+'/layout.gds')
    region = db.Region(layout.cell('TOP').begin_shapes_rec(layout.layer(5,0)))
    expected = transform_bbox([[0,0],[2,3]], [7,9], orient)
    assert region.bbox().to_dtype(layout.dbu) == db.DBox(*expected[0], *expected[1])
    assert region.area()*layout.dbu**2 == pytest.approx(4)  # preserve the concave polygon, not its bbox


def test_missing_cell_is_never_created(design):
    session, client, _ = design
    with pytest.raises(ValueError, match='does not exist'):
        service.verify(client, {'library':'LIB','cell':'MISSING'})
    assert not session.design.cell_exists('LIB','MISSING')


def test_labels_alone_are_not_physical_geometry(design):
    session, client, target=design
    session.evaluate('dbDeleteObject(car(cv~>shapes))')
    session.evaluate('dbCreateLabel(cv list("text" "drawing") 0:0 "A" "centerCenter" "R0" "roman" 0.2)')
    with pytest.raises(ValueError,match='Empty physical geometry'):
        service.verify(client,target)


def test_export_refuses_silent_layer_loss_and_rounding(design):
    session, client, target = design
    session.evaluate('dbCreateRect(cv list("custom" "drawing") list(3:0 4:1))')
    with pytest.raises(ValueError, match='No explicit'):
        service.verify(client, target)
    session.evaluate('dbDeleteObject(car(cdr(cv~>shapes)))')
    session.evaluate('dbCreateRect(cv list("met1" "drawing") list(3.00001:0 4:1))')
    with pytest.raises(ValueError, match='export grid'):
        service.verify(client, target)


def test_explicit_sky130_mapping_and_external_source_evidence(design, monkeypatch):
    session, client, target = design
    directory = service.ROOT / 'external'; directory.mkdir()
    def verify(payload):
        assert payload['top'] == 'TOP'
        assert payload['netlist'] == '.subckt TOP A B\n.ends\n'
        return {'directory':str(directory),'run_id':'a'*32, 'drc':{'status':'pass'}, 'lvs':{'status':'fail'}}
    monkeypatch.setattr(service.verification_service, 'verify_upload', verify)
    report = service.verify(client, {**target,'profile':'sky130','netlist':'.subckt TOP A B\n.ends\n'})
    assert report['external']['lvs']['status'] == 'fail'
    evidence = json.loads((directory/'layout-snapshot.json').read_text())
    assert evidence['snapshot_sha256'] == report['snapshot_sha256']
    assert report['external']['source_layout']['gds_sha256'] == report['gds_sha256']
    layout = db.Layout(); layout.read(report['directory']+'/layout.gds')
    assert layout.layer_infos() == [db.LayerInfo(68,20)]


def test_snapshot_does_not_open_closed_cell(design):
    session, client, target = design
    session.evaluate('dbClose(cv)')
    assert session.evaluate('dbGetOpenCellViews()') == []
    service.read_snapshot(client,target)
    assert session.evaluate('dbGetOpenCellViews()') == []


def test_canvas_and_gds_keep_path_width_and_nested_master_shapes(design):
    session, client, target = design
    session.evaluate('leaf = dbOpenCellViewByType("LIB" "LEAF" "layout" "maskLayout" "a")')
    session.evaluate('dbCreatePath(leaf list("met2" "drawing") list(0:0 2:0 2:3) 0.2)')
    session.evaluate('m = dbOpenCellViewByType("LIB" "M" "layout" "maskLayout" "a")')
    session.evaluate('dbCreateInst(m leaf "L0" 4:5 "MY")')
    session.evaluate('dbCreateInst(cv m "I0" 7:9 "R90")')
    data = service.canvas_geometry(service.read_snapshot(client,target))
    path = data['masters']['LIB/M'][0]
    assert path['points']==[[4,5],[2,5],[2,8]]
    assert path['width']==.2
    assert path['bbox'][0]==pytest.approx([1.9,4.9])
    assert path['bbox'][1]==pytest.approx([4.1,8.1])
    report=service.verify(client,target)
    layout=db.Layout();layout.read(report['directory']+'/layout.gds')
    region=db.Region(layout.cell('TOP').begin_shapes_rec(layout.layer(5,0)))
    # The L path is not its rectangular bounding box.
    assert region.area()*layout.dbu**2 < 2


def test_exported_public_inverter_passes_real_decks(tmp_path, monkeypatch):
    from pathlib import Path
    from toolkit.standard_cell_layouts import geometry, skill_for
    root = Path(__file__).resolve().parents[2]
    fixture = root / '.tools/sky130-fixture'
    top = 'sky130_fd_sc_hd__inv_1'
    exe = service.verification_service.find_klayout()
    if not exe or not (fixture/f'{top}.gds').exists():
        pytest.skip('Install KLayout and SKY130 fixtures')
    session = Session(artifact_dir=tmp_path)
    session.evaluate(skill_for('INV_X1', geometry(fixture/f'{top}.gds')).replace('INV_X1',top))
    class Client:
        def execute_skill(self, source):
            return SimpleNamespace(status=SimpleNamespace(value='success'),output=json.dumps(session.evaluate(source)))
    monkeypatch.setattr(service,'ROOT',tmp_path)
    monkeypatch.setattr(service.verification_service,'ROOT',tmp_path)
    monkeypatch.setenv('SKY130_DECKS',str(root/'.tools/sky130'))
    monkeypatch.setenv('KLAYOUT_EXE',exe)
    report = service.verify(Client(), {'library':'SKY130_EXAMPLES','cell':top,'profile':'sky130',
        'settings':{'substrate':'VNB'}, 'netlist':(fixture/f'{top}.spice').read_text()})
    assert report['external']['drc']['status']=='pass',report['external']['drc']
    assert report['external']['lvs']['status']=='pass',report['external']['lvs']
    assert report['external']['inputs']['gds']['sha256']==report['gds_sha256']
    assert not report['stale']
    with zipfile.ZipFile(io.BytesIO(service.verification_service.evidence(report['external']['run_id']))) as archive:
        assert 'layout-snapshot.json' in archive.namelist()
