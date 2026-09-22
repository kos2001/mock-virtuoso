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
        'vd = techFindViaDefByName(tf "M1_M2") '
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


def test_db_purge_needs_a_cellview(session):
    """It used to answer t to dbPurge() with no argument at all."""
    with pytest.raises(SkillError):
        session.evaluate("dbPurge()")


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


# --- Final fix wave: ddGetObj/ddDeleteObj must accept-and-lie no more
# (finding 7). The mock's own honesty (Task 10) is the point of this
# project; a stub that always says a cell exists and always says a
# delete succeeded defeats that. ------------------------------------


def test_dd_get_obj_returns_nil_for_a_cell_the_design_never_opened(session):
    assert session.evaluate('ddGetObj("LIB" "CELL")') is NIL


def test_dd_get_obj_returns_truthy_for_a_cell_the_design_has_opened(session):
    session.evaluate(
        'dbOpenCellViewByType("LIB" "CELL" "layout" "maskLayout" "w")')
    result = session.evaluate('ddGetObj("LIB" "CELL")')
    assert result is not NIL


def test_dd_get_obj_still_true_after_the_cellview_is_closed(session):
    # ddGetObj asks the library manager, not the open-window state:
    # closing an editor session does not delete the cell from the
    # library.
    cv = session.evaluate(
        'dbOpenCellViewByType("LIB" "CELL" "layout" "maskLayout" "w")')
    session.evaluate(f"dbClose({cv.handle})")
    assert session.evaluate('ddGetObj("LIB" "CELL")') is not NIL


def test_dd_delete_obj_returns_nil_when_nothing_to_delete(session):
    assert session.evaluate(
        'let((ddcell) ddcell = ddGetObj("LIB" "CELL") '
        'ddDeleteObj(ddcell))') is NIL


def test_dd_delete_obj_deletes_and_returns_true_then_ddgetobj_says_nil(
        session):
    # Mirrors the bridge's actual composed usage:
    #   ddcell = ddGetObj(lib cell) if(ddcell then ddDeleteObj(ddcell) ...)
    session.evaluate(
        'dbOpenCellViewByType("LIB" "CELL" "layout" "maskLayout" "w")')
    deleted = session.evaluate(
        'let((ddcell) ddcell = ddGetObj("LIB" "CELL") '
        'ddDeleteObj(ddcell))')
    assert deleted is TRUE
    # A follow-up existence check must now honestly report gone, not
    # always-succeed.
    assert session.evaluate('ddGetObj("LIB" "CELL")') is NIL


def test_dd_get_obj_read_path_rejects_a_non_cellview_string(session, tmp_path):
    # Old (wrong) behaviour: ddGetObjReadPath ignored its argument and
    # always returned str(session.artifact_dir), regardless of what was
    # passed. That let the bridge's get_current_design() parse the mock's
    # own temp-directory path as if it were lib/cell/view, returning
    # garbage. It must now derive the path from a real cellview object
    # instead, and reject anything else -- see
    # test_dd_get_obj_read_path_splits_into_lib_cell_view below for the
    # correct-argument case.
    with pytest.raises(SkillError):
        session.evaluate('ddGetObjReadPath("LIB" "CELL")')


def test_tech_get_tech_file_returns_the_technology(session):
    """It used to return t, which satisfied the bridge and lied to everyone else.

    The bridge only uses the result as a truthy gate before handing it to
    techFindViaDefByName, so `t` passed its contract -- but an agent that
    navigated the result got a loud failure about a non-object, and nothing
    could tell which vias the technology actually had.
    """
    assert session.evaluate('techGetTechFile("LIB")~>objType') == "techFile"


def test_tech_find_via_def_by_name_needs_a_real_tech_file(session):
    with pytest.raises(SkillError, match="expected a tech file"):
        session.evaluate('techFindViaDefByName(t "M1_M2")')


# -- Finding 3: artifact_dir must not default to the process cwd.

