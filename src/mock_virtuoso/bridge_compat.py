"""Helpers for programs that drive this mock through virtuoso-bridge.

Nothing here imports the bridge — everything is duck-typed on a client object
the caller already has — so the package keeps standing on its own. It lives
with the mock because the bundled tools (`webapp/`, `floor/`, `hermes/`,
`demo/`) all need the same accommodation, and one copy is better than four.
"""

from __future__ import annotations

from typing import Any


def build_layout(client: Any, lib: str, cell: str, view: str = "layout") -> Any:
    """A layout editor for building *cell* from scratch, across bridge versions.

    The bridge used to expose a single `layout.edit()` whose default mode was
    "w". Newer versions deprecate it in favour of an explicit `create()` (mode
    "w", replacing any existing view) and `modify()` (mode "a"), and flipped
    `edit()`'s own default to "a" on the way past.

    That flip is the reason this exists: a caller that says `edit(lib, cell)`
    and means "build this cell" silently starts appending to the previous
    build on a newer bridge, so running the same request twice doubles the
    geometry. Asking for `create()` when it is there says what was always
    meant, and falling back to `edit()` keeps older bridges working.
    """
    create = getattr(client.layout, "create", None)
    if create is not None:
        return create(lib, cell, view)
    return client.layout.edit(lib, cell, view, mode="w")


_CLEAR_SKILL = (
    'let((cv) cv = dbOpenCellViewByType("{lib}" "{cell}" "{view}" "maskLayout" "a") '
    "foreach(s cv~>shapes dbDeleteObject(s)) "
    "foreach(i cv~>instances dbDeleteObject(i)) "
    "length(cv~>shapes) + length(cv~>instances))"
)


def clear_layout(client: Any, lib: str, cell: str, view: str = "layout",
                 *, attempts: int = 12) -> bool:
    """Empty a cellview before rebuilding it. True once it reports empty.

    A layout editor binds the cellview already open in a window when there is
    one, so asking to open in "w" mode does not necessarily get you an empty
    cell -- that is how Virtuoso behaves too. A tool that means "build this
    cell from scratch" therefore has to clear it itself.

    `foreach` walks the live list while `dbDeleteObject` removes from it, so a
    single pass can step over entries. Repeat until the cellview says it holds
    nothing rather than trusting one sweep.
    """
    skill = _CLEAR_SKILL.format(lib=lib, cell=cell, view=view)
    for _ in range(attempts):
        result = client.execute_skill(skill)
        remaining = (getattr(result, "output", "") or "").strip()
        if remaining in ("0", '"0"'):
            return True
        if getattr(getattr(result, "status", None), "value", None) != "success":
            return False
    return False
