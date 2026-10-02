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
            # Name the slots that do exist. Driving this mock is mostly
            # probing it, and a refusal that lists the alternatives turns
            # each wrong guess into the documentation it was after.
            raise SkillError(
                f"{type(self).__name__} has no slot '{name}'; "
                f"it has {', '.join(self._SLOTS)}")
        value = getattr(self, "_slot_" + name, NIL)
        return value


class ViaDef(DbObject):
    """One via definition the technology provides.

    A via can only be drawn from one of these: an invented name resolves to
    nil, and a shape referencing a master the technology lacks is exactly the
    kind of quietly-wrong layout this mock refuses to produce.
    """

    _SLOTS = ("objType", "name", "layer1", "layer2")

    def __init__(self, name: str, layer1: str, layer2: str) -> None:
        super().__init__()
        self._slot_objType = "viaDef"
        self._slot_name = name
        self._slot_layer1 = layer1
        self._slot_layer2 = layer2

    @property
    def name(self) -> str:
        return self._slot_name


class TechFile(DbObject):
    """The technology bound to this session, as techGetTechFile returns it."""

    _SLOTS = ("objType", "techLibName", "viaDefs")

    def __init__(self, lib_name: str, via_defs: list[ViaDef]) -> None:
        super().__init__()
        self._slot_objType = "techFile"
        self._slot_techLibName = lib_name
        self._slot_viaDefs = via_defs

    def find_via_def(self, name: object) -> ViaDef | None:
        for via_def in self._slot_viaDefs:
            if via_def.name == name:
                return via_def
        return None


class Shape(DbObject):
    _SLOTS = ("objType", "lpp", "bBox", "points", "xy", "orient",
              "theLabel", "net", "width", "viaDef")

    def __init__(self, obj_type: str, layer: str, purpose: str, *,
                 bbox, points=None, xy=None, orient=None,
                 text=None, width=None, via_def=None) -> None:
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
        self._slot_viaDef = via_def if via_def is not None else NIL

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


class Net(DbObject):
    """A named electrical net in one cellview.

    Connectivity was the one thing a layout here could not carry. A cell drew
    shapes and labels and nothing said which of them were the same signal, so
    `leMarkNet` had nothing to find and answered `t` to every point — the
    `csh` failure again, a call that always succeeds teaching an agent it did
    something.
    """

    _SLOTS = ("objType", "name", "pins", "terminals", "cellView")

    def __init__(self, name: str, cellview) -> None:
        super().__init__()
        self._slot_objType = "net"
        self._slot_name = name
        self._slot_pins: list = []
        self._slot_terminals: list = []
        self._slot_cellView = cellview

    @property
    def name(self) -> str:
        return self._slot_name


class Term(DbObject):
    """A terminal: the name a net presents to whoever instantiates the cell."""

    _SLOTS = ("objType", "name", "direction", "net", "pins")

    def __init__(self, name: str, direction: str, net: Net) -> None:
        super().__init__()
        self._slot_objType = "term"
        self._slot_name = name
        self._slot_direction = direction
        self._slot_net = net
        self._slot_pins = net.get_prop("pins")

    @property
    def name(self) -> str:
        return self._slot_name


class Pin(DbObject):
    """One shape offered as a connection point for a net."""

    _SLOTS = ("objType", "name", "fig", "net", "term", "accessDir")

    def __init__(self, name: str, fig, net: Net, term=None) -> None:
        super().__init__()
        self._slot_objType = "pin"
        self._slot_name = name
        self._slot_fig = fig
        self._slot_net = net
        self._slot_term = term if term is not None else NIL
        self._slot_accessDir = NIL

    @property
    def name(self) -> str:
        return self._slot_name


class CellView(DbObject):
    _SLOTS = ("objType", "libName", "cellName", "viewName", "shapes",
              "instances", "nets", "terminals", "bBox", "cellView")

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
        self._slot_nets: list[Net] = []
        self._slot_terminals: list[Term] = []
        self.saved = False
        self.circuit: dict = {}

    def clear_contents(self) -> None:
        """Empty the cell in place, keeping every handle onto it valid."""
        self._slot_shapes.clear()
        self._slot_instances.clear()
        self._slot_nets.clear()
        self._slot_terminals.clear()
        self.circuit.clear()
        self.saved = False

    def adopt_contents(self, other: "CellView") -> None:
        """Take over another cellview's geometry, by reference, not by copy.

        Used when a stored cell is reopened: the new cellview object is a new
        handle onto the same cell, so the two must not drift apart.
        """
        self._slot_shapes = other._slot_shapes
        self._slot_instances = other._slot_instances
        self._slot_nets = other._slot_nets
        self._slot_terminals = other._slot_terminals
        self.saved = other.saved
        self.circuit = other.circuit

    @property
    def shapes(self) -> list:
        return self._slot_shapes

    @property
    def instances(self) -> list:
        return self._slot_instances

    @property
    def nets(self) -> list:
        return self._slot_nets

    def find_net(self, name) -> "Net | None":
        for net in self._slot_nets:
            if net.name == name:
                return net
        return None

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
        if name in ("shapes", "instances"):
            # A traversal builds a list and hands it over. Handing out the
            # cellview's own list made `foreach(s cv~>shapes dbDeleteObject(s))`
            # delete every other shape, because the loop walked the list while
            # it shrank underneath — three agents in a row hit that and each
            # worked around it.
            return list(super().get_prop(name))
        return super().get_prop(name)
