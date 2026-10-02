import pytest

db=pytest.importorskip('klayout.db')
from mock_virtuoso.session import Session
from toolkit.standard_cell_layouts import geometry, skill_for


def test_import_preserves_holes_units_and_existing_cells(tmp_path):
    layout=db.Layout();layout.dbu=.001;cell=layout.create_cell('source')
    polygon=db.Polygon(db.Box(0,0,4000,4000))
    polygon.insert_hole(db.Box(1000,1000,3000,3000))
    cell.shapes(layout.layer(68,20)).insert(polygon)
    cell.shapes(layout.layer(68,5)).insert(db.Text('Y',2000,500))
    path=tmp_path/'source.gds';layout.write(str(path))
    shapes=geometry(path)
    polygons=[s for s in shapes if s['type']=='polygon']
    area=sum(abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(s['points'],s['points'][1:]+s['points'][:1])))/2 for s in polygons)
    assert area==pytest.approx(12)
    assert {s['layer'] for s in shapes}=={'met1'}
    assert next(s for s in shapes if s['type']=='label')['xy']==[2,.5]
    session=Session(artifact_dir=tmp_path)
    skill=skill_for('INV_X1',shapes)
    assert session.evaluate(skill)=='created'
    cv=session.evaluate('dbOpenCellViewByType("SKY130_EXAMPLES" "INV_X1" "layout" "maskLayout" "a")')
    session.evaluate('user=dbOpenCellViewByType("DEMO" "CELL" "layout" "maskLayout" "a") dbCreateRect(user list("met1" "drawing") list(0:0 1:1))')
    count=len(cv.shapes)
    assert session.evaluate(skill)=='existing'
    assert len(cv.shapes)==count
    assert session.evaluate('length(user~>shapes)')==1


def test_rejects_unknown_destination():
    with pytest.raises(ValueError,match='Unknown'):
        skill_for('USER_DESIGN',[])
