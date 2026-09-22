import pytest

from mock_virtuoso.session import Session
from mock_virtuoso.skill.errors import SkillError
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


def test_ge_get_sel_set_returns_the_selected_shape_objects(session):
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w") '
        'dbCreateRect(cv list("met1" "drawing") list(list(0 0) list(1 1)))')
    session.open_window(session.design.find_cellview("LIB", "C", "layout"))
    session.evaluate("geSelectArea(list(list(-1 -1) list(2 2)))")
    selected = session.evaluate("geGetSelSet()")
    assert len(selected) == 1
    assert selected[0].get_prop("objType") == "rect"


def test_ge_add_select_box_selects_shapes_inside_the_given_box(session):
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w") '
        'dbCreateRect(cv list("met1" "drawing") list(list(0 0) list(1 1))) '
        'dbCreateRect(cv list("met1" "drawing") list(list(9 9) list(10 10)))')
    session.open_window(session.design.find_cellview("LIB", "C", "layout"))
    # 브릿지가 실제로 내보내는 형태: geAddSelectBox(nil bbox) — 첫 인자(윈도우)는
    # 무시되고 두 번째 인자가 bbox다.
    session.evaluate("geAddSelectBox(nil list(list(-1 -1) list(2 2)))")
    selected = session.evaluate("geGetSelSet()")
    assert len(selected) == 1
    assert selected[0].get_prop("bBox") == [[0.0, 0.0], [1.0, 1.0]]


def test_ge_deselect_area_leaves_only_the_other_shape_selected(session):
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w") '
        'dbCreateRect(cv list("met1" "drawing") list(list(0 0) list(1 1))) '
        'dbCreateRect(cv list("met1" "drawing") list(list(9 9) list(10 10)))')
    session.open_window(session.design.find_cellview("LIB", "C", "layout"))
    session.evaluate("geSelectArea(list(list(-1 -1) list(11 11)))")
    assert session.evaluate("geGetSelSetCount()") == 2
    session.evaluate("geDeselectArea(list(list(-1 -1) list(2 2)))")
    selected = session.evaluate("geGetSelSet()")
    assert len(selected) == 1
    assert selected[0].get_prop("bBox") == [[9.0, 9.0], [10.0, 10.0]]


def test_ge_select_all_fig_selects_every_shape_even_with_prior_selection(session):
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w") '
        'dbCreateRect(cv list("met1" "drawing") list(list(0 0) list(1 1))) '
        'dbCreateRect(cv list("met1" "drawing") list(list(9 9) list(10 10)))')
    session.open_window(session.design.find_cellview("LIB", "C", "layout"))
    session.evaluate("geSelectArea(list(list(-1 -1) list(2 2)))")
    assert session.evaluate("geGetSelSetCount()") == 1
    session.evaluate("geSelectAllFig(nil)")
    cv = session.design.find_cellview("LIB", "C", "layout")
    assert session.evaluate("geGetSelSetCount()") == len(cv.shapes) == 2


def test_hi_get_ci_window_before_and_after_open(session):
    assert session.evaluate("hiGetCIWindow()") is NIL
    cv = session.evaluate(
        'dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w")')
    session.open_window(cv)
    assert (session.evaluate("hiGetCIWindow()")
            is session.evaluate("hiGetCurrentWindow()"))


def test_hi_raise_window_makes_it_current_without_changing_window_count(session):
    cv1 = session.evaluate(
        'dbOpenCellViewByType("LIB" "C1" "layout" "maskLayout" "w")')
    w1 = session.open_window(cv1)
    cv2 = session.evaluate(
        'dbOpenCellViewByType("LIB" "C2" "layout" "maskLayout" "w")')
    session.open_window(cv2)
    assert len(session.evaluate("hiGetWindowList()")) == 2
    session.evaluate(f"hiRaiseWindow({w1.handle})")
    assert session.evaluate("hiGetCurrentWindow()") is w1
    assert len(session.evaluate("hiGetWindowList()")) == 2


