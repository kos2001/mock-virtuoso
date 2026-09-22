"""Virtuoso-style layout workbench, served over HTTP, driven by the real bridge API.

Nothing here reaches into mock_virtuoso's internals. Every design action goes out
through `virtuoso_bridge.VirtuosoClient` over TCP — the same calls you would make
against a licensed Cadence Virtuoso. The mock is simply what is listening.

Run:  .venv/bin/python webapp/app.py    then open http://127.0.0.1:8808
Stdlib only; the bridge must be installed (see README).
"""
from __future__ import annotations

import json
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from mock_virtuoso.server import MockVirtuosoServer
from mock_virtuoso.session import Session

from virtuoso_bridge import ExecutionStatus, VirtuosoClient
from virtuoso_bridge.virtuoso.layout import (
    layout_create_label,
    layout_create_param_inst,
    layout_create_path,
    layout_create_rect,
    layout_create_via_by_name,
    layout_read_geometry,
    layout_select_box,
    parse_layout_geometry_output,
)

HERE = Path(__file__).parent
ARTIFACTS = Path(tempfile.mkdtemp(prefix="virtuoso-workbench-"))

# module-level session handles, set in main()
CLIENT: VirtuosoClient | None = None
LOG: list[dict] = []


def log(kind: str, text: str, detail: str = "") -> None:
    LOG.append({"kind": kind, "text": text, "detail": detail})
    del LOG[:-400]


def run_skill(skill: str, label: str = "") -> dict:
    """Execute SKILL through the bridge and record it for the console."""
    assert CLIENT is not None
    res = CLIENT.execute_skill(skill)
    ok = res.status is ExecutionStatus.SUCCESS
    log("cmd", label or skill[:110])
    log("ok" if ok else "err", (res.output or "").strip() if ok else "; ".join(res.errors))
    return {"ok": ok, "output": res.output, "errors": res.errors}


# ---------------------------------------------------------------- design ops

DEMO_CELLS = {
    "INV": [
        ("nwell", -1.0, -1.0, 5.0, 7.0),
        ("poly", 1.5, 0.0, 2.5, 6.0),
        ("diff", 0.0, 3.5, 4.0, 6.0),
        ("diff", 0.0, 0.0, 4.0, 2.5),
        ("met1", 0.2, 4.0, 3.8, 4.6),
        ("met1", 0.2, 1.2, 3.8, 1.8),
    ],
}


def reset_cell(lib: str, cell: str) -> None:
    """Empty a cellview through the bridge, the way a tool's File>New would.

    `foreach` walks the live list, so a single pass can skip entries while
    dbDeleteObject removes them; loop until the cellview reports empty.
    """
    assert CLIENT is not None
    skill = (
        f'let((cv) cv = dbOpenCellViewByType("{lib}" "{cell}" "layout" "maskLayout" "a") '
        'foreach(s cv~>shapes dbDeleteObject(s)) '
        'foreach(i cv~>instances dbDeleteObject(i)) '
        'length(cv~>shapes) + length(cv~>instances))'
    )
    for _ in range(12):
        r = CLIENT.execute_skill(skill)
        if r.status is not ExecutionStatus.SUCCESS or (r.output or "").strip() == "0":
            break


def build_demo(lib: str, cell: str) -> dict:
    """Build a small standard-cell-ish layout using the bridge's own builders."""
    assert CLIENT is not None
    reset_cell(lib, cell)
    with CLIENT.layout.edit(lib, cell) as ed:
        for layer, x0, y0, x1, y1 in DEMO_CELLS["INV"]:
            ed.add(layout_create_rect(layer, "drawing", x0, y0, x1, y1))
        ed.add(layout_create_path("met1", "drawing", [(2.0, 6.0), (2.0, 8.0)], 0.4))
        ed.add(layout_create_path("met2", "drawing", [(4.0, 3.0), (7.0, 3.0)], 0.5))
        ed.add(layout_create_via_by_name("M1_M2", 4.0, 3.0))
        ed.add(layout_create_label("text", "drawing", 2.0, 8.3, "IN",
                                   "centerCenter", "R0", "stick", 0.45))
        ed.add(layout_create_label("text", "drawing", 7.0, 3.0, "OUT",
                                   "centerCenter", "R0", "stick", 0.45))
    log("cmd", f"client.layout.edit({lib}, {cell}) — {len(ed.commands)} ops, one round trip")
    log("ok", f"saved {lib}/{cell}/layout")
    CLIENT.open_window(lib, cell, view="layout")
    return {"ok": True, "ops": len(ed.commands)}


def build_top(lib: str, top: str, child: str, count: int) -> dict:
    assert CLIENT is not None
    reset_cell(lib, top)
    with CLIENT.layout.edit(lib, top) as ed:
        for i in range(count):
            orient = "R0" if i % 2 == 0 else "MY"
            ed.add(layout_create_param_inst(lib, child, "layout", f"I{i}",
                                            i * 9.0, 0.0, orient))
    log("cmd", f"client.layout.edit({lib}, {top}) — {count} instances placed")
    log("ok", f"saved {lib}/{top}/layout")
    CLIENT.open_window(lib, top, view="layout")
    return {"ok": True, "instances": count}


