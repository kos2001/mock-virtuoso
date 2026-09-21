import pytest

from mock_virtuoso.db.design import Design
from mock_virtuoso.db.objects import CellView, Instance, Shape
from mock_virtuoso.skill.errors import SkillError
from mock_virtuoso.skill.values import NIL, Symbol


def test_shape_exposes_skill_slot_names():
    shape = Shape("rect", "met1", "drawing", bbox=[[0.0, 0.0], [2.0, 1.0]])
    assert shape.get_prop("objType") == "rect"
    assert shape.get_prop("lpp") == ["met1", "drawing"]
    assert shape.get_prop("bBox") == [[0.0, 0.0], [2.0, 1.0]]


def test_shape_unset_slots_return_nil():
    shape = Shape("rect", "met1", "drawing", bbox=[[0.0, 0.0], [1.0, 1.0]])
    assert shape.get_prop("theLabel") is NIL
    assert shape.get_prop("net") is NIL


def test_unknown_slot_raises():
    shape = Shape("rect", "met1", "drawing", bbox=[[0.0, 0.0], [1.0, 1.0]])
    with pytest.raises(SkillError):
        shape.get_prop("noSuchSlot")


def test_cellview_slots():
    cv = CellView("LIB", "CELL", "layout", "maskLayout", "w")
    assert cv.get_prop("libName") == "LIB"
    assert cv.get_prop("cellName") == "CELL"
    assert cv.get_prop("viewName") == "layout"
    assert cv.get_prop("shapes") == []
    assert cv.get_prop("instances") == []


def test_instance_transform_is_offset_and_orient():
    master = CellView("LIB", "M", "layout", "maskLayout", "r")
    inst = Instance("I0", "LIB", "M", "layout", [1.0, 2.0], "R90", master)
    assert inst.get_prop("transform") == [[1.0, 2.0], "R90"]


def test_design_open_cellview_is_idempotent_per_identity():
    design = Design()
    a = design.open_cellview("LIB", "CELL", "layout", "maskLayout", "w")
    b = design.open_cellview("LIB", "CELL", "layout", "maskLayout", "a")
    assert a is b


def test_design_separates_different_cells():
    design = Design()
    a = design.open_cellview("LIB", "A", "layout", "maskLayout", "w")
    b = design.open_cellview("LIB", "B", "layout", "maskLayout", "w")
    assert a is not b


def test_handles_are_stable_and_resolvable():
    design = Design()
    cv = design.open_cellview("LIB", "CELL", "layout", "maskLayout", "w")
    assert cv.handle.startswith("db:0x")
    assert design.resolve(cv.handle) is cv


def test_resolving_unknown_handle_raises():
    design = Design()
    with pytest.raises(SkillError):
        design.resolve("db:0xdeadbeef")


def test_handles_are_unique_across_objects():
    design = Design()
    a = design.open_cellview("LIB", "A", "layout", "maskLayout", "w")
    b = design.open_cellview("LIB", "B", "layout", "maskLayout", "w")
    assert a.handle != b.handle


def test_open_cellviews_lists_everything_opened():
    design = Design()
    design.open_cellview("LIB", "A", "layout", "maskLayout", "w")
    design.open_cellview("LIB", "B", "layout", "maskLayout", "w")
    assert len(design.open_cellviews) == 2
