"""브릿지 빌더 -> mock 실행 -> 브릿지 reader 왕복 검증.

이 파일만 virtuoso_bridge를 import한다 (다른 어떤 mock_virtuoso 모듈도 하지 않는다).
브릿지가 설치되지 않은 환경에서는 importorskip으로 건너뛴다.
"""

from __future__ import annotations

import pytest

pytest.importorskip("virtuoso_bridge")

from virtuoso_bridge import ExecutionStatus, VirtuosoClient  # noqa: E402
from virtuoso_bridge.virtuoso.basic.composition import compose_skill_script  # noqa: E402
from virtuoso_bridge.virtuoso.layout.ops import (  # noqa: E402
    layout_bind_current_or_open_cell_view,
    layout_create_label,
    layout_create_param_inst,
    layout_create_path,
    layout_create_polygon,
    layout_create_rect,
    layout_delete_cell,
    layout_delete_selected,
    layout_fit_view,
    layout_highlight_net,
    layout_list_shapes,
    layout_read_geometry,
    layout_read_summary,
    layout_select_box,
    layout_set_active_lpp,
    layout_show_only_layers,
)
from virtuoso_bridge.virtuoso.layout.reader import parse_layout_geometry_output  # noqa: E402
from virtuoso_bridge.virtuoso.ops import open_window  # noqa: E402

from mock_virtuoso.server import MockVirtuosoServer  # noqa: E402
from mock_virtuoso.session import Session  # noqa: E402


def _run(client, *commands):
    result = client.execute_skill(compose_skill_script(list(commands)))
    assert result.status == ExecutionStatus.SUCCESS, result.errors
    return result


def _counts_by_kind(rows):
    counts: dict[str, int] = {}
    for row in rows:
        kind = "instance" if row["kind"] == "instance" else row.get("objType", row["kind"])
        counts[kind] = counts.get(kind, 0) + 1
    return counts


# -- 1. 산술 스모크 경로: 성공, 정확한 출력, 경고 없음 -----------------------


def test_arithmetic_no_warnings(bridge_client):
    client, _ = bridge_client
    result = client.execute_skill("1+2")
    assert result.status == ExecutionStatus.SUCCESS
    assert result.output == "3"
    # 경고가 있다면 \x02 접두어를 브릿지가 인식하지 못했다는 뜻이다.
    assert result.warnings == []


# -- 2. 도형 생성이 layout_read_geometry + reader를 통해 정확한 수치로 왕복 --


def test_create_rect_round_trips_through_reader(bridge_client):
    client, _ = bridge_client
    _run(client,
         layout_bind_current_or_open_cell_view("LIB", "CELL"),
         layout_create_rect("met1", "drawing", 0.0, 0.0, 2.5, 1.0))

    result = client.execute_skill(layout_read_geometry("LIB", "CELL"))
    assert result.status == ExecutionStatus.SUCCESS

    rows = parse_layout_geometry_output(result.output)
    counts = _counts_by_kind(rows)
    assert counts == {"rect": 1}

    rect = next(r for r in rows if r.get("objType") == "rect")
    assert rect["layer"] == "met1"
    assert rect["purpose"] == "drawing"
    assert rect["bbox"] == [(0.0, 0.0), (2.5, 1.0)]


def test_create_path_round_trips_through_reader(bridge_client):
    client, _ = bridge_client
    _run(client,
         layout_bind_current_or_open_cell_view("LIB", "CELL"),
         layout_create_path("met2", "drawing", [(0.0, 0.0), (4.0, 0.0)], 2.0))

    result = client.execute_skill(layout_read_geometry("LIB", "CELL"))
    rows = parse_layout_geometry_output(result.output)
    assert _counts_by_kind(rows) == {"path": 1}

    path = next(r for r in rows if r.get("objType") == "path")
    assert path["layer"] == "met2"
    assert path["points"] == [(0.0, 0.0), (4.0, 0.0)]
    # width=2.0 is only observable through the widened bbox: the points'
    # bbox expanded by half the width on every side. A mock that dropped
    # the width parameter entirely would report the unexpanded points bbox
    # [(0.0, 0.0), (4.0, 0.0)] here instead.
    assert path["bbox"] == [(-1.0, -1.0), (5.0, 1.0)]