def test_default_artifact_dir_is_not_cwd():
    s = Session()
    assert s.artifact_dir != Path.cwd()


# -- Final fix wave: cyclic instance hierarchy must be rejected at
# creation time, not blow the Python recursion stack on later ~>bBox
# reads (finding: CellView.bbox composes through instances now, so an
# accepted self/mutual master is a live RecursionError bomb on the main
# read path).


def test_self_instantiating_cellview_raises_skill_error_at_creation(
        session, capsys):
    with pytest.raises(SkillError) as exc_info:
        session.evaluate(
            'cv = dbOpenCellViewByType("L" "C" "layout" "maskLayout" "w") '
            'dbCreateParamInstByMasterName(cv "L" "C" "layout" "SELF" '
            'list(1 1) "R0")')
    message = str(exc_info.value)
    assert "cyclic" in message.lower()
    assert "L/C/layout" in message
    assert capsys.readouterr().err == ""


def test_two_cellview_cycle_raises_skill_error_at_second_creation(
        session, capsys):
    session.evaluate(
        'cvA = dbOpenCellViewByType("L" "A" "layout" "maskLayout" "w") '
        'cvB = dbOpenCellViewByType("L" "B" "layout" "maskLayout" "w") '
        'dbCreateParamInstByMasterName(cvA "L" "B" "layout" "I0" '
        'list(0 0) "R0")')
    with pytest.raises(SkillError) as exc_info:
        session.evaluate(
            'cvB = dbOpenCellViewByType("L" "B" "layout" "maskLayout" "w") '
            'dbCreateParamInstByMasterName(cvB "L" "A" "layout" "I1" '
            'list(0 0) "R0")')
    assert "cyclic" in str(exc_info.value).lower()
    assert capsys.readouterr().err == ""


def test_cellview_still_usable_after_cycle_rejected(session, capsys):
    session.evaluate(
        'cv = dbOpenCellViewByType("L" "C2" "layout" "maskLayout" "w") '
        'dbCreateRect(cv list("met1" "drawing") '
        'list(list(0 0) list(1 1)))')
    with pytest.raises(SkillError):
        session.evaluate(
            # "a", not "w": the point is that a rejected instance leaves the
            # existing geometry intact, and "w" would legitimately clear it.
            'cv = dbOpenCellViewByType("L" "C2" "layout" "maskLayout" "a") '
            'dbCreateParamInstByMasterName(cv "L" "C2" "layout" "SELF" '
            'list(1 1) "R0")')
    cv = session.design.find_cellview("L", "C2", "layout")
    assert cv.bbox == [[0.0, 0.0], [1.0, 1.0]]
    # A read-geometry-style ~>bBox traversal must still work fine.
    assert cv.get_prop("bBox") == [[0.0, 0.0], [1.0, 1.0]]
    assert capsys.readouterr().err == ""


def test_deep_acyclic_hierarchy_still_composes(session, capsys):
    session.evaluate(
        'leaf = dbOpenCellViewByType("L" "LEAF2" "layout" "maskLayout" "w") '
        'dbCreateRect(leaf list("met1" "drawing") '
        'list(list(0 0) list(1 1))) '
        'mid = dbOpenCellViewByType("L" "MID2" "layout" "maskLayout" "w") '
        'dbCreateParamInstByMasterName(mid "L" "LEAF2" "layout" "I0" '
        'list(5 5) "R0") '
        'top = dbOpenCellViewByType("L" "TOP2" "layout" "maskLayout" "w") '
        'dbCreateParamInstByMasterName(top "L" "MID2" "layout" "J0" '
        'list(100 100) "R0")')
    top = session.design.find_cellview("L", "TOP2", "layout")
    assert top.bbox == [[105.0, 105.0], [106.0, 106.0]]
    assert capsys.readouterr().err == ""


