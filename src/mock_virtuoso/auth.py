"""Bridge token authentication, mirroring the real daemon's wire protocol v1.

Every rule here is taken from the daemon the bridge actually ships,
`virtuoso_bridge/virtuoso/basic/resources/ramic_bridge_daemon_3.py`. The mock
is only useful if a client cannot tell it apart, so this module copies that
daemon's domains, framing, error strings and fail-closed choices rather than
inventing equivalents:

* the token never crosses the wire — it lives in a 0600 file both ends read;
* requests carry HMAC over the *complete* request, so no field can be swapped
  in flight, with a separate domain for the handshake and for execution;
* responses are signed too, over the status marker and the body, so a client
  can detect a squatter on the port even on an error reply;
* request nonces are remembered and replays refused, fail-closed at capacity.

Running without a token needs an explicit `RB_ALLOW_UNAUTHENTICATED=1`, the
same opt-in name the daemon uses.
"""

from __future__ import annotations

import binascii
import errno
import hashlib
import hmac
import json
import os
import tempfile
import time

TOKEN_PATH_ENV = "RB_TOKEN_PATH"
ALLOW_UNAUTH_ENV = "RB_ALLOW_UNAUTHENTICATED"

PROTOCOL_VERSION = 1
_REQ_DOMAIN = "vb1-request"
_RESP_DOMAIN = "vb1-response"
_HELLO_DOMAIN = "vb1-hello"
_TRUTHY = ("1", "true", "yes", "on")
_HEX_DIGITS = set("0123456789abcdefABCDEF")

_NONCE_MARK_MAX = 4096


class TokenUnavailable(RuntimeError):
    """The token file cannot be read or created and auth was not opted out of."""


def allow_unauthenticated() -> bool:
    return os.environ.get(ALLOW_UNAUTH_ENV, "").strip().lower() in _TRUTHY


def token_file_path() -> str:
    override = os.environ.get(TOKEN_PATH_ENV, "").strip()
    if override:
        return override
    return os.path.join(os.path.expanduser("~"), ".virtuoso-bridge", "bridge_token")


def _is_hex_token(text: object, min_len: int, max_len: int) -> bool:
    return (isinstance(text, str) and min_len <= len(text) <= max_len
            and all(c in _HEX_DIGITS for c in text))


