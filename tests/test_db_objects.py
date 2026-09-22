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


# --- Final fix wave: CellView.bbox must include instances (finding 1) ---


def test_cellview_bbox_includes_instances_two_level_hierarchy():
    """A cellview whose only content is instances must not report a
    degenerate [[0,0],[0,0]] box: its bbox must compose through the
    instances' own (master-derived) bboxes.

    LEAF(rect 0,0-1,1) <- MID(I0 @5,5) <- TOP(J0 @100,100)
    """
    leaf = CellView("LIB", "LEAF", "layout", "maskLayout", "r")
    leaf_shape = Shape("rect", "met1", "drawing",
                        bbox=[[0.0, 0.0], [1.0, 1.0]])
    leaf.shapes.append(leaf_shape)

    mid = CellView("LIB", "MID", "layout", "maskLayout", "r")
    i0 = Instance("I0", "LIB", "LEAF", "layout", [5.0, 5.0], "R0", leaf)
    mid.instances.append(i0)

    # MID's bbox must come from I0's composed bbox, not be degenerate.
    assert mid.get_prop("bBox") == [[5.0, 5.0], [6.0, 6.0]]

    top = CellView("LIB", "TOP", "layout", "maskLayout", "r")
    j0 = Instance("J0", "LIB", "MID", "layout", [100.0, 100.0], "R0", mid)
    top.instances.append(j0)

    # dbTransformBBox(J0~>master~>bBox J0~>transform) equivalent: J0's own
    # composed bBox should already reflect MID's real (non-degenerate) box.
    assert j0.get_prop("bBox") == [[105.0, 105.0], [106.0, 106.0]]


def test_cellview_bbox_skips_masterless_instances():
    """A masterless instance returns NIL for bBox (Task 7 ruling); the
    cellview's own bbox composition must skip it rather than error."""
    cv = CellView("LIB", "CELL", "layout", "maskLayout", "r")
    good = Shape("rect", "met1", "drawing", bbox=[[0.0, 0.0], [1.0, 1.0]])
    cv.shapes.append(good)
    orphan = Instance("ORPHAN", "LIB", "GONE", "layout",
                       [50.0, 50.0], "R0", None)
    cv.instances.append(orphan)

    assert cv.get_prop("bBox") == [[0.0, 0.0], [1.0, 1.0]]


# --- Final fix wave: the bBox traversal itself must guard against a
# cycle (defence in depth for a cycle introduced by any route other
# than dbCreateParamInstByMasterName/dbCreateInst, e.g. a master
# assigned directly at the Python level). It must raise SkillError,
# never let a RecursionError escape.


def test_cellview_bbox_self_cycle_raises_skill_error_not_recursion_error(
        capsys):
    a = CellView("LIB", "SELFCYCLE", "layout", "maskLayout", "r")
    inst = Instance("I0", "LIB", "SELFCYCLE", "layout",
                     [0.0, 0.0], "R0", a)
    a.instances.append(inst)

    with pytest.raises(SkillError):
        _ = a.bbox
    assert capsys.readouterr().err == ""


def test_cellview_bbox_mutual_cycle_raises_skill_error_not_recursion_error(
        capsys):
    a = CellView("LIB", "MUTA", "layout", "maskLayout", "r")
    b = CellView("LIB", "MUTB", "layout", "maskLayout", "r")
    inst_b_in_a = Instance("IB", "LIB", "MUTB", "layout",
                           [0.0, 0.0], "R0", b)
    a.instances.append(inst_b_in_a)
    inst_a_in_b = Instance("IA", "LIB", "MUTA", "layout",
                           [0.0, 0.0], "R0", a)
    b.instances.append(inst_a_in_b)

    with pytest.raises(SkillError):
        _ = a.bbox
    assert capsys.readouterr().err == ""


def test_cellview_bbox_diamond_reuse_of_same_master_is_not_a_false_cycle():
    """Using the same acyclic master twice under one parent (a diamond,
    not a cycle) must still compose fine -- the guard must not treat
    sequential reentry into an already-finished bbox computation as a
    cycle."""
    leaf = CellView("LIB", "DLEAF", "layout", "maskLayout", "r")
    leaf.shapes.append(
        Shape("rect", "met1", "drawing", bbox=[[0.0, 0.0], [1.0, 1.0]]))

    top = CellView("LIB", "DTOP", "layout", "maskLayout", "r")
    top.instances.append(
        Instance("I0", "LIB", "DLEAF", "layout", [0.0, 0.0], "R0", leaf))
    top.instances.append(
        Instance("I1", "LIB", "DLEAF", "layout", [10.0, 10.0], "R0", leaf))

    assert top.bbox == [[0.0, 0.0], [11.0, 11.0]]


