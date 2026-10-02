"""Execute agent guidance through the actual installed bridge in isolation."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("virtuoso_bridge")

ROOT = Path(__file__).resolve().parents[2]


def read_json_result(result):
    assert result.status.value == "success", result.errors
    value = json.loads(result.output)
    return json.loads(value) if isinstance(value, str) else value


def test_documented_build_is_repeatable_and_inspection_is_nonmutating(bridge_client):
    client, session = bridge_client
    caps = read_json_result(client.execute_skill("mockCapabilities()"))
    assert caps["backend"] == "mock-virtuoso"
    absent = read_json_result(client.execute_skill('mockInspectCell("ABSENT" "CELL" "layout")'))
    assert absent["exists"] is False
    assert not session.design.cell_exists("ABSENT", "CELL")
    source = (ROOT / "skills/design-floor/examples/owned-layout.il").read_text(encoding="utf-8")
    for _ in range(2):
        report = read_json_result(client.execute_skill(source))
        assert report["counts"] == {"shapes": 1, "instances": 0, "nets": 1, "terminals": 1, "pins": 1}
        assert report["bbox"] == [[0, 0], [4, 2]]
        assert report["verification"] == "not_run"
    drc = client.execute_skill('mockDrcCheck(dbOpenCellViewByType("AGENT_EXAMPLES" "PIN_DEMO" "layout" "maskLayout" "r"))')
    assert drc.status.value == "success", drc.errors
    assert drc.output == "nil"


def test_failed_mutation_remains_visible_for_recovery(bridge_client):
    client, _ = bridge_client
    result = client.execute_skill('cv = dbOpenCellViewByType("LIB" "PARTIAL" "layout" "maskLayout" "w") '
                                  'dbCreateRect(cv list("met1" "drawing") list(0:0 4:2)) '
                                  'notAFunction()')
    assert result.status.value != "success"
    report = read_json_result(client.execute_skill('mockInspectCell("LIB" "PARTIAL" "layout")'))
    assert report["counts"]["shapes"] == 1


def test_authenticated_lane_runner_and_failure_exit(bridge_client, tmp_path):
    client, _ = bridge_client
    env = tmp_path / "lanes.env"
    env.write_text(f"VB_REMOTE_HOST_verify=localhost\nVB_LOCAL_PORT_verify={client.port}\n"
                   f"VB_REMOTE_PORT_verify={client.port}\n", encoding="utf-8")
    command = [sys.executable, str(ROOT / "tools/floor_skill.py"), "--env", str(env),
               "-p", "verify", "--stdin"]
    result = subprocess.run(command, input="mockCapabilities()", text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["status"] == "success"
    failed = subprocess.run(command, input="notAFunction()", text=True, capture_output=True, timeout=20)
    assert failed.returncode == 1
    assert json.loads(failed.stdout)["status"] == "error"
    env.write_text("VB_REMOTE_HOST_verify=remote.example\n", encoding="utf-8")
    rejected = subprocess.run(command, input="1+2", text=True, capture_output=True, timeout=20)
    assert rejected.returncode == 2
