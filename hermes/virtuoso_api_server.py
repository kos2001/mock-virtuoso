"""OpenAI-compatible API server: natural language in, a real layout out.

    POST /v1/chat/completions   "STDLIB에 INV 셀 만들고 TOP에 3개 배치해줘"
      → planner turns the request into a JSON plan
      → the plan is VALIDATED against a strict schema (never executed as-is)
      → each op runs through virtuoso-bridge-lite's own builders
      → the design is read BACK through the bridge's reader
      → the reply reports what the database actually contains

The planner is pluggable:
  * `hermes`  — POST the request to a hermes-agent OpenAI server and parse its JSON
  * `rules`   — a deterministic intent parser, so this runs with no LLM at all
  * `auto`    — hermes if reachable, else rules

Model output is never trusted: ops outside the whitelist, unknown layers,
non-numeric coordinates and oversized plans are rejected before anything is sent
to the bridge. The grounding claim in the reply comes from the read-back, not
from the plan.

Run:  .venv/bin/python hermes/virtuoso_api_server.py --port 8750
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import time
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from mock_virtuoso.auth import Authenticator
from mock_virtuoso.bridge_compat import build_layout, clear_layout
from mock_virtuoso.server import MockVirtuosoServer
from mock_virtuoso.session import Session

from virtuoso_bridge import ExecutionStatus, VirtuosoClient
from virtuoso_bridge.virtuoso.layout import (
    layout_create_label,
    layout_create_param_inst,
    layout_create_path,
    layout_create_rect,
    layout_read_geometry,
    parse_layout_geometry_output,
)

MODEL = "virtuoso-fde"
LAYERS = {"nwell", "diff", "poly", "met1", "met2", "met3", "text"}
ORIENTS = {"R0", "R90", "R180", "R270", "MX", "MY", "MXR90", "MYR90"}
MAX_OPS = 80

PLAN_SCHEMA = (
    "You translate analog-layout requests into a JSON plan. Reply with JSON ONLY, no prose.\n"
    'Schema: {"lib":"<library>","cell":"<name>","ops":[ ... ]}\n'
    'Ops: {"op":"rect","layer":L,"x0":n,"y0":n,"x1":n,"y1":n}\n'
    '     {"op":"path","layer":L,"points":[[x,y],[x,y]],"width":n}\n'
    '     {"op":"label","layer":L,"x":n,"y":n,"text":T}\n'
    '     {"op":"place","child":C,"name":I,"x":n,"y":n,"orient":"R0"|"MY"}\n'
    f"Layers allowed: {', '.join(sorted(LAYERS))}. Coordinates are microns, keep them under 100.\n"
    "If the request asks for instances of a cell, you MUST define that cell first: put its\n"
    'shapes in "ops" with "cell" set to the cell name, and put the placements in\n'
    '{"then":{"cell":"<top>","ops":[{"op":"place",...}]}}. Never place a cell you did not define.'
)

CLIENT: VirtuosoClient | None = None
PLANNER = "auto"
HERMES = {"url": "http://127.0.0.1:8642/v1/chat/completions", "model": "lsi", "key": None}


# ------------------------------------------------------------------ planners

def _hermes_key() -> str | None:
    if HERMES["key"]:
        return HERMES["key"]
    env = pathlib.Path.home() / ".hermes" / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("API_SERVER_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def plan_with_hermes(text: str, timeout: int = 90) -> tuple[dict | None, str]:
    key = _hermes_key()
    if not key:
        return None, "no hermes API key"
    body = json.dumps({
        "model": HERMES["model"], "temperature": 0, "max_tokens": 1200,
        "messages": [{"role": "system", "content": PLAN_SCHEMA},
                     {"role": "user", "content": text}],
    }).encode()
    req = urllib.request.Request(HERMES["url"], data=body, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out = json.load(r)
    except Exception as exc:                                   # noqa: BLE001
        return None, f"hermes unreachable: {type(exc).__name__}"
    raw = (out.get("choices", [{}])[0].get("message", {}).get("content") or "")
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None, "hermes returned no JSON"
    try:
        return json.loads(m.group(0)), "hermes"
    except json.JSONDecodeError as exc:
        return None, f"hermes JSON invalid: {exc}"


def plan_with_rules(text: str) -> tuple[dict, str]:
    """Deterministic fallback so the server works with no LLM at all."""
    t = text.lower()
    lib = (re.search(r"\b([A-Z][A-Z0-9_]{2,})\s*(?:라이브러리|library|lib)", text) or [None, "DEMO"])[1]
    cell = (re.search(r"\b(INV|NAND2|NOR2|BUF|DFF)\b", text.upper()) or [None, "CELL"])[1]
    ops: list[dict] = [
        {"op": "rect", "layer": "nwell", "x0": -0.2, "y0": 2.0, "x1": 4.2, "y1": 4.2},
        {"op": "rect", "layer": "diff", "x0": 0.5, "y0": 2.5, "x1": 3.5, "y1": 3.7},
        {"op": "rect", "layer": "diff", "x0": 0.5, "y0": 0.3, "x1": 3.5, "y1": 1.5},
        {"op": "rect", "layer": "poly", "x0": 1.8, "y0": 0.0, "x1": 2.2, "y1": 4.0},
        {"op": "rect", "layer": "met1", "x0": 0.0, "y0": 3.8, "x1": 4.0, "y1": 4.0},
        {"op": "rect", "layer": "met1", "x0": 0.0, "y0": 0.0, "x1": 4.0, "y1": 0.2},
        {"op": "label", "layer": "text", "x": 0.3, "y": 3.9, "text": "VDD"},
        {"op": "label", "layer": "text", "x": 0.3, "y": 0.1, "text": "VSS"},
        {"op": "label", "layer": "text", "x": 2.0, "y": 4.1, "text": "IN"},
        {"op": "label", "layer": "text", "x": 3.7, "y": 2.0, "text": "OUT"},
    ]
    n = int((re.search(r"(\d+)\s*(?:개|instances?|번|x|×)", t) or [0, 0])[1] or 0)
    if n:
        top = (re.search(r"\b(TOP|ROW|ARRAY)\b", text.upper()) or [None, "TOP"])[1]
        return {"lib": lib, "cell": cell, "ops": ops,
                "then": {"cell": top, "ops": [
                    {"op": "place", "child": cell, "name": f"I{i}", "x": i * 4.4, "y": 0.0,
                     "orient": "MY" if i % 2 else "R0"} for i in range(min(n, 16))]}}, "rules"
    return {"lib": lib, "cell": cell, "ops": ops}, "rules"


# ---------------------------------------------------------------- validation

class PlanError(ValueError):
    pass


def _num(v, what: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise PlanError(f"{what} must be a number, got {v!r}")
    f = float(v)
    if not -1e4 < f < 1e4:
        raise PlanError(f"{what} out of range: {f}")
    return f


def _name(v, what: str) -> str:
    if not isinstance(v, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", v):
        raise PlanError(f"{what} must be a simple identifier, got {v!r}")
    return v


def validate(plan: dict) -> dict:
    """Reject anything the planner produced that we are not willing to execute."""
    if not isinstance(plan, dict):
        raise PlanError("plan is not an object")
    out = {"lib": _name(plan.get("lib", "DEMO"), "lib"),
           "cell": _name(plan.get("cell", "CELL"), "cell"), "ops": [], "then": None}
    ops = plan.get("ops") or []
    if not isinstance(ops, list) or len(ops) > MAX_OPS:
        raise PlanError(f"ops must be a list of at most {MAX_OPS}")
    for i, o in enumerate(ops):
        out["ops"].append(_validate_op(o, f"ops[{i}]"))
    then = plan.get("then")
    if then:
        t_ops = then.get("ops") or []
        if len(t_ops) > MAX_OPS:
            raise PlanError("too many placement ops")
        out["then"] = {"cell": _name(then.get("cell", "TOP"), "then.cell"),
                       "ops": [_validate_op(o, f"then.ops[{i}]") for i, o in enumerate(t_ops)]}
    if not out["ops"] and not (out["then"] and out["then"]["ops"]):
        raise PlanError("plan contains no executable operations")
    return out


def _validate_op(o, where: str) -> dict:
    if not isinstance(o, dict):
        raise PlanError(f"{where} is not an object")
    kind = o.get("op")
    if kind in ("rect", "path", "label"):
        layer = o.get("layer")
        if layer not in LAYERS:
            raise PlanError(f"{where}: unknown layer {layer!r}; allowed: {sorted(LAYERS)}")
    if kind == "rect":
        return {"op": "rect", "layer": o["layer"],
                **{k: _num(o.get(k), f"{where}.{k}") for k in ("x0", "y0", "x1", "y1")}}
    if kind == "label":
        text = o.get("text")
        if not isinstance(text, str) or not (0 < len(text) <= 32):
            raise PlanError(f"{where}.text must be a short string")
        return {"op": "label", "layer": o["layer"], "text": text,
                "x": _num(o.get("x"), f"{where}.x"), "y": _num(o.get("y"), f"{where}.y")}
    if kind == "path":
        pts = o.get("points")
        if not isinstance(pts, list) or not 2 <= len(pts) <= 32:
            raise PlanError(f"{where}.points must hold 2-32 points")
        return {"op": "path", "layer": o["layer"],
                "points": [(_num(p[0], f"{where}.pt.x"), _num(p[1], f"{where}.pt.y")) for p in pts],
                "width": _num(o.get("width", 0.4), f"{where}.width")}
    if kind == "place":
        orient = o.get("orient", "R0")
        if orient not in ORIENTS:
            raise PlanError(f"{where}.orient must be one of {sorted(ORIENTS)}")
        return {"op": "place", "child": _name(o.get("child"), f"{where}.child"),
                "name": _name(o.get("name", "I0"), f"{where}.name"), "orient": orient,
                "x": _num(o.get("x", 0), f"{where}.x"), "y": _num(o.get("y", 0), f"{where}.y")}
    raise PlanError(f"{where}: unsupported op {kind!r}")


# ----------------------------------------------------------------- execution

def _emit(op: dict, lib: str) -> str:
    if op["op"] == "place":
        return layout_create_param_inst(lib, op["child"], "layout",
                                        op["name"], op["x"], op["y"], op["orient"])
    if op["op"] == "rect":
        return layout_create_rect(op["layer"], "drawing", op["x0"], op["y0"], op["x1"], op["y1"])
    if op["op"] == "path":
        return layout_create_path(op["layer"], "drawing", op["points"], op["width"])
    if op["op"] == "label":
        return layout_create_label(op["layer"], "drawing", op["x"], op["y"], op["text"],
                                   "centerCenter", "R0", "stick", 0.3)
    # Every validated op must have a builder. Falling through here would drop the
    # operation silently, which is the one failure mode this whole project exists
    # to eliminate.
    raise PlanError(f"no builder for validated op {op['op']!r}")


def execute(plan: dict) -> dict:
    assert CLIENT is not None
    lib = plan["lib"]
    done: list[str] = []

    if plan["ops"]:
        # A plan describes a cell, not an addition to one, so the cell is
        # emptied first -- otherwise repeating a request doubles the geometry.
        clear_layout(CLIENT, lib, plan["cell"])
        with build_layout(CLIENT, lib, plan["cell"]) as ed:
            for op in plan["ops"]:
                ed.add(_emit(op, lib))
        n_sh = sum(1 for o in plan["ops"] if o["op"] != "place")
        n_in = sum(1 for o in plan["ops"] if o["op"] == "place")
        done.append(f"{lib}/{plan['cell']}: {n_sh} shapes"
                    + (f", {n_in} instances" if n_in else ""))
        CLIENT.open_window(lib, plan["cell"], view="layout")

    if plan["then"] and plan["then"]["ops"]:
        top = plan["then"]["cell"]
        clear_layout(CLIENT, lib, top)
        with build_layout(CLIENT, lib, top) as ed:
            for op in plan["then"]["ops"]:
                ed.add(layout_create_param_inst(lib, op["child"], "layout",
                                                op["name"], op["x"], op["y"], op["orient"]))
        done.append(f"{lib}/{top}: {len(plan['then']['ops'])} instances")
        CLIENT.open_window(lib, top, view="layout")

    # A placement whose master has no geometry is almost always the planner
    # forgetting to define the child cell. Surface it rather than shipping an
    # empty box.
    warn: list[str] = []
    placed = {o["child"] for o in plan["ops"] if o["op"] == "place"}
    if plan["then"]:
        placed |= {o["child"] for o in plan["then"]["ops"]}
    for child in sorted(placed):
        r = CLIENT.execute_skill(
            f'length(dbOpenCellViewByType("{lib}" "{child}" "layout" "maskLayout" "r")~>shapes)')
        if (r.output or "").strip() == "0":
            warn.append(f"{lib}/{child} was instantiated but contains no shapes — "
                        "the plan never defined it")

    # Ground the answer in the database, not in the plan.
    report = {"built": done, "warnings": warn, "cells": {}}
    for cell in [plan["cell"]] + ([plan["then"]["cell"]] if plan["then"] else []):
        res = CLIENT.execute_skill(layout_read_geometry(lib, cell))
        if res.status is not ExecutionStatus.SUCCESS:
            report["cells"][cell] = {"error": res.errors}
            continue
        rows = parse_layout_geometry_output(res.output or "")
        by_layer: dict[str, int] = {}
        insts = []
        for r in rows:
            if r.get("kind") == "instance":
                insts.append({"name": r.get("name"), "cell": r.get("cell"),
                              "orient": (r.get("orient") or "").strip('"'), "bbox": r.get("bbox")})
            elif r.get("layer"):
                by_layer[r["layer"]] = by_layer.get(r["layer"], 0) + 1
        bb = CLIENT.execute_skill(
            f'dbOpenCellViewByType("{lib}" "{cell}" "layout" "maskLayout" "r")~>bBox')
        report["cells"][cell] = {"shapes_by_layer": by_layer, "instances": insts,
                                 "bBox": (bb.output or "").strip()}
    return report


def answer_text(plan: dict, report: dict, planner: str, elapsed: float) -> str:
    lines = [f"Built via virtuoso-bridge ({planner} planner, {elapsed:.1f}s):", ""]
    for b in report["built"]:
        lines.append(f"  • {b}")
    for w in report.get("warnings", []):
        lines.append(f"  ! {w}")
    lines.append("")
    lines.append("Read back from the design database:")
    for cell, info in report["cells"].items():
        if "error" in info:
            lines.append(f"  {cell}: ERROR {info['error']}")
            continue
        layers = ", ".join(f"{k}×{v}" for k, v in sorted(info["shapes_by_layer"].items())) or "—"
        lines.append(f"  {plan['lib']}/{cell}  bBox={info['bBox']}")
        lines.append(f"    layers: {layers}")
        for i in info["instances"]:
            lines.append(f"    inst {i['name']} ({i['cell']}) {i['orient']} bbox={i['bbox']}")
    return "\n".join(lines)


# ---------------------------------------------------------------- OpenAI API

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_a):  # quiet
        return

    def _json(self, payload, code=200):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/") == "/v1/models":
            return self._json({"object": "list", "data": [
                {"id": MODEL, "object": "model", "owned_by": "mock-virtuoso"}]})
        self._json({"error": {"message": "not found"}}, 404)

    def do_POST(self):
        if self.path.rstrip("/") != "/v1/chat/completions":
            return self._json({"error": {"message": "not found"}}, 404)
        n = int(self.headers.get("Content-Length") or 0)
        req = json.loads(self.rfile.read(n) or b"{}")
        msgs = [m for m in req.get("messages", []) if m.get("role") == "user"]
        text = msgs[-1].get("content", "") if msgs else ""

        t0 = time.time()
        planner_used = "rules"
        plan_raw = None
        if PLANNER in ("auto", "hermes"):
            plan_raw, note = plan_with_hermes(text)
            if plan_raw is not None:
                planner_used = "hermes"
            elif PLANNER == "hermes":
                return self._chat(f"planner failed: {note}", t0, "hermes", error=True)
        if plan_raw is None:
            plan_raw, planner_used = plan_with_rules(text)

        try:
            plan = validate(plan_raw)
        except PlanError as exc:
            return self._chat(
                f"Rejected the {planner_used} plan before touching the design: {exc}\n"
                "Nothing was executed.", t0, planner_used, error=True)
        try:
            report = execute(plan)
        except Exception as exc:                               # noqa: BLE001
            return self._chat(f"bridge error: {type(exc).__name__}: {exc}", t0, planner_used,
                              error=True)
        self._chat(answer_text(plan, report, planner_used, time.time() - t0), t0, planner_used)

    def _chat(self, content: str, t0: float, planner: str, error: bool = False):
        self._json({
            "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
            "object": "chat.completion", "created": int(time.time()), "model": MODEL,
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "x_virtuoso": {"planner": planner, "elapsed_s": round(time.time() - t0, 2),
                           "error": error},
        })


def main() -> int:
    global CLIENT, PLANNER
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8750)
    ap.add_argument("--mock-port", type=int, default=0)
    ap.add_argument("--planner", choices=["auto", "hermes", "rules"], default="auto")
    ap.add_argument("--hermes-url", default=HERMES["url"])
    ap.add_argument("--hermes-model", default=HERMES["model"])
    args = ap.parse_args()
    PLANNER = args.planner
    HERMES["url"], HERMES["model"] = args.hermes_url, args.hermes_model

    import tempfile
    mock = MockVirtuosoServer(Session(artifact_dir=pathlib.Path(tempfile.mkdtemp())),
                              port=args.mock_port)
    CLIENT = VirtuosoClient.local(port=mock.port)
    # The bridge gained token auth partway through this project's life. Rather
    # than sniff versions, the daemon adopts whatever secret this client holds:
    # a client new enough to carry one gets an authenticated daemon sharing it,
    # an older tokenless client gets the legacy wire. The port is bound by the
    # constructor and nothing is served until start(), so this fits in between.
    mock.auth = Authenticator(getattr(CLIENT, "daemon_token", None))
    mock.start()

    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"virtuoso-fde OpenAI API on http://127.0.0.1:{args.port}/v1  "
          f"(planner={PLANNER}, mock daemon :{mock.port})", flush=True)
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
