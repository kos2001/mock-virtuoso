"""Bridge token authentication on the mock's wire.

These exercise the daemon side of protocol v1: the capability handshake, the
MAC over each complete request, response signing, and replay rejection. The
contract tests cover the same ground from the real client's end; this module
covers the cases a well-behaved client will never produce.
"""

import json
import os
import secrets
import socket
import stat

import pytest

from mock_virtuoso.auth import (
    ALLOW_UNAUTH_ENV,
    PROTOCOL_VERSION,
    Authenticator,
    TokenUnavailable,
    load_or_create_token,
)
from mock_virtuoso.server import MockVirtuosoServer
from mock_virtuoso.session import Session

TOKEN = "a" * 64


@pytest.fixture
def authed_server(tmp_path):
    with MockVirtuosoServer(Session(artifact_dir=tmp_path),
                            authenticator=Authenticator(TOKEN)) as srv:
        yield srv


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


def hello(port, *, token=TOKEN, nonce=None, proto=PROTOCOL_VERSION):
    auth = Authenticator(token)
    nonce = nonce or secrets.token_hex(16)
    payload = {"proto": proto, "nonce": nonce, "op": "hello",
               "mac": auth.mac_hex("vb1-hello", str(proto), nonce)}
    return nonce, send(port, payload)


def run_skill(port, skill, *, token=TOKEN, nonce=None, timeout=30.0):
    auth = Authenticator(token)
    nonce = nonce or secrets.token_hex(16)
    payload = {"proto": PROTOCOL_VERSION, "nonce": nonce, "timeout": timeout,
               "skill": skill,
               "mac": auth.mac_hex("vb1-request", str(PROTOCOL_VERSION), nonce,
                                   "%.6f" % timeout, skill)}
    return nonce, send(port, payload)


def split(reply):
    """A signed reply is marker + 64 hex MAC + body."""
    return reply[:1], reply[1:65].decode("ascii"), reply[65:]


# -- handshake -----------------------------------------------------------

def test_hello_returns_signed_capabilities(authed_server):
    nonce, reply = hello(authed_server.port)
    marker, mac, body = split(reply)
    assert marker == b"\x02"
    assert mac == Authenticator(TOKEN).mac_hex("vb1-response", nonce, b"\x02", body)
    caps = json.loads(body)
    assert caps["proto"] == PROTOCOL_VERSION
    assert caps["auth"] == "on"
    assert caps["daemon"] == "ramic-bridge"
    assert caps["virtuoso_pid"] == os.getpid()


def test_hello_executes_nothing(authed_server):
    """The handshake must not be a way to run SKILL before authenticating."""
    _, reply = hello(authed_server.port)
    assert reply[:1] == b"\x02"
    assert authed_server.session.design.open_cellviews == []


def test_hello_with_a_foreign_token_is_refused(authed_server):
    _, reply = hello(authed_server.port, token="b" * 64)
    assert reply.startswith(b"\x15AuthError: bridge token mismatch")


def test_unsigned_hello_is_refused(authed_server):
    reply = send(authed_server.port, {"proto": 1, "op": "hello",
                                      "nonce": secrets.token_hex(16)})
    assert reply.startswith(b"\x15AuthError: bridge token required")


# -- execution -----------------------------------------------------------

def test_signed_request_runs_and_the_reply_is_signed(authed_server):
    nonce, reply = run_skill(authed_server.port, "1+2")
    marker, mac, body = split(reply)
    assert (marker, body) == (b"\x02", b"3")
    assert mac == Authenticator(TOKEN).mac_hex("vb1-response", nonce, b"\x02", body)


def test_error_replies_are_signed_too(authed_server):
    """A squatter must not be able to hide behind an error reply."""
    nonce, reply = run_skill(authed_server.port, "noSuchFn()")
    marker, mac, body = split(reply)
    assert marker == b"\x15"
    assert b"unknown function: noSuchFn" in body
    assert mac == Authenticator(TOKEN).mac_hex("vb1-response", nonce, b"\x15", body)


