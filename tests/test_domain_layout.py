from pathlib import Path

import pytest

from mock_virtuoso.session import Session
from mock_virtuoso.skill.errors import SkillError, UnknownFunction
from mock_virtuoso.skill.values import NIL, TRUE


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


# -- Finding 1: malformed SKILL arguments raise SkillError, not raw
# -- Python exceptions, and the wrapper does not swallow _ProgReturn.

def test_too_few_args_raises_skill_error_naming_the_function(session):
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w")')
    with pytest.raises(SkillError) as excinfo:
        session.evaluate("dbCreateRect(cv)")
    assert "dbCreateRect" in str(excinfo.value)


def test_bad_type_raises_skill_error_naming_the_function(session):
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w")')
    with pytest.raises(SkillError) as excinfo:
        session.evaluate(
            'dbCreatePath(cv list("met1" "drawing") '
            'list(list(0 0) list(4 0)) "wide")')
    assert "dbCreatePath" in str(excinfo.value)


def test_negative_path_width_surfaces_as_skill_error(session):
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w") '
        'w = 0 - 2')
    with pytest.raises(SkillError) as excinfo:
        session.evaluate(
            'dbCreatePath(cv list("met1" "drawing") '
            'list(list(0 0) list(4 0)) w)')
    assert "dbCreatePath" in str(excinfo.value)


def test_deliberate_skill_error_passes_through_unmodified(session):
    with pytest.raises(SkillError) as excinfo:
        session.evaluate(
            'dbCreateRect("not-a-cv" list("met1" "drawing") '
            'list(list(0 0) list(1 1)))')
    assert str(excinfo.value) == "expected a cellView"


def test_prog_return_survives_the_new_wrapper(session):
    result = session.evaluate(
        'prog((cv) unless(cv return("ERROR")) return("ok"))')
    assert result == "ERROR"


# -- Finding 2: the 13 previously-untested builtins.

def test_db_open_cellview_returns_a_cellview(session):
    cv = session.evaluate(
        'dbOpenCellView("LIB" "C7" "layout" "someTech" "w")')
    assert cv.get_prop("libName") == "LIB"
    assert cv.get_prop("cellName") == "C7"
    assert cv.get_prop("viewName") == "layout"


def test_db_create_via_adds_a_via_shape(session):
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w") '
        'tf = techGetTechFile(cv) '
        'vd = techFindViaDefByName(tf "M1M2") '
        'dbCreateVia(cv vd list(3 4) "R0" nil)')
    shape = session.design.find_cellview("LIB", "C", "layout").shapes[0]
    assert shape.get_prop("objType") == "via"
    assert shape.get_prop("xy") == [3, 4]


def test_db_create_inst_with_real_master_adds_an_instance(session):
    session.evaluate(
        'master = dbOpenCellViewByType("LIB" "M" "layout" "maskLayout" "w") '
        'cv = dbOpenCellViewByType("LIB" "TOP3" "layout" "maskLayout" "w") '
        'dbCreateInst(cv master "I1" list(1 2) "R0")')
    cv = session.design.find_cellview("LIB", "TOP3", "layout")
    assert len(cv.instances) == 1
    inst = cv.instances[0]
    assert inst.get_prop("name") == "I1"
    assert inst.get_prop("cellName") == "M"


def test_db_create_inst_raises_for_a_non_cellview_master(session):
    with pytest.raises(SkillError):
        session.evaluate(
            'cv = dbOpenCellViewByType("LIB" "TOP4" "layout" "maskLayout" "w") '
            'dbCreateInst(cv "not-a-cv" "I1" list(1 2) "R0")')


def test_db_create_simple_mosaic_creates_a_grid(session):
    session.evaluate(
        'master = dbOpenCellViewByType("LIB" "M" "layout" "maskLayout" "w") '
        'cv = dbOpenCellViewByType("LIB" "TOP5" "layout" "maskLayout" "w") '
        'dbCreateSimpleMosaic(cv master "U" list(0 0) "R0" 2 3 10 5)')
    cv = session.design.find_cellview("LIB", "TOP5", "layout")
    assert len(cv.instances) == 6
    names = {inst.get_prop("name") for inst in cv.instances}
    assert len(names) == 6
    by_name = {inst.get_prop("name"): inst.get_prop("xy")
              for inst in cv.instances}
    # column pitch (5) moves x; row pitch (10) moves y.
    assert by_name["U_0_1"] == [5, 0]
    assert by_name["U_1_0"] == [0, 10]


def test_db_create_simple_mosaic_with_nil_name_uses_default_names(session):
    session.evaluate(
        'master = dbOpenCellViewByType("LIB" "M" "layout" "maskLayout" "w") '
        'cv = dbOpenCellViewByType("LIB" "TOP6" "layout" "maskLayout" "w") '
        'dbCreateSimpleMosaic(cv master nil list(0 0) "R0" 1 2 10 5)')
    cv = session.design.find_cellview("LIB", "TOP6", "layout")
    names = {inst.get_prop("name") for inst in cv.instances}
    assert names == {"M_0_0", "M_0_1"}


def test_db_close_removes_cellview_and_invalidates_handle(session):
    cv = session.evaluate(
        'dbOpenCellViewByType("LIB" "C5" "layout" "maskLayout" "w")')
    handle = cv.handle
    assert cv in session.design.open_cellviews
    session.evaluate(f"dbClose({handle})")
    assert cv not in session.design.open_cellviews
    with pytest.raises(SkillError):
        session.evaluate(f"{handle}~>cellName")


def test_db_purge_returns_true(session):
    assert session.evaluate("dbPurge()") == TRUE


def test_db_get_open_cellviews_grows_and_shrinks(session):
    assert session.evaluate("dbGetOpenCellViews()") == []
    cv = session.evaluate(
        'dbOpenCellViewByType("LIB" "C6" "layout" "maskLayout" "w")')
    assert cv in session.evaluate("dbGetOpenCellViews()")
    session.evaluate(f"dbClose({cv.handle})")
    assert cv not in session.evaluate("dbGetOpenCellViews()")


def test_db_get_cellview_dd_id_returns_the_same_object(session):
    cv = session.evaluate(
        'dbOpenCellViewByType("LIB" "C8" "layout" "maskLayout" "w")')
    result = session.evaluate(f"dbGetCellViewDdId({cv.handle})")
    assert result is cv


def test_dd_get_obj_returns_true(session):
    assert session.evaluate('ddGetObj("LIB" "CELL")') == TRUE


def test_dd_get_obj_read_path_returns_artifact_dir(session, tmp_path):
    assert session.evaluate(
        'ddGetObjReadPath("LIB" "CELL")') == str(tmp_path)


def test_dd_delete_obj_returns_true(session):
    assert session.evaluate('ddDeleteObj("LIB" "CELL")') == TRUE


def test_tech_get_tech_file_returns_true(session):
    assert session.evaluate('techGetTechFile("LIB")') == TRUE


def test_tech_find_via_def_by_name_returns_the_name(session):
    assert session.evaluate(
        'techFindViaDefByName(techGetTechFile("LIB") "M1M2")') == "M1M2"


# -- Finding 3: artifact_dir must not default to the process cwd.

def test_default_artifact_dir_is_not_cwd():
    s = Session()
    assert s.artifact_dir != Path.cwd()
