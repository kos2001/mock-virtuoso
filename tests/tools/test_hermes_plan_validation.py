"""The gate between a language model's output and the design database.

The API server never executes what a planner produced; it executes what
`validate` returned. Everything a model could say that we are unwilling to run
has to die here, so this module is mostly about the rejections. The injection
cases matter most: plan fields are interpolated into SKILL, so a field that
escapes its quoting is arbitrary code against the design.
"""

import importlib

import pytest

api = importlib.import_module("hermes.virtuoso_api_server")
PlanError = api.PlanError


def rect(**over):
    op = {"op": "rect", "layer": "met1", "x0": 0, "y0": 0, "x1": 1, "y1": 1}
    op.update(over)
    return op


# -- what should pass ----------------------------------------------------

def test_a_plain_plan_survives_and_is_normalised():
    out = api.validate({"lib": "STDLIB", "cell": "INV", "ops": [rect()]})
    assert out["lib"], out["cell"] == ("STDLIB", "INV")
    assert out["ops"][0]["op"] == "rect"
    assert out["then"] is None


def test_a_hierarchical_plan_keeps_both_halves():
    out = api.validate({
        "lib": "STDLIB", "cell": "INV", "ops": [rect()],
        "then": {"cell": "TOP", "ops": [
            {"op": "place", "child": "INV", "name": "I0", "x": 0, "y": 0, "orient": "MY"}]},
    })
    assert out["then"]["cell"] == "TOP"
    assert out["then"]["ops"][0]["orient"] == "MY"


# -- injection -----------------------------------------------------------

@pytest.mark.parametrize("field,value", [
    ("cell", 'C") dbDeleteObject(cv) ("'),
    ("lib", 'L" "X'),
])
def test_skill_injection_through_a_name_is_refused(field, value):
    plan = {"lib": "STDLIB", "cell": "INV", "ops": [rect()]}
    plan[field] = value
    with pytest.raises(PlanError, match="simple identifier"):
        api.validate(plan)


def test_skill_injection_through_a_coordinate_is_refused():
    with pytest.raises(PlanError, match="must be a number"):
        api.validate({"lib": "L", "cell": "C",
                      "ops": [rect(x0="0; dbDeleteObject(cv)")]})


def test_an_instance_name_must_be_an_identifier():
    with pytest.raises(PlanError, match="simple identifier"):
        api.validate({"lib": "L", "cell": "C", "ops": [],
                      "then": {"cell": "TOP", "ops": [
                          {"op": "place", "child": "C", "name": 'I0" "evil',
                           "x": 0, "y": 0, "orient": "R0"}]}})


# -- the allow-lists -----------------------------------------------------

def test_an_unknown_layer_is_refused():
    with pytest.raises(PlanError, match="unknown layer"):
        api.validate({"lib": "L", "cell": "C", "ops": [rect(layer="metal47")]})


def test_an_unsupported_op_is_refused():
    with pytest.raises(PlanError, match="unsupported op"):
        api.validate({"lib": "L", "cell": "C", "ops": [{"op": "exec", "cmd": "rm -rf /"}]})


def test_an_unknown_orientation_is_refused():
    with pytest.raises(PlanError, match="orient"):
        api.validate({"lib": "L", "cell": "C", "ops": [],
                      "then": {"cell": "TOP", "ops": [
                          {"op": "place", "child": "C", "name": "I0",
                           "x": 0, "y": 0, "orient": "SIDEWAYS"}]}})


# -- bounds --------------------------------------------------------------

def test_coordinates_out_of_range_are_refused():
    with pytest.raises(PlanError, match="out of range"):
        api.validate({"lib": "L", "cell": "C", "ops": [rect(x1=1e9)]})


def test_a_boolean_is_not_a_coordinate():
    """bool is an int in Python; a plan saying x0=true is not a plan we run."""
    with pytest.raises(PlanError, match="must be a number"):
        api.validate({"lib": "L", "cell": "C", "ops": [rect(x0=True)]})


def test_an_oversized_plan_is_refused():
    with pytest.raises(PlanError, match=f"at most {api.MAX_OPS}"):
        api.validate({"lib": "L", "cell": "C", "ops": [rect()] * (api.MAX_OPS + 1)})


def test_an_empty_plan_is_refused():
    with pytest.raises(PlanError, match="no executable operations"):
        api.validate({"lib": "L", "cell": "C", "ops": []})


# -- the builder -----------------------------------------------------------

def test_every_validated_op_has_a_builder():
    """A validated op with no builder must raise, never be skipped.

    Dropping one silently would mean reporting success for a design missing
    part of what was asked for, which is the failure this project exists to
    eliminate -- and it is a mistake that was actually made here once.
    """
    ops = [
        rect(),
        {"op": "path", "layer": "met1", "points": [[0, 0], [1, 1]], "width": 0.2},
        {"op": "label", "layer": "text", "x": 0, "y": 0, "text": "A", "height": 0.1},
        {"op": "place", "child": "C", "name": "I0", "x": 0, "y": 0, "orient": "R0"},
    ]
    assert {o["op"] for o in ops} == {"rect", "path", "label", "place"}, (
        "this list must stay in step with what the validator accepts")
    for op in ops:
        validated = api._validate_op(op, "op")
        assert api._emit(validated, "LIB"), f"no SKILL emitted for {op['op']}"

    # Vias are not in the API's vocabulary; the validator is where that is said.
    with pytest.raises(PlanError, match="unsupported op"):
        api._validate_op({"op": "via", "name": "M1_M2", "x": 0, "y": 0}, "op")

    with pytest.raises(PlanError, match="no builder"):
        api._emit({"op": "teleport"}, "LIB")
