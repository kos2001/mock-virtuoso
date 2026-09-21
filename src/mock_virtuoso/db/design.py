"""열린 셀뷰들과 객체 핸들 레지스트리."""

from __future__ import annotations

import itertools

from mock_virtuoso.db.objects import CellView, DbObject
from mock_virtuoso.skill.errors import SkillError


class Design:
    def __init__(self) -> None:
        self._cellviews: dict[tuple[str, str, str], CellView] = {}
        self._handles: dict[str, DbObject] = {}
        self._counter = itertools.count(0x1000)

    # -- 핸들 ------------------------------------------------------------

    def register(self, obj: DbObject) -> str:
        handle = f"db:0x{next(self._counter):x}"
        obj.handle = handle
        self._handles[handle] = obj
        return handle

    def resolve(self, handle: str) -> DbObject:
        obj = self._handles.get(handle)
        if obj is None:
            raise SkillError(f"stale or unknown object handle: {handle}")
        return obj

    # -- 셀뷰 ------------------------------------------------------------

    @property
    def open_cellviews(self) -> list[CellView]:
        return list(self._cellviews.values())

    def find_cellview(self, lib: str, cell: str, view: str) -> CellView | None:
        return self._cellviews.get((lib, cell, view))

    def open_cellview(self, lib: str, cell: str, view: str,
                      view_type: str, mode: str) -> CellView:
        key = (lib, cell, view)
        existing = self._cellviews.get(key)
        if existing is not None:
            # Update mode and view_type on cache hit (last-open-wins)
            existing.mode = mode
            existing.view_type = view_type
            return existing
        cv = CellView(lib, cell, view, view_type, mode)
        self.register(cv)
        self._cellviews[key] = cv
        return cv

    def close_cellview(self, cv: CellView) -> None:
        key = (cv.get_prop("libName"), cv.get_prop("cellName"),
               cv.get_prop("viewName"))
        self._cellviews.pop(key, None)
        # Unregister handle so resolving closed cellview raises error
        self._handles.pop(cv.handle, None)
