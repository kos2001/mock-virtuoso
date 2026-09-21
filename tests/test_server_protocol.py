import json
import socket

import pytest

from mock_virtuoso.server import MockVirtuosoServer, build_response
from mock_virtuoso.session import Session


@pytest.fixture
def server(tmp_path):
    with MockVirtuosoServer(Session(artifact_dir=tmp_path)) as srv:
        yield srv


def request(port, skill, timeout=30):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(10)
        s.connect(("127.0.0.1", port))
        s.sendall(json.dumps({"skill": skill, "timeout": timeout}).encode())
        s.shutdown(socket.SHUT_WR)
        chunks = []
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
    return b"".join(chunks)


def test_success_is_stx_prefixed(server):
    assert request(server.port, "1+2") == b"\x023"


def test_string_result_is_percent_L_quoted(server):
    assert request(server.port, '"hi"') == b'\x02"hi"'


def test_nil_result(server):
    assert request(server.port, "nil") == b"\x02nil"


def test_list_result_uses_percent_L(server):
    assert request(server.port, "list(1 2)") == b"\x02(1 2)"


def test_unknown_function_is_nak(server):
    response = request(server.port, "noSuchFn()")
    assert response.startswith(b"\x15")
    assert b"unknown function: noSuchFn" in response


def test_parse_error_is_nak(server):
    assert request(server.port, '"unterminated').startswith(b"\x15")


def test_malformed_json_is_nak(server):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(10)
        s.connect(("127.0.0.1", server.port))
        s.sendall(b"not json")
        s.shutdown(socket.SHUT_WR)
        data = s.recv(65536)
    assert data.startswith(b"\x15JSONDecodeError")


def test_no_trailing_record_separator(server):
    # 실제 데몬은 0x1e 를 소비하고 전달하지 않는다.
    assert b"\x1e" not in request(server.port, "1+2")


def test_state_persists_across_requests(server):
    request(server.port,
            'cv = dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w") '
            'dbCreateRect(cv list("met1" "drawing") list(list(0 0) list(1 1)))')
    response = request(
        server.port,
        'length(dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "r")~>shapes)')
    assert response == b"\x021"


def test_handle_from_one_request_works_in_the_next(server):
    handle = request(
        server.port,
        'dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w")')[1:].decode()
    assert request(server.port, f"{handle}~>cellName") == b'\x02"C"'


def test_step_budget_exceeded_reports_timeout_error(tmp_path):
    session = Session(artifact_dir=tmp_path, step_budget=10)
    response = build_response(session, "foreach(i list(1 2 3 4 5) i + 1)", 30)
    assert response.startswith(b"\x15")


def test_build_response_timeout_message_shape(tmp_path):
    session = Session(artifact_dir=tmp_path)
    # timeout=0 이면 즉시 타임아웃으로 취급한다.
    assert build_response(session, "1+2", 0) == b"\x15TimeoutError"
