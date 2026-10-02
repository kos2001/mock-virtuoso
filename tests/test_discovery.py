import json

import pytest

from mock_virtuoso.session import Session
from mock_virtuoso.skill.errors import SkillError


def test_discovery_lists_runtime_functions_and_discloses_noops():
    session = Session()
    report = json.loads(session.evaluate("mockCapabilities()"))
    assert report["backend"] == "mock-virtuoso"
    assert {"mockInspectCell", "mockCircuitERC", "schCheck", "let"} <= set(report["functions"])
    assert "maeRunSimulation" not in report["functions"]
    assert set(report["accepted_noops"]) <= set(report["functions"])
    session.interp.register("testNewFunction", lambda *_: None)
    assert "testNewFunction" in json.loads(session.evaluate("mockCapabilities()"))["functions"]


def test_inspection_does_not_create_absent_cell_or_open_closed_cell():
    session = Session()
    absent = json.loads(session.evaluate('mockInspectCell("LIB" "CELL" "layout")'))
    assert absent["exists"] is False
    assert "counts" not in absent
    assert not session.design.cell_exists("LIB", "CELL")
    session.evaluate('cv = dbOpenCellViewByType("LIB" "CELL" "layout" "maskLayout" "a")')
    cv = session.design.find_cellview("LIB", "CELL", "layout")
    session.evaluate('dbCreateRect(cv list("met1" "drawing") list(0:0 4:2))')
    session.evaluate('dbClose(cv)')
    assert session.evaluate('dbGetOpenCellViews()') == []
    report = json.loads(session.evaluate('mockInspectCell("LIB" "CELL" "layout")'))
    assert report["exists"] and report["counts"]["shapes"] == 1
    assert report["layers"] == {"met1/drawing": 1}
    assert report["bbox"] == [[0, 0], [4, 2]]
    assert report["verification"] == "not_run"
    assert cv.mode == "a"
    assert session.evaluate('dbGetOpenCellViews()') == []
    assert session.windows == []


@pytest.mark.parametrize("expression", ["mockCapabilities(1)", "mockInspectCell()",
                         'mockInspectCell("LIB" "CELL" 1)', 'mockInspectCell("" "CELL" "layout")'])
def test_bad_discovery_arguments_are_skill_errors(expression):
    with pytest.raises(SkillError):
        Session().evaluate(expression)