def test_unsigned_request_neither_runs_nor_is_answered_with_a_result(authed_server):
    reply = send(authed_server.port, {"skill": '1+2', "timeout": 30})
    assert reply.startswith(b"\x15AuthError: bridge token required")


def test_a_tampered_skill_is_refused(authed_server):
    """The MAC covers the whole request, so a swapped skill does not verify."""
    auth = Authenticator(TOKEN)
    nonce = secrets.token_hex(16)
    honest = '1+2'
    payload = {"proto": PROTOCOL_VERSION, "nonce": nonce, "timeout": 30.0,
               "skill": 'dbDeleteObject(nil)',   # swapped in flight
               "mac": auth.mac_hex("vb1-request", "1", nonce, "%.6f" % 30.0, honest)}
    assert send(authed_server.port, payload).startswith(
        b"\x15AuthError: bridge token mismatch")


def test_a_hello_mac_cannot_authorise_execution(authed_server):
    """Separate MAC domains: a handshake signature is not an execution one."""
    auth = Authenticator(TOKEN)
    nonce = secrets.token_hex(16)
    payload = {"proto": PROTOCOL_VERSION, "nonce": nonce, "timeout": 30.0,
               "skill": "1+2",
               "mac": auth.mac_hex("vb1-hello", "1", nonce)}
    assert send(authed_server.port, payload).startswith(
        b"\x15AuthError: bridge token mismatch")


def test_a_replayed_nonce_is_refused(authed_server):
    nonce, first = run_skill(authed_server.port, "1+2")
    assert first[:1] == b"\x02"
    _, second = run_skill(authed_server.port, "1+2", nonce=nonce)
    assert second.startswith(b"\x15AuthError: replayed request nonce")


def test_a_short_nonce_is_refused(authed_server):
    reply = send(authed_server.port, {"proto": 1, "nonce": "abcd", "timeout": 30.0,
                                      "skill": "1+2", "mac": "00" * 32})
    assert reply.startswith(b"\x15AuthError: invalid nonce")


def test_protocol_skew_is_named(authed_server):
    _, reply = hello(authed_server.port, proto=99)
    assert reply.startswith(b"\x15AuthError: protocol version mismatch")


# -- the opt-out ---------------------------------------------------------

def test_disabled_auth_says_so_and_signs_nothing(tmp_path):
    with MockVirtuosoServer(Session(artifact_dir=tmp_path),
                            authenticator=Authenticator(None)) as srv:
        reply = send(srv.port, {"proto": 1, "nonce": secrets.token_hex(16),
                                "op": "hello"})
        assert reply[:1] == b"\x02"
        assert json.loads(reply[1:])["auth"] == "off"
        assert send(srv.port, {"skill": "1+2", "timeout": 30}) == b"\x023"


# -- the token file ------------------------------------------------------

def test_the_token_file_is_created_private(tmp_path, monkeypatch):
    path = tmp_path / "nested" / "bridge_token"
    monkeypatch.setenv("RB_TOKEN_PATH", str(path))
    token = load_or_create_token()
    assert len(token) == 64 and token == token.lower()
    assert load_or_create_token() == token, "a second daemon must adopt the same secret"
    if os.name != "nt":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_an_unusable_token_file_is_fatal_unless_opted_out(tmp_path, monkeypatch):
    # A directory where the token file should be: unreadable and uncreatable.
    path = tmp_path / "token_is_a_directory"
    path.mkdir()
    monkeypatch.setenv("RB_TOKEN_PATH", str(path))

    monkeypatch.delenv(ALLOW_UNAUTH_ENV, raising=False)
    with pytest.raises(TokenUnavailable):
        load_or_create_token()

    monkeypatch.setenv(ALLOW_UNAUTH_ENV, "1")
    assert load_or_create_token() is None