def test_create_polygon_round_trips_through_reader(bridge_client):
    client, _ = bridge_client
    _run(client,
         layout_bind_current_or_open_cell_view("LIB", "CELL"),
         layout_create_polygon("poly", "drawing",
                                [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]))

    result = client.execute_skill(layout_read_geometry("LIB", "CELL"))
    rows = parse_layout_geometry_output(result.output)
    assert _counts_by_kind(rows) == {"polygon": 1}

    polygon = next(r for r in rows if r.get("objType") == "polygon")
    assert polygon["layer"] == "poly"
    assert polygon["purpose"] == "drawing"
    assert polygon["points"] == [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]


def test_create_label_round_trips_through_reader(bridge_client):
    client, _ = bridge_client
    _run(client,
         layout_bind_current_or_open_cell_view("LIB", "CELL"),
         layout_create_label("text", "drawing", 1.0, 2.0, "VDD",
                              "centerCenter", "R0", "stick", 0.5))

    result = client.execute_skill(layout_read_geometry("LIB", "CELL"))
    rows = parse_layout_geometry_output(result.output)
    assert _counts_by_kind(rows) == {"label": 1}

    label = next(r for r in rows if r.get("objType") == "label")
    assert label["xy"] == (1.0, 2.0)
    assert label["text"] == '"VDD"'
    # orient is reported as the raw wire token, quotes and all — do not
    # strip the quotes just to make this prettier, that would stop pinning
    # the actual wire format.
    assert label["orient"] == '"R0"'
    # height=0.5 is only observable through the half-height bbox around
    # the anchor point. A mock that dropped height would report a
    # zero-size box at the anchor instead.
    assert label["bbox"] == [(0.75, 1.75), (1.25, 2.25)]
    # justification ("centerCenter") and font ("stick") are passed to
    # layout_create_label but parse_layout_geometry_output does not expose
    # them (the reader only yields objType/layer/purpose/bbox/points/xy/
    # orient/text) — this is a limit of the reader, not an oversight here.


# -- 3. 인스턴스 bbox가 마스터를 통해 합성된다 -------------------------------


def test_instance_bbox_composes_through_master(bridge_client):
    client, _ = bridge_client
    _run(client,
         layout_bind_current_or_open_cell_view("LIB", "MASTER"),
         layout_create_rect("met1", "drawing", 0.0, 0.0, 1.0, 1.0))
    _run(client,
         layout_bind_current_or_open_cell_view("LIB", "TOP"),
         layout_create_param_inst("LIB", "MASTER", "layout", "I0",
                                   10.0, 20.0, "R0"))

    result = client.execute_skill(layout_read_geometry("LIB", "TOP"))
    rows = parse_layout_geometry_output(result.output)
    assert _counts_by_kind(rows) == {"instance": 1}

    inst = rows[0]
    assert inst["name"] == "I0"
    assert inst["lib"] == "LIB"
    assert inst["cell"] == "MASTER"
    assert inst["xy"] == (10.0, 20.0)
    assert inst["bbox"] == [(10.0, 20.0), (11.0, 21.0)]


def test_layout_delete_cell_actually_deletes_then_reports_not_found(
        bridge_client):
    """Final fix wave, finding 7: ddGetObj/ddDeleteObj must not
    accept-and-lie. layout_delete_cell's real composed SKILL does
    ddcell = ddGetObj(lib cell) then if(ddcell then ddDeleteObj(ddcell)
    "deleted..." else "ERROR: cell not found..."); a dishonest stub
    always reports "deleted" even on a second call with nothing left to
    delete."""
    client, _ = bridge_client
    _run(client,
         layout_bind_current_or_open_cell_view("LIB", "CELL"),
         layout_create_rect("met1", "drawing", 0.0, 0.0, 1.0, 1.0))

    first = client.execute_skill(layout_delete_cell("LIB", "CELL"))
    assert first.status == ExecutionStatus.SUCCESS
    assert first.output == '"deleted: LIB/CELL"'

    second = client.execute_skill(layout_delete_cell("LIB", "CELL"))
    assert second.status == ExecutionStatus.SUCCESS
    assert second.output == '"ERROR: cell not found: LIB/CELL"'


