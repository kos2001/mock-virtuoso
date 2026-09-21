import json
import socket

import pytest

from mock_virtuoso.server import NAK, MockVirtuosoServer, build_response
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
    # Large workload that takes ~0.5+ seconds, timeout of 0.05 seconds ensures 10x margin
    # Workload: 50000-item foreach takes ~0.5 seconds on reference machine
    import time
    large_list = " ".join(str(i) for i in range(50000))
    start = time.monotonic()
    response = request(server.port, f"foreach(i list({large_list}) i)", timeout=0.05)
    elapsed = time.monotonic() - start

    assert response == b"\x15TimeoutError", f"Expected timeout, got {response!r}"
    # Verify timeout triggered: elapsed should be ~0.05 + overhead, not 0.5 seconds
    # The margin between timeout (0.05s) and full workload (0.5s) is 10x
    assert elapsed < 0.2, f"Timeout should fire before full workload, took {elapsed:.3f}s"
    assert elapsed >= 0.04, f"Should respect the timeout deadline, took {elapsed:.3f}s"


# ---- Finding 4: Errors logged and marked ----

def test_internal_error_marked_distinctly(tmp_path, capsys):
    """An internal error (not SkillError) should be marked as internal, with traceback logged."""
    session = Session(artifact_dir=tmp_path)

    # Register a builtin that raises a non-SkillError exception (RuntimeError)
    def builtin_raise_runtime_error(interp, args, kwargs):
        raise RuntimeError("Simulated internal error")

    session.interp.register("raiseRuntimeError", builtin_raise_runtime_error)

    # Call the builtin
    response = build_response(session, "raiseRuntimeError()", 30)

    # Verify response starts with NAK
    assert response.startswith(b"\x15"), f"Expected NAK, got {response!r}"

    # Verify response contains "internal error:" prefix
    assert b"internal error:" in response, f"Expected 'internal error:' marker, got {response!r}"

    # Verify response names the exception type
    assert b"RuntimeError" in response, f"Expected exception type in response, got {response!r}"

    # Verify traceback was logged to stderr
    captured = capsys.readouterr()
    assert "RuntimeError" in captured.err, "Expected traceback in stderr"
    assert "Simulated internal error" in captured.err, "Expected error message in traceback"

    # Verify server survives - a normal request still works
    # (This is tested through the fact that we can call build_response again)
    response2 = build_response(session, "1+2", 30)
    assert response2 == b"\x023", "Server should still work after internal error"


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
    import time
    srv = MockVirtuosoServer(Session(artifact_dir=tmp_path))
    srv.start()
    assert srv._thread is not None
    assert srv._thread.is_alive()

    srv.stop()
    # Give a moment for thread to fully stop
    time.sleep(0.1)
    assert not srv._thread.is_alive(), "Thread should be dead after stop()"

    # Calling stop() again should not raise
    srv.stop()


def test_stop_unblocks_stuck_client(tmp_path):
    """stop() should unblock a client stuck in recv(), not wait for socket timeout."""
    import time
    import threading

    srv = MockVirtuosoServer(Session(artifact_dir=tmp_path))
    srv.start()

    # Open a client connection but don't send EOF or data
    client_connected = threading.Event()
    client_done = threading.Event()

    def stuck_client():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect(("127.0.0.1", srv.port))
                # Send incomplete JSON without shutdown; handler will block in recv()
                s.sendall(b'{"skill": "')
                client_connected.set()
                # Don't close or shutdown; the handler should be stuck now
                s.recv(1)  # Block here
        finally:
            client_done.set()

    thread = threading.Thread(target=stuck_client, daemon=True)
    thread.start()

    # Wait for client to connect and get stuck
    assert client_connected.wait(timeout=2), "Client should connect"
    time.sleep(0.1)  # Give handler time to block in recv()

    # Handler thread should be stuck
    assert srv._thread.is_alive(), "Handler should be stuck in recv()"

    # Call stop() - it should unblock the handler immediately
    start = time.monotonic()
    srv.stop()
    stop_time = time.monotonic() - start

    # Give thread a moment to unblock
    time.sleep(0.1)

    # Thread should be dead shortly, well before the 5-second socket timeout
    assert not srv._thread.is_alive(), "Thread should be dead shortly after stop()"
    assert stop_time < 2, f"stop() should return quickly, took {stop_time:.2f}s"


def test_stop_does_not_log_spurious_traceback(tmp_path, capfd):
    """stop() should not log a traceback when closing the in-flight connection."""
    import time
    import threading

    srv = MockVirtuosoServer(Session(artifact_dir=tmp_path))
    srv.start()

    # Open a client connection but don't send EOF
    client_connected = threading.Event()

    def stuck_client():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect(("127.0.0.1", srv.port))
                s.sendall(b'{"skill": "')
                client_connected.set()
                s.recv(1)  # Block here
        except OSError:
            pass

    thread = threading.Thread(target=stuck_client, daemon=True)
    thread.start()

    assert client_connected.wait(timeout=2)
    time.sleep(0.1)

    # Call stop() while client is stuck
    srv.stop()
    time.sleep(0.1)

    # Capture stderr output
    captured = capfd.readouterr()

    # Should NOT contain a traceback (no "Traceback" line, no "OSError")
    assert "Traceback" not in captured.err, f"Should not log traceback on shutdown, got: {captured.err!r}"
    assert "Bad file descriptor" not in captured.err, f"Should not log OSError on shutdown, got: {captured.err!r}"


