"""한 mock 프로세스의 전체 상태."""

from __future__ import annotations

import tempfile
from pathlib import Path

from mock_virtuoso.db.design import Design
from mock_virtuoso.db.objects import DbObject
from mock_virtuoso.skill.evaluator import Interpreter


class Window(DbObject):
    """열린 Virtuoso 윈도우 하나."""

    _SLOTS = ("cellView", "windowName", "windowNumber")

    def __init__(self, number: int, name: str, cellview) -> None:
        super().__init__()
        self.number = number
        self.name = name
        self.cellview = cellview
        self._slot_cellView = cellview
        self._slot_windowName = name
        self._slot_windowNumber = number


class Session:
    def __init__(self, *, artifact_dir: Path | str | None = None,
                 step_budget: int = 2_000_000) -> None:
        self.design = Design()
        self.interp = Interpreter(step_budget=step_budget)
        self.windows: list[Window] = []
        self.palette: dict[tuple[str, str], bool] = {}
        self.active_lpp: tuple[str, str] | None = None
        self.selection: list = []
        self.artifact_dir = (
            Path(artifact_dir) if artifact_dir
            else Path(tempfile.gettempdir()) / "mock-virtuoso")

        # 핸들 해석을 Design에 연결한다. 인터프리터는 DB를 모르고,
        # 이 한 줄만이 둘을 잇는다.
        self.interp.resolve_handle = self.design.resolve

        from mock_virtuoso.domain import layout, windows as windows_domain
        layout.install(self)
        windows_domain.install(self)

    def evaluate(self, source: str) -> object:
        return self.interp.evaluate_source(source)

    def open_window(self, cellview) -> Window:
        number = len(self.windows) + 1
        name = (f"{cellview.get_prop('libName')} "
                f"{cellview.get_prop('cellName')} "
                f"{cellview.get_prop('viewName')}")
        window = Window(number, name, cellview)
        self.design.register(window)
        self.windows.append(window)
        return window
