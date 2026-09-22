"""The introduction panel both front ends mount.

Its failure mode is silent: someone edits a sentence in one language and the
other keeps saying the old thing, or a new entry arrives with only English.
Nothing breaks, so nothing tells you.
"""

import importlib
import re
from pathlib import Path

import pytest

ABOUT = Path(__file__).resolve().parents[2] / "toolkit" / "static" / "about.js"


def test_every_entry_carries_both_languages():
    source = ABOUT.read_text(encoding="utf-8")
    ko = len(re.findall(r"(?<![A-Za-z0-9_])ko:", source))
    en = len(re.findall(r"(?<![A-Za-z0-9_])en:", source))
    assert ko == en, f"{ko} Korean entries against {en} English ones"
    assert ko >= 8, "the panel should have more to say than this"


def test_neither_language_is_left_empty():
    source = ABOUT.read_text(encoding="utf-8")
    assert not re.search(r"(?<![A-Za-z0-9_])(ko|en):\s*(\"\"|\[\s*\])", source)


def test_the_one_screen_describes_itself():
    """There is one front end now; the panel should not still offer two."""
    source = ABOUT.read_text(encoding="utf-8")
    assert "floor:" in source
    assert "workbench:" not in source, "the workbench was retired"
    assert "recording proxy" in source, "the floor's lane is what makes it worth watching"


def test_the_language_preference_is_read_defensively():
    """localStorage throws in a private window; the panel must still open."""
    source = ABOUT.read_text(encoding="utf-8")
    getter = source[source.index("function aboutLang"):source.index("function mountAbout")]
    assert "try" in getter and "catch" in getter


def test_the_floor_serves_it():
    floor = importlib.import_module("floor.design_floor")
    assert (floor.STATIC / "about.js") == ABOUT


def test_the_page_loads_and_mounts_it():
    source = (ABOUT.parents[2] / "floor" / "floor.html").read_text(encoding="utf-8")
    assert '<script src="/about.js"></script>' in source
    assert 'mountAbout("floor")' in source