def test_close_cellview_keeps_the_cell_contents():
    """dbClose releases the cellview; it does not empty the cell.

    Two agents driving the mock independently hit this: they drew a cell,
    closed it, reopened it, and found it empty. Closing a window in Virtuoso
    does not delete geometry from the library, and a mock that loses it that
    silently is worse than one that refuses the call.
    """
    design = Design()
    cv = design.open_cellview("LIB", "CELL", "layout", "maskLayout", "w")
    shape = Shape("rect", "met1", "drawing", bbox=[[0.0, 0.0], [4.0, 4.0]])
    cv.shapes.append(shape)
    design.close_cellview(cv)

    reopened = design.open_cellview("LIB", "CELL", "layout", "maskLayout", "r")
    assert reopened is not cv                      # a new cellview object...
    assert [s.handle for s in reopened.shapes] == [shape.handle]   # ...same cell


def test_closed_cellview_is_not_an_open_cellview():
    design = Design()
    cv = design.open_cellview("LIB", "CELL", "layout", "maskLayout", "w")
    assert cv in design.open_cellviews
    design.close_cellview(cv)
    assert design.open_cellviews == []


def test_closed_cell_is_still_findable_as_an_instance_master():
    """A master need not be open in a window to be instantiated."""
    design = Design()
    cv = design.open_cellview("LIB", "MASTER", "layout", "maskLayout", "w")
    cv.shapes.append(Shape("rect", "met1", "drawing", bbox=[[0.0, 0.0], [2.0, 2.0]]))
    design.close_cellview(cv)

    master = design.find_cellview("LIB", "MASTER", "layout")
    assert master is not None
    assert len(master.shapes) == 1


def test_deleting_a_cell_discards_its_contents():
    """ddDeleteObj removes the cell; recreating it must not resurrect geometry.

    Storage outliving `_known_cells` meant a deleted cell came back fully drawn
    the next time anything opened it.
    """
    design = Design()
    cv = design.open_cellview("LIB", "CELL", "layout", "maskLayout", "w")
    cv.shapes.append(Shape("rect", "met1", "drawing", bbox=[[0.0, 0.0], [4.0, 4.0]]))
    design.close_cellview(cv)

    design.forget_cell("LIB", "CELL")
    assert not design.cell_exists("LIB", "CELL")
    assert design.find_cellview("LIB", "CELL", "layout") is None

    recreated = design.open_cellview("LIB", "CELL", "layout", "maskLayout", "w")
    assert recreated.shapes == []


def test_deleting_a_cell_closes_views_that_are_still_open():
    """Deleting a cell out from under an open view leaves no live handle to it."""
    design = Design()
    cv = design.open_cellview("LIB", "CELL", "layout", "maskLayout", "w")
    cv.shapes.append(Shape("rect", "met1", "drawing", bbox=[[0.0, 0.0], [1.0, 1.0]]))
    handle = cv.handle

    design.forget_cell("LIB", "CELL")

    assert design.open_cellviews == []
    with pytest.raises(SkillError):
        design.resolve(handle)


def test_deleting_one_cell_leaves_its_neighbours_alone():
    design = Design()
    keep = design.open_cellview("LIB", "KEEP", "layout", "maskLayout", "w")
    keep.shapes.append(Shape("rect", "met1", "drawing", bbox=[[0.0, 0.0], [1.0, 1.0]]))
    drop = design.open_cellview("LIB", "DROP", "layout", "maskLayout", "w")
    drop.shapes.append(Shape("rect", "poly", "drawing", bbox=[[0.0, 0.0], [1.0, 1.0]]))

    design.forget_cell("LIB", "DROP")

    assert design.cell_exists("LIB", "KEEP")
    assert len(design.find_cellview("LIB", "KEEP", "layout").shapes) == 1
    assert design.find_cellview("LIB", "DROP", "layout") is None


def test_opening_for_write_starts_the_cellview_empty():
    """Mode "w" means overwrite: Virtuoso hands back a new, empty cellview.

    Keeping the old contents made every caller that meant "build this cell"
    silently append to the previous build, which is why the bundled tools grew
    their own clear-the-cell loops.
    """
    design = Design()
    first = design.open_cellview("LIB", "CELL", "layout", "maskLayout", "w")
    first.shapes.append(Shape("rect", "met1", "drawing", bbox=[[0.0, 0.0], [1.0, 1.0]]))

    rewritten = design.open_cellview("LIB", "CELL", "layout", "maskLayout", "w")
    assert rewritten.shapes == []


def test_opening_for_append_keeps_what_is_there():
    design = Design()
    first = design.open_cellview("LIB", "CELL", "layout", "maskLayout", "a")
    first.shapes.append(Shape("rect", "met1", "drawing", bbox=[[0.0, 0.0], [1.0, 1.0]]))

    appended = design.open_cellview("LIB", "CELL", "layout", "maskLayout", "a")
    assert len(appended.shapes) == 1


def test_opening_for_read_keeps_what_is_there():
    design = Design()
    first = design.open_cellview("LIB", "CELL", "layout", "maskLayout", "a")
    first.shapes.append(Shape("rect", "met1", "drawing", bbox=[[0.0, 0.0], [1.0, 1.0]]))

    assert len(design.open_cellview("LIB", "CELL", "layout", "maskLayout", "r").shapes) == 1
