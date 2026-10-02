"""Real PDK models, acceptance gates, and native extraction regression fixtures."""
from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from mock_virtuoso.circuit import example
from mock_virtuoso.experiments import measure, run_experiment, validate_plan
from mock_virtuoso.pdk import installed, models
from mock_virtuoso.simulation import find_ngspice, simulate


def transistor():
    return {"name": "PDK_NMOS", "model_profile": "sky130", "devices": [
        {"id": "VD", "kind": "V", "nodes": ["drain", "0"], "value": 1.8},
        {"id": "VG", "kind": "V", "nodes": ["gate", "0"], "value": 1.8},
        {"id": "M1", "kind": "NMOS", "nodes": ["drain", "gate", "0", "0"], "width": 1e-6, "length": .15e-6}],
        "analysis": {"type": "op"}}


def plan():
    return {"name": "DIVIDER_TEST", "circuit": example(), "measurements": [
        {"name": "output", "signal": "v(vout)", "min": .49, "max": .51}]}


@pytest.mark.skipif(not installed() or not find_ngspice(), reason="Real SKY130/ngspice required")
def test_real_corners_change_current_and_snapshot_models(tmp_path):
    values = []
    for corner in ("ss", "tt", "ff"):
        c = transistor()
        c["corner"] = corner
        result = simulate(c, output=tmp_path)
        assert result["status"] == "pass", result
        current = next(v["real"][0] for v in result["data"]["columns"] if v["name"] == "i(v_vd)")
        values.append(abs(current))
        assert result["pdk"]["corner"] == corner
        assert (tmp_path / result["run_id"] / "models.spice").is_file()
        assert len(result["pdk"]["source_files"]) > 100
    assert 0 < values[0] < values[1] < values[2] < .01


@pytest.mark.skipif(not find_ngspice(), reason="Real ngspice required")
def test_sweep_acceptance_failure_is_persisted(tmp_path):
    p = plan()
    p["sweep"] = {"device": "V1", "values": [1, 2]}
    result = run_experiment(p, output=tmp_path)
    assert [r["status"] for r in result["runs"]] == ["pass", "fail"]
    assert result["status"] == "fail"
    assert json.loads((tmp_path / result["run_id"] / "result.json").read_text())["status"] == "fail"
    assert not result["foundry_qualified"]


def test_missing_signal_is_error_not_pass():
    assert measure({"columns": []}, plan()["measurements"])[0]["status"] == "error"


@pytest.mark.parametrize("mutation", [
    {"corners": ["ff"]}, {"temperatures": [27] * 31},
    {"measurements": [{"name": "m", "signal": "v(x)"}]},
    {"sweep": {"device": "absent", "values": [1]}},
    {"measurements": [{"name": "m", "signal": "v(x)", "min": 2, "max": 1}]},
])
def test_invalid_plans_rejected_before_any_runs(mutation):
    with pytest.raises(ValueError):
        validate_plan({**plan(), **mutation})


@pytest.mark.skipif(not os.environ.get("RUN_MAGIC_TESTS"), reason="Requires WSL Magic")
def test_real_rc_and_antenna(tmp_path):
    from mock_virtuoso.extraction import extract
    fixture = Path(".tools/sky130-fixture/sky130_fd_sc_hd__inv_1.gds")
    result = extract(fixture, "sky130_fd_sc_hd__inv_1", output=tmp_path)
    assert result["pex"]["status"] == "pass", result
    assert result["pex"]["resistors"] > 0
    assert result["pex"]["capacitors"] > 0
    assert result["antenna"]["status"] == "pass"
    assert result["antenna"]["checked_devices"] == 2


@pytest.mark.skipif(not os.environ.get("RUN_MAGIC_TESTS"), reason="Requires WSL Magic")
def test_empty_extraction_never_passes(tmp_path):
    import klayout.db as db
    from mock_virtuoso.extraction import extract
    layout = db.Layout()
    cell = layout.create_cell("EMPTY")
    cell.shapes(layout.layer(68, 20)).insert(db.Box(0, 0, 1000, 1000))
    path = tmp_path / "empty.gds"
    layout.write(str(path))
    result = extract(path, "EMPTY", output=tmp_path)
    assert result["pex"]["status"] == "error"
    assert result["antenna"]["status"] == "error"


@pytest.mark.skipif(not os.environ.get("RUN_MAGIC_TESTS"), reason="Requires WSL Magic")
def test_oversized_gate_antenna_is_detected(tmp_path):
    import klayout.db as db
    from mock_virtuoso.extraction import extract
    layout = db.Layout()
    layout.read(".tools/sky130-fixture/sky130_fd_sc_hd__inv_1.gds")
    cell = layout.top_cell()
    cell.shapes(layout.layer(67, 44)).insert(db.Box(360, 1105, 530, 1275))
    cell.shapes(layout.layer(68, 20)).insert(db.Box(-110000, 1100, 530, 1280))
    cell.shapes(layout.layer(68, 20)).insert(db.Box(-110000, -50000, -10000, 50000))
    path = tmp_path / "antenna.gds"
    layout.write(str(path))
    result = extract(path, cell.name, output=tmp_path)
    assert result["antenna"]["status"] == "fail", result
    assert result["antenna"]["feedback_count"] > 0
    assert "metal1" in result["antenna"]["feedback"]


@pytest.mark.skipif(not os.environ.get("RUN_MAGIC_TESTS") or not os.environ.get("KLAYOUT_EXE"), reason="Requires real verification engines")
def test_end_to_end_postlayout_and_review_bundle(tmp_path, monkeypatch):
    import base64
    import io
    import zipfile
    from toolkit import circuit_service, verification_service
    root = Path.cwd()
    monkeypatch.setenv("SKY130_DECKS", str(root / ".tools/sky130"))
    monkeypatch.setenv("NGSPICE_EXE", str(find_ngspice()))
    monkeypatch.setattr(circuit_service, "ROOT", tmp_path)
    monkeypatch.setattr(verification_service, "ROOT", tmp_path)
    fixture = root / ".tools/sky130-fixture/sky130_fd_sc_hd__inv_1"
    result = verification_service.verify_upload({"top": fixture.name, "physical_checks": True,
        "substrate": "VNB", "gds_base64": base64.b64encode(fixture.with_suffix(".gds").read_bytes()).decode(),
        "netlist": fixture.with_suffix(".spice").read_text()})
    assert result["signoff"]["status"] == "ready_for_review", result
    assert not result["signoff"]["eligible"]
    payload = {"run_id": result["run_id"], "ports": {"VPB": "vdd", "VNB": "0", "VGND": "0", "VPWR": "vdd", "A": "vin", "Y": "vout"},
        "circuit": {"name": "POST", "devices": [
            {"id": "VDD", "kind": "V", "nodes": ["vdd", "0"], "value": 1.8},
            {"id": "VIN", "kind": "V", "nodes": ["vin", "0"], "value": 1.8}], "analysis": {"type": "op"}}}
    post = circuit_service.postlayout(payload)
    assert post["status"] == "pass", post
    out = next(c["real"][0] for c in post["data"]["columns"] if c["name"] == "v(vout)")
    assert abs(out) < .01
    archive = zipfile.ZipFile(io.BytesIO(verification_service.evidence(result["run_id"])))
    assert "REVIEW.json" in archive.namelist()
    assert any(n.endswith("extracted.spice") for n in archive.namelist())
    assert json.loads(archive.read("REVIEW.json"))["foundry_qualified"] is False
    payload["ports"].pop("VPB")
    with pytest.raises(ValueError, match="Map every"):
        circuit_service.postlayout(payload)