def geometry(lib: str, cell: str) -> dict:
    assert CLIENT is not None
    res = CLIENT.execute_skill(layout_read_geometry(lib, cell))
    if res.status is not ExecutionStatus.SUCCESS:
        return {"ok": False, "errors": res.errors, "rows": []}
    rows = parse_layout_geometry_output(res.output or "")
    out = []
    for r in rows:
        row = {k: v for k, v in r.items()}
        for key in ("bbox", "points", "xy"):
            if row.get(key) is not None:
                v = row[key]
                row[key] = [list(p) for p in v] if isinstance(v, list) else list(v)
        if isinstance(row.get("orient"), str):
            row["orient"] = row["orient"].strip('"')
        if isinstance(row.get("text"), str):
            row["text"] = row["text"].strip('"')
        out.append(row)

    masters: dict[str, list] = {}
    for r in out:
        if r.get("kind") == "instance":
            key = f"{r.get('lib')}/{r.get('cell')}"
            if key not in masters:
                sub = geometry(r.get("lib"), r.get("cell"))
                masters[key] = [s for s in sub.get("rows", []) if s.get("kind") == "shape"]
    return {"ok": True, "rows": out, "masters": masters}


def snapshot() -> dict:
    assert CLIENT is not None
    lib, cell, view = CLIENT.get_current_design()
    return {
        "design": {"lib": lib, "cell": cell, "view": view},
        "windows": CLIENT.list_windows(),
        "log": LOG[-160:],
    }


# ---------------------------------------------------------------- http layer

class Handler(BaseHTTPRequestHandler):
    def _send(self, payload: dict, code: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args) -> None:  # keep the console clean
        return

    def do_GET(self) -> None:
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path in ("/", "/index.html"):
            body = (HERE / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if u.path in ("/favicon.ico", "/favicon.svg", "/icon.svg"):
            name = "icon.svg" if u.path == "/icon.svg" else "icon-small.svg"
            body = (HERE.parent / "assets" / name).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Cache-Control", "max-age=3600")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if u.path == "/render.js":
            body = (HERE / "render.js").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if u.path == "/api/state":
            return self._send(snapshot())
        if u.path == "/api/geometry":
            return self._send(geometry(q.get("lib", ["DEMO"])[0], q.get("cell", ["INV"])[0]))
        self._send({"error": "not found"}, 404)

    def do_POST(self) -> None:
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        data = json.loads(self.rfile.read(n) or b"{}")
        lib = data.get("lib", "DEMO")
        if u.path == "/api/skill":
            return self._send(run_skill(data.get("skill", "")))
        if u.path == "/api/build-cell":
            return self._send(build_demo(lib, data.get("cell", "INV")))
        if u.path == "/api/build-top":
            return self._send(build_top(lib, data.get("top", "TOP"),
                                        data.get("child", "INV"),
                                        int(data.get("count", 4))))
        if u.path == "/api/open-window":
            assert CLIENT is not None
            r = CLIENT.open_window(lib, data.get("cell", "INV"), view="layout")
            log("cmd", f"client.open_window({lib}, {data.get('cell','INV')}, view='layout')")
            log("ok" if r.status is ExecutionStatus.SUCCESS else "err", (r.output or "").strip())
            return self._send({"ok": r.status is ExecutionStatus.SUCCESS})
        if u.path == "/api/select":
            b = data.get("bbox", [-5, -5, 30, 12])
            return self._send(run_skill(layout_select_box(tuple(b)),
                                        f"layout_select_box({tuple(b)})"))
        if u.path == "/api/fetch":
            assert CLIENT is not None
            fields = data.get("fields", ["objType", "lpp"])
            objs = CLIENT.fetch("geGetSelSet()", fields)
            log("cmd", f"client.fetch('geGetSelSet()', {fields})")
            log("ok", f"{len(objs)} objects in ONE round trip")
            return self._send({"ok": True, "objects": objs})
        if u.path == "/api/screenshot":
            assert CLIENT is not None
            path = ARTIFACTS / "window.png"
            r = CLIENT.screenshot(output=path, target="layout")
            ok = path.exists()
            log("cmd", "client.screenshot(target='layout')")
            log("ok" if ok else "err",
                f"{path.name} — {path.stat().st_size} bytes" if ok else str(r.errors))
            return self._send({"ok": ok, "path": str(path)})
        self._send({"error": "not found"}, 404)


def main() -> int:
    global CLIENT
    mock = MockVirtuosoServer(Session(artifact_dir=ARTIFACTS))
    mock.start()
    CLIENT = VirtuosoClient.local(port=mock.port)
    log("sys", f"mock-virtuoso listening on 127.0.0.1:{mock.port}")
    log("sys", "VirtuosoClient connected — no Cadence licence, no EDA server")

    httpd = ThreadingHTTPServer(("127.0.0.1", 8808), Handler)
    url = "http://127.0.0.1:8808"
    print(f"Virtuoso workbench → {url}   (mock daemon on port {mock.port})")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
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
