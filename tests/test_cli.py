import re
import socket
import subprocess
import threading
import time
from typing import Optional

from mock_virtuoso.cli import main


def _read_line_bounded(proc: subprocess.Popen, timeout: float) -> Optional[str]:
    """Read one line from process stdout with timeout.

    Returns the line if available within timeout, None if timeout expires.
    Raises AssertionError with timeout message if the read takes too long.
    """
    result = [None]
    exception = [None]

    def read_thread():
        try:
            result[0] = proc.stdout.readline()
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=read_thread, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if exception[0]:
        raise exception[0]

    if thread.is_alive():
        # Thread is still reading; this means readline() blocked.
        # This indicates the data was not flushed.
        raise AssertionError(
            f"readline() did not return within {timeout}s — "
            "banner may not be flushed"
        )

    return result[0]


def test_eval_prints_result(capsys):
    assert main(["eval", "1+2"]) == 0
    assert capsys.readouterr().out.strip() == "3"


def test_eval_reports_unknown_function(capsys):
    assert main(["eval", "noSuchFn()"]) == 1
    assert "unknown function: noSuchFn" in capsys.readouterr().err


def test_no_command_returns_error():
    assert main([]) == 2


def test_serve_banner_flushed_when_redirected(tmp_path):
    """Verify banner appears quickly even when stdout is redirected (not a TTY)."""
    # Run serve with port 0 and capture stdout
    proc = subprocess.Popen(
        [".venv/bin/python", "-m", "mock_virtuoso.cli", "serve", "--port", "0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Read the banner with bounded timeout (fails fast if flush is missing)
    start = time.time()
    try:
        line1 = _read_line_bounded(proc, timeout=1.0)
        assert line1 is not None, "readline() returned None (unexpected EOF)"
        elapsed = time.time() - start

        # Should get the first line quickly (not waiting for EOF)
        assert elapsed < 1.0, f"Banner took {elapsed}s to appear (not flushed)"
        assert "mock-virtuoso listening on" in line1

        # Extract the port from the banner
        match = re.search(r":(\d+)$", line1.strip())
        assert match, f"Could not extract port from: {line1}"
        port = int(match.group(1))
        assert port > 0, "Port should be positive"

        # Read second line with bounded timeout
        line2 = _read_line_bounded(proc, timeout=1.0)
        assert line2 is not None, "readline() returned None on second line"
        assert "VirtuosoClient.local" in line2
        assert str(port) in line2, f"Port {port} not in second line: {line2}"

        # Verify server is actually bound on that port by connecting
        import json
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect(("127.0.0.1", port))
            # Send JSON request: {"skill": "1+2", "timeout": 30}
            request = json.dumps({"skill": "1+2", "timeout": 30}).encode("utf-8")
            s.sendall(request)
            s.shutdown(socket.SHUT_WR)  # Signal EOF
            response = s.recv(1024)
            # Should get STX + "3"
            assert response.startswith(b"\x02"), f"Expected STX response, got {response!r}"
            assert response == b"\x023", f"Expected b'\\x023', got {response!r}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def test_serve_responds_to_sigint(tmp_path):
    """Verify serve stops cleanly on SIGINT (Ctrl-C) within reasonable time."""
    # Run serve with port 0
    proc = subprocess.Popen(
        [".venv/bin/python", "-m", "mock_virtuoso.cli", "serve", "--port", "0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Wait for banner to ensure server is up (with bounded timeout)
        line1 = _read_line_bounded(proc, timeout=1.0)
        assert line1 is not None, "readline() returned None (unexpected EOF)"
        assert "mock-virtuoso listening on" in line1

        # Send SIGINT
        start = time.time()
        proc.send_signal(2)  # SIGINT
        returncode = proc.wait(timeout=2)  # Should exit in < 2 seconds
        elapsed = time.time() - start

        # Should exit cleanly with code 0 or -2 (SIGINT)
        assert returncode == 0 or returncode == -2, \
            f"Exit code {returncode} (elapsed {elapsed:.1f}s)"
        assert elapsed < 2.0, f"Did not respond to SIGINT within 2s (took {elapsed:.1f}s)"
    finally:
        # Ensure process is cleaned up
        try:
            proc.terminate()
            proc.wait(timeout=1)
        except (subprocess.TimeoutExpired, ProcessLookupError):
            try:
                proc.kill()
                proc.wait()
            except ProcessLookupError:
                pass