def test_dd_get_obj_read_path_splits_into_lib_cell_view(session):
    # Mirrors virtuoso_bridge's own get_current_design() parsing so this
    # test would fail if the two ever drift apart:
    #   parts = output.split("/"); parts[-4], parts[-3], parts[-2]
    path = session.evaluate(
        'cv = dbOpenCellViewByType("DEMO" "INV" "layout" "maskLayout" "w") '
        'ddGetObjReadPath(dbGetCellViewDdId(cv))')
    assert isinstance(path, str)
    parts = path.split("/")
    assert len(parts) >= 4
    assert (parts[-4], parts[-3], parts[-2]) == ("DEMO", "INV", "layout")


def test_dd_get_obj_read_path_rejects_non_cellview(session):
    with pytest.raises(SkillError):
        session.evaluate('ddGetObjReadPath("not a cellview")')


# ---- The technology: via definitions are real, or they are refused -------

def test_the_tech_file_is_an_object_with_via_definitions(session):
    names = session.evaluate(
        'mapcar(lambda((vd) vd~>name) techGetTechFile(nil)~>viaDefs)')
    assert set(names) == {"DIFF_M1", "PO_M1", "M1_M2", "M2_M3"}


def test_a_known_via_definition_resolves(session):
    assert session.evaluate(
        'techFindViaDefByName(techGetTechFile(nil) "M1_M2")~>name') == "M1_M2"


def test_an_unknown_via_definition_is_nil(session):
    """Virtuoso answers nil for a via def the technology does not have."""
    assert session.evaluate(
        'techFindViaDefByName(techGetTechFile(nil) "NO_SUCH_VIA")') is NIL


def test_a_via_records_the_definition_it_was_made_from(session):
    session.evaluate(
        'let((cv) cv = dbOpenCellViewByType("L" "C" "layout" "maskLayout" "a") '
        'dbCreateVia(cv techFindViaDefByName(techGetTechFile(cv) "M1_M2") 0:0 "R0"))')
    assert session.evaluate(
        'let((cv) cv = dbOpenCellViewByType("L" "C" "layout" "maskLayout" "r") '
        'car(cv~>shapes)~>viaDef~>name)') == "M1_M2"


def test_a_via_from_a_definition_that_does_not_exist_is_refused(session):
    """The whole point: an invented via master must not quietly become a shape.

    techFindViaDefByName returns nil for it, and dbCreateVia has to say so
    rather than draw something that references a master the technology lacks.
    """
    with pytest.raises(SkillError, match="via definition"):
        session.evaluate(
            'let((cv) cv = dbOpenCellViewByType("L" "C" "layout" "maskLayout" "a") '
            'dbCreateVia(cv techFindViaDefByName(techGetTechFile(cv) "INVENTED") 0:0 "R0"))')


def test_a_bare_string_is_not_a_via_definition(session):
    with pytest.raises(SkillError, match="via definition"):
        session.evaluate(
            'let((cv) cv = dbOpenCellViewByType("L" "C" "layout" "maskLayout" "a") '
            'dbCreateVia(cv "M1_M2" 0:0 "R0"))')


# ---- Stubs that used to claim success -----------------------------------

def test_csh_refuses_rather_than_claiming_the_command_ran(session):
    """The mock must not run shell commands -- and must not pretend it did.

    `client.run_shell_command()` sends csh(...) and reads `t` as success, so a
    stub returning t reported every shell command as having succeeded. Not
    running it is right; saying it worked is the failure this mock exists to
    prevent.
    """
    with pytest.raises(SkillError, match="does not run shell commands"):
        session.evaluate('csh("streamOut -library LIB -topCell C")')


def test_db_purge_releases_the_cellview(session):
    """dbPurge forces a cellview out of memory; the handle dies with it."""
    handle = session.evaluate(
        'let((cv) cv = dbOpenCellViewByType("L" "C" "layout" "maskLayout" "a") '
        'dbCreateRect(cv list("met1" "drawing") list(0:0 2:2)) '
        'dbSave(cv) cv)').handle
    assert session.evaluate('dbPurge(%s)' % handle) is TRUE
    with pytest.raises(SkillError, match="stale or unknown object handle"):
        session.evaluate(f'{handle}~>shapes')