def test_open_window_through_skill_actually_opens_a_window(bridge_client):
    """Final fix wave, finding 2: geOpen was a lying stub that returned
    t without opening anything. The bridge opens windows entirely over
    SKILL via open_window()'s geOpen(?lib ... ?cell ... ?view ...
    ?viewType ... ?mode ...) call; after it succeeds,
    hiGetCurrentWindow() must be non-nil and name the right cellview."""
    client, _ = bridge_client
    result = client.execute_skill(open_window("LIB", "CELL"))
    assert result.status == ExecutionStatus.SUCCESS
    assert result.output != "nil"

    current = client.execute_skill("hiGetCurrentWindow()")
    assert current.status == ExecutionStatus.SUCCESS
    assert current.output != "nil"

    cv_name = client.execute_skill(
        "hiGetCurrentWindow()~>cellView~>cellName")
    assert cv_name.output == '"CELL"'
    lib_name = client.execute_skill(
        "hiGetCurrentWindow()~>cellView~>libName")
    assert lib_name.output == '"LIB"'


def test_two_level_instance_hierarchy_bbox_composes_through_mid_cellview(
        bridge_client):
    """Final fix wave, finding 1: a cellview whose only content is
    instances (MID) must report a real bbox, not a degenerate
    [[0,0],[0,0]] one — otherwise a TOP-level instance of it composes a
    plausible-looking but wrong bbox via dbTransformBBox(inst~>master~>bBox
    inst~>transform).

    LEAF(rect 0,0-1,1) <- MID(I0 @5,5) <- TOP(J0 @100,100)
    """
    client, _ = bridge_client
    _run(client,
         layout_bind_current_or_open_cell_view("LIB", "LEAF"),
         layout_create_rect("met1", "drawing", 0.0, 0.0, 1.0, 1.0))
    _run(client,
         layout_bind_current_or_open_cell_view("LIB", "MID"),
         layout_create_param_inst("LIB", "LEAF", "layout", "I0",
                                   5.0, 5.0, "R0"))
    _run(client,
         layout_bind_current_or_open_cell_view("LIB", "TOP"),
         layout_create_param_inst("LIB", "MID", "layout", "J0",
                                   100.0, 100.0, "R0"))

    mid_rows = parse_layout_geometry_output(
        client.execute_skill(layout_read_geometry("LIB", "MID")).output)
    mid_inst = mid_rows[0]
    assert mid_inst["bbox"] == [(5.0, 5.0), (6.0, 6.0)]

    top_rows = parse_layout_geometry_output(
        client.execute_skill(layout_read_geometry("LIB", "TOP")).output)
    top_inst = top_rows[0]
    assert top_inst["bbox"] == [(105.0, 105.0), (106.0, 106.0)]


# -- 4. db:0x... 핸들이 요청 경계를 넘어 fetch() 패턴으로 해석된다 -----------


def test_handle_resolves_across_requests(bridge_client):
    client, _ = bridge_client
    _run(client,
         layout_bind_current_or_open_cell_view("LIB", "CELL"),
         layout_create_rect("met1", "drawing", 0.0, 0.0, 1.0, 1.0))

    # 첫 요청: cv를 열고 그 핸들을 되돌려 받는다.
    first = client.execute_skill(
        'let((cv) cv = dbOpenCellViewByType("LIB" "CELL" "layout" '
        '"maskLayout" "a") cv)')
    assert first.status == ExecutionStatus.SUCCESS
    handle = first.output
    assert handle.startswith("db:0x")

    # 두 번째 요청: 첫 요청의 핸들을 소스에 그대로 이어 붙여
    # 같은 cellview를 참조하는지 확인한다 (브릿지의 fetch() 패턴).
    second = client.execute_skill(f"length({handle}~>shapes)")
    assert second.status == ExecutionStatus.SUCCESS
    assert second.output == "1"


