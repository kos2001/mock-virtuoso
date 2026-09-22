"""The briefs the floor's agents work from.

Lanes are declared in `floor/design_floor.py`; each one's brief is a file in
`skills/design-floor/roles/`. Adding a lane without its brief leaves an agent
with nothing to read, and a brief with no lane is a file nobody opens. Neither
breaks anything, so neither announces itself.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "design-floor" / "SKILL.md"
ROLES = SKILL.parent / "roles"


def lane_names() -> set[str]:
    source = (ROOT / "floor" / "design_floor.py").read_text(encoding="utf-8")
    block = source[source.index("LANES: dict[str, str] = {"):]
    block = block[:block.index("}")]
    return set(re.findall(r'"([a-z]+)":', block))


def test_every_lane_has_a_brief():
    assert lane_names() == {p.stem for p in ROLES.glob("*.md")}


def test_the_skill_has_frontmatter_naming_itself():
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    front = text.split("---", 2)[1]
    assert re.search(r"^name:\s*design-floor\s*$", front, re.M)
    assert re.search(r"^description:\s*\".+\"\s*$", front, re.M)


def test_the_skill_names_every_lane_in_its_trigger():
    """An agent handed a lane name should be able to find this skill by it."""
    front = SKILL.read_text(encoding="utf-8").split("---", 2)[1]
    for lane in lane_names():
        assert lane in front, f"lane {lane} is not in the skill's description"


@pytest.mark.parametrize("brief", sorted(ROLES.glob("*.md")), ids=lambda p: p.stem)
def test_each_brief_says_what_it_owns_and_what_to_report(brief):
    text = brief.read_text(encoding="utf-8")
    assert text.startswith(f"# Lane `{brief.stem}`"), "a brief should name its lane first"
    assert "## Report" in text, "every brief ends by saying what to hand back"
    assert "own" in text.lower(), "a brief should say which cells the lane owns"


def test_the_shared_skill_carries_the_house_rules():
    """The rules that stop an agent silently destroying a colleague's work."""
    text = SKILL.read_text(encoding="utf-8")
    for rule in ("dbClose", "read back", "Touch only the cells"):
        assert rule in text, f"the shared skill should state: {rule}"


def test_the_technology_in_the_skill_matches_the_mock():
    """A brief that promises a via the technology lacks sends agents at a wall."""
    from mock_virtuoso.domain.layout import VIA_DEFS

    text = SKILL.read_text(encoding="utf-8")
    for name, layer1, layer2 in VIA_DEFS:
        assert name in text, f"{name} is in the technology but not in the skill"
        for layer in (layer1, layer2):
            assert f"`{layer}`" in text, f"{layer} is in the technology but not in the skill"
