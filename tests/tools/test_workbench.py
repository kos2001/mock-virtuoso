"""The layout workbench's HTTP layer.

Every design action the page can trigger goes out through the real bridge API,
so these tests drive the HTTP endpoints and then read the database back to see
whether the thing the endpoint claimed to do actually happened.
"""

import importlib
import json
import re
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from mock_virtuoso.auth import Authenticator
from mock_virtuoso.server import MockVirtuosoServer
from mock_virtuoso.session import Session

app = importlib.import_module("webapp.app")


@pytest.fixture
def workbench(tmp_path, monkeypatch):
    """The workbench wired to its own mock, served on an ephemeral port."""
    from virtuoso_bridge import VirtuosoClient

    mock = MockVirtuosoServer(Session(artifact_dir=tmp_path))
    client = VirtuosoClient.local(port=mock.port)
    mock.auth = Authenticator(getattr(client, "daemon_token", None))
    mock.start()

    monkeypatch.setattr(app, "CLIENT", client)
    monkeypatch.setattr(app, "LOG", [])
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        mock.stop()


def get(base, path):
    with urllib.request.urlopen(base + path, timeout=10) as r:
        return r.status, r.read(), r.headers.get("Content-Type", "")


def post(base, path, payload=None):
    req = urllib.request.Request(
        base + path, data=json.dumps(payload or {}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def geometry(base, lib, cell):
    _, body, _ = get(base, f"/api/geometry?lib={lib}&cell={cell}")
    return json.loads(body)


# -- static -------------------------------------------------------------

def test_the_page_loads_and_pulls_in_the_shared_renderer(workbench):
    status, body, content_type = get(workbench, "/")
    assert status == 200 and content_type.startswith("text/html")
    assert b'src="/render.js"' in body, "the page must load the shared renderer"


def test_the_shared_renderer_is_served(workbench):
    status, body, content_type = get(workbench, "/render.js")
    assert status == 200
    assert "javascript" in content_type
    assert b"function draw()" in body


def test_an_unknown_path_is_a_404(workbench):
    with pytest.raises(urllib.error.HTTPError) as exc:
        get(workbench, "/api/nope")
    assert exc.value.code == 404


# -- building -----------------------------------------------------------

def test_building_a_cell_puts_real_geometry_in_the_database(workbench):
    result = post(workbench, "/api/build-cell", {"lib": "DEMO", "cell": "INV"})
    assert result["ok"] and result["ops"] > 0

    rows = geometry(workbench, "DEMO", "INV")["rows"]
    shapes = [r for r in rows if r["kind"] == "shape"]
    # Six rects, two paths, a via and two labels. Asserting the number, not
    # just "some shapes", is the point: a dropped op is the failure to catch.
    assert len(shapes) == 11
    # Every edit() batch also carries two bookkeeping commands, binding the
    # cellview and saving it, so the op count runs two ahead of the shapes.
    assert result["ops"] == len(shapes) + 2
    assert {r["layer"] for r in shapes} >= {"nwell", "diff", "poly", "met1", "met2", "text"}


def test_rebuilding_a_cell_replaces_it_rather_than_layering_on_top(workbench):
    """reset_cell loops until the cellview reports empty; this is why."""
    first = post(workbench, "/api/build-cell", {"lib": "DEMO", "cell": "INV"})
    again = post(workbench, "/api/build-cell", {"lib": "DEMO", "cell": "INV"})
    assert first["ops"] == again["ops"]

    shapes = [r for r in geometry(workbench, "DEMO", "INV")["rows"] if r["kind"] == "shape"]
    assert len(shapes) == 11, "a second build must replace the cell, not add to it"


def test_building_a_top_places_instances_and_reports_their_masters(workbench):
    post(workbench, "/api/build-cell", {"lib": "DEMO", "cell": "INV"})
    result = post(workbench, "/api/build-top",
                  {"lib": "DEMO", "top": "TOP", "child": "INV", "count": 4})
    assert result["ok"] and result["instances"] == 4

    data = geometry(workbench, "DEMO", "TOP")
    instances = [r for r in data["rows"] if r["kind"] == "instance"]
    assert [i["name"] for i in instances] == ["I0", "I1", "I2", "I3"]
    assert [i["orient"] for i in instances] == ["R0", "MY", "R0", "MY"]
    # The renderer draws instances from their master's shapes, so the reader
    # has to hand those over too.
    assert data["masters"]["DEMO/INV"], "instance masters must come back with the rows"


def test_geometry_of_a_cell_nobody_drew_is_empty_not_an_error(workbench):
    data = geometry(workbench, "DEMO", "NEVER_DRAWN")
    assert data["ok"] and data["rows"] == []


# -- SKILL passthrough and the console ----------------------------------

def test_the_skill_endpoint_runs_skill_and_reports_the_result(workbench):
    assert post(workbench, "/api/skill", {"skill": "1+2"})["output"].strip() == "3"


def test_a_failing_skill_is_reported_as_failing(workbench):
    result = post(workbench, "/api/skill", {"skill": "noSuchFn()"})
    assert result["ok"] is False
    assert any("unknown function: noSuchFn" in e for e in result["errors"])


def test_state_carries_the_console_and_the_current_design(workbench):
    post(workbench, "/api/build-cell", {"lib": "DEMO", "cell": "INV"})
    _, body, _ = get(workbench, "/api/state")
    state = json.loads(body)
    assert state["design"]["cell"] == "INV"
    assert any("saved DEMO/INV" in entry["text"] for entry in state["log"])


def test_the_console_does_not_grow_without_bound(monkeypatch):
    monkeypatch.setattr(app, "LOG", [])
    for i in range(900):
        app.log("cmd", f"line {i}")
    assert len(app.LOG) == 400
    assert app.LOG[-1]["text"] == "line 899", "the newest lines are the ones kept"


# -- selection ----------------------------------------------------------

def test_selecting_a_box_reports_what_is_inside_it(workbench):
    post(workbench, "/api/build-cell", {"lib": "DEMO", "cell": "INV"})
    result = post(workbench, "/api/select", {"bbox": [-5, -5, 30, 12]})
    assert result["ok"]
    count = int(re.search(r"(\d+)", result["output"]).group(1))
    assert count == 11, f"the box covers the whole cell, got {result['output']!r}"

    fetched = post(workbench, "/api/fetch", {"fields": ["objType", "lpp"]})
    assert fetched["ok"] and fetched["objects"], "fetch should return the selection"
    assert all("objType" in o for o in fetched["objects"])