def _harden(path: str, *, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def load_or_create_token() -> str | None:
    """Read the shared token, creating it atomically at 0600 if absent.

    Returns None only when the file is unusable *and* the operator opted out;
    otherwise an unusable file raises, because a daemon that silently accepts
    anyone is the incident this exists to prevent.
    """
    path = token_file_path()
    try:
        with open(path, "r") as handle:
            token = handle.read().strip()
        if _is_hex_token(token, 32, 512):
            _harden(os.path.dirname(path) or ".", mode=0o700)
            _harden(path, mode=0o600)
            return token.lower()
    except OSError:
        pass

    token = binascii.hexlify(os.urandom(32)).decode("ascii")
    try:
        parent = os.path.dirname(path) or "."
        os.makedirs(parent, exist_ok=True)
        _harden(parent, mode=0o700)
        fd, tmp_path = tempfile.mkstemp(dir=parent, prefix=".bridge_token.", suffix=".tmp")
        try:
            os.fchmod(fd, 0o600)
        except (OSError, AttributeError):
            pass
        with os.fdopen(fd, "w") as handle:
            handle.write(token + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            # Link rather than rename: under a first-time creation race the
            # winner's complete file is the one that stays on disk.
            os.link(tmp_path, path)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        _harden(path, mode=0o600)
        # Adopt whatever is on disk so every racer converges on one secret.
        with open(path, "r") as handle:
            disk = handle.read().strip()
        if _is_hex_token(disk, 32, 512):
            return disk.lower()
        raise OSError(f"token file {path} holds no usable token")
    except OSError as exc:
        if allow_unauthenticated():
            return None
        raise TokenUnavailable(
            f"cannot read or create the bridge token file {path} ({exc}); "
            f"refusing to serve unauthenticated SKILL — set {ALLOW_UNAUTH_ENV}=1 "
            "to explicitly opt into insecure legacy mode") from exc


def _frame(*parts: str | bytes) -> bytes:
    """Length-prefixed canonical byte frame, as the daemon builds it."""
    out = bytearray()
    for part in parts:
        raw = part.encode("utf-8") if isinstance(part, str) else part
        out += str(len(raw)).encode("ascii") + b":" + raw
    return bytes(out)


class Authenticator:
    """Verifies requests and signs replies for one daemon's lifetime.

    With `token=None` every check passes and nothing is signed, which is the
    daemon's explicit opt-out mode, not a default.
    """

    def __init__(self, token: str | None) -> None:
        self.token = token
        self._nonce_mark: dict[str, float] = {}

    @property
    def enabled(self) -> bool:
        return self.token is not None

    def mac_hex(self, *parts: str | bytes) -> str:
        assert self.token is not None
        return hmac.new(self.token.encode("utf-8"), _frame(*parts),
                        hashlib.sha256).hexdigest()

    # -- nonce replay ----------------------------------------------------

    def _consume_nonce(self, nonce: str, ttl_seconds: float) -> str:
        """Mark *nonce* used: "ok", "replay", or "full".

        Fail-closed at capacity — live entries are never evicted, so memory
        pressure cannot be used to reopen a replay window.
        """
        now = time.time()
        expiry = self._nonce_mark.get(nonce)
        if expiry is not None and expiry > now:
            return "replay"
        if len(self._nonce_mark) >= _NONCE_MARK_MAX:
            for key in [k for k, v in self._nonce_mark.items() if v <= now]:
                del self._nonce_mark[key]
            if len(self._nonce_mark) >= _NONCE_MARK_MAX:
                return "full"
        self._nonce_mark[nonce] = now + max(900.0, 2.0 * float(ttl_seconds or 0) + 60.0)
        return "ok"

    # -- verification ----------------------------------------------------

    def error_for(self, request: dict, kind: str) -> str | None:
        """The AuthError to return for this request, or None if it is good.

        *kind* is "hello" for the capability handshake or "req" for execution;
        it selects the MAC domain, so a handshake MAC cannot be replayed as an
        execution MAC.
        """
        if not self.enabled:
            return None
        nonce = request.get("nonce")
        mac = request.get("mac")
        if not nonce or not mac:
            return ("AuthError: bridge token required - this daemon rejects "
                    "unauthenticated SKILL (client too old, or unauthorized)")
        nonce = str(nonce)
        if not _is_hex_token(nonce, 16, 128):
            return "AuthError: invalid nonce"
        try:
            proto = int(request.get("proto") or 0)
        except (TypeError, ValueError):
            return "AuthError: invalid protocol field"

        if kind == "hello":
            expected = self.mac_hex(_HELLO_DOMAIN, str(proto), nonce)
            ttl = 300.0
        else:
            try:
                timeout = float(request.get("timeout"))
            except (TypeError, ValueError):
                return "AuthError: invalid timeout field"
            skill = request.get("skill")
            if not isinstance(skill, str):
                return "AuthError: invalid skill field"
            expected = self.mac_hex(_REQ_DOMAIN, str(proto), nonce,
                                    "%.6f" % timeout, skill)
            ttl = timeout

        if not hmac.compare_digest(expected, str(mac).lower()):
            return ("AuthError: bridge token mismatch - the daemon on this port "
                    "belongs to a different user (or the token was rotated); run "
                    "`virtuoso-bridge restart` after RBStop()")

        verdict = self._consume_nonce(nonce, ttl)
        if verdict == "replay":
            return ("AuthError: replayed request nonce - rejected by server-side "
                    "replay protection")
        if verdict == "full":
            return ("AuthError: nonce cache at capacity - request rejected "
                    "(fail-closed; retry shortly)")
        if proto != PROTOCOL_VERSION:
            return "AuthError: protocol version mismatch (daemon speaks v1)"
        return None

    # -- replies ---------------------------------------------------------

    def capabilities_body(self, virtuoso_pid: int) -> bytes:
        return json.dumps({
            "proto": PROTOCOL_VERSION,
            "auth": "on" if self.enabled else "off",
            "daemon": "ramic-bridge",
            "virtuoso_pid": virtuoso_pid,
        }).encode("utf-8")

    def sign_reply(self, nonce: object, reply: bytes) -> bytes:
        """Insert the response MAC between the status marker and the body.

        The MAC covers both, so a client can tell a squatter's error reply
        from the real daemon's.
        """
        if not self.enabled or not nonce:
            return reply
        mac = self.mac_hex(_RESP_DOMAIN, str(nonce), reply[:1], reply[1:])
        return reply[:1] + mac.encode("ascii") + reply[1:]
