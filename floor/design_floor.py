"""An agent design floor: several agents designing into one mock through the bridge.

The point of this program is to make the *process* visible. One mock Virtuoso
holds the design database, the way one CIW session would. Each agent gets its own
lane — a recording proxy in front of that mock — and drives it with the real
`virtuoso-bridge` CLI. The observatory then shows, live, every SKILL expression
that crossed the wire, who sent it, what came back, and the layout as it grows.

Recording happens on the wire, not inside the mock: `mock_virtuoso` is imported
only to start the daemon, and nothing here reaches into its internals. What the
transcript shows is therefore exactly what a real Virtuoso would have received.

Run:  .venv/bin/python floor/design_floor.py       then open http://127.0.0.1:8900
"""
from __future__ import annotations

import json
import re
import socket
import tempfile
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import sys
from pathlib import Path

# Run as a script, so the repository root is not on sys.path; the shared
# toolkit lives there.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from floor.lanes import read_lanes
from toolkit.layout_reader import read_layout
from toolkit.planner import (
    PlanError,
    answer_text,
    execute,
    plan_with_hermes,
    plan_with_rules,
    validate,
)

from mock_virtuoso.bridge_compat import match_client_auth
from mock_virtuoso.server import MockVirtuosoServer
from mock_virtuoso.session import Session

from virtuoso_bridge import VirtuosoClient

HERE = Path(__file__).parent
STATIC = HERE.parent / "toolkit" / "static"
ARTIFACTS = Path(tempfile.mkdtemp(prefix="virtuoso-floor-"))
HTTP_PORT = 8900

# Lane name -> the role its agent plays on this floor.
LANES: dict[str, str] = read_lanes()

STX = 0x02
NAK = 0x15
_RECV = 65536

# The mock speaks the daemon's protocol, and the daemon is one Virtuoso session:
# it serves a single connection at a time. Lanes therefore take turns on it, the
# same way engineers sharing one CIW would.
_MOCK_LOCK = threading.Lock()


class Transcript:
    """Every SKILL expression that crossed the wire, in order, with its reply."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: list[dict] = []
        self._t0 = time.time()

    def record(self, lane: str, skill: str, reply: bytes, ms: float) -> None:
        ok = bool(reply) and reply[0] == STX
        body = reply[1:].decode("utf-8", "replace") if reply else "(no reply)"
        with self._lock:
            self._events.append({
                "seq": len(self._events) + 1,
                "t": round(time.time() - self._t0, 2),
                "lane": lane,
                "skill": skill,
                "ok": ok,
                "reply": body,
                "ms": round(ms, 1),
            })

    def since(self, seq: int) -> list[dict]:
        with self._lock:
            return self._events[seq:]

    def summary(self) -> dict:
        with self._lock:
            events = list(self._events)
        lanes = {
            name: {"role": role, "ops": 0, "errors": 0, "last": "", "ms": 0.0}
            for name, role in LANES.items()
        }
        for e in events:
            lane = lanes.setdefault(
                e["lane"], {"role": "", "ops": 0, "errors": 0, "last": "", "ms": 0.0})
            lane["ops"] += 1
            lane["errors"] += 0 if e["ok"] else 1
            lane["last"] = e["skill"][:90]
            lane["ms"] += e["ms"]
        for lane in lanes.values():
            lane["ms"] = round(lane["ms"], 1)
        return {"seq": len(events), "lanes": lanes, "cells": self._cells(events)}

    # Which cellviews the agents have been working in. Derived from the
    # transcript rather than from the mock, so it reports what was *asked for* —
    # a cell an agent opened but failed to build still shows up, which is
    # exactly the case worth seeing.
    _OPEN = re.compile(r'dbOpenCellViewByType\(\s*"([^"]+)"\s+"([^"]+)"\s+"layout"')
    _INST = re.compile(r'dbCreateParamInstByMasterName\(\s*\w+\s+"([^"]+)"\s+"([^"]+)"\s+"layout"')

    def _cells(self, events: list[dict]) -> list[dict]:
        seen: dict[tuple[str, str], str] = {}
        for e in events:
            for pattern in (self._OPEN, self._INST):
                for lib, cell in pattern.findall(e["skill"]):
                    seen.setdefault((lib, cell), e["lane"])
        return [{"lib": lib, "cell": cell, "lane": lane}
                for (lib, cell), lane in seen.items()]


class Lane:
    """A recording proxy standing where the Virtuoso daemon's port would be."""

    def __init__(self, name: str, mock_port: int, transcript: Transcript) -> None:
        self.name = name
        self._mock_port = mock_port
        self._transcript = transcript
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(("127.0.0.1", 0))
        self._socket.listen(8)
        self.port = self._socket.getsockname()[1]

    def start(self) -> None:
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self) -> None:
        while True:
            try:
                conn, _ = self._socket.accept()
            except OSError:
                return
            threading.Thread(target=self._proxy, args=(conn,), daemon=True).start()

    def _proxy(self, conn: socket.socket) -> None:
        with conn:
            conn.settimeout(60)
            try:
                request = _read_to_eof(conn)
            except OSError:
                return
            skill = _skill_of(request)
            started = time.perf_counter()
            try:
                reply = self._forward(request)
            except OSError as exc:
                reply = bytes([NAK]) + f"lane {self.name}: {exc}".encode()
            elapsed_ms = (time.perf_counter() - started) * 1000
            self._transcript.record(self.name, skill, reply, elapsed_ms)
            try:
                conn.sendall(reply)
            except OSError:
                pass

    def _forward(self, request: bytes) -> bytes:
        with _MOCK_LOCK:
            with socket.create_connection(("127.0.0.1", self._mock_port), timeout=60) as up:
                up.sendall(request)
                up.shutdown(socket.SHUT_WR)
                return _read_to_eof(up)