def test_pte_set_all_visible_makes_every_entry_visible(session):
    session.evaluate('pteSetVisible("met1 drawing" nil "Layers")')
    session.evaluate('pteSetVisible("met2 drawing" t "Layers")')
    session.evaluate('pteSetAllVisible(?mode "All" ?panel "Layers")')
    assert session.palette[("met1", "drawing")] is True
    assert session.palette[("met2", "drawing")] is True
    assert all(v is True for v in session.palette.values())


def test_le_mark_net_no_longer_says_yes_to_everything(session):
    # 이전에는 accept-and-return-TRUE 스텁이었고, 그 얇음이 의도라고
    # 적혀 있었다. 틀린 의도였다: 브리지의 net-highlight 연산이
    # shape~>net~>name 을 읽으므로, 넷 개념이 없으면 그 연산은 구조적으로
    # 항상 "net not found" 였다 — mock 이 막으라고 존재하는 바로 그 상황.
    # 이제 넷을 찾거나 이유를 대고 거절한다. 연결성 동작은
    # tests/test_domain_connectivity.py 가 다룬다.
    with pytest.raises(SkillError):
        session.evaluate('leMarkNet(nil "net1")')
    assert session.evaluate('leHiUnmarkNet(nil "net1")') is TRUE


# --- Final fix wave: window slot must be named windowNum (finding 3) -----


def test_window_slot_is_windownum_not_windownumber(session):
    cv = session.evaluate(
        'dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w")')
    session.open_window(cv)
    assert session.evaluate("hiGetCurrentWindow()~>windowNum") == 1
    with pytest.raises(SkillError):
        session.evaluate("hiGetCurrentWindow()~>windowNumber")


# --- Final fix wave: geOpen must actually open a window (finding 2) -------


def test_ge_open_opens_a_window_over_the_named_cellview(session):
    result = session.evaluate(
        'geOpen(?lib "LIB" ?cell "CELL" ?view "layout" '
        '?viewType "maskLayout" ?mode "a")')
    assert result is not TRUE
    assert result is not NIL
    current = session.evaluate("hiGetCurrentWindow()")
    assert current is result
    assert current.get_prop("cellView").get_prop("cellName") == "CELL"
    assert current.get_prop("cellView").get_prop("libName") == "LIB"


def test_ge_open_reuses_an_already_open_matching_cellview(session):
    first = session.evaluate(
        'geOpen(?lib "LIB" ?cell "CELL" ?view "layout" '
        '?viewType "maskLayout" ?mode "a")')
    second = session.evaluate(
        'geOpen(?lib "LIB" ?cell "CELL" ?view "layout" '
        '?viewType "maskLayout" ?mode "a")')
    # Reopening the same lib/cell/view must bind to the same open
    # cellview (Design.open_cellview is idempotent by identity), not
    # fabricate a second one.
    assert first.get_prop("cellView") is second.get_prop("cellView")


# --- Final fix wave: hiCloseWindow must unregister the handle (finding 9) -


# --- Selection family must treat instances as figures too, alongside
# shapes: Cadence "figures" include instances, and a hierarchical top
# cell with only placed instances must be selectable/deletable exactly
# like a cell full of shapes.


def _place_instance(session, cv_var, inst_name, xy, lib="LIB", cell="M"):
    session.evaluate(
        f'dbCreateParamInstByMasterName({cv_var} "{lib}" "{cell}" '
        f'"layout" "{inst_name}" list({xy[0]} {xy[1]}) "R0")')


def _make_master(session, lib="LIB", cell="M"):
    session.evaluate(
        f'mcv = dbOpenCellViewByType("{lib}" "{cell}" "layout" '
        '"maskLayout" "w") '
        'dbCreateRect(mcv list("met1" "drawing") '
        'list(list(0 0) list(1 1)))')


def test_select_area_selects_instances_inside_box(session):
    _make_master(session)
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "TOP" "layout" "maskLayout" "w")')
    _place_instance(session, "cv", "I0", (0, 0))
    _place_instance(session, "cv", "I1", (100, 100))
    session.open_window(session.design.find_cellview("LIB", "TOP", "layout"))
    session.evaluate("geSelectArea(list(list(-1 -1) list(2 2)))")
    assert session.evaluate("geGetSelSetCount()") == 1