# -- 5. 상태가 별도의 TCP 연결 사이에도 유지된다 ------------------------------


def test_state_persists_across_connections(bridge_client):
    client, session = bridge_client
    # 각 execute_skill 호출은 독립적인 TCP 연결을 새로 맺는다 (VirtuosoClient는
    # 커넥션을 재사용하지 않는다). 서로 다른 연결에 걸쳐 셀뷰 상태가
    # 유지되는지 확인한다.
    first = client.execute_skill(
        compose_skill_script([
            layout_bind_current_or_open_cell_view("LIB", "CELL"),
            layout_create_rect("met1", "drawing", 0.0, 0.0, 1.0, 1.0),
        ]))
    assert first.status == ExecutionStatus.SUCCESS

    second = client.execute_skill(layout_read_geometry("LIB", "CELL"))
    assert second.status == ExecutionStatus.SUCCESS
    rows = parse_layout_geometry_output(second.output)
    assert _counts_by_kind(rows) == {"rect": 1}

    # 세션 객체(같은 프로세스, TCP를 우회한 파이썬 레벨 확인)도 일치해야 한다.
    cv = session.design.find_cellview("LIB", "CELL", "layout")
    assert cv is not None
    assert len(cv.shapes) == 1


# -- 6. 알 수 없는 함수는 브릿지 ERROR로 드러난다 -----------------------------


def test_unknown_function_surfaces_as_bridge_error(bridge_client):
    client, _ = bridge_client
    result = client.execute_skill("noSuchFn()")
    assert result.status == ExecutionStatus.ERROR
    assert any("unknown function: noSuchFn" in e for e in result.errors)


# -- 7/8. layout_read_summary의 업스트림 버그를 있는 그대로 고정한다 ---------
#
# virtuoso-bridge-lite의 layout_read_summary가 만드는 SKILL은
#     foreach(inst cv~>instances buf = strcat(...) return(buf)))
# 로, return(buf)가 foreach 본문 "안"에 있다. 이건 우리 mock의 버그가
# 아니라 브릿지가 내보내는 SKILL 자체의 결함이며, mock은 그 SKILL을
# 충실히 실행할 뿐이다. Arcadia가 이 함수를 고치면 아래 두 단언은
# 뒤집혀야 한다.
#
# 2026-09-22: 업스트림에 리포트했다 —
#     https://github.com/Arcadia-1/virtuoso-bridge-lite/issues/158
# 그 시점의 origin/main에도 그대로 남아 있음을 확인했다.


def test_read_summary_upstream_bug_zero_instances_yields_nil(bridge_client):
    client, _ = bridge_client
    _run(client, layout_bind_current_or_open_cell_view("LIB", "CELL"))
    # 인스턴스가 0개면 foreach 본문이 한 번도 실행되지 않아 return(buf)가
    # 절대 실행되지 않는다. prog는 그러면 nil을 낸다.
    result = client.execute_skill(layout_read_summary("LIB", "CELL"))
    assert result.status == ExecutionStatus.SUCCESS
    assert result.output == "nil"


