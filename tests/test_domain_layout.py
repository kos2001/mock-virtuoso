import pytest

from mock_virtuoso.session import Session
from mock_virtuoso.skill.errors import SkillError, UnknownFunction
from mock_virtuoso.skill.values import NIL


@pytest.fixture
def session(tmp_path):
    return Session(artifact_dir=tmp_path)


def test_open_cellview_returns_an_object_handle(session):
    result = session.evaluate(
        'dbOpenCellViewByType("LIB" "CELL" "layout" "maskLayout" "w")')
    assert result.get_prop("cellName") == "CELL"


def test_create_rect_adds_a_shape(session):
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "CELL" "layout" "maskLayout" "w") '
        'dbCreateRect(cv list("met1" "drawing") '
        'list(list(0 0) list(2.5 1)))')
    cv = session.design.find_cellview("LIB", "CELL", "layout")
    assert len(cv.shapes) == 1
    shape = cv.shapes[0]
    assert shape.get_prop("objType") == "rect"
    assert shape.layer == "met1"
    assert shape.bbox == [[0.0, 0.0], [2.5, 1.0]]


def test_create_path_bbox_expands_by_half_width(session):
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w") '
        'dbCreatePath(cv list("met1" "drawing") '
        'list(list(0 0) list(4 0)) 2)')
    shape = session.design.find_cellview("LIB", "C", "layout").shapes[0]
    assert shape.get_prop("objType") == "path"
    assert shape.bbox == [[-1.0, -1.0], [5.0, 1.0]]


def test_create_polygon_keeps_points(session):
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w") '
        'dbCreatePolygon(cv list("poly" "drawing") '
        'list(list(0 0) list(1 0) list(1 1)))')
    shape = session.design.find_cellview("LIB", "C", "layout").shapes[0]
    assert shape.get_prop("objType") == "polygon"
    assert shape.get_prop("points") == [[0, 0], [1, 0], [1, 1]]


def test_create_label_keeps_text(session):
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w") '
        'dbCreateLabel(cv list("text" "drawing") list(1 2) '
        '"VDD" "centerCenter" "R0" "stick" 0.5)')
    shape = session.design.find_cellview("LIB", "C", "layout").shapes[0]
    assert shape.get_prop("objType") == "label"
    assert shape.get_prop("theLabel") == "VDD"
    assert shape.get_prop("xy") == [1, 2]


def test_create_param_inst_by_master_name(session):
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "TOP" "layout" "maskLayout" "w") '
        'dbCreateParamInstByMasterName(cv "LIB" "M" "layout" "I0" '
        'list(1 2) "R90")')
    cv = session.design.find_cellview("LIB", "TOP", "layout")
    assert len(cv.instances) == 1
    inst = cv.instances[0]
    assert inst.get_prop("name") == "I0"
    assert inst.get_prop("cellName") == "M"
    assert inst.get_prop("orient") == "R90"


def test_db_save_marks_cellview_saved(session):
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w") '
        'dbSave(cv)')
    assert session.design.find_cellview("LIB", "C", "layout").saved is True


def test_db_delete_object_removes_shape(session):
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w") '
        's = dbCreateRect(cv list("met1" "drawing") list(list(0 0) list(1 1))) '
        'dbDeleteObject(s)')
    assert session.design.find_cellview("LIB", "C", "layout").shapes == []


def test_db_transform_point(session):
    assert session.evaluate(
        'dbTransformPoint(list(1 0) list(list(0 0) "R90"))') == [0.0, 1.0]


def test_db_transform_bbox(session):
    assert session.evaluate(
        'dbTransformBBox(list(list(0 0) list(2 1)) list(list(10 20) "R0"))') \
        == [[10.0, 20.0], [12.0, 21.0]]


def test_handle_survives_across_evaluations(session):
    handle = session.evaluate(
        'dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w")').handle
    name = session.evaluate(f"{handle}~>cellName")
    assert name == "C"


def test_unknown_function_still_raises_in_session(session):
    with pytest.raises(UnknownFunction):
        session.evaluate("maeOpenSetup()")
