"""The replay score is grounded in the same real execution path as the UI."""
import importlib.util
import importlib
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
import threading
from urllib.request import Request, urlopen

spec = importlib.util.spec_from_file_location(
    "harness_evaluation", Path(__file__).resolve().parents[2] / "tools/evaluate_harness.py")
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


def test_replay_recovers_errors_without_hiding_persistent_failures():
    report = evaluation.evaluate()
    assert report["summary"]["0"]["successes"] == 1
    assert report["summary"]["1"]["successes"] == 5
    for run in report["runs"]:
        assert run["model_calls"] <= 2
        if run["case"] == "clean":
            assert run["model_calls"] == 1
        if run["case"] == "persistent_invalid":
            assert not run["success"]
            assert "PlanResponseError" in run["error"]
        if run["success"]:
            assert run["report"]["harness"]["status"] == "verified"
            assert len(run["rows"]) == 1


def test_both_service_surfaces_expose_real_execution_attempts(tmp_path, monkeypatch):
    floor = importlib.import_module("floor.design_floor")
    api = importlib.import_module("hermes.virtuoso_api_server")
    mock = evaluation.MockVirtuosoServer(evaluation.Session(artifact_dir=tmp_path))
    client = evaluation.VirtuosoClient.local(port=mock.port)
    evaluation.match_client_auth(mock, client)
    mock.start()
    monkeypatch.setattr(floor, "REQUEST_CLIENT", client)
    monkeypatch.setattr(api, "CLIENT", client)
    monkeypatch.setattr(api, "PLANNER", "hermes")
    monkeypatch.setattr(evaluation.planner, "plan_with_hermes",
                        lambda *a, **k: (evaluation.PLAN, "hermes"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        result = floor.build_from_request(evaluation.REQUEST)
        assert result["harness"]["status"] == "verified"
        request = Request(f"http://127.0.0.1:{server.server_port}/v1/chat/completions",
                          data=json.dumps({"messages": [{"role": "user", "content": evaluation.REQUEST}]}).encode(),
                          headers={"Content-Type": "application/json"})
        with urlopen(request) as response:
            meta = json.load(response)["x_virtuoso"]
        assert meta["error"] is False
        assert meta["harness"]["status"] == "verified"
        assert [a["stage"] for a in meta["harness"]["attempts"]] == ["planning", "build"]
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
        mock.stop()