def test_read_summary_upstream_bug_truncates_after_first_instance(bridge_client):
    client, _ = bridge_client
    _run(client,
         layout_bind_current_or_open_cell_view("LIB", "MASTER"),
         layout_create_rect("met1", "drawing", 0.0, 0.0, 1.0, 1.0))
    _run(client,
         layout_bind_current_or_open_cell_view("LIB", "TOP"),
         layout_create_param_inst("LIB", "MASTER", "layout", "I0",
                                   0.0, 0.0, "R0"),
         layout_create_param_inst("LIB", "MASTER", "layout", "I1",
                                   5.0, 5.0, "R0"),
         layout_create_param_inst("LIB", "MASTER", "layout", "I2",
                                   10.0, 10.0, "R0"))

    result = client.execute_skill(layout_read_summary("LIB", "TOP"))
    assert result.status == ExecutionStatus.SUCCESS
    # 헤더는 진짜 개수(3)를 주장하지만...
    assert "0 shapes" in result.output
    assert "3 instances" in result.output
    # ...본문은 foreach의 첫 반복에서 return되어 첫 인스턴스만 나온다.
    assert "inst: I0" in result.output
    assert "inst: I1" not in result.output
    assert "inst: I2" not in result.output


# -- 편집 경로: select 후 delete가 실제로 도형 개수를 바꾼다 -----------------


def test_select_then_delete_changes_shape_count(bridge_client):
    client, session = bridge_client
    _run(client,
         layout_bind_current_or_open_cell_view("LIB", "CELL"),
         layout_create_rect("met1", "drawing", 0.0, 0.0, 1.0, 1.0))
    # layout_select_box/layout_delete_selected resolve the "current edit
    # cellview" via hiGetWindowList()/geGetEditCellView(), which requires an
    # open window. Opening a layout window is a UI action the bridge's own
    # builders never issue over SKILL (Virtuoso already has one open before
    # the daemon is driven), so we open it directly through the session, the
    # same way the unit tests under tests/test_domain_windows.py do.
    cv = session.design.find_cellview("LIB", "CELL", "layout")
    session.open_window(cv)

    before = client.execute_skill(layout_read_geometry("LIB", "CELL"))
    assert len(parse_layout_geometry_output(before.output)) == 1

    select_result = client.execute_skill(
        layout_select_box((0.0, 0.0, 1.0, 1.0)))
    assert select_result.status == ExecutionStatus.SUCCESS
    assert select_result.output.strip('"') == "selected 1 figure(s)"

    delete_result = client.execute_skill(layout_delete_selected())
    assert delete_result.status == ExecutionStatus.SUCCESS
    assert delete_result.output.strip('"') == "deleted 1 selected figure(s)"

    after = client.execute_skill(layout_read_geometry("LIB", "CELL"))
    assert parse_layout_geometry_output(after.output) == []


def test_select_box_on_instance_only_top_cell_reports_nonzero_figures(
        bridge_client):
    # geSelectArea historically only looked at cv.shapes, so a top cell
    # whose only content is placed instances (a hierarchical cell) reported
    # 0 selected figures even though a real Virtuoso selects the instances
    # as figures too. This is the bridge-level user-visible symptom.
    client, session = bridge_client
    _run(client,
         layout_bind_current_or_open_cell_view("LIB", "MASTER"),
         layout_create_rect("met1", "drawing", 0.0, 0.0, 1.0, 1.0))
    _run(client,
         layout_bind_current_or_open_cell_view("LIB", "TOP"),
         layout_create_param_inst("LIB", "MASTER", "layout", "I0",
                                   0.0, 0.0, "R0"))
    cv = session.design.find_cellview("LIB", "TOP", "layout")
    session.open_window(cv)

    select_result = client.execute_skill(
        layout_select_box((-1.0, -1.0, 2.0, 2.0)))
    assert select_result.status == ExecutionStatus.SUCCESS
    assert select_result.output.strip('"') == "selected 1 figure(s)"


# -- 그 밖의 편집 경로: 층 표시, 활성 lpp, fit view, shape 목록, 에러 경로 --
#
# 각 함수를 별도 테스트로 나눈다: 묶어두면 첫 하위 검사의 실패가 나머지를
# 가리고, 테스트 이름만으로는 무엇이 깨졌는지 알 수 없다.


def _bind_and_open_window(client, session, lib="LIB", cell="CELL"):
    _run(client,
         layout_bind_current_or_open_cell_view(lib, cell),
         layout_create_rect("met1", "drawing", 0.0, 0.0, 1.0, 1.0))
    cv = session.design.find_cellview(lib, cell, "layout")
    session.open_window(cv)
    return cv


