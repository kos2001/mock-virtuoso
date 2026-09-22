"""Layout 도메인 SKILL 함수."""

from __future__ import annotations

from mock_virtuoso.db.geometry import (
    bbox_of_path,
    bbox_of_points,
    transform_bbox,
    transform_point,
)
from mock_virtuoso.db.objects import CellView, Instance, Shape, TechFile, ViaDef
from mock_virtuoso.domain import drc
from mock_virtuoso.skill.errors import SkillError
from mock_virtuoso.skill.values import NIL, TRUE, skill_repr


def _as_cellview(value) -> CellView:
    if not isinstance(value, CellView):
        raise SkillError("expected a cellView")
    return value


def _lpp(value) -> tuple[str, str]:
    if not isinstance(value, list) or len(value) < 2:
        raise SkillError("expected a layer-purpose pair")
    return value[0], value[1]


def _number(value, what: str) -> float:
    """A SKILL number, or a refusal that names the argument.

    Without this the coercion happens inside the arithmetic and a caller gets
    Python's own wording back -- "unsupported operand type(s) for -: 'str' and
    'float'" names neither the argument nor what it should have been.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SkillError(f"{what} must be a number, got {skill_repr(value)}")
    return float(value)


def _point(value, what: str = "point") -> list[float]:
    if not isinstance(value, list) or len(value) != 2:
        raise SkillError(
            f"expected a {what} like list(x y), got {skill_repr(value)}")
    return [_number(value[0], f"{what} x"), _number(value[1], f"{what} y")]


def _points(value) -> list[list[float]]:
    if not isinstance(value, list) or not value:
        raise SkillError(f"expected a list of points, got {skill_repr(value)}")
    return [_point(p) for p in value]


class DdCellHandle:
    """A ``ddGetObj`` result: a truthy handle onto a known lib/cell pair.

    Minimal on purpose (finding 7): just enough for the bridge's
    ``ddcell = ddGetObj(lib cell) if(ddcell then ddDeleteObj(ddcell) ...)``
    pattern to round-trip honestly. Not registered in Design's handle
    table -- the bridge never stashes this across a request boundary via
    a ``db:0x...`` handle.
    """

    __slots__ = ("lib", "cell", "handle")

    def __init__(self, lib: str, cell: str) -> None:
        self.lib = lib
        self.cell = cell
        self.handle = f"ddcell:{lib}:{cell}"

    def get_prop(self, name: str) -> object:
        if name == "libName":
            return self.lib
        if name == "cellName":
            return self.cell
        raise SkillError(f"DdCellHandle has no slot '{name}'")


# The technology this session offers. Small and fixed, but real: a via can
# only be drawn from one of these, so a layout can never reference a via
# master that does not exist.
VIA_DEFS = (
    ("DIFF_M1", "diff", "met1"),
    ("PO_M1", "poly", "met1"),
    ("M1_M2", "met1", "met2"),
    ("M2_M3", "met2", "met3"),
)


def install(session) -> None:
    design = session.design
    interp = session.interp

    tech_file = TechFile("mockTech", [ViaDef(*spec) for spec in VIA_DEFS])
    design.register(tech_file)
    for via_def in tech_file.get_prop("viaDefs"):
        design.register(via_def)

    def db_open_cellview_by_type(it, args, kwargs):
        lib, cell, view, view_type, mode = (
            args[0], args[1], args[2], args[3],
            args[4] if len(args) > 4 else "r")
        return design.open_cellview(lib, cell, view, view_type, mode)

    def db_open_cellview(it, args, kwargs):
        # dbOpenCellView(lib cell view tech mode) — tech 인자는 무시한다.
        lib, cell, view = args[0], args[1], args[2]
        mode = args[4] if len(args) > 4 else "r"
        return design.open_cellview(lib, cell, view, "maskLayout", mode)

    def db_create_rect(it, args, kwargs):
        cv = _as_cellview(args[0])
        layer, purpose = _lpp(args[1])
        box = _points(args[2])
        shape = Shape("rect", layer, purpose,
                      bbox=bbox_of_points(box))
        design.register(shape)
        cv.shapes.append(shape)
        return shape

    def db_create_path(it, args, kwargs):
        cv = _as_cellview(args[0])
        layer, purpose = _lpp(args[1])
        pts = _points(args[2])
        width = float(args[3])
        shape = Shape("path", layer, purpose,
                      bbox=bbox_of_path(pts, width),
                      points=pts, width=width)
        design.register(shape)
        cv.shapes.append(shape)
        return shape

    def db_create_polygon(it, args, kwargs):
        cv = _as_cellview(args[0])
        layer, purpose = _lpp(args[1])
        pts = _points(args[2])
        shape = Shape("polygon", layer, purpose,
                      bbox=bbox_of_points(pts), points=pts)
        design.register(shape)
        cv.shapes.append(shape)
        return shape

    def db_create_label(it, args, kwargs):
        cv = _as_cellview(args[0])
        layer, purpose = _lpp(args[1])
        xy = _point(args[2])
        text = args[3]
        orient = args[5] if len(args) > 5 else "R0"
        height = _number(args[7], "height") if len(args) > 7 else 0.1
        half = height / 2.0
        shape = Shape("label", layer, purpose,
                      bbox=[[xy[0] - half, xy[1] - half],
                            [xy[0] + half, xy[1] + half]],
                      xy=xy, orient=orient, text=text)
        design.register(shape)
        cv.shapes.append(shape)
        return shape

    def db_create_via(it, args, kwargs):
        cv = _as_cellview(args[0])
        via_def = args[1]
        if not isinstance(via_def, ViaDef):
            # techFindViaDefByName answers nil for a name the technology does
            # not have, and this is where that nil has to stop. Drawing it
            # anyway would put a via on a master that does not exist.
            known = ", ".join(vd.name for vd in tech_file.get_prop("viaDefs"))
            raise SkillError(
                "dbCreateVia: expected a via definition from "
                f"techFindViaDefByName, got {skill_repr(via_def)}; "
                f"this technology has {known}")
        xy = _point(args[2])
        orient = args[3] if len(args) > 3 else "R0"
        shape = Shape("via", "via", "drawing",
                      bbox=[[xy[0], xy[1]], [xy[0], xy[1]]],
                      xy=xy, orient=orient, via_def=via_def)
        design.register(shape)
        cv.shapes.append(shape)
        return shape

    def _reachable_cellviews(start):
        """All cellviews reachable from ``start`` through instance
        masters, including ``start`` itself."""
        visited: set[CellView] = set()
        stack = [start]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            for inst in current.instances:
                master = inst.get_prop("master")
                if isinstance(master, CellView):
                    stack.append(master)
        return visited

    def _add_instance(cv, lib, cell, view, name, xy, orient):
        master = design.find_cellview(lib, cell, view)
        # Real Virtuoso refuses cyclic instance hierarchy at
        # instantiation time: a cellview may not (directly or
        # transitively) instantiate itself. Without this check, an
        # accepted cyclic master turns CellView.bbox composition (and
        # therefore layout_read_geometry/layout_read_summary, both on
        # the bridge's main read path) into a live RecursionError bomb.
        if master is not None and cv in _reachable_cellviews(master):
            raise SkillError(
                "cyclic instance hierarchy: "
                f"{cv.get_prop('libName')}/{cv.get_prop('cellName')}/"
                f"{cv.get_prop('viewName')}")
        inst = Instance(name, lib, cell, view, xy, orient, master)
        design.register(inst)
        cv.instances.append(inst)
        return inst

    def db_create_param_inst_by_master_name(it, args, kwargs):
        cv = _as_cellview(args[0])
        return _add_instance(cv, args[1], args[2], args[3], args[4],
                             _point(args[5]), args[6])

    def db_create_inst(it, args, kwargs):
        cv = _as_cellview(args[0])
        master = args[1]
        if not isinstance(master, CellView):
            raise SkillError("dbCreateInst needs a master cellView")
        return _add_instance(cv, master.get_prop("libName"),
                             master.get_prop("cellName"),
                             master.get_prop("viewName"),
                             args[2], _point(args[3]), args[4])

    def db_create_simple_mosaic(it, args, kwargs):
        cv = _as_cellview(args[0])
        master = args[1]
        base_name = args[2]
        origin = args[3]
        orient = args[4]
        rows, cols = int(args[5]), int(args[6])
        row_pitch, col_pitch = float(args[7]), float(args[8])
        created = []
        for r in range(rows):
            for c in range(cols):
                xy = [origin[0] + c * col_pitch, origin[1] + r * row_pitch]
                name = (f"M_{r}_{c}" if base_name is NIL
                        else f"{base_name}_{r}_{c}")
                created.append(_add_instance(
                    cv, master.get_prop("libName"),
                    master.get_prop("cellName"),
                    master.get_prop("viewName"), name, xy, orient))
        return created

    def db_save(it, args, kwargs):
        cv = _as_cellview(args[0])
        cv.saved = True
        return TRUE

    def db_close(it, args, kwargs):
        design.close_cellview(_as_cellview(args[0]))
        return TRUE

    def db_purge(it, args, kwargs):
        # dbPurge forces a cellview out of memory. It is not a delete: the
        # cell stays in the library and reopening finds it. What dies is the
        # handle, and saying otherwise leaves callers holding one that
        # Virtuoso would have invalidated.
        design.close_cellview(_as_cellview(args[0]))
        return TRUE

    def db_delete_object(it, args, kwargs):
        target = args[0]
        for cv in design.open_cellviews:
            if target in cv.shapes:
                cv.shapes.remove(target)
                return TRUE
            if target in cv.instances:
                cv.instances.remove(target)
                return TRUE
        return NIL

    def db_get_open_cellviews(it, args, kwargs):
        return design.open_cellviews

    def db_get_cellview_dd_id(it, args, kwargs):
        return _as_cellview(args[0])

    def _transform_parts(transform):
        offset = transform[0]
        orient = transform[1]
        return offset, orient

    def db_transform_point(it, args, kwargs):
        offset, orient = _transform_parts(args[1])
        return transform_point(args[0], offset, orient)

    def db_transform_bbox(it, args, kwargs):
        offset, orient = _transform_parts(args[1])
        return transform_bbox(args[0], offset, orient)

    def dd_get_obj(it, args, kwargs):
        # 라이브러리/셀 존재 확인용. design이 실제로 아는 lib/cell일 때만
        # truthy 핸들을 낸다 (finding 7: accept-and-lie 금지).
        lib, cell = args[0], args[1]
        if not design.cell_exists(lib, cell):
            return NIL
        return DdCellHandle(lib, cell)

    def dd_get_obj_read_path(it, args, kwargs):
        # The bridge's get_current_design() calls
        # ddGetObjReadPath(dbGetCellViewDdId(geGetEditCellView())) and
        # splits the result on "/", taking parts[-4:-1] as (lib, cell,
        # view). A real Virtuoso path looks like
        # .../<lib>/<cell>/<view>/... , so this must derive its answer
        # from the cellview it is given rather than an unrelated
        # constant, and end in a trailing separator so those three
        # components land exactly where the bridge expects them.
        obj = args[0] if args else NIL
        if not isinstance(obj, CellView):
            raise SkillError("ddGetObjReadPath needs a cellView")
        lib = obj.get_prop("libName")
        cell = obj.get_prop("cellName")
        view = obj.get_prop("viewName")
        return f"{session.artifact_dir}/{lib}/{cell}/{view}/"

    def dd_delete_obj(it, args, kwargs):
        ddcell = args[0]
        if (isinstance(ddcell, DdCellHandle)
                and design.cell_exists(ddcell.lib, ddcell.cell)):
            design.forget_cell(ddcell.lib, ddcell.cell)
            return TRUE
        return NIL

    def tech_get_tech_file(it, args, kwargs):
        return tech_file

    def mock_drc_check(it, args, kwargs):
        """This session's own rule check. Not Cadence SKILL, and named so.

        Called `mockDrcCheck` rather than anything Assura- or PVS-shaped
        because an agent that learns it here will write it somewhere else,
        and a plausible-looking name would be a lie that travels.
        """
        cv = _as_cellview(args[0] if args else NIL)
        found = drc.check(cv)
        if not found:
            return []
        return [str(v) for v in found]

    def tech_find_via_def_by_name(it, args, kwargs):
        target = args[0] if args else NIL
        if not isinstance(target, TechFile):
            raise SkillError(
                "techFindViaDefByName: expected a tech file from "
                f"techGetTechFile, got {skill_repr(target)}")
        found = target.find_via_def(args[1] if len(args) > 1 else NIL)
        return found if found is not None else NIL

    for name, fn in (
        ("dbOpenCellViewByType", db_open_cellview_by_type),
        ("dbOpenCellView", db_open_cellview),
        ("dbCreateRect", db_create_rect),
        ("dbCreatePath", db_create_path),
        ("dbCreatePolygon", db_create_polygon),
        ("dbCreateLabel", db_create_label),
        ("dbCreateVia", db_create_via),
        ("dbCreateInst", db_create_inst),
        ("dbCreateParamInstByMasterName", db_create_param_inst_by_master_name),
        ("dbCreateSimpleMosaic", db_create_simple_mosaic),
        ("dbSave", db_save),
        ("dbClose", db_close),
        ("dbPurge", db_purge),
        ("dbDeleteObject", db_delete_object),
        ("dbGetOpenCellViews", db_get_open_cellviews),
        ("dbGetCellViewDdId", db_get_cellview_dd_id),
        ("dbTransformPoint", db_transform_point),
        ("dbTransformBBox", db_transform_bbox),
        ("ddGetObj", dd_get_obj),
        ("ddGetObjReadPath", dd_get_obj_read_path),
        ("ddDeleteObj", dd_delete_obj),
        ("mockDrcCheck", mock_drc_check),
        ("techGetTechFile", tech_get_tech_file),
        ("techFindViaDefByName", tech_find_via_def_by_name),
    ):
        interp.register(name, fn)
