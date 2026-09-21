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


# -- 그 밖의 편집 경로: 층 표시, 활성 lpp, fit view, shape 목록, 에러 경로 --


def test_additional_editing_paths(bridge_client):
    client, session = bridge_client
    _run(client,
         layout_bind_current_or_open_cell_view("LIB", "CELL"),
         layout_create_rect("met1", "drawing", 0.0, 0.0, 1.0, 1.0))
    cv = session.design.find_cellview("LIB", "CELL", "layout")
    session.open_window(cv)

    show_layers = client.execute_skill(
        layout_show_only_layers([("met1", "drawing")]))
    assert show_layers.status == ExecutionStatus.SUCCESS

    set_lpp = client.execute_skill(layout_set_active_lpp("met1", "drawing"))
    assert set_lpp.status == ExecutionStatus.SUCCESS

    fit_view = client.execute_skill(layout_fit_view())
    assert fit_view.status == ExecutionStatus.SUCCESS

    list_shapes = client.execute_skill(layout_list_shapes())
    assert list_shapes.status == ExecutionStatus.SUCCESS
    assert "met1" in list_shapes.output

    net_error = client.execute_skill(layout_highlight_net("VDD"))
    assert net_error.status == ExecutionStatus.SUCCESS
    assert net_error.output.strip('"') == "ERROR: net not found: VDD"
