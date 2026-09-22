"""The knowledge base, and the promise each case makes.

A case that records a lesson and leaves it there is a diary. What makes this a
knowledge base is that a case names the rule it produced and where that rule
lives, and these tests check the rule is really there — so a rule cannot be
quietly dropped from a skill while a case goes on claiming it.
"""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "skills" / "design-floor" / "kb"
CASES = KB / "cases"
SRC = ROOT / "src"

sys.path.insert(0, str(ROOT))
from floor.harvest import (group_failures, load_cases, match_case,  # noqa: E402
                           template)

ALL = load_cases(CASES)
REQUIRED = ("id", "outcome", "lanes", "audience", "rule", "rule_in")


def ids(case):
    return case["id"]


def test_there_are_cases_at_all():
    assert len(ALL) >= 8, "a knowledge base of three cases is a note"


@pytest.mark.parametrize("case", ALL, ids=ids)
def test_a_case_carries_its_front_matter(case):
    for key in REQUIRED:
        assert key in case, f"{case['path'].name} has no {key}"
    assert case["outcome"] in ("success", "failure")
    assert case["body"], "a case with no prose records nothing"


@pytest.mark.parametrize("case", ALL, ids=ids)
def test_a_case_id_matches_its_filename(case):
    assert case["path"].stem == case["id"]


def test_case_ids_are_unique_and_numbered_in_order():
    numbers = [int(case["id"].split("-")[0]) for case in ALL]
    assert len(set(numbers)) == len(numbers), "two cases share a number"
    assert numbers == sorted(numbers)


@pytest.mark.parametrize("case", [c for c in ALL if c.get("signature")], ids=ids)
def test_a_signature_is_a_usable_regex(case):
    re.compile(case["signature"])


@pytest.mark.parametrize("case", [c for c in ALL if c["rule"] != "none"], ids=ids)
def test_the_rule_a_case_claims_is_where_it_says_it_is(case):
    """The whole point: a case's lesson has to be somewhere an agent reads."""
    # Skills are wrapped prose, so a rule sentence usually spans a line break.
    # Compare on collapsed whitespace: the words are the promise, not the wrap.
    flat = lambda s: " ".join(s.split())
    rule, where = flat(case["rule"]), case["rule_in"]
    if where == "code":
        # A lesson often lands in code rather than in a document, and which
        # directory hardly matters to a reader — naming them separately just
        # made the field easy to file wrongly, three times.
        roots = [ROOT / d for d in ("src", "toolkit", "floor", "hermes", "demo")]
        files = [f for root in roots for pattern in ("*.py", "*.js", "*.html")
                 for f in root.rglob(pattern)]
        haystack = flat("\n".join(f.read_text(encoding="utf-8") for f in files))
        location = "the code"
    else:
        # rule_in is relative to the skill root, not to the case file
        target = (KB.parent / where).resolve()
        assert target.is_file(), f"{case['id']} points at {where}, which does not exist"
        haystack = flat(target.read_text(encoding="utf-8"))
        location = str(target.relative_to(ROOT))
    assert rule in haystack, f"{case['id']} claims a rule that is not in {location}: {rule!r}"


@pytest.mark.parametrize("case", [c for c in ALL if c["rule"] == "none"], ids=ids)
def test_a_case_with_no_rule_says_why(case):
    """Deciding not to act is a decision; it belongs in the case."""
    assert case["rule_in"] == "none"
    assert re.search(r"not acted on|No rule|no rule", case["body"], re.I), (
        "a case that produced no rule should say why not")


# -- the harvester ---------------------------------------------------------

def test_the_harvester_groups_by_lesson_not_by_wording():
    """Two agents guessing two slot names is one lesson."""
    grouped = group_failures([
        {"ok": False, "reply": "Shape has no slot 'layerName'; it has objType, lpp"},
        {"ok": False, "reply": "Shape has no slot 'purpose'; it has objType, lpp"},
        {"ok": True, "reply": "3"},
    ])
    assert list(grouped.values()) == [2], grouped


def test_the_harvester_finds_the_case_for_a_known_failure():
    reply = "Shape has no slot '…'; it has objType, lpp, bBox"
    assert match_case(reply, ALL)["id"] == "002-guessing-object-slots"


def test_the_harvester_admits_when_it_has_no_case():
    assert match_case("something nobody has ever seen before", ALL) is None


def test_the_template_offers_every_field_the_suite_requires():
    """Harvest says which case to write; it should say what a case needs.

    The fields are checked here and were described only in the README, so the
    loop was: read the output here, write the case there, learn from a red
    test which field was forgotten. A seventh required field must appear in
    the template too, or this fails.
    """
    printed = template(19)
    for key in REQUIRED + ("signature",):
        assert key in printed, f"the harvest template should offer {key}"
    assert "019-" in printed, "the template should carry the next number"


def test_the_readme_explains_the_loop():
    text = (KB / "README.md").read_text(encoding="utf-8")
    assert "harvest.py" in text
    for key in REQUIRED + ("signature",):
        assert key in text, f"the README should describe the {key} field"