def test_show_only_layers_updates_palette(bridge_client):
    client, session = bridge_client
    _bind_and_open_window(client, session)

    result = client.execute_skill(
        layout_show_only_layers([("met1", "drawing")]))
    assert result.status == ExecutionStatus.SUCCESS
    # The fixture yields the Session directly, so palette state is
    # observable without a bridge read-back path (there isn't one).
    assert session.palette == {("met1", "drawing"): True}


def test_set_active_lpp_updates_session_state(bridge_client):
    client, session = bridge_client
    _bind_and_open_window(client, session)

    result = client.execute_skill(layout_set_active_lpp("met2", "drawing"))
    assert result.status == ExecutionStatus.SUCCESS
    assert session.active_lpp == ("met2", "drawing")


def test_fit_view_succeeds(bridge_client):
    client, session = bridge_client
    _bind_and_open_window(client, session)

    # layout_fit_view() has no observable effect in the mock (it only
    # calls hiZoomAbsoluteScale, which the mock accepts and ignores) —
    # a status check is deliberately the whole test here, not a gap.
    result = client.execute_skill(layout_fit_view())
    assert result.status == ExecutionStatus.SUCCESS


def test_list_shapes_reports_layer(bridge_client):
    client, session = bridge_client
    _bind_and_open_window(client, session)

    result = client.execute_skill(layout_list_shapes())
    assert result.status == ExecutionStatus.SUCCESS
    assert "met1" in result.output


def test_highlight_net_not_found_error_path(bridge_client):
    client, session = bridge_client
    _bind_and_open_window(client, session)

    result = client.execute_skill(layout_highlight_net("VDD"))
    assert result.status == ExecutionStatus.SUCCESS
    assert result.output.strip('"') == "ERROR: net not found: VDD"


# -- 브릿지의 client 편의 메서드 (raw SKILL 빌더가 아니라) ------------------
#
# 위 테스트들은 전부 raw SKILL 빌더(client.execute_skill(builder(...)))를
# 구동한다. 실제 사용자는 client의 편의 메서드(open_window,
# get_current_design, list_windows, screenshot, fetch)를 직접 호출한다 --
# 이 파일이 그 경로를 하나도 구동하지 않았던 것이 세 가지 갭을 놓친 원인.


def test_client_get_current_design_after_open_window(bridge_client):
    client, _session = bridge_client
    result = client.open_window("DEMO", "INV", view="layout")
    assert result.status == ExecutionStatus.SUCCESS

    assert client.get_current_design() == ("DEMO", "INV", "layout")


def test_client_list_windows_after_open_window(bridge_client):
    client, _session = bridge_client
    result = client.open_window("DEMO", "INV", view="layout")
    assert result.status == ExecutionStatus.SUCCESS

    windows = client.list_windows()
    assert windows
    entry = windows[0]
    assert "num" in entry
    assert "name" in entry
    assert "DEMO" in entry["name"]


def test_client_screenshot_writes_a_png(bridge_client, tmp_path):
    client, _session = bridge_client
    result = client.open_window("DEMO", "INV", view="layout")
    assert result.status == ExecutionStatus.SUCCESS

    output = tmp_path / "shot.png"
    shot = client.screenshot(output=output, target="layout")
    assert shot.status == ExecutionStatus.SUCCESS
    assert output.exists()
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_client_fetch_on_selection(bridge_client):
    client, session = bridge_client
    _bind_and_open_window(client, session)

    select_result = client.execute_skill(
        layout_select_box((0.0, 0.0, 1.0, 1.0)))
    assert select_result.status == ExecutionStatus.SUCCESS

    rows = client.fetch("geGetSelSet()", ["objType", "lpp"])
    assert len(rows) == 1
    assert rows[0]["objType"] == "rect"
    assert rows[0]["lpp"] == ["met1", "drawing"]
