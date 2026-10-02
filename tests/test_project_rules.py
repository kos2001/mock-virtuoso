import base64

import pytest

db = pytest.importorskip("klayout.db")
from mock_virtuoso.project_rules import check_constraints, validate_constraints
from mock_virtuoso.verification import signoff_status
from toolkit.verification_service import inspect_upload, validate_settings


def geometry():
    layout = db.Layout()
    layout.dbu = 0.001
    cell = layout.create_cell("TOP")
    layer = layout.layer(68, 20)
    cell.shapes(layer).insert(db.DBox(0, 0, 0.1, 1))
    cell.shapes(layer).insert(db.DBox(0.15, 0, 0.3, 1))
    return layout


def rule(kind, value, layer=68):
    return {"kind": kind, "layer": layer, "datatype": 20, "value_um": value}


def test_width_spacing_and_size_are_measured_by_geometry():
    result = check_constraints(geometry(), "TOP", {"max_height_um": 0.5,
                              "rules": [rule("min_width", 0.14), rule("min_space", 0.14)]})
    assert result["status"] == "fail"
    assert result["checked_rules"] == 3
    assert {m["rule"] for m in result["markers"]} == {"max_height_um", "min_width", "min_space"}
    assert result["markers"][0]["measured_um"] == 1


def test_equal_minimum_passes_and_rounding_does_not_weaken_rule():
    result = check_constraints(geometry(), "TOP", {"rules": [rule("min_width", 0.1), rule("min_space", 0.05)]})
    assert result["status"] == "pass"
    assert check_constraints(geometry(), "TOP", {"rules": [rule("min_width", 0.1001)]})["status"] == "fail"


def test_minimum_area_checks_each_merged_island_and_preserves_units():
    constraint = {"kind": "min_area", "layer": 68, "datatype": 20, "value_um2": .12}
    result = check_constraints(geometry(), "TOP", {"rules": [constraint]})
    assert result["violations"] == 1
    assert result["markers"][0]["measured_um2"] == pytest.approx(.1)
    assert result["markers"][0]["required_um2"] == .12
    constraint["value_um2"] = .1
    assert check_constraints(geometry(), "TOP", {"rules": [constraint]})["status"] == "pass"
    constraint["value_um2"] = .100001
    assert check_constraints(geometry(), "TOP", {"rules": [constraint]})["status"] == "fail"
    with pytest.raises(ValueError, match="value_um2"):
        validate_constraints({"rules": [rule("min_area", .1)]})


def test_hierarchy_is_included_in_project_checks():
    layout = geometry()
    parent = layout.create_cell("PARENT")
    parent.insert(db.CellInstArray(layout.cell("TOP").cell_index(), db.Trans(1000, 2000)))
    result = check_constraints(layout, "PARENT", {"rules": [rule("min_width", 0.14)]})
    assert result["status"] == "fail"
    assert result["markers"][0]["bbox"][0][0] >= 1


def test_missing_layer_blocks_project_gate():
    constraints = {"rules": [rule("min_width", 0.14, 999)]}
    check = check_constraints(geometry(), "TOP", constraints)
    assert check["status"] == "not_run"
    result = {"drc": {"status": "pass"}, "lvs": {"status": "pass"},
              "project_constraints": constraints, "project_rules": check}
    assert signoff_status(result, "cell")["blocking_checks"] == ["project_rules"]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, 0, True, "0.14"])
def test_invalid_values_are_rejected(value):
    with pytest.raises(ValueError):
        validate_constraints({"rules": [rule("min_width", value)]})


def test_settings_reject_unknown_pdk_and_executable_rules():
    with pytest.raises(ValueError, match="SKY130"):
        validate_settings({"pdk": "invented"})
    with pytest.raises(ValueError, match="Unknown"):
        validate_settings({"ruby": "puts 'hi'"})
    with pytest.raises(ValueError, match="kind"):
        validate_settings({"project_constraints": {"rules": [rule("run_ruby", 1)]}})


def test_layout_inspection_returns_real_cells_and_layers(tmp_path, monkeypatch):
    from toolkit import verification_service
    monkeypatch.setattr(verification_service, "ROOT", tmp_path)
    path = tmp_path / "top.gds"
    geometry().write(str(path))
    result = inspect_upload({"gds_base64": base64.b64encode(path.read_bytes()).decode()})
    assert result["top_cells"] == [{"name": "TOP", "width_um": 0.3, "height_um": 1.0}]
    assert result["layers"] == [{"name": "met1", "layer": 68, "datatype": 20}]
    assert result["dbu_um"] == 0.001
