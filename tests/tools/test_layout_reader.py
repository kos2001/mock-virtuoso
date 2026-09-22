"""The reader both frontends draw from.

It used to be a copy in each, and the copies had already drifted: one returned
a `masters` key when the read failed and the other did not, so the same JSON
endpoint had two shapes depending on which server answered.
"""

import pytest

from mock_virtuoso.bridge_compat import match_client_auth
from mock_virtuoso.bridge_compat import build_layout
from mock_virtuoso.server import MockVirtuosoServer
from mock_virtuoso.session import Session
from toolkit.layout_reader import read_layout


@pytest.fixture
def client(tmp_path):
    from virtuoso_bridge import VirtuosoClient

    mock = MockVirtuosoServer(Session(artifact_dir=tmp_path))
    bridge = VirtuosoClient.local(port=mock.port)
    match_client_auth(mock, bridge)
    mock.start()
    try:
        yield bridge
    finally:
        mock.stop()


def _draw_master(client):
    from virtuoso_bridge.virtuoso.layout import layout_create_label, layout_create_rect

    with build_layout(client, "LIB", "M") as ed:
        ed.add(layout_create_rect("met1", "drawing", 0.0, 0.0, 2.0, 2.0))
        ed.add(layout_create_label("text", "drawing", 1.0, 1.0, "A",
                                   "centerCenter", "R0", "stick", 0.3))


def test_shapes_come_back_as_plain_json_the_canvas_can_use(client):
    _draw_master(client)
    data = read_layout(client, "LIB", "M")

    assert data["ok"] and data["masters"] == {}
    rect = next(r for r in data["rows"] if r["layer"] == "met1")
    # Tuples do not survive JSON as the renderer wants them, and strings come
    # off the wire still quoted.
    assert rect["bbox"] == [[0.0, 0.0], [2.0, 2.0]]
    assert all(isinstance(p, list) for p in rect["bbox"])
    label = next(r for r in data["rows"] if r["layer"] == "text")
    assert label["text"] == "A", "the quotes belong on the wire, not in the payload"


def test_instance_masters_come_back_alongside_the_rows(client):
    from virtuoso_bridge.virtuoso.layout import layout_create_param_inst

    _draw_master(client)
    with build_layout(client, "LIB", "TOP") as ed:
        ed.add(layout_create_param_inst("LIB", "M", "layout", "I0", 0.0, 0.0, "MY"))

    data = read_layout(client, "LIB", "TOP")
    instance = next(r for r in data["rows"] if r["kind"] == "instance")
    assert (instance["name"], instance["orient"]) == ("I0", "MY")
    # The renderer draws an instance from its master's shapes, so they have to
    # arrive with it.
    assert [s["layer"] for s in data["masters"]["LIB/M"]] == ["met1", "text"]


def test_a_cell_nobody_drew_is_empty_rather_than_an_error(client):
    data = read_layout(client, "LIB", "NEVER_DRAWN")
    assert data == {"ok": True, "rows": [], "masters": {}}


def test_a_failed_read_still_has_the_keys_a_caller_indexes(client):
    """Both frontends do `data["masters"]` without checking `ok` first."""
    class _Failing:
        def execute_skill(self, skill):
            from virtuoso_bridge import ExecutionStatus
            return type("R", (), {"status": ExecutionStatus.ERROR,
                                  "errors": ["boom"], "output": ""})()

    data = read_layout(_Failing(), "LIB", "M")
    assert data["ok"] is False
    assert data["rows"] == [] and data["masters"] == {}
    assert data["errors"] == ["boom"]
