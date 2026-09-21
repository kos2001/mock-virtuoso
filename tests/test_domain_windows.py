import pytest

from mock_virtuoso.session import Session
from mock_virtuoso.skill.values import NIL, TRUE


@pytest.fixture
def session(tmp_path):
    return Session(artifact_dir=tmp_path)


def test_no_windows_initially(session):
    assert session.evaluate("hiGetWindowList()") == []
    assert session.evaluate("hiGetCurrentWindow()") is NIL


def test_open_window_appears_in_list(session):
    cv = session.evaluate(
        'dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w")')
    session.open_window(cv)
    windows = session.evaluate("hiGetWindowList()")
    assert len(windows) == 1
    assert session.evaluate("hiGetWindowName(hiGetCurrentWindow())") \
        == "LIB C layout"


def test_window_cellview_slot_is_reachable(session):
    cv = session.evaluate(
        'dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w")')
    session.open_window(cv)
    assert session.evaluate(
        "hiGetCurrentWindow()~>cellView~>viewName") == "layout"


def test_ge_get_edit_cellview_returns_current_window_cellview(session):
    cv = session.evaluate(
        'dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w")')
    session.open_window(cv)
    assert session.evaluate("geGetEditCellView()~>cellName") == "C"


def test_bridge_edit_cv_discovery_expression_finds_the_layout(session):
    # virtuoso_bridge의 _layout_get_edit_cv_expr 와 같은 모양의 식.
    cv = session.evaluate(
        'dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w")')
    session.open_window(cv)
    found = session.evaluate(
        'let((cv editCv) '
        'editCv = geGetEditCellView() '
        'cv = if(editCv && editCv~>viewName == "layout" then editCv else nil) '
        'foreach(win hiGetWindowList() '
        'when(!cv && win~>cellView && win~>cellView~>viewName == "layout" '
        'cv = dbOpenCellViewByType(win~>cellView~>libName '
        'win~>cellView~>cellName "layout" "maskLayout" "a"))) '
        'cv)')
    assert found.get_prop("cellName") == "C"


def test_selection_count_starts_at_zero(session):
    assert session.evaluate("geGetSelSetCount()") == 0


def test_select_area_selects_shapes_inside_box(session):
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w") '
        'dbCreateRect(cv list("met1" "drawing") list(list(0 0) list(1 1))) '
        'dbCreateRect(cv list("met1" "drawing") list(list(9 9) list(10 10)))')
    session.open_window(session.design.find_cellview("LIB", "C", "layout"))
    session.evaluate("geSelectArea(list(list(-1 -1) list(2 2)))")
    assert session.evaluate("geGetSelSetCount()") == 1


def test_deselect_all_clears_selection(session):
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w") '
        'dbCreateRect(cv list("met1" "drawing") list(list(0 0) list(1 1)))')
    session.open_window(session.design.find_cellview("LIB", "C", "layout"))
    session.evaluate("geSelectArea(list(list(-1 -1) list(2 2)))")
    session.evaluate("geDeselectAllFig(nil)")
    assert session.evaluate("geGetSelSetCount()") == 0


def test_le_hi_delete_removes_selected_shapes(session):
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w") '
        'dbCreateRect(cv list("met1" "drawing") list(list(0 0) list(1 1)))')
    session.open_window(session.design.find_cellview("LIB", "C", "layout"))
    session.evaluate("geSelectArea(list(list(-1 -1) list(2 2)))")
    session.evaluate("leHiDelete()")
    assert session.design.find_cellview("LIB", "C", "layout").shapes == []


def test_palette_visibility_is_tracked(session):
    session.evaluate('pteSetVisible("met1 drawing" t "Layers")')
    assert session.palette[("met1", "drawing")] is True
    session.evaluate('pteSetVisible("met1 drawing" nil "Layers")')
    assert session.palette[("met1", "drawing")] is False


def test_set_none_visible_clears_all(session):
    session.evaluate('pteSetVisible("met1 drawing" t "Layers")')
    session.evaluate('pteSetNoneVisible(?mode "All" ?panel "Layers")')
    assert all(v is False for v in session.palette.values())


def test_set_active_lpp(session):
    session.evaluate('pteSetActiveLpp("met2 drawing")')
    assert session.active_lpp == ("met2", "drawing")


def test_window_save_image_writes_a_real_file(session, tmp_path):
    cv = session.evaluate(
        'dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w")')
    session.open_window(cv)
    target = tmp_path / "shot.png"
    session.evaluate(
        f'hiWindowSaveImage(hiGetCurrentWindow() ?path "{target}" '
        f'?format "png" ?toplevel t)')
    assert target.exists()
    assert target.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_zoom_and_redraw_are_accepted(session):
    cv = session.evaluate(
        'dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w")')
    session.open_window(cv)
    assert session.evaluate("hiZoomAbsoluteScale(hiGetCurrentWindow() 0.9)") is TRUE
    assert session.evaluate("hiRedraw()") is TRUE
    assert session.evaluate("hiFlush()") is TRUE


def test_close_window_removes_it(session):
    cv = session.evaluate(
        'dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w")')
    session.open_window(cv)
    session.evaluate("hiCloseWindow(hiGetCurrentWindow())")
    assert session.evaluate("hiGetWindowList()") == []
