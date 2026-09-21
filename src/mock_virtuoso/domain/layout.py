"""Layout 도메인 SKILL 함수."""

from __future__ import annotations

from mock_virtuoso.db.geometry import (
    bbox_of_path,
    bbox_of_points,
    transform_bbox,
    transform_point,
)
from mock_virtuoso.db.objects import CellView, Instance, Shape
from mock_virtuoso.skill.errors import SkillError
from mock_virtuoso.skill.values import NIL, TRUE


def _as_cellview(value) -> CellView:
    if not isinstance(value, CellView):
        raise SkillError("expected a cellView")
    return value


def _lpp(value) -> tuple[str, str]:
    if not isinstance(value, list) or len(value) < 2:
        raise SkillError("expected a layer-purpose pair")
    return value[0], value[1]


def _points(value) -> list[list[float]]:
    if not isinstance(value, list):
        raise SkillError("expected a point list")
    return [[p[0], p[1]] for p in value]


def install(session) -> None:
    design = session.design
    interp = session.interp

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
        xy = list(args[2])
        text = args[3]
        orient = args[5] if len(args) > 5 else "R0"
        height = float(args[7]) if len(args) > 7 else 0.1
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
        xy = list(args[2])
        orient = args[3] if len(args) > 3 else "R0"
        shape = Shape("via", "via", "drawing",
                      bbox=[[xy[0], xy[1]], [xy[0], xy[1]]],
                      xy=xy, orient=orient)
        design.register(shape)
        cv.shapes.append(shape)
        return shape

    def _add_instance(cv, lib, cell, view, name, xy, orient):
        master = design.find_cellview(lib, cell, view)
        inst = Instance(name, lib, cell, view, xy, orient, master)
        design.register(inst)
        cv.instances.append(inst)
        return inst

    def db_create_param_inst_by_master_name(it, args, kwargs):
        cv = _as_cellview(args[0])
        return _add_instance(cv, args[1], args[2], args[3], args[4],
                             list(args[5]), args[6])

    def db_create_inst(it, args, kwargs):
        cv = _as_cellview(args[0])
        master = args[1]
        if not isinstance(master, CellView):
            raise SkillError("dbCreateInst needs a master cellView")
        return _add_instance(cv, master.get_prop("libName"),
                             master.get_prop("cellName"),
                             master.get_prop("viewName"),
                             args[2], list(args[3]), args[4])

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
        # 라이브러리/셀 존재 확인용. mock은 항상 존재한다고 본다.
        return TRUE

    def dd_get_obj_read_path(it, args, kwargs):
        return str(session.artifact_dir)

    def dd_delete_obj(it, args, kwargs):
        return TRUE

    def tech_get_tech_file(it, args, kwargs):
        return TRUE

    def tech_find_via_def_by_name(it, args, kwargs):
        # via 정의는 이름만 있는 더미다.
        return args[1] if len(args) > 1 else NIL

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
        ("techGetTechFile", tech_get_tech_file),
        ("techFindViaDefByName", tech_find_via_def_by_name),
    ):
        interp.register(name, fn)
