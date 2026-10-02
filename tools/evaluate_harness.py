"""Evaluate recovery with real HTTP, bridge, database and mockTech DRC.

Replay mode substitutes only the model responses. --live uses the configured
Hermes endpoint instead; neither mode falls back to the rules planner.
"""
from __future__ import annotations

import argparse
import copy
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mock_virtuoso.bridge_compat import match_client_auth
from mock_virtuoso.server import MockVirtuosoServer
from mock_virtuoso.session import Session
from toolkit import planner
from virtuoso_bridge import VirtuosoClient


PLAN = {"lib": "HARNESS", "cell": "WIRE", "ops": [
    {"op": "rect", "layer": "met1", "x0": 0, "y0": 0, "x1": 1, "y1": 1}]}
REQUEST = ("In HARNESS library create WIRE containing exactly one met1 drawing rectangle "
           "from (0,0) to (1,1) microns. No labels, pins, paths, instances or other shapes.")


def cases():
    good = json.dumps(PLAN)
    bad_path = copy.deepcopy(PLAN)
    bad_path["ops"] = [{"op": "path", "layer": "met1", "points": [[0], [1, 1]]}]
    thin = copy.deepcopy(PLAN)
    thin["ops"][0]["x1"] = 0.05
    return [
        ("clean", [(good, "stop")]),
        ("broken_json", [(good[:-1], "stop"), (good, "stop")]),
        ("malformed_points", [(json.dumps(bad_path), "stop"), (good, "stop")]),
        ("truncated", [(good, "length"), (good, "stop")]),
        ("drc_repair", [(json.dumps(thin), "stop"), (good, "stop")]),
        ("persistent_invalid", [("not a plan", "stop")]),
    ]


class Replay(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append(request)
        index = min(len(self.server.requests) - 1, len(self.server.responses) - 1)
        raw, reason = self.server.responses[index]
        body = json.dumps({"choices": [{"message": {"content": raw},
                                         "finish_reason": reason}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def trial(retries, artifact_dir):
    mock = MockVirtuosoServer(Session(artifact_dir=artifact_dir))
    client = VirtuosoClient.local(port=mock.port)
    match_client_auth(mock, client)
    mock.start()
    trace = []
    started = time.monotonic()
    result = {"success": False, "trace": trace}
    try:
        plan, source = planner.plan_and_validate(REQUEST, retries=retries, trace=trace,
                                                 allow_fallback=False)
        plan, report, source = planner.build_and_check(client, REQUEST, plan, source,
                                                       retries=retries, trace=trace)
        # Independent readback oracle checks the task, not merely the absence of DRC errors.
        geometry = client.execute_skill(planner.layout_read_geometry("HARNESS", "WIRE"))
        rows = planner.parse_layout_geometry_output(geometry.output or "")
        box = client.execute_skill(
            'dbOpenCellViewByType("HARNESS" "WIRE" "layout" "maskLayout" "r")~>bBox')
        result.update(planner=source, report=report, rows=rows, bbox=box.output)
        info = report.get("cells", {}).get("WIRE", {})
        result["success"] = (not report["harness"]["verification_errors"]
                             and not report["harness"]["drc_errors"]
                             and info.get("shapes_by_layer") == {"met1": 1}
                             and not info.get("instances")
                             and len(rows) == 1 and rows[0].get("objType") == "rect"
                             and tuple(map(tuple, rows[0].get("bbox") or [])) == ((0, 0), (1, 1)))
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        mock.stop()
    result["elapsed_s"] = round(time.monotonic() - started, 4)
    return result


def evaluate(*, live=False, repeats=1):
    records = []
    with tempfile.TemporaryDirectory(prefix="hermes-harness-") as directory:
        for repeat in range(repeats):
            for name, responses in (cases()[:1] if live else cases()):
                for retries in (0, 1):
                    if live:
                        result = trial(retries, Path(directory))
                    else:
                        server = ThreadingHTTPServer(("127.0.0.1", 0), Replay)
                        server.responses, server.requests = responses, []
                        worker = threading.Thread(target=server.serve_forever, daemon=True)
                        worker.start()
                        try:
                            endpoint = (f"http://127.0.0.1:{server.server_port}", "replay", "local-test")
                            with patch.object(planner, "configured_planner", return_value=endpoint):
                                result = trial(retries, Path(directory))
                            result["model_calls"] = len(server.requests)
                        finally:
                            server.shutdown()
                            server.server_close()
                            worker.join()
                    records.append({"case": name, "repeat": repeat, "retries": retries, **result})
    summary = {}
    for retries in (0, 1):
        group = [r for r in records if r["retries"] == retries]
        summary[str(retries)] = {"tasks": len(group), "successes": sum(r["success"] for r in group),
                                 "elapsed_s": round(sum(r["elapsed_s"] for r in group), 4)}
    return {"mode": "live" if live else "replay", "summary": summary, "runs": records,
            "scope": "mockTech layout task; not foundry sign-off or a general model benchmark"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--output", type=Path, default=Path(".tools/harness-evaluation.json"))
    args = ap.parse_args()
    if not 1 <= args.repeats <= 100:
        ap.error("--repeats must be between 1 and 100")
    report = evaluate(live=args.live, repeats=args.repeats)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    if args.live:
        return 0 if report["summary"]["1"]["successes"] == args.repeats else 1
    expected = {"clean", "broken_json", "malformed_points", "truncated", "drc_repair"}
    return 0 if all(r["success"] == (r["case"] in (expected if r["retries"] else {"clean"}))
                    for r in report["runs"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
