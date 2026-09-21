"""디자인 DB 객체. SKILL도 TCP도 모른다."""

from __future__ import annotations

from mock_virtuoso.skill.errors import SkillError
from mock_virtuoso.skill.values import NIL


class DbObject:
    """``~>`` 접근과 핸들을 갖는 객체의 기반."""

    _SLOTS: tuple[str, ...] = ()

    def __init__(self) -> None:
        self.handle = "db:0x0"

    def get_prop(self, name: str) -> object:
        if name not in self._SLOTS:
            raise SkillError(
                f"{type(self).__name__} has no slot '{name}'")
        value = getattr(self, "_slot_" + name, NIL)
        return value


class Shape(DbObject):
    _SLOTS = ("objType", "lpp", "bBox", "points", "xy", "orient",
              "theLabel", "net", "width")

    def __init__(self, obj_type: str, layer: str, purpose: str, *,
                 bbox, points=None, xy=None, orient=None,
                 text=None, width=None) -> None:
        super().__init__()
        self._slot_objType = obj_type
        self._slot_lpp = [layer, purpose]
        self._slot_bBox = bbox
        self._slot_points = points if points is not None else NIL
        self._slot_xy = xy if xy is not None else NIL
        self._slot_orient = orient if orient is not None else NIL
        self._slot_theLabel = text if text is not None else NIL
        self._slot_width = width if width is not None else NIL
        self._slot_net = NIL

    @property
    def layer(self) -> str:
        return self._slot_lpp[0]

    @property
    def purpose(self) -> str:
        return self._slot_lpp[1]

    @property
    def bbox(self):
        return self._slot_bBox


class Instance(DbObject):
    _SLOTS = ("objType", "name", "libName", "cellName", "viewName",
              "xy", "orient", "master", "transform", "bBox")

    def __init__(self, name: str, lib_name: str, cell_name: str,
                 view_name: str, xy, orient: str, master) -> None:
        super().__init__()
        self._slot_objType = "inst"
        self._slot_name = name
        self._slot_libName = lib_name
        self._slot_cellName = cell_name
        self._slot_viewName = view_name
        self._slot_xy = list(xy)
        self._slot_orient = orient
        self._slot_master = master if master is not None else NIL
        self.params: dict[str, object] = {}

    def get_prop(self, name: str) -> object:
        if name == "transform":
            return [list(self._slot_xy), self._slot_orient]
        if name == "bBox":
            from mock_virtuoso.db.geometry import transform_bbox
            master = self._slot_master
            if master is NIL:
                return [list(self._slot_xy), list(self._slot_xy)]
            return transform_bbox(master.bbox, self._slot_xy,
                                  self._slot_orient)
        return super().get_prop(name)


class CellView(DbObject):
    _SLOTS = ("objType", "libName", "cellName", "viewName", "shapes",
              "instances", "bBox", "cellView")

    def __init__(self, lib_name: str, cell_name: str, view_name: str,
                 view_type: str, mode: str) -> None:
        super().__init__()
        self._slot_objType = "cellView"
        self._slot_libName = lib_name
        self._slot_cellName = cell_name
        self._slot_viewName = view_name
        self.view_type = view_type
        self.mode = mode
        self._slot_shapes: list[Shape] = []
        self._slot_instances: list[Instance] = []
        self.saved = False

    @property
    def shapes(self) -> list:
        return self._slot_shapes

    @property
    def instances(self) -> list:
        return self._slot_instances

    @property
    def bbox(self):
        from mock_virtuoso.db.geometry import bbox_of_points
        corners: list[tuple[float, float]] = []
        for shape in self._slot_shapes:
            box = shape.bbox
            corners.append((box[0][0], box[0][1]))
            corners.append((box[1][0], box[1][1]))
        if not corners:
            return [[0.0, 0.0], [0.0, 0.0]]
        return bbox_of_points(corners)

    def get_prop(self, name: str) -> object:
        if name == "bBox":
            return self.bbox
        if name == "cellView":
            return self
        return super().get_prop(name)
