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


# --- Issues from brief code review ---


def test_open_cellview_updates_mode_on_cache_hit():
    """Issue 1: open_cellview silently discards caller's requested mode."""
    design = Design()
    a = design.open_cellview("LIB", "CELL", "layout", "maskLayout", "r")
    assert a.mode == "r"
    b = design.open_cellview("LIB", "CELL", "layout", "maskLayout", "w")
    # Same object (idempotent by identity)
    assert a is b
    # But mode updated to last-open-wins
    assert b.mode == "w"


def test_open_cellview_updates_view_type_on_cache_hit():
    """Issue 1: open_cellview silently discards caller's requested view_type."""
    design = Design()
    a = design.open_cellview("LIB", "CELL", "layout", "schematic", "r")
    assert a.view_type == "schematic"
    b = design.open_cellview("LIB", "CELL", "layout", "maskLayout", "w")
    # Same object (idempotent by identity)
    assert a is b
    # But view_type updated to last-open-wins
    assert b.view_type == "maskLayout"


def test_close_cellview_unregisters_handle():
    """Issue 2: close_cellview leaves stale handles resolvable."""
    design = Design()
    cv = design.open_cellview("LIB", "CELL", "layout", "maskLayout", "w")
    handle = cv.handle
    design.close_cellview(cv)
    # Resolving closed cellview should raise SkillError
    with pytest.raises(SkillError) as exc_info:
        design.resolve(handle)
    assert "stale" in str(exc_info.value).lower()


def test_close_and_reopen_cellview_creates_new_object():
    """Issue 2: close-then-reopen should create new object with new handle."""
    design = Design()
    cv1 = design.open_cellview("LIB", "CELL", "layout", "maskLayout", "w")
    handle1 = cv1.handle
    design.close_cellview(cv1)
    cv2 = design.open_cellview("LIB", "CELL", "layout", "maskLayout", "w")
    # New object with new handle
    assert cv1 is not cv2
    assert handle1 != cv2.handle
    # New handle should resolve
    assert design.resolve(cv2.handle) is cv2
    # Old handle should raise error
    with pytest.raises(SkillError):
        design.resolve(handle1)


def test_instance_bbox_nil_when_master_is_nil():
    """Issue 3: Instance.bBox with NIL master should return NIL, not degenerate box."""
    inst = Instance("I0", "LIB", "M", "layout", [1.0, 2.0], "R0", None)
    assert inst.get_prop("bBox") is NIL


def test_instance_bbox_composes_with_master():
    """Issue 3: Instance.bBox should compose with master's bbox."""
    master = CellView("LIB", "M", "layout", "maskLayout", "r")
    # Add a shape to master so it has a non-trivial bbox
    shape = Shape("rect", "met1", "drawing", bbox=[[0.0, 0.0], [1.0, 1.0]])
    master.shapes.append(shape)

    inst = Instance("I0", "LIB", "M", "layout", [10.0, 20.0], "R0", master)
    bbox = inst.get_prop("bBox")
    # Master bbox [[0,0],[1,1]], offset [10,20], orient R0
    # Should be [[10.0,20.0],[11.0,21.0]]
    assert bbox == [[10.0, 20.0], [11.0, 21.0]]
