import pytest

from mock_virtuoso.session import Session
from mock_virtuoso.skill.errors import SkillError
from mock_virtuoso.skill.values import NIL


@pytest.fixture
def s(tmp_path):
    session = Session(artifact_dir=tmp_path)
    session.evaluate('cv=dbOpenCellViewByType("L" "C" "layout" "maskLayout" "w") '
                     'f=dbCreateRect(cv list("met1" "drawing") list(0:0 2:1))')
    return session


def test_copy_then_move_keeps_original_and_handle(s):
    original = s.evaluate('f')
    duplicate = s.evaluate('g=dbCopyFig(f cv list(10:5 "R90" 2))')
    assert duplicate.bbox == [[8, 5], [10, 9]]
    assert original.bbox == [[0, 0], [2, 1]]
    assert duplicate.handle != original.handle
    assert s.evaluate('dbMoveFig(g nil list(1:2 "MX"))') is duplicate
    assert duplicate.bbox == [[9, -7], [11, -3]]
    assert original.bbox == [[0, 0], [2, 1]]


def test_path_and_label_metadata(s):
    p = s.evaluate('p=dbCreatePath(cv list("met1" "drawing") list(0:0 4:0) 2) '
                   'dbCopyFig(p cv list(0:0 "R90" 2))')
    assert p.get_prop('points') == [[0, 0], [0, 8]]
    assert p.get_prop('width') == 4
    assert p.bbox == [[-2, -2], [2, 10]]
    label = s.evaluate('l=dbCreateLabel(cv list("text" "drawing") 1:2 '
                       '"VDD" "centerCenter" "MX" "stick" 0.5) '
                       'dbCopyFig(l cv list(3:4 "R90"))')
    assert label.get_prop('xy') == [1, 5]
    assert label.get_prop('orient') == 'MXR90'
    assert label.get_prop('theLabel') == 'VDD'


def test_instance_composes_transform_and_preserves_master(s):
    s.evaluate('top=dbOpenCellViewByType("L" "TOP" "layout" "maskLayout" "w") '
               'i=dbCreateInst(top cv "I0" 2:3 "MX")')
    inst = s.evaluate('j=dbCopyFig(i top list(10:20 "R90"))')
    assert inst.get_prop('master') is s.evaluate('cv')
    assert inst.get_prop('xy') == [7, 22]
    assert inst.get_prop('orient') == 'MXR90'
    assert inst.get_prop('bBox') == [[7, 22], [8, 24]]
    assert inst.get_prop('name') != 'I0'
    with pytest.raises(SkillError, match='cyclic'):
        s.evaluate('dbCopyFig(i cv)')
    assert len(s.evaluate('cv').instances) == 0


def test_cross_cell_move_and_connectivity(s):
    source = s.evaluate('cv')
    dest = s.evaluate('dest=dbOpenCellViewByType("L" "D" "layout" "maskLayout" "w")')
    fig = s.evaluate('dbMoveFig(f dest list(4:0 "R0"))')
    assert not source.shapes
    assert dest.shapes == [fig]
    s.evaluate('n=dbCreateNet(dest "VDD") pin=dbCreatePin(n f)')
    s.evaluate('dbMoveFig(f nil list(1:0 "R0"))')
    assert s.evaluate('pin~>fig') is fig
    assert fig.get_prop('net') is s.evaluate('n')
    with pytest.raises(SkillError, match='connected'):
        s.evaluate('dbMoveFig(f cv)')
    copied = s.evaluate('dbCopyFig(f cv)')
    assert copied.get_prop('net') is NIL
    assert len(s.evaluate('n~>pins')) == 1


@pytest.mark.parametrize('transform', [
    'list(0:0 "BAD")', 'list(0:0 "R0" 0)', 'list(0:0 "R0" -1)',
    'list(list(1) "R0")', 'list(0:0 "R0" "bad")', 'nil',
])
def test_invalid_transform_is_atomic(s, transform):
    fig = s.evaluate('f')
    with pytest.raises(SkillError):
        s.evaluate(f'dbMoveFig(f nil {transform})')
    assert fig.bbox == [[0, 0], [2, 1]]
    assert s.evaluate('cv').shapes == [fig]


def test_deleted_figure_and_read_only_destination_rejected(s):
    s.evaluate('dbDeleteObject(f)')
    with pytest.raises(SkillError, match='open cellView'):
        s.evaluate('dbCopyFig(f cv)')
    s.evaluate('f=dbCreateRect(cv list("met1" "drawing") list(0:0 1:1)) '
               'dbOpenCellViewByType("L" "C" "layout" "maskLayout" "r")')
    with pytest.raises(SkillError, match='read-only'):
        s.evaluate('dbMoveFig(f nil)')
