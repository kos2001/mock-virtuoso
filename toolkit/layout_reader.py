"""Reading a cellview back in the shape a canvas can draw.

Rows as `layout_read_geometry` reports them, plus each instance master's shapes
so the renderer can draw hierarchy. Two front ends had a copy of this each,
which had already drifted — one returned a `masters` key on the error path and
the other did not. One of those front ends has since been retired; the reader
stayed here, because the OpenAI server reads the same way.
"""

from __future__ import annotations

from typing import Any

from virtuoso_bridge import ExecutionStatus
from virtuoso_bridge.virtuoso.layout import (
    layout_read_geometry,
    parse_layout_geometry_output,
)


def read_layout(client: Any, lib: str, cell: str) -> dict:
    """`{ok, rows, masters}` for *lib/cell*, ready for the shared renderer.

    Coordinates arrive as tuples and strings arrive still quoted, neither of
    which survives a trip through JSON the way a canvas wants, so both are
    normalised here. Instance masters are read recursively and returned
    alongside, keyed "LIB/CELL"; a cell nobody drew simply reports no rows,
    which is not an error.
    """
    result = client.execute_skill(layout_read_geometry(lib, cell))
    if result.status is not ExecutionStatus.SUCCESS:
        return {"ok": False, "errors": result.errors, "rows": [], "masters": {}}

    rows = []
    for raw in parse_layout_geometry_output(result.output or ""):
        row = dict(raw)
        for key in ("bbox", "points", "xy"):
            value = row.get(key)
            if value is not None:
                row[key] = [list(p) for p in value] if isinstance(value, list) else list(value)
        for key in ("orient", "text"):
            if isinstance(row.get(key), str):
                row[key] = row[key].strip('"')
        rows.append(row)

    masters: dict[str, list] = {}
    for row in rows:
        if row.get("kind") != "instance":
            continue
        key = f"{row.get('lib')}/{row.get('cell')}"
        if key not in masters:
            sub = read_layout(client, row.get("lib"), row.get("cell"))
            masters[key] = [s for s in sub["rows"] if s.get("kind") == "shape"]
    return {"ok": True, "rows": rows, "masters": masters}