def test_select_all_fig_selects_shapes_and_instances(session):
    _make_master(session)
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "TOP" "layout" "maskLayout" "w") '
        'dbCreateRect(cv list("met1" "drawing") list(list(0 0) list(1 1))) '
        'dbCreateRect(cv list("met1" "drawing") list(list(2 2) list(3 3)))')
    _place_instance(session, "cv", "I0", (10, 10))
    _place_instance(session, "cv", "I1", (20, 20))
    _place_instance(session, "cv", "I2", (30, 30))
    session.open_window(session.design.find_cellview("LIB", "TOP", "layout"))
    session.evaluate("geSelectAllFig(nil)")
    assert session.evaluate("geGetSelSetCount()") == 5


def test_deselect_area_over_one_instance_leaves_the_other_selected(session):
    _make_master(session)
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "TOP" "layout" "maskLayout" "w")')
    _place_instance(session, "cv", "I0", (0, 0))
    _place_instance(session, "cv", "I1", (100, 100))
    session.open_window(session.design.find_cellview("LIB", "TOP", "layout"))
    session.evaluate("geSelectArea(list(list(-1 -1) list(101 101)))")
    assert session.evaluate("geGetSelSetCount()") == 2
    session.evaluate("geDeselectArea(list(list(-1 -1) list(2 2)))")
    selected = session.evaluate("geGetSelSet()")
    assert len(selected) == 1
    assert selected[0].get_prop("name") == "I1"


def test_le_hi_delete_removes_selected_instance_and_leaves_shapes(session):
    _make_master(session)
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "TOP" "layout" "maskLayout" "w") '
        'dbCreateRect(cv list("met1" "drawing") list(list(50 50) list(51 51)))')
    _place_instance(session, "cv", "I0", (0, 0))
    session.open_window(session.design.find_cellview("LIB", "TOP", "layout"))
    session.evaluate("geSelectArea(list(list(-1 -1) list(2 2)))")
    session.evaluate("leHiDelete()")
    cv = session.design.find_cellview("LIB", "TOP", "layout")
    assert cv.instances == []
    assert len(cv.shapes) == 1


def test_le_hi_delete_removes_selected_shape_and_leaves_instances(session):
    _make_master(session)
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "TOP" "layout" "maskLayout" "w") '
        'dbCreateRect(cv list("met1" "drawing") list(list(0 0) list(1 1)))')
    _place_instance(session, "cv", "I0", (100, 100))
    session.open_window(session.design.find_cellview("LIB", "TOP", "layout"))
    session.evaluate("geSelectArea(list(list(-1 -1) list(2 2)))")
    session.evaluate("leHiDelete()")
    cv = session.design.find_cellview("LIB", "TOP", "layout")
    assert cv.shapes == []
    assert len(cv.instances) == 1


def test_masterless_instance_is_skipped_not_selected_or_crashed(session):
    session.evaluate(
        'cv = dbOpenCellViewByType("LIB" "TOP" "layout" "maskLayout" "w")')
    session.evaluate(
        'dbCreateParamInstByMasterName(cv "LIB" "GONE" "layout" "I0" '
        'list(0 0) "R0")')
    # Master "GONE" was never opened/created, so the instance ends up
    # masterless (bBox NIL) -- exactly the deliberately-allowed case from
    # the earlier CellView.bbox ruling.
    session.open_window(session.design.find_cellview("LIB", "TOP", "layout"))
    # geSelectAllFig selects every figure unconditionally (no bbox test),
    # so the masterless instance is selected without crashing.
    session.evaluate("geSelectAllFig(nil)")
    assert session.evaluate("geGetSelSetCount()") == 1
    session.evaluate("geDeselectAllFig(nil)")
    # geSelectArea, however, does test bbox containment -- a masterless
    # instance has none, so it must be skipped rather than crashing or
    # being treated as at the origin.
    session.evaluate("geSelectArea(list(list(-100 -100) list(100 100)))")
    assert session.evaluate("geGetSelSetCount()") == 0


def test_close_window_unregisters_its_handle(session):
    cv = session.evaluate(
        'dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w")')
    window = session.open_window(cv)
    handle = window.handle
    session.evaluate(f"hiCloseWindow({handle})")
    with pytest.raises(SkillError):
        session.design.resolve(handle)
