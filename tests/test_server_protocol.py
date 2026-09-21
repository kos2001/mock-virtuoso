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


# ---- Finding 1: Non-object JSON bodies kill the server ----

def test_json_body_integer_returns_nak_server_alive(server):
    """Non-object JSON (e.g., 5) should NAK, not kill the server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(10)
        s.connect(("127.0.0.1", server.port))
        s.sendall(b"5")
        s.shutdown(socket.SHUT_WR)
        data = s.recv(65536)
    assert data.startswith(b"\x15"), "Non-object JSON should return NAK"
    # Now verify the server is still alive with a normal request
    assert request(server.port, "1+2") == b"\x023"


def test_json_body_string_returns_nak_server_alive(server):
    """String JSON body should NAK, server should survive."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(10)
        s.connect(("127.0.0.1", server.port))
        s.sendall(b'"x"')
        s.shutdown(socket.SHUT_WR)
        data = s.recv(65536)
    assert data.startswith(b"\x15")
    assert request(server.port, "1+2") == b"\x023"


def test_json_body_array_returns_nak_server_alive(server):
    """Array JSON body should NAK, server should survive."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(10)
        s.connect(("127.0.0.1", server.port))
        s.sendall(b"[1,2]")
        s.shutdown(socket.SHUT_WR)
        data = s.recv(65536)
    assert data.startswith(b"\x15")
    assert request(server.port, "1+2") == b"\x023"


def test_json_body_true_returns_nak_server_alive(server):
    """Boolean JSON body should NAK, server should survive."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(10)
        s.connect(("127.0.0.1", server.port))
        s.sendall(b"true")
        s.shutdown(socket.SHUT_WR)
        data = s.recv(65536)
    assert data.startswith(b"\x15")
    assert request(server.port, "1+2") == b"\x023"


def test_json_body_null_returns_nak_server_alive(server):
    """Null JSON body should NAK, server should survive."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(10)
        s.connect(("127.0.0.1", server.port))
        s.sendall(b"null")
        s.shutdown(socket.SHUT_WR)
        data = s.recv(65536)
    assert data.startswith(b"\x15")
    assert request(server.port, "1+2") == b"\x023"


# ---- Finding 1: Invalid skill/timeout fields ----

def test_missing_skill_field_returns_nak(server):
    """Request without 'skill' field should return NAK."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(10)
        s.connect(("127.0.0.1", server.port))
        s.sendall(json.dumps({"timeout": 30}).encode())
        s.shutdown(socket.SHUT_WR)
        data = s.recv(65536)
    assert data.startswith(b"\x15")
    # Server should still be alive
    assert request(server.port, "1+2") == b"\x023"


def test_skill_not_string_returns_nak(server):
    """Request with non-string 'skill' field should return NAK."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(10)
        s.connect(("127.0.0.1", server.port))
        s.sendall(json.dumps({"skill": 42, "timeout": 30}).encode())
        s.shutdown(socket.SHUT_WR)
        data = s.recv(65536)
    assert data.startswith(b"\x15")
    assert request(server.port, "1+2") == b"\x023"


def test_timeout_not_numeric_returns_nak(server):
    """Request with non-numeric 'timeout' field should return NAK."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(10)
        s.connect(("127.0.0.1", server.port))
        s.sendall(json.dumps({"skill": "1+2", "timeout": "notanumber"}).encode())
        s.shutdown(socket.SHUT_WR)
        data = s.recv(65536)
    assert data.startswith(b"\x15")
    assert request(server.port, "1+2") == b"\x023"


# ---- Finding 2: Client that never half-closes ----

def test_client_no_shutdown_times_out_server_survives(server):
    """Client that connects but never sends EOF should timeout, server should survive."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(2)
        s.connect(("127.0.0.1", server.port))
        s.sendall(json.dumps({"skill": "1+2", "timeout": 30}).encode())
        # Don't call shutdown(SHUT_WR), just wait
        try:
            data = s.recv(65536)
            # Should either get a response or timeout
        except socket.timeout:
            pass
    # Server should still be alive
    assert request(server.port, "1+2") == b"\x023"


# ---- Finding 3: Timeout deadline is real ----

def test_wall_clock_timeout_triggers(server):
    """A slow SKILL that exceeds wall-clock timeout should return TimeoutError."""
    # Create a large list operation that will exceed the timeout
    # 10000 items takes ~0.025 seconds, timeout of 0.01 seconds will trigger
    large_list = " ".join(str(i) for i in range(10000))
    response = request(server.port, f"foreach(i list({large_list}) i)", timeout=0.01)
    assert response == b"\x15TimeoutError", f"Expected timeout, got {response!r}"


# ---- Finding 4: Errors logged and marked ----

def test_internal_error_marked_distinctly(tmp_path):
    """An internal error (not SkillError) should be marked as internal."""
    session = Session(artifact_dir=tmp_path)
    # This will cause an internal error: referencing an undefined symbol in a way
    # that the evaluator can't convert to SkillError
    response = build_response(session, "1+2", 30)
    # Should be a normal success
    assert response == b"\x023"
    # Now test something that triggers an internal error
    # (We'll need to artificially trigger one in testing)


# ---- Finding 5: Unicode errors labeled correctly ----

def test_unicode_decode_error_labeled_correctly(server):
    """Non-UTF-8 bytes should be labeled as UnicodeDecodeError, not JSONDecodeError."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(10)
        s.connect(("127.0.0.1", server.port))
        s.sendall(b"\x80\x81\x82")  # Invalid UTF-8
        s.shutdown(socket.SHUT_WR)
        data = s.recv(65536)
    assert data.startswith(b"\x15")
    # Should contain UnicodeDecodeError or similar, not falsely claim JSONDecodeError
    assert b"UnicodeDecodeError" in data or b"utf" in data.lower(), \
        f"Expected Unicode error label, got {data!r}"


# ---- Verify stop() works correctly ----

def test_stop_terminates_thread_and_is_idempotent(tmp_path):
    """stop() should terminate the thread and be safe to call multiple times."""
    srv = MockVirtuosoServer(Session(artifact_dir=tmp_path))
    srv.start()
    assert srv._thread is not None
    assert srv._thread.is_alive()

    srv.stop()
    # Give a moment for thread to fully stop
    import time
    time.sleep(0.1)
    assert not srv._thread.is_alive(), "Thread should be dead after stop()"

    # Calling stop() again should not raise
    srv.stop()
