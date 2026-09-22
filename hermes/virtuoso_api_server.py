"""An OpenAI-compatible server that answers a request with a real layout.

POST /v1/chat/completions with a request in words and this plans it, refuses
anything it is not willing to run, builds what survives through
virtuoso-bridge, reads the design back and answers from what the database
actually holds. The pipeline itself lives in `toolkit/planner.py`, shared with
the design floor; this file is the HTTP surface around it.

The model's output is never executed. `validate` stands between the planner and
the bridge, and a plan that fails it is reported as refused with nothing run.

Run:  .venv/bin/python hermes/virtuoso_api_server.py --port 8750
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mock_virtuoso.bridge_compat import match_client_auth
from mock_virtuoso.server import MockVirtuosoServer
from mock_virtuoso.session import Session
from toolkit.planner import (
    HERMES,
    PlanError,
    answer_text,
    build_and_check,
    plan_and_validate,
    plan_with_rules,
    validate,
)

from virtuoso_bridge import VirtuosoClient

MODEL = "virtuoso-fde"
CLIENT: VirtuosoClient | None = None
PLANNER = "auto"


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
        try:
            if PLANNER == "rules":
                plan = validate(plan_with_rules(text)[0])
            else:
                # Refusals go back to the model once, carrying what the
                # knowledge base knows about that failure. Nothing has been
                # executed at this point, so a retry cannot half-build a cell.
                plan, planner_used = plan_and_validate(text)
        except PlanError as exc:
            return self._chat(
                f"Rejected the {planner_used} plan before touching the design: {exc}\n"
                "It was sent back once with that reason and still did not validate. "
                "Nothing was executed.", t0, planner_used, error=True)
        try:
            plan, report, planner_used = build_and_check(CLIENT, text, plan, planner_used)
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
    match_client_auth(mock, CLIENT)
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

