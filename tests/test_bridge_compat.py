"""Choosing a layout editor across bridge versions.

These use stand-ins rather than a bridge: the helper is duck-typed on purpose,
so the package keeps working with no bridge installed, and the behaviour worth
pinning is which method gets called with what.
"""

from mock_virtuoso.bridge_compat import build_layout, clear_layout


class _Layout:
    def __init__(self, *, has_create):
        self.calls = []
        if has_create:
            self.create = self._create

    def _create(self, lib, cell, view):
        self.calls.append(("create", lib, cell, view, None))
        return "editor"

    def edit(self, lib, cell, view="layout", mode="a", timeout=60):
        self.calls.append(("edit", lib, cell, view, mode))
        return "editor"


class _Client:
    def __init__(self, *, has_create):
        self.layout = _Layout(has_create=has_create)


def test_a_newer_bridge_is_asked_to_create():
    client = _Client(has_create=True)
    assert build_layout(client, "LIB", "CELL") == "editor"
    assert client.layout.calls == [("create", "LIB", "CELL", "layout", None)]


def test_an_older_bridge_falls_back_to_edit_in_write_mode():
    """The fallback must say mode="w" out loud.

    Older bridges defaulted edit() to "w" and newer ones to "a", so relying on
    the default is how the same call quietly turns from "build this cell" into
    "add to whatever is already there".
    """
    client = _Client(has_create=False)
    assert build_layout(client, "LIB", "CELL") == "editor"
    assert client.layout.calls == [("edit", "LIB", "CELL", "layout", "w")]


def test_the_view_is_passed_through():
    for has_create in (True, False):
        client = _Client(has_create=has_create)
        build_layout(client, "LIB", "CELL", "abstract")
        assert client.layout.calls[0][3] == "abstract"


# -- clearing a cellview ---------------------------------------------------

class _Result:
    def __init__(self, output, ok=True):
        self.output = output
        self.status = type("S", (), {"value": "success" if ok else "error"})()


class _Sweeper:
    """A daemon whose first sweeps leave some objects behind, as foreach does."""

    def __init__(self, remaining):
        self.remaining = list(remaining)
        self.skills = []

    def execute_skill(self, skill):
        self.skills.append(skill)
        return _Result(str(self.remaining.pop(0)))


def test_clearing_repeats_until_the_cellview_reports_empty():
    client = _Sweeper([3, 1, 0])
    assert clear_layout(client, "LIB", "CELL") is True
    assert len(client.skills) == 3
    assert 'dbOpenCellViewByType("LIB" "CELL" "layout"' in client.skills[0]


def test_clearing_gives_up_rather_than_looping_forever():
    client = _Sweeper([1] * 20)
    assert clear_layout(client, "LIB", "CELL", attempts=4) is False
    assert len(client.skills) == 4


def test_clearing_stops_when_the_daemon_reports_an_error():
    class _Broken:
        def __init__(self):
            self.calls = 0

        def execute_skill(self, skill):
            self.calls += 1
            return _Result("", ok=False)

    client = _Broken()
    assert clear_layout(client, "LIB", "CELL") is False
    assert client.calls == 1, "a failing daemon should not be swept twelve times"


def test_error_output_zero_is_not_success():
    class Broken:
        def execute_skill(self, source):
            return _Result("0", ok=False)
    assert clear_layout(Broken(), "LIB", "CELL") is False


def test_clear_quotes_identifiers_instead_of_executing_them():
    from mock_virtuoso.session import Session
    session = Session()

    class Local:
        def execute_skill(self, source):
            return _Result(str(session.evaluate(source)))

    name = 'CELL" unexpectedFunction() "'
    assert clear_layout(Local(), "LIB", name)
    assert session.design.cell_exists("LIB", name)
