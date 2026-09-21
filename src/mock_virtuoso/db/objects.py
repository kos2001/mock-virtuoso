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
            master = self._slot_master
            if master is NIL:
                return NIL
            from mock_virtuoso.db.geometry import transform_bbox
            return transform_bbox(master.bbox, self._slot_xy,
                                  self._slot_orient)
        return super().get_prop(name)


# Cycle guard for CellView.bbox: identities of cellviews whose bbox
# composition is currently in progress on this call stack. A second
# entry for the same cellview while its own computation is still
# unwound (i.e. an ancestor instantiates itself, directly or through a
# chain) means a cyclic instance hierarchy, not legitimate recursion --
# real recursion always finishes and pops before it is reached again.
# This is defence in depth: the primary guard rejects the cycle at
# dbCreateParamInstByMasterName/dbCreateInst time (layout.py
# ``_add_instance``); this one exists so any other route to a cyclic
# master (e.g. assigning ``master`` directly) fails cleanly instead of
# blowing the Python recursion stack with a RecursionError.
_BBOX_IN_PROGRESS: set[int] = set()


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
        key = id(self)
        if key in _BBOX_IN_PROGRESS:
            raise SkillError(
                "cyclic instance hierarchy: "
                f"{self._slot_libName}/{self._slot_cellName}/"
                f"{self._slot_viewName}")
        _BBOX_IN_PROGRESS.add(key)
        try:
            corners: list[tuple[float, float]] = []
            for shape in self._slot_shapes:
                box = shape.bbox
                corners.append((box[0][0], box[0][1]))
                corners.append((box[1][0], box[1][1]))
            for inst in self._slot_instances:
                box = inst.get_prop("bBox")
                if box is NIL:
                    continue
                corners.append((box[0][0], box[0][1]))
                corners.append((box[1][0], box[1][1]))
            if not corners:
                return [[0.0, 0.0], [0.0, 0.0]]
            return bbox_of_points(corners)
        finally:
            _BBOX_IN_PROGRESS.discard(key)

    def get_prop(self, name: str) -> object:
        if name == "bBox":
            return self.bbox
        if name == "cellView":
            return self
        return super().get_prop(name)
