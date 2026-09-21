"""한 mock 프로세스의 전체 상태."""

from __future__ import annotations

from pathlib import Path

from mock_virtuoso.db.design import Design
from mock_virtuoso.skill.evaluator import Interpreter


class Window:
    """열린 Virtuoso 윈도우 하나."""

    __slots__ = ("number", "name", "cellview")

    def __init__(self, number: int, name: str, cellview) -> None:
        self.number = number
        self.name = name
        self.cellview = cellview


class Session:
    def __init__(self, *, artifact_dir: Path | str | None = None,
                 step_budget: int = 2_000_000) -> None:
        self.design = Design()
        self.interp = Interpreter(step_budget=step_budget)
        self.windows: list[Window] = []
        self.palette: dict[tuple[str, str], bool] = {}
        self.active_lpp: tuple[str, str] | None = None
        self.selection: list = []
        self.artifact_dir = Path(artifact_dir) if artifact_dir else Path.cwd()

        # 핸들 해석을 Design에 연결한다. 인터프리터는 DB를 모르고,
        # 이 한 줄만이 둘을 잇는다.
        self.interp.resolve_handle = self.design.resolve

        from mock_virtuoso.domain import layout, windows as windows_domain
        layout.install(self)
        windows_domain.install(self)

    def evaluate(self, source: str) -> object:
        return self.interp.evaluate_source(source)
