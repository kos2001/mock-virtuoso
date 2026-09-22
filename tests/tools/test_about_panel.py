"""The introduction panel both front ends mount.

Its failure mode is silent: someone edits a sentence in one language and the
other keeps saying the old thing, or a new entry arrives with only English.
Nothing breaks, so nothing tells you.
"""

import importlib
import re
from pathlib import Path

import pytest

from tests.tools.test_workbench import workbench  # noqa: F401

ABOUT = Path(__file__).resolve().parents[2] / "webapp" / "about.js"


def test_every_entry_carries_both_languages():
    source = ABOUT.read_text(encoding="utf-8")
    ko = len(re.findall(r"(?<![A-Za-z0-9_])ko:", source))
    en = len(re.findall(r"(?<![A-Za-z0-9_])en:", source))
    assert ko == en, f"{ko} Korean entries against {en} English ones"
    assert ko >= 8, "the panel should have more to say than this"


def test_neither_language_is_left_empty():
    source = ABOUT.read_text(encoding="utf-8")
    assert not re.search(r"(?<![A-Za-z0-9_])(ko|en):\s*(\"\"|\[\s*\])", source)


def test_the_two_screens_are_described_separately():
    """Each front end explains itself, not the other one."""
    source = ABOUT.read_text(encoding="utf-8")
    assert "workbench:" in source and "floor:" in source
    assert "recording proxy" in source, "the floor's lane is what makes it worth watching"


def test_the_language_preference_is_read_defensively():
    """localStorage throws in a private window; the panel must still open."""
    source = ABOUT.read_text(encoding="utf-8")
    getter = source[source.index("function aboutLang"):source.index("function mountAbout")]
    assert "try" in getter and "catch" in getter


def test_the_workbench_serves_it(workbench):
    import urllib.request

    with urllib.request.urlopen(workbench + "/about.js", timeout=10) as response:
        assert response.status == 200
        assert "javascript" in response.headers.get("Content-Type", "")
        assert b"function mountAbout" in response.read()


def test_the_floor_serves_it_from_the_same_file():
    """One copy, two hosts — the floor reads the workbench's directory."""
    floor = importlib.import_module("floor.design_floor")
    assert (floor.WEBAPP / "about.js") == ABOUT


@pytest.mark.parametrize("page,marker", [
    ("webapp/index.html", 'mountAbout("workbench")'),
    ("floor/floor.html", 'mountAbout("floor")'),
])
def test_both_pages_load_and_mount_it(page, marker):
    source = (ABOUT.parents[1] / page).read_text(encoding="utf-8")
    assert '<script src="/about.js"></script>' in source
    assert marker in source