def _read_to_eof(sock: socket.socket) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = sock.recv(_RECV)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _skill_of(request: bytes) -> str:
    """The SKILL text inside a daemon request, or a description of why not."""
    try:
        payload = json.loads(request.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return f"<unparseable request, {len(request)} bytes>"
    if not isinstance(payload, dict):
        return "<request was not a JSON object>"
    skill = payload.get("skill")
    return skill if isinstance(skill, str) else "<request had no skill string>"


# ---------------------------------------------------------------- observatory

TRANSCRIPT = Transcript()
READER: VirtuosoClient | None = None   # reads the DB for the UI, off the lanes
REQUEST_CLIENT: VirtuosoClient | None = None   # requests build through a lane


def build_from_request(text: str) -> dict:
    """A request in words, through the planner, onto this floor's own database.

    The same pipeline the OpenAI server runs, against the same mock the lanes
    are working in — so what an agent builds and what a request builds land in
    one design, visible on one canvas.

    It goes through a lane rather than the reader's connection, so the SKILL it
    sends appears in the transcript like anyone else's. A request is a
    participant here, not a privileged side door.
    """
    started = time.time()
    plan_raw, planner = plan_with_hermes(text)
    if plan_raw is None:
        plan_raw, planner = plan_with_rules(text)

    try:
        plan = validate(plan_raw)
    except PlanError as exc:
        return {"ok": False, "planner": planner, "plan": plan_raw,
                "answer": f"Refused the {planner} plan before touching the design: {exc}\n"
                          "Nothing was executed."}

    assert REQUEST_CLIENT is not None
    try:
        report = execute(REQUEST_CLIENT, plan)
    except Exception as exc:                                   # noqa: BLE001
        return {"ok": False, "planner": planner, "plan": plan,
                "answer": f"bridge error: {type(exc).__name__}: {exc}"}

    return {"ok": True, "planner": planner, "plan": plan,
            "cells": [{"lib": plan["lib"], "cell": c} for c in report["cells"]],
            "answer": answer_text(plan, report, planner, time.time() - started)}


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload: dict, code: int = 200) -> None:
        self._raw(json.dumps(payload).encode(), "application/json", code)

    def _raw(self, body: bytes, content_type: str, code: int = 200) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args) -> None:   # the floor's own log is the UI
        return

    def do_POST(self) -> None:
        url = urlparse(self.path)
        if url.path != "/api/request":
            return self._send({"error": "not found"}, 404)
        length = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(length) or b"{}")
        text = (payload.get("text") or "").strip()
        if not text:
            return self._send({"ok": False, "answer": "Say what you want built."})
        self._send(build_from_request(text))

    def do_GET(self) -> None:
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if url.path in ("/", "/index.html"):
            return self._raw((HERE / "floor.html").read_bytes(), "text/html; charset=utf-8")
        if url.path in ("/render.js", "/about.js"):
            return self._raw((STATIC / url.path.lstrip("/")).read_bytes(),
                             "application/javascript; charset=utf-8")
        if url.path in ("/favicon.ico", "/favicon.svg"):
            return self._raw((HERE.parent / "assets" / "icon-small.svg").read_bytes(),
                             "image/svg+xml")
        if url.path == "/api/feed":
            since = int(query.get("since", ["0"])[0])
            payload = TRANSCRIPT.summary()
            payload["events"] = TRANSCRIPT.since(since)
            return self._send(payload)
        if url.path == "/api/geometry":
            return self._send(read_layout(READER, query.get("lib", ["STDLIB"])[0],
                                          query.get("cell", ["INV"])[0]))
        self._send({"error": "not found"}, 404)


def write_lane_env(lanes: dict[str, Lane], path: Path) -> None:
    """Point each bridge profile at its lane, so agents use the real CLI.

    `virtuoso-bridge eval --env <this file> -p <lane>` resolves
    VB_REMOTE_HOST_<lane>=localhost into local mode on the lane's port. The
    agents therefore run the shipped CLI unmodified; only where it dials differs.
    """
    lines = ["# generated by floor/design_floor.py — one bridge profile per agent lane"]
    for name, lane in lanes.items():
        lines += [
            f"VB_REMOTE_HOST_{name}=localhost",
            f"VB_LOCAL_PORT_{name}={lane.port}",
            f"VB_REMOTE_PORT_{name}={lane.port}",
        ]
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    global READER, REQUEST_CLIENT
    mock = MockVirtuosoServer(Session(artifact_dir=ARTIFACTS))
    READER = VirtuosoClient.local(port=mock.port)
    match_client_auth(mock, READER)
    mock.start()

    lanes = {name: Lane(name, mock.port, TRANSCRIPT) for name in LANES}
    for lane in lanes.values():
        lane.start()

    # Requests typed into the window build through their own lane, so their
    # SKILL shows up in the transcript exactly like an agent's.
    REQUEST_CLIENT = VirtuosoClient.local(port=lanes["request"].port)
    env_path = HERE / "lanes.env"
    write_lane_env(lanes, env_path)

    httpd = ThreadingHTTPServer(("127.0.0.1", HTTP_PORT), Handler)
    print(f"design floor  → http://127.0.0.1:{HTTP_PORT}")
    print(f"mock daemon   → 127.0.0.1:{mock.port}   (one design database)")
    for name, lane in lanes.items():
        print(f"  lane {name:<7} → 127.0.0.1:{lane.port}   {LANES[name]}")
    print(f"agents run: virtuoso-bridge eval --env {env_path} -p <lane> '<SKILL>'")
    threading.Timer(0.6, lambda: webbrowser.open(f"http://127.0.0.1:{HTTP_PORT}")).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        mock.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