def test_genuine_error_still_logs_traceback(tmp_path, capfd):
    """Genuine internal errors should still log a traceback to stderr."""
    session = Session(artifact_dir=tmp_path)

    # Register a builtin that raises RuntimeError
    def builtin_raise_runtime_error(interp, args, kwargs):
        raise RuntimeError("Genuine internal error")

    session.interp.register("raiseRuntimeError", builtin_raise_runtime_error)

    # Call build_response which will execute the builtin
    response = build_response(session, "raiseRuntimeError()", 30)

    # Verify response is NAK
    assert response.startswith(b"\x15")
    assert b"internal error:" in response

    # Capture stderr - should have traceback
    captured = capfd.readouterr()

    # SHOULD contain a traceback
    assert "Traceback" in captured.err, f"Should log traceback for genuine error, got: {captured.err!r}"
    assert "RuntimeError" in captured.err, f"Should log error type, got: {captured.err!r}"
    assert "Genuine internal error" in captured.err, f"Should log error message, got: {captured.err!r}"


def test_serve_logs_traceback_for_genuine_handle_error(tmp_path, capfd):
    """A genuine (non-shutdown) exception that escapes _handle inside _serve()
    must still be logged, and the accept loop must survive to serve the next
    client.

    This is the missing half of the round-3 pair: the existing
    test_genuine_error_still_logs_traceback calls build_response() directly,
    which has its own unconditional traceback.print_exc and never touches
    _serve()'s guarded handler at all. That test would pass unchanged even if
    _serve() suppressed all logging unconditionally. This test forces the
    error through the real _serve() handler over a live socket, so it fails
    against a `_serve()` that swallows genuine errors.
    """
    import threading

    srv = MockVirtuosoServer(Session(artifact_dir=tmp_path))
    original_handle = srv._handle
    calls = {"n": 0}
    handled_first = threading.Event()

    def flaky_handle(conn):
        calls["n"] += 1
        if calls["n"] == 1:
            handled_first.set()
            raise RuntimeError("boom from _handle")
        return original_handle(conn)

    srv._handle = flaky_handle

    with srv:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect(("127.0.0.1", srv.port))
            s.shutdown(socket.SHUT_WR)
            chunks = []
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
            data = b"".join(chunks)

        assert handled_first.wait(timeout=2)
        # _serve()'s exception handler tries to notify the client too.
        assert data.startswith(NAK)
        assert b"internal error: RuntimeError" in data

        # The accept loop must have survived the genuine error: a normal
        # request afterward still succeeds.
        assert request(srv.port, "1+2") == b"\x023"

    captured = capfd.readouterr()
    assert "Traceback" in captured.err, f"Should log traceback for genuine _serve error, got: {captured.err!r}"
    assert "RuntimeError" in captured.err
    assert "boom from _handle" in captured.err


def test_stop_wins_toctou_race_between_accept_and_recording_connection(tmp_path):
    """Force the exact race the review flagged: accept() returns a connection,
    but the thread is paused (simulating scheduler preemption) before it
    records that connection under `_conn_lock`. If stop() runs to completion
    during that window, it must still cause the freshly-accepted connection
    to be abandoned instead of handled -- otherwise the handler thread blocks
    in recv() until its own 5s socket timeout and stop()'s join() returns
    with the thread still alive.

    The interleaving is forced deterministically (not hoped for) by wrapping
    the listening socket's accept() so it pauses, after returning the real
    connection, until the test has driven stop() through its critical
    section (observed via `_stopping` becoming set).
    """
    import threading
    import time

    class _AcceptPauseWrapper:
        """Delegates to the real listening socket, but pauses inside
        accept() -- after the real accept() has already returned a
        connection -- until told to resume. This forces the scheduler
        interleaving the review described without relying on luck."""

        def __init__(self, sock, accepted_event, resume_event):
            self._sock = sock
            self._accepted = accepted_event
            self._resume = resume_event

        def accept(self):
            conn, addr = self._sock.accept()
            self._accepted.set()
            self._resume.wait(timeout=5)
            return conn, addr

        def __getattr__(self, name):
            return getattr(self._sock, name)

    srv = MockVirtuosoServer(Session(artifact_dir=tmp_path))
    accepted = threading.Event()
    resume = threading.Event()
    srv._socket = _AcceptPauseWrapper(srv._socket, accepted, resume)
    srv.start()

    stop_elapsed = {}

    def call_stop():
        start = time.monotonic()
        srv.stop()
        stop_elapsed["seconds"] = time.monotonic() - start

    # Deliberately do NOT use a `with` block / close the client here: closing
    # the client socket would itself unblock the server's recv() via EOF,
    # masking the very bug this test targets. The client stays open (and is
    # closed explicitly at the end) so the only thing that can unblock the
    # server-side handler is the fix under test.
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.settimeout(5)
        client.connect(("127.0.0.1", srv.port))
        assert accepted.wait(timeout=2), "server should have accepted the connection"

        stopper = threading.Thread(target=call_stop, daemon=True)
        stopper.start()

        # Wait for stop()'s critical section (setting _stopping, atomically
        # with checking/closing _current_conn) to have run. Since nothing
        # was recorded yet, this must NOT find/close a current connection;
        # instead _serve(), once resumed, must notice _stopping itself.
        assert srv._stopping.wait(timeout=2), "stop() should set the shutdown flag promptly"

        # Now let the paused thread proceed past accept() into the window;
        # it must abandon the connection instead of calling _handle().
        resume.set()

        stopper.join(timeout=5)

        srv._thread.join(timeout=2)
        assert not srv._thread.is_alive(), "handler thread must not survive stop() across the race window"
        assert stop_elapsed["seconds"] < 2, (
            f"stop() should return promptly (well under the 5s socket timeout), "
            f"took {stop_elapsed['seconds']:.2f}s"
        )
    finally:
        client.close()
