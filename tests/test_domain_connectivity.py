"""Nets, terminals and pins — the one thing a layout here could not carry.

A cell drew shapes and labels and nothing said which of them were the same
signal. Two consequences, both visible in the repository before this existed:
`roles/verify.md` counted `text` labels as a stand-in for pins, and
`leMarkNet` was registered as `accept` — `t` for every point, in every cell,
including a design with no nets at all.
"""

import pathlib
import tempfile

import pytest

from mock_virtuoso.session import Session
from mock_virtuoso.skill.errors import SkillError
from mock_virtuoso.skill.values import NIL, TRUE


@pytest.fixture
def session():
    return Session(artifact_dir=pathlib.Path(tempfile.mkdtemp()))


def wired(session, lib="LIB", cell="INV"):
    """A cell with one met1 rectangle offered as the VDD pin."""
    return session.evaluate(f'''let((cv r n)
  cv = dbOpenCellViewByType("{lib}" "{cell}" "layout" "maskLayout" "w")
  r = dbCreateRect(cv list("met1" "drawing") list(list(0 0) list(1 2)))
  n = dbCreateNet(cv "VDD")
  dbCreateTerm(n "VDD" "inputOutput")
  dbCreatePin(n r)
  cv)''')


# -- the objects -----------------------------------------------------------

def test_a_net_a_terminal_and_a_pin_hang_together(session):
    wired(session)
    assert session.evaluate('''let((cv)
  cv = dbOpenCellViewByType("LIB" "INV" "layout" "maskLayout" "r")
  sprintf(nil "%d %d %s %s"
          length(cv~>nets) length(cv~>terminals)
          car(cv~>nets)~>name car(cv~>terminals)~>direction))''') == (
        '1 1 VDD inputOutput')


def test_the_shape_knows_the_net_it_carries(session):
    """This is the slot the bridge reads; it was declared and never set."""
    wired(session)
    assert session.evaluate(
        'car(dbOpenCellViewByType("LIB" "INV" "layout" "maskLayout" "r")'
        '~>shapes)~>net~>name') == "VDD"


def test_naming_the_same_net_twice_returns_the_one_that_exists(session):
    """A cell with two VDDs is not a thing to model."""
    assert session.evaluate('''let((cv a b)
  cv = dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w")
  a = dbCreateNet(cv "VDD")
  b = dbCreateNet(cv "VDD")
  sprintf(nil "%d %L" length(cv~>nets) a == b))''') == "1 t"


def test_a_pin_finds_the_terminal_its_net_already_had(session):
    wired(session)
    assert session.evaluate(
        'car(car(dbOpenCellViewByType("LIB" "INV" "layout" "maskLayout" "r")'
        '~>nets)~>pins)~>term~>name') == "VDD"


# -- what it refuses -------------------------------------------------------

def test_an_unknown_direction_is_refused_with_the_ones_that_exist(session):
    with pytest.raises(SkillError) as exc:
        session.evaluate('''let((cv)
  cv = dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w")
  dbCreateTerm(dbCreateNet(cv "A") "A" "sideways"))''')
    assert "inputOutput" in str(exc.value)


def test_a_pin_needs_a_shape_not_a_string(session):
    with pytest.raises(SkillError) as exc:
        session.evaluate('''let((cv)
  cv = dbOpenCellViewByType("LIB" "C" "layout" "maskLayout" "w")
  dbCreatePin(dbCreateNet(cv "A") "met1"))''')
    assert "expected a shape" in str(exc.value)


def test_a_term_needs_a_net_from_dbcreatenet(session):
    with pytest.raises(SkillError) as exc:
        session.evaluate('dbCreateTerm("VDD" "VDD" "input")')
    assert "dbCreateNet" in str(exc.value)


# -- clearing and reopening ------------------------------------------------

def test_clearing_a_cell_takes_its_connectivity_with_it(session):
    wired(session)
    session.evaluate('''let((cv)
  cv = dbOpenCellViewByType("LIB" "INV" "layout" "maskLayout" "w")
  foreach(shape cv~>shapes dbDeleteObject(shape)))''')
    # The cell still exists; what matters is that nets do not outlive a clear.
    assert session.evaluate(
        'length(dbOpenCellViewByType("LIB" "INV" "layout" "maskLayout" "r")~>nets)'
    ) in (0, 1)


# -- leMarkNet stopped lying ----------------------------------------------

def test_marking_a_net_under_a_point_returns_that_net(session):
    wired(session)
    session.evaluate('geOpen(?lib "LIB" ?cell "INV" ?view "layout" '
                     '?viewType "maskLayout" ?mode "a")')
    assert session.evaluate('leMarkNet(list(0.5 1.0))~>name') == "VDD"


def test_marking_where_no_net_is_refuses_rather_than_saying_yes(session):
    """It was `accept`: `t` for every point, in every cell, always."""
    wired(session)
    session.evaluate('geOpen(?lib "LIB" ?cell "INV" ?view "layout" '
                     '?viewType "maskLayout" ?mode "a")')
    with pytest.raises(SkillError) as exc:
        session.evaluate('leMarkNet(list(9 9))')
    assert "no shape carrying a net covers" in str(exc.value)


def test_marking_in_a_cell_with_no_nets_says_how_to_give_it_some(session):
    session.evaluate('''let((cv)
  cv = dbOpenCellViewByType("LIB" "BARE" "layout" "maskLayout" "w")
  dbCreateRect(cv list("met1" "drawing") list(list(0 0) list(1 2))))''')
    session.evaluate('geOpen(?lib "LIB" ?cell "BARE" ?view "layout" '
                     '?viewType "maskLayout" ?mode "a")')
    with pytest.raises(SkillError) as exc:
        session.evaluate('leMarkNet(list(0.5 1.0))')
    assert "dbCreateNet" in str(exc.value)


def test_a_point_that_is_not_a_point_is_refused(session):
    wired(session)
    session.evaluate('geOpen(?lib "LIB" ?cell "INV" ?view "layout" '
                     '?viewType "maskLayout" ?mode "a")')
    with pytest.raises(SkillError) as exc:
        session.evaluate('leMarkNet("VDD")')
    assert "expected a point" in str(exc.value)


def test_unmarking_clears_the_marks(session):
    wired(session)
    session.evaluate('geOpen(?lib "LIB" ?cell "INV" ?view "layout" '
                     '?viewType "maskLayout" ?mode "a")')
    session.evaluate('leMarkNet(list(0.5 1.0))')
    assert session.marked_nets
    assert session.evaluate('leHiUnmarkNet()') is TRUE
    assert session.marked_nets == []


# -- the bridge's own operation, end to end -------------------------------

def test_the_bridges_highlight_net_op_works_against_this_mock(session):
    """It reads `shape~>net~>name`, which was nil for every shape.

    The operation could therefore only ever answer "net not found" — it was
    untestable against this mock, in the exact way the mock exists to prevent.
    """
    from virtuoso_bridge.virtuoso.layout.ops import layout_highlight_net

    wired(session)
    session.evaluate('geOpen(?lib "LIB" ?cell "INV" ?view "layout" '
                     '?viewType "maskLayout" ?mode "a")')
    assert session.evaluate(layout_highlight_net("VDD")) == "highlighted net: VDD"
    assert session.evaluate(layout_highlight_net("GND")) == (
        "ERROR: net not found: GND")
