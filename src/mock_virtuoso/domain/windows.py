"""윈도우 / 레이어 팔레트 / 선택 상태."""

from __future__ import annotations

from pathlib import Path

from mock_virtuoso.db.objects import Shape
from mock_virtuoso.skill.errors import SkillError
from mock_virtuoso.skill.values import NIL, TRUE, is_truthy

# 1x1 투명 PNG. hiWindowSaveImage가 실제 파일을 써야 하기 때문에 필요하다.
_PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae"
    "426082"
)


def _split_lpp(text: str) -> tuple[str, str]:
    parts = text.split()
    if len(parts) != 2:
        raise SkillError(f"malformed layer-purpose pair: {text!r}")
    return parts[0], parts[1]


def _inside(shape: Shape, box) -> bool:
    (llx, lly), (urx, ury) = box[0], box[1]
    (sx0, sy0), (sx1, sy1) = shape.bbox[0], shape.bbox[1]
    return sx0 >= llx and sy0 >= lly and sx1 <= urx and sy1 <= ury


def install(session) -> None:
    interp = session.interp

    def current_window():
        return session.windows[-1] if session.windows else None

    def current_cellview():
        window = current_window()
        return window.cellview if window is not None else None

    # -- 윈도우 ----------------------------------------------------------

    def hi_get_window_list(it, args, kwargs):
        return list(session.windows)

    def hi_get_current_window(it, args, kwargs):
        window = current_window()
        return window if window is not None else NIL

    def hi_get_ci_window(it, args, kwargs):
        return current_window() or NIL

    def hi_get_window_name(it, args, kwargs):
        window = args[0]
        return NIL if window is NIL else window.name

    def hi_close_window(it, args, kwargs):
        window = args[0]
        if window in session.windows:
            session.windows.remove(window)
        return TRUE

    def hi_raise_window(it, args, kwargs):
        window = args[0]
        if window in session.windows:
            session.windows.remove(window)
            session.windows.append(window)
        return TRUE

    def accept(it, args, kwargs):
        return TRUE

    def hi_window_save_image(it, args, kwargs):
        path = kwargs.get("path")
        if not isinstance(path, str):
            raise SkillError("hiWindowSaveImage needs ?path")
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_PNG_1X1)
        return TRUE

    # -- 편집 컨텍스트 ---------------------------------------------------

    def ge_get_edit_cellview(it, args, kwargs):
        cv = current_cellview()
        return cv if cv is not None else NIL

    def ge_open(it, args, kwargs):
        return TRUE

    def ge_get_sel_set(it, args, kwargs):
        return list(session.selection)

    def ge_get_sel_set_count(it, args, kwargs):
        return len(session.selection)

    def ge_select_area(it, args, kwargs):
        cv = current_cellview()
        if cv is None:
            return NIL
        box = args[0]
        for shape in cv.shapes:
            if _inside(shape, box) and shape not in session.selection:
                session.selection.append(shape)
        return TRUE

    def ge_add_select_box(it, args, kwargs):
        return ge_select_area(it, [args[1]], kwargs)

    def ge_deselect_area(it, args, kwargs):
        cv = current_cellview()
        if cv is None:
            return NIL
        box = args[0]
        session.selection = [s for s in session.selection
                             if not _inside(s, box)]
        return TRUE

    def ge_select_all_fig(it, args, kwargs):
        cv = current_cellview()
        if cv is not None:
            session.selection = list(cv.shapes)
        return TRUE

    def ge_deselect_all_fig(it, args, kwargs):
        session.selection = []
        return TRUE

    def le_hi_delete(it, args, kwargs):
        cv = current_cellview()
        if cv is None:
            return NIL
        for shape in list(session.selection):
            if shape in cv.shapes:
                cv.shapes.remove(shape)
        session.selection = []
        return TRUE

    # -- 팔레트 ----------------------------------------------------------

    def pte_set_visible(it, args, kwargs):
        layer, purpose = _split_lpp(args[0])
        session.palette[(layer, purpose)] = is_truthy(args[1])
        return TRUE

    def pte_set_none_visible(it, args, kwargs):
        for key in session.palette:
            session.palette[key] = False
        return TRUE

    def pte_set_all_visible(it, args, kwargs):
        for key in session.palette:
            session.palette[key] = True
        return TRUE

    def pte_set_active_lpp(it, args, kwargs):
        session.active_lpp = _split_lpp(args[0])
        return TRUE

    for name, fn in (
        ("hiGetWindowList", hi_get_window_list),
        ("hiGetCurrentWindow", hi_get_current_window),
        ("hiGetCIWindow", hi_get_ci_window),
        ("hiGetWindowName", hi_get_window_name),
        ("hiCloseWindow", hi_close_window),
        ("hiRaiseWindow", hi_raise_window),
        ("hiRedraw", accept),
        ("hiFlush", accept),
        ("hiZoomAbsoluteScale", accept),
        ("hiWindowSaveImage", hi_window_save_image),
        ("geGetEditCellView", ge_get_edit_cellview),
        ("geOpen", ge_open),
        ("geGetSelSet", ge_get_sel_set),
        ("geGetSelSetCount", ge_get_sel_set_count),
        ("geSelectArea", ge_select_area),
        ("geAddSelectBox", ge_add_select_box),
        ("geDeselectArea", ge_deselect_area),
        ("geSelectAllFig", ge_select_all_fig),
        ("geDeselectAllFig", ge_deselect_all_fig),
        ("leHiDelete", le_hi_delete),
        ("leMarkNet", accept),
        ("leHiUnmarkNet", accept),
        ("pteSetVisible", pte_set_visible),
        ("pteSetNoneVisible", pte_set_none_visible),
        ("pteSetAllVisible", pte_set_all_visible),
        ("pteSetActiveLpp", pte_set_active_lpp),
    ):
        interp.register(name, fn)
