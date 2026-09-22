"""The knowledge base reaching the prompt that needs it.

Seventeen cases recorded how this floor fails, and none of them reached the
planner: every request was planned cold. These tests hold the two paths that
fixed that — standing lessons before planning, matching cases after a refusal
— and the one property that makes either worth having: a case is retrieved
because it matches something, and can say what.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from toolkit import precedent  # noqa: E402


def case(**fields):
    base = {"id": "000-x", "outcome": "failure", "lanes": "all",
            "audience": "agent", "rule": "none", "rule_in": "none",
            "body": "# A title\n\nprose", "path": Path("000-x.md")}
    base.update(fields)
    return base


# -- what a case is worth quoting for -------------------------------------

def test_a_lesson_is_the_rule_the_case_produced():
    assert precedent.lesson(case(rule="`MY` mirrors about the origin")) == (
        "`MY` mirrors about the origin")


def test_a_case_with_no_rule_still_has_something_to_say():
    """Dropping it would lose a real failure over a missing field."""
    assert precedent.lesson(case(rule="none")) == "A title"


# -- guidance: before planning --------------------------------------------

def test_only_planner_cases_reach_the_planner():
    """Most cases teach an agent writing SKILL by hand.

    `foreach` cannot count is a true and expensive lesson, and it is noise in
    a prompt that emits JSON ops. A block nobody can finish reading teaches
    nothing, so audience is the filter.
    """
    block = precedent.guidance_block([
        case(id="a", rule="`MY` mirrors about the origin", audience="agent, planner"),
        case(id="b", rule="`foreach` walks a list and cannot count", audience="agent"),
    ])
    assert "MY` mirrors" in block
    assert "foreach" not in block


def test_guidance_is_empty_rather_than_a_heading_with_nothing_under_it():
    assert precedent.guidance_block([case(audience="agent")]) == ""


def test_the_real_knowledge_base_offers_the_planner_something():
    assert "MY` mirrors about the origin" in precedent.guidance_block()


# -- precedent: after a refusal -------------------------------------------

def test_a_case_is_retrieved_by_matching_the_error_not_by_resembling_it():
    found = precedent.matching("ops[3]: height must be a number, got 'roman'", [
        case(id="hit", signature="must be a number, got"),
        case(id="miss", signature="has no slot"),
    ])
    assert [c["id"] for c in found] == ["hit"]


def test_matching_ignores_case_because_tools_do_not_agree_on_it():
    assert precedent.matching("Has No Slot 'x'", [case(signature="has no slot")])


def test_a_case_with_no_signature_is_never_retrieved():
    """A signature is the claim that this case can be recognised again."""
    assert precedent.matching("anything at all", [case(rule="a lesson")]) == []


def test_a_precedent_block_names_the_case_it_came_from():
    """Retrieval that cannot say why it retrieved is a similarity score."""
    block = precedent.precedent_block("has no slot 'layerName'", [
        case(id="002-guessing-object-slots", signature="has no slot",
             rule="shapes carry `lpp`")])
    assert "002-guessing-object-slots" in block and "lpp" in block


def test_nothing_known_says_nothing():
    assert precedent.precedent_block("a failure nobody has seen", []) == ""


def test_the_real_knowledge_base_recognises_the_validators_own_words():
    """The validator and the case were written to say the same thing."""
    block = precedent.precedent_block('height must be a number, got "roman"')
    assert block, "a real refusal should find its recorded case"


# -- the audience contract -------------------------------------------------

@pytest.mark.parametrize("c", precedent.load_cases(), ids=lambda c: c["id"])
def test_every_case_says_who_it_is_for(c):
    got = precedent.audiences(c)
    assert got, f"{c['id']} has no audience"
    unknown = set(got) - set(precedent.AUDIENCES)
    assert not unknown, f"{c['id']} claims an audience nobody reads: {unknown}"
