"""The design floor's recording layer.

The floor's claim is that its transcript is the wire: what it shows is what a
real Virtuoso would have received, because the recording happens in a proxy in
front of the daemon rather than inside it. These tests hold it to that.
"""

import importlib
import json
import socket

import pytest

from mock_virtuoso.auth import Authenticator
from mock_virtuoso.server import MockVirtuosoServer
from mock_virtuoso.session import Session

floor = importlib.import_module("floor.design_floor")


@pytest.fixture
def lane(tmp_path):
    """One mock behind one recording lane, on the unauthenticated wire."""
    mock = MockVirtuosoServer(Session(artifact_dir=tmp_path),
                              authenticator=Authenticator(None))
    mock.start()
    transcript = floor.Transcript()
    lane = floor.Lane("cells", mock.port, transcript)
    lane.start()
    try:
        yield lane, transcript, mock
    finally:
        mock.stop()


def send(port, payload):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(10)
        s.connect(("127.0.0.1", port))
        s.sendall(json.dumps(payload).encode())
        s.shutdown(socket.SHUT_WR)
        chunks = []
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
    return b"".join(chunks)


# -- the proxy is transparent -------------------------------------------

def test_a_lane_relays_the_reply_unchanged(lane):
    ln, transcript, mock = lane
    through_lane = send(ln.port, {"skill": "1+2", "timeout": 30})
    direct = send(mock.port, {"skill": "1+2", "timeout": 30})
    assert through_lane == direct == b"\x023"


def test_a_lane_relays_errors_unchanged(lane):
    ln, _, mock = lane
    assert send(ln.port, {"skill": "noSuchFn()", "timeout": 30}) \
        == send(mock.port, {"skill": "noSuchFn()", "timeout": 30})


def test_what_is_recorded_is_what_crossed_the_wire(lane):
    ln, transcript, _ = lane
    skill = 'dbOpenCellViewByType("LIB" "CELL" "layout" "maskLayout" "a")'
    send(ln.port, {"skill": skill, "timeout": 30})
    events = transcript.since(0)
    assert len(events) == 1
    assert events[0]["skill"] == skill      # verbatim, not a summary
    assert events[0]["lane"] == "cells"
    assert events[0]["ok"] is True


def test_a_failed_call_is_recorded_as_failed(lane):
    ln, transcript, _ = lane
    send(ln.port, {"skill": "noSuchFn()", "timeout": 30})
    event = transcript.since(0)[0]
    assert event["ok"] is False
    assert "unknown function: noSuchFn" in event["reply"]


def test_several_lanes_share_one_design_and_stay_distinguishable(tmp_path):
    mock = MockVirtuosoServer(Session(artifact_dir=tmp_path),
                              authenticator=Authenticator(None))
    mock.start()
    transcript = floor.Transcript()
    lanes = {}
    for name in ("cells", "top"):
        lanes[name] = floor.Lane(name, mock.port, transcript)
        lanes[name].start()
    try:
        send(lanes["cells"].port,
             {"skill": 'let((cv) cv=dbOpenCellViewByType("L" "M" "layout" "maskLayout" "a") '
                       'dbCreateRect(cv list("met1" "drawing") list(0:0 2:2)) "made")',
              "timeout": 30})
        # A different lane sees the first lane's work: one design database.
        reply = send(lanes["top"].port,
                     {"skill": 'let((cv) cv=dbOpenCellViewByType("L" "M" "layout" "maskLayout" "r") '
                               'length(cv~>shapes))', "timeout": 30})
        assert reply == b"\x021"
        assert [e["lane"] for e in transcript.since(0)] == ["cells", "top"]
    finally:
        mock.stop()


# -- the transcript ------------------------------------------------------

def test_summary_counts_per_lane():
    transcript = floor.Transcript()
    transcript.record("cells", "1+2", b"\x023", 1.0)
    transcript.record("cells", "boom()", b"\x15unknown function: boom", 2.0)
    transcript.record("top", "1+2", b"\x023", 3.0)
    lanes = transcript.summary()["lanes"]
    assert (lanes["cells"]["ops"], lanes["cells"]["errors"]) == (2, 1)
    assert (lanes["top"]["ops"], lanes["top"]["errors"]) == (1, 0)


def test_since_returns_only_what_is_new():
    transcript = floor.Transcript()
    transcript.record("cells", "1+2", b"\x023", 1.0)
    first = transcript.since(0)
    transcript.record("cells", "2+3", b"\x025", 1.0)
    assert [e["seq"] for e in first] == [1]
    assert [e["seq"] for e in transcript.since(1)] == [2]


def test_cells_are_derived_from_what_was_asked_for():
    """A cell an agent opened but failed to build still belongs in the list."""
    transcript = floor.Transcript()
    transcript.record("cells", 'dbOpenCellViewByType("STDLIB" "INV" "layout" "maskLayout" "a")',
                      b"\x15boom", 1.0)
    transcript.record("top", 'dbCreateParamInstByMasterName(cv "STDLIB" "INV" "layout" "I0" 0:0 "R0")',
                      b"\x02t", 1.0)
    cells = transcript.summary()["cells"]
    assert cells == [{"lib": "STDLIB", "cell": "INV", "lane": "cells"}]


def test_a_reply_with_no_bytes_is_not_a_success():
    transcript = floor.Transcript()
    transcript.record("cells", "1+2", b"", 1.0)
    assert transcript.since(0)[0]["ok"] is False


# -- malformed requests --------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    (b"not json at all", "unparseable request"),
    (b'["a", "list"]', "not a JSON object"),
    (b'{"timeout": 30}', "no skill string"),
])
def test_a_request_that_is_not_a_skill_call_is_described_not_crashed_on(raw, expected):
    """The transcript must survive whatever turns up on the port."""
    assert expected in floor._skill_of(raw)


def test_a_malformed_request_still_reaches_the_daemon_and_is_recorded(lane):
    ln, transcript, _ = lane
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(10)
        s.connect(("127.0.0.1", ln.port))
        s.sendall(b"not json at all")
        s.shutdown(socket.SHUT_WR)
        reply = s.recv(65536)
    assert reply.startswith(b"\x15")
    event = transcript.since(0)[0]
    assert event["ok"] is False
    assert "unparseable request" in event["skill"]
