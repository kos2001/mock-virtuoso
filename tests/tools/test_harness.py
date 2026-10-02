"""Failures observed at model and tool boundaries must stay recoverable."""
import json

import pytest

from toolkit import planner as p


def plan():
    return {"lib": "EVAL", "cell": "WIRE", "ops": [
        {"op": "rect", "layer": "met1", "x0": 0, "y0": 0, "x1": 1, "y1": 1}]}


def response(raw, finish="stop"):
    return {"choices": [{"message": {"content": raw}, "finish_reason": finish}]}


@pytest.mark.parametrize("value", [None, [], {}, {"choices": []},
                                      response(None), response("{}", "length"),
                                      response("{} {}"), response("[]"), response("prose {}")])
def test_invalid_model_envelope_is_a_repairable_error(value):
    with pytest.raises(p.PlanResponseError):
        p.parse_plan_response(value)


def test_fenced_json_is_accepted_without_guessing():
    assert p.parse_plan_response(response("```json\n" + json.dumps(plan()) + "\n```")) == plan()


@pytest.mark.parametrize("patch", [
    {"then": []}, {"then": "TOP"}, {"then": {"ops": 12}}, {"ops": False},
    {"ops": [{"op": "rect", "layer": []}]},
    {"ops": [{"op": "place", "orient": []}]},
    {"ops": [{"op": "pin", "layer": "met1", "dir": []}]},
    {"ops": [{"op": "path", "layer": "met1", "points": [[0], None]}]},
    {"ops": [{"op": "path", "layer": "met1", "points": [[0, 0], [1, 1]], "width": -1}]},
])
def test_malformed_fields_reach_the_repair_loop_instead_of_crashing(patch):
    with pytest.raises(p.PlanError):
        p.validate({**plan(), **patch})


def test_json_repair_retains_original_request_and_response(monkeypatch):
    calls = []
    def model(text, **kwargs):
        calls.append((text, kwargs))
        if len(calls) == 1:
            raise p.PlanResponseError("missing closing brace", '{"cell":"WIRE"')
        return plan(), "hermes"
    monkeypatch.setattr(p, "plan_with_hermes", model)
    trace = []
    result, source = p.plan_and_validate("draw WIRE", trace=trace)
    assert result["cell"] == "WIRE" and source == "hermes (retried)"
    assert [c[0] for c in calls] == ["draw WIRE", "draw WIRE"]
    assert '{"cell":"WIRE"' in calls[1][1]["feedback"]
    assert [a["outcome"] for a in trace] == ["PlanResponseError", "pass"]
    assert all(a["elapsed_s"] >= 0 for a in trace)


def test_strict_hermes_mode_never_claims_a_template_is_model_output(monkeypatch):
    monkeypatch.setattr(p, "plan_with_hermes", lambda *a, **k: (None, "offline"))
    with pytest.raises(p.PlanError, match="unavailable"):
        p.plan_and_validate("INV", allow_fallback=False)


def test_a_missing_drc_result_cannot_win_a_correction(monkeypatch):
    original = p.validate(plan())
    dirty = {"cells": {"WIRE": {"drc": ["DRC-WIDTH [error] thin"]}}}
    missing = {"cells": {"WIRE": {"drc": ["NOT CHECKED — transport error"]}}}
    reports = iter([dirty, missing, dirty])
    monkeypatch.setattr(p, "execute", lambda *a: next(reports))
    monkeypatch.setattr(p, "plan_with_hermes", lambda *a, **k: (plan(), "hermes"))
    trace = []
    kept, report, _ = p.build_and_check(None, "wire", original, "hermes", trace=trace)
    assert kept is original
    assert report["cells"] == dirty["cells"]
    assert trace[-1]["outcome"] == "reverted"


def test_invalid_json_correction_keeps_original_design(monkeypatch):
    original = p.validate(plan())
    dirty = {"cells": {"WIRE": {"drc": ["DRC-WIDTH [error] thin"]}}}
    monkeypatch.setattr(p, "execute", lambda *a: dirty)
    def broken(*a, **k):
        raise p.PlanResponseError("truncated")
    monkeypatch.setattr(p, "plan_with_hermes", broken)
    kept, _, _ = p.build_and_check(None, "wire", original, "hermes")
    assert kept is original
