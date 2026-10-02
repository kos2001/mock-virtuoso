import copy
import json

import pytest

from mock_virtuoso.circuit import check_circuit, example, netlist, validate_circuit
from mock_virtuoso.session import Session
from mock_virtuoso.skill.errors import SkillError


def test_divider_erc_and_netlist():
    c = example()
    assert check_circuit(c)["status"] == "pass"
    text = netlist(c)
    assert "R_R1 vin vout 1000" in text
    assert ".op" in text and ".end" in text


@pytest.mark.parametrize("kind", ["missing_ground", "dangling", "capacitive_float", "source_loop", "short"])
def test_structural_erc_rejects_broken_connectivity(kind):
    c = example()
    if kind == "missing_ground":
        for d in c["devices"]:
            d["nodes"] = ["gnd" if n == "0" else n for n in d["nodes"]]
    elif kind == "dangling":
        c["devices"].pop()
    elif kind == "capacitive_float":
        c["devices"][1]["kind"] = "C"
        c["devices"][2]["kind"] = "C"
    elif kind == "source_loop":
        c["devices"].append({"id": "V2", "kind": "V", "nodes": ["vin", "0"], "value": 2})
    else:
        c["devices"][1]["nodes"] = ["vin", "vin"]
    assert check_circuit(c)["status"] == "fail"


@pytest.mark.parametrize("value", ["1k", True, float("nan"), float("inf"), -1, 0])
def test_passive_values_require_finite_positive_si_numbers(value):
    c = example()
    c["devices"][1]["value"] = value
    with pytest.raises(ValueError):
        validate_circuit(c)


def test_case_insensitive_names_and_no_spice_injection():
    c = example()
    c["devices"][1]["id"] = "v1"
    with pytest.raises(ValueError, match="Duplicate"):
        validate_circuit(c)
    c = example()
    c["devices"][0]["nodes"][0] = "a\n.control\nshell echo bad"
    with pytest.raises(ValueError, match="identifier"):
        validate_circuit(c)
    c = example()
    c["include"] = "C:/secret"
    with pytest.raises(ValueError):
        validate_circuit(c)


@pytest.mark.parametrize("analysis", [
    {"type": "dc", "source": "R1", "start": 0, "stop": 1, "step": .1},
    {"type": "dc", "source": "V1", "start": 0, "stop": 1, "step": -.1},
    {"type": "tran", "step": 1e-15, "stop": 1},
    {"type": "ac", "start": 10, "stop": 1, "points": 10},
    {"type": "op", "step": 1},
])
def test_bad_analysis_cannot_reach_simulator(analysis):
    c = example()
    c["analysis"] = analysis
    with pytest.raises(ValueError):
        validate_circuit(c)


def test_circuit_bridge_roundtrip_close_reopen_readonly_and_overwrite():
    s = Session()
    s.evaluate('cv = dbOpenCellViewByType("LIB" "C" "schematic" "schematic" "w")')
    encoded = json.dumps(json.dumps(example()))
    s.evaluate(f"mockCircuitLoad(cv {encoded})")
    assert s.evaluate("schCheck(cv)") == [0, 0]
    assert "R_R1" in s.evaluate("mockCircuitNetlist(cv)")
    s.evaluate("dbSave(cv) dbClose(cv)")
    s.evaluate('cv = dbOpenCellViewByType("LIB" "C" "schematic" "schematic" "r")')
    assert json.loads(s.evaluate("mockCircuitRead(cv)"))["name"] == "DIVIDER"
    with pytest.raises(SkillError, match="read-only"):
        s.evaluate(f"mockCircuitLoad(cv {encoded})")
    s.evaluate('cv = dbOpenCellViewByType("LIB" "C" "schematic" "schematic" "w")')
    with pytest.raises(SkillError, match="No circuit"):
        s.evaluate("schCheck(cv)")


def test_failed_load_preserves_last_valid_circuit():
    s = Session()
    s.evaluate('cv = dbOpenCellViewByType("L" "C" "schematic" "schematic" "w")')
    s.evaluate(f"mockCircuitLoad(cv {json.dumps(json.dumps(example()))})")
    with pytest.raises(SkillError):
        s.evaluate('mockCircuitLoad(cv "{}")')
    assert s.evaluate("schCheck(cv)") == [0, 0]
