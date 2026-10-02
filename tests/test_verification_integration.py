"""Real upstream SKY130 decks, enabled when KLAYOUT_EXE and fixtures are installed."""
import os
from pathlib import Path

import pytest

db = pytest.importorskip("klayout.db")
from mock_virtuoso.verification import run_verification

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / ".tools/sky130-fixture"
TOP = "sky130_fd_sc_hd__inv_1"
EXE = os.environ.get("KLAYOUT_EXE")
pytestmark = pytest.mark.skipif(not EXE or not (FIXTURE / f"{TOP}.gds").exists(),
                               reason="Set KLAYOUT_EXE and fetch decks with --fixtures")


def run(tmp_path, **changes):
    options = dict(executable=EXE, gds=FIXTURE / f"{TOP}.gds", top=TOP,
                   netlist=FIXTURE / f"{TOP}.spice", substrate="VNB",
                   decks=ROOT / ".tools/sky130", output=tmp_path)
    options.update(changes)
    return run_verification(**options)


def test_public_inverter_passes_drc_and_lvs(tmp_path):
    result = run(tmp_path)
    assert result["drc"]["status"] == "pass", result["drc"]
    assert result["lvs"]["status"] == "pass", result["lvs"]
    assert result["lvs"]["extracted_devices"] == 2
    assert result["signoff"]["status"] == "ready_for_review"
    assert result["signoff"]["eligible"] is False
    assert Path(result["directory"], "extracted.spice").is_file()


def test_narrow_added_metal_is_reported_at_actual_location(tmp_path):
    layout = db.Layout()
    layout.read(str(FIXTURE / f"{TOP}.gds"))
    layout.cell(TOP).shapes(layout.layer(68, 20)).insert(db.DBox(10, 10, 10.05, 11))
    bad = tmp_path / "narrow.gds"
    layout.write(str(bad))
    result = run(tmp_path, gds=bad)
    assert result["drc"]["status"] == "fail"
    assert result["drc"]["violations"] > 0
    assert any("10" in str(marker["values"]) for marker in result["drc"]["markers"])
    assert "drc" in result["signoff"]["blocking_checks"]


def test_wrong_transistor_width_blocks_lvs(tmp_path):
    source = (FIXTURE / f"{TOP}.spice").read_text()
    assert "650000u" in source
    bad = tmp_path / "wrong.spice"
    bad.write_text(source.replace("650000u", "750000u"))
    result = run(tmp_path, netlist=bad)
    assert result["drc"]["status"] == "pass"
    assert result["lvs"]["status"] == "fail"
    assert "lvs" in result["signoff"]["blocking_checks"]


def test_chip_without_boundary_does_not_claim_density_pass(tmp_path):
    result = run(tmp_path, scope="chip")
    assert result["density"]["status"] == "not_run"
    assert "235/4" in result["density"]["reason"]
    assert {"density", "erc", "antenna"} <= set(result["signoff"]["blocking_checks"])


def test_density_detects_overfilled_chip_boundary(tmp_path):
    layout = db.Layout()
    layout.read(str(FIXTURE / f"{TOP}.gds"))
    cell = layout.cell(TOP)
    cell.shapes(layout.layer(235, 4)).insert(db.DBox(0, 0, 100, 100))
    cell.shapes(layout.layer(71, 20)).insert(db.DBox(0, 0, 90, 100))
    bad = tmp_path / "dense.gds"
    layout.write(str(bad))
    result = run(tmp_path, gds=bad, scope="chip")
    assert result["density"]["status"] == "fail", result["density"]
    assert any(m["category"] == "m4.pd.1d" for m in result["density"]["markers"])
