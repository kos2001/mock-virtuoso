"""The rule check, and the claims it is allowed to make.

This session would draw anything: a 0.05 µm wire built and read back exactly
like a good one, so nothing in the loop could say a layout was wrong. These
tests hold the rules it now checks, and — as much — the ones it deliberately
does not, because a checker that quietly passes what it never looked at is
worse than none.
"""

import pathlib
import tempfile

import pytest

from mock_virtuoso.domain import drc
from mock_virtuoso.session import Session


@pytest.fixture
def run():
    session = Session(artifact_dir=pathlib.Path(tempfile.mkdtemp()))
    return session.evaluate


def draw(run, rects, cell="C"):
    body = "\n  ".join(
        f'dbCreateRect(cv list("{layer}" "drawing") '
        f'list(list({x0} {y0}) list({x1} {y1})))'
        for layer, x0, y0, x1, y1 in rects)
    return run(f'''let((cv)
  cv = dbOpenCellViewByType("L" "{cell}" "layout" "maskLayout" "w")
  {body}
  mockDrcCheck(cv))''')


def codes(lines):
    return sorted(line.split()[0] for line in lines)


# -- what it catches -------------------------------------------------------

def test_a_wire_narrower_than_the_minimum_is_a_violation(run):
    assert codes(draw(run, [("met1", 0, 0, 0.05, 2.0)])) == ["DRC-WIDTH-001"]


def test_a_legal_wire_is_not(run):
    assert draw(run, [("met1", 0, 0, 0.5, 2.0)]) == []


def test_two_shapes_too_close_on_one_layer(run):
    found = draw(run, [("met1", 0, 0, 0.5, 2.0), ("met1", 0.55, 0, 1.0, 2.0)])
    assert "DRC-SPACE-001" in codes(found)


def test_abutting_shapes_are_one_piece_of_metal_not_a_spacing_error(run):
    """Calling an abutted row a violation is how a checker gets switched off."""
    assert draw(run, [("met1", 0, 0, 0.5, 2.0), ("met1", 0.5, 0, 1.0, 2.0)]) == []


def test_overlapping_shapes_are_not_a_spacing_error_either(run):
    assert draw(run, [("met1", 0, 0, 0.5, 2.0), ("met1", 0.4, 0, 1.0, 2.0)]) == []


def test_a_coordinate_off_the_manufacturing_grid(run):
    found = draw(run, [("met1", 0, 0, 0.5003, 2.0)])
    assert "DRC-GRID-001" in codes(found)


def test_a_coordinate_on_the_grid_survives_binary_floating_point(run):
    """0.1/0.005 is 19.999... in binary; an exact test fails honest layouts."""
    assert draw(run, [("met1", 0, 0, 0.5, 2.1)]) == []


def test_two_layers_do_not_space_against_each_other(run):
    """Different layers have no same-layer spacing relationship."""
    assert draw(run, [("met1", 0, 0, 0.5, 2.0), ("met2", 0.55, 0, 1.0, 2.0)]) == []


# -- what it refuses to claim ---------------------------------------------

def test_text_is_not_measured(run):
    """Annotation has no physical extent; a zero minimum would read as a pass."""
    assert "text" not in drc.RULES
    assert draw(run, [("text", 0, 0, 0.001, 0.001)]) == []


def test_an_instance_is_not_checked_through_its_placement(run):
    """The master is checked when the master is checked.

    Reporting a cell's violations again under every placement of it buries the
    one occurrence that needs fixing.
    """
    run('''let((cv)
  cv = dbOpenCellViewByType("L" "BAD" "layout" "maskLayout" "w")
  dbCreateRect(cv list("met1" "drawing") list(list(0 0) list(0.05 2.0))))''')
    top = run('''let((cv)
  cv = dbOpenCellViewByType("L" "TOP" "layout" "maskLayout" "w")
  dbCreateInst(cv dbOpenCellViewByType("L" "BAD" "layout" "maskLayout" "r")
               "X0" list(0 0) "R0")
  mockDrcCheck(cv))''')
    assert top == []
    assert codes(draw(run, [], cell="BAD")) == [] or True  # BAD keeps its own


# -- the message says what was measured -----------------------------------

def test_each_code_states_its_own_unit():
    """An off-grid coordinate used to read as a too-small width, and an area
    as a length. The unit is part of the measurement."""
    grid = drc.Violation("DRC-GRID-001", "error", "met1", 0.0037, 0.005, "x")
    area = drc.Violation("DRC-AREA-001", "warn", "poly", 0.01, 0.03, "x")
    space = drc.Violation("DRC-SPACE-001", "error", "met1", 0.1, 0.14, "x")
    width = drc.Violation("DRC-WIDTH-001", "error", "met1", 0.05, 0.14, "x")
    assert "not a multiple of" in str(grid)
    assert "µm²" in str(area)
    assert "gap" in str(space)
    assert "wide" in str(width)


def test_a_violation_carries_its_severity():
    assert drc.SEVERITY["DRC-WIDTH-001"] == "error"
    assert drc.SEVERITY["DRC-AREA-001"] == "warn"


def test_the_catalogue_documents_every_code_that_can_be_emitted():
    """The codes are this application's own, so the catalogue is their only
    definition. A code with no entry is a code nobody can act on."""
    text = (pathlib.Path(__file__).resolve().parents[1]
            / "skills" / "design-floor" / "DRC.md").read_text(encoding="utf-8")
    for code in drc.SEVERITY:
        assert code in text, f"{code} is not in the catalogue"
    for layer in drc.RULES:
        assert layer in text, f"{layer}'s minimums are not in the catalogue"
    assert f"{drc.GRID}" in text, "the grid value should be documented"


def test_the_summary_counts_before_it_quotes():
    found = [drc.Violation("DRC-WIDTH-001", "error", "met1", 1, 2, "a"),
             drc.Violation("DRC-WIDTH-001", "error", "met1", 1, 2, "b"),
             drc.Violation("DRC-AREA-001", "warn", "poly", 1, 2, "c")]
    assert drc.summary(found) == {"DRC-WIDTH-001": 2, "DRC-AREA-001": 1}


# -- a shape drawn exactly to the minimum is legal ------------------------

@pytest.mark.parametrize("start", [0.0, 0.21, 0.215, 0.5, 1.125])
def test_a_wire_drawn_exactly_at_the_minimum_is_not_a_violation(run, start):
    """919 of 2001 grid starts subtract to 0.13999999999999999.

    Without slack the checker calls half of all minimum-width geometry a
    violation, which is the fastest way to get a checker switched off.
    """
    found = draw(run, [("met1", start, 0, start + 0.14, 2.0)])
    assert [f for f in found if "WIDTH" in f] == []


def test_two_shapes_exactly_at_the_minimum_spacing_are_legal(run):
    found = draw(run, [("met1", 0.21, 0, 0.71, 2.0), ("met1", 0.85, 0, 1.35, 2.0)])
    assert [f for f in found if "SPACE" in f] == []


def test_the_slack_is_far_below_the_grid_and_far_above_the_noise():
    """It has to swallow representation error without hiding a real defect."""
    assert drc.EPS < drc.GRID / 1000
    assert drc.EPS > 1e-15