def test_db_purge_does_not_delete_the_cell(session):
    """Purging is a memory operation, not a delete: reopening finds the cell."""
    session.evaluate(
        'let((cv) cv = dbOpenCellViewByType("L" "C" "layout" "maskLayout" "a") '
        'dbCreateRect(cv list("met1" "drawing") list(0:0 2:2)) '
        'dbSave(cv) dbPurge(cv))')
    assert session.evaluate(
        'let((cv) cv = dbOpenCellViewByType("L" "C" "layout" "maskLayout" "r") '
        'length(cv~>shapes))') == 1


def test_a_refused_via_says_which_definitions_exist(session):
    """Loud is not enough; a refusal should say what would have worked."""
    with pytest.raises(SkillError) as excinfo:
        session.evaluate(
            'let((cv) cv = dbOpenCellViewByType("L" "C" "layout" "maskLayout" "a") '
            'dbCreateVia(cv techFindViaDefByName(techGetTechFile(cv) "M1M2") 0:0 "R0"))')
    message = str(excinfo.value)
    assert "M1_M2" in message and "M2_M3" in message
    assert "DIFF_M1" in message and "PO_M1" in message


# ---- Malformed arguments name the argument, not Python's stack -----------

def test_a_label_at_a_non_point_says_what_a_point_is(session):
    """A Python TypeError leaking through tells an agent nothing.

    An agent that passed a string where the point goes got
    "unsupported operand type(s) for -: 'str' and 'float'", which names
    neither the argument nor what it should have been.
    """
    session.evaluate('cv = dbOpenCellViewByType("L" "C" "layout" "maskLayout" "a")')
    with pytest.raises(SkillError) as excinfo:
        session.evaluate('dbCreateLabel(cv list("text" "drawing") "2.0" "A" '
                         '"centerCenter" "R0" "stick" 0.5)')
    message = str(excinfo.value)
    # A deliberate SkillError passes through unmodified here, by convention, so
    # the message has to carry its own meaning rather than lean on a prefix.
    assert "point" in message and "list(x y)" in message
    assert "operand" not in message, "Python's own wording should not reach the wire"


def test_a_label_height_that_is_not_a_number_says_so(session):
    session.evaluate('cv = dbOpenCellViewByType("L" "C" "layout" "maskLayout" "a")')
    with pytest.raises(SkillError, match="height"):
        session.evaluate('dbCreateLabel(cv list("text" "drawing") list(1 2) "A" '
                         '"centerCenter" "R0" "stick" "tall")')


def test_a_point_with_one_coordinate_is_refused(session):
    session.evaluate('cv = dbOpenCellViewByType("L" "C" "layout" "maskLayout" "a")')
    with pytest.raises(SkillError, match="point"):
        session.evaluate('dbCreateLabel(cv list("text" "drawing") list(1) "A" '
                         '"centerCenter" "R0" "stick" 0.5)')


def test_a_via_at_a_non_point_says_what_a_point_is(session):
    session.evaluate('cv = dbOpenCellViewByType("L" "C" "layout" "maskLayout" "a")')
    with pytest.raises(SkillError, match="point"):
        session.evaluate('dbCreateVia(cv techFindViaDefByName(techGetTechFile(cv) "M1_M2") '
                         '"nope" "R0")')


def test_a_good_label_still_works(session):
    session.evaluate(
        'cv = dbOpenCellViewByType("L" "C" "layout" "maskLayout" "a") '
        'dbCreateLabel(cv list("text" "drawing") list(1 2) "A" '
        '"centerCenter" "R0" "stick" 0.5)')
    shape = session.design.find_cellview("L", "C", "layout").shapes[0]
    assert shape.get_prop("theLabel") == "A"
    assert shape.bbox == [[0.75, 1.75], [1.25, 2.25]]
