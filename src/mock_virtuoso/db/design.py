"""열린 셀뷰들과 객체 핸들 레지스트리."""

from __future__ import annotations

import itertools

from mock_virtuoso.db.objects import CellView, DbObject
from mock_virtuoso.skill.errors import SkillError


class Design:
    def __init__(self) -> None:
        # The library on disk: what each cellview contains, whether or not it
        # is currently open. Closing a cellview releases the handle; it does
        # not empty the cell.
        self._stored: dict[tuple[str, str, str], CellView] = {}
        # The cellviews open right now, which is what dbGetOpenCellViews and
        # object deletion work against.
        self._cellviews: dict[tuple[str, str, str], CellView] = {}
        self._handles: dict[str, DbObject] = {}
        self._counter = itertools.count(0x1000)
        # Cells the library manager knows about, independent of whether a
        # view is currently open in an editor window (closing a window
        # does not delete the cell from the library). Populated by
        # open_cellview, consulted/mutated by ddGetObj/ddDeleteObj.
        self._known_cells: set[tuple[str, str]] = set()

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

    def unregister(self, obj: DbObject) -> None:
        self._handles.pop(obj.handle, None)

    # -- 셀뷰 ------------------------------------------------------------

    @property
    def open_cellviews(self) -> list[CellView]:
        return list(self._cellviews.values())

    def find_cellview(self, lib: str, cell: str, view: str) -> CellView | None:
        """The stored cellview, open or not — a master is instantiable either way."""
        return self._stored.get((lib, cell, view))

    def cell_exists(self, lib: str, cell: str) -> bool:
        return (lib, cell) in self._known_cells

    def forget_cell(self, lib: str, cell: str) -> None:
        self._known_cells.discard((lib, cell))

    def open_cellview(self, lib: str, cell: str, view: str,
                      view_type: str, mode: str) -> CellView:
        self._known_cells.add((lib, cell))
        key = (lib, cell, view)
        existing = self._cellviews.get(key)
        if existing is not None:
            # Update mode and view_type on cache hit (last-open-wins)
            existing.mode = mode
            existing.view_type = view_type
            return existing
        cv = CellView(lib, cell, view, view_type, mode)
        stored = self._stored.get(key)
        if stored is not None:
            # Reopening the same cell: a fresh cellview object with a fresh
            # handle, holding the geometry that was already there. The lists
            # are shared rather than copied, so the stored cellview and the
            # open one remain one cell.
            cv.adopt_contents(stored)
        self.register(cv)
        self._cellviews[key] = cv
        self._stored[key] = cv
        return cv

    def close_cellview(self, cv: CellView) -> None:
        key = (cv.get_prop("libName"), cv.get_prop("cellName"),
               cv.get_prop("viewName"))
        # Only the open set loses it; `_stored` keeps the cell's contents.
        self._cellviews.pop(key, None)
        # Unregister handle so resolving closed cellview raises error
        self.unregister(cv)
