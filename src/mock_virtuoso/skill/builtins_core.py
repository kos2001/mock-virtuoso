"""도메인과 무관한 SKILL 코어 빌트인."""

from __future__ import annotations

import re

from mock_virtuoso.skill.errors import SkillError
from mock_virtuoso.skill.evaluator import Interpreter, Lambda
from mock_virtuoso.skill.values import NIL, TRUE, Symbol, skill_repr

_FORMAT_RE = re.compile(r"%(?:[-+ 0#]*\d*(?:\.\d+)?)[sdfLnx%]")


def _as_list(value: object) -> list:
    if value is NIL:
        return []
    if isinstance(value, list):
        return value
    raise SkillError("expected a list")


def _format(fmt: str, values: list) -> str:
    out: list[str] = []
    index = 0
    pos = 0
    for m in _FORMAT_RE.finditer(fmt):
        out.append(fmt[pos:m.start()])
        pos = m.end()
        spec = m.group(0)
        if spec == "%%":
            out.append("%")
            continue
        if index >= len(values):
            raise SkillError(f"not enough arguments for format {fmt!r}")
        value = values[index]
        index += 1
        conv = spec[-1]
        if conv == "L":
            out.append(skill_repr(value))
        elif conv == "s":
            out.append(value if isinstance(value, str)
                       else ("" if value is NIL else skill_repr(value).strip('"')))
        elif conv == "n":
            out.append(skill_repr(value))
        else:
            py_spec = spec[:-1] + conv
            if conv == "d":
                out.append(py_spec % int(value))
            elif conv == "f":
                out.append(py_spec % float(value))
            else:
                out.append(py_spec % value)
    out.append(fmt[pos:])
    return "".join(out)


def install(interp: Interpreter) -> None:
    def sprintf(it, args, kwargs):
        # 첫 인자는 출력 포트다. nil이면 문자열을 돌려준다.
        fmt = args[1]
        return _format(fmt, list(args[2:]))

    def printf(it, args, kwargs):
        _format(args[0], list(args[1:]))
        return TRUE

    def strcat(it, args, kwargs):
        return "".join(a for a in args if isinstance(a, str))

    def length(it, args, kwargs):
        value = args[0]
        if value is NIL:
            return 0
        if isinstance(value, (list, str)):
            return len(value)
        raise SkillError("length needs a list or string")

    def car(it, args, kwargs):
        items = _as_list(args[0])
        return items[0] if items else NIL

    def cadr(it, args, kwargs):
        items = _as_list(args[0])
        return items[1] if len(items) > 1 else NIL

    def cdr(it, args, kwargs):
        items = _as_list(args[0])
        return items[1:] if len(items) > 1 else NIL

    def nth(it, args, kwargs):
        index, items = args[0], _as_list(args[1])
        return items[index] if 0 <= index < len(items) else NIL

    def make_list(it, args, kwargs):
        return list(args)

    def mapcar(it, args, kwargs):
        fn, items = args[0], _as_list(args[1])
        if not isinstance(fn, Lambda):
            raise SkillError("mapcar needs a lambda")
        return [it.call_lambda(fn, [item]) for item in items]

    def member(it, args, kwargs):
        needle, items = args[0], _as_list(args[1])
        for i, item in enumerate(items):
            if item == needle:
                return items[i:]
        return NIL

    def sort_(it, args, kwargs):
        items = _as_list(args[0])
        return sorted(items, key=skill_repr)

    def boundp(it, args, kwargs):
        name = args[0]
        if not isinstance(name, Symbol):
            raise SkillError("boundp needs a symbol")
        try:
            it.globals.get(name.name)
        except SkillError:
            return NIL
        return TRUE

    def xcoord(it, args, kwargs):
        return _as_list(args[0])[0]

    def ycoord(it, args, kwargs):
        return _as_list(args[0])[1]

    def atoi(it, args, kwargs):
        return int(args[0])

    def atof(it, args, kwargs):
        return float(args[0])

    def csh(it, args, kwargs):
        # 셸을 실제로 실행하지 않는다. 테스트 더블이 시스템을 건드리면 안 된다.
        return TRUE

    for name, fn in (
        ("sprintf", sprintf), ("printf", printf), ("strcat", strcat),
        ("length", length), ("car", car), ("cadr", cadr), ("cdr", cdr),
        ("nth", nth), ("list", make_list), ("mapcar", mapcar),
        ("member", member), ("sort", sort_), ("boundp", boundp),
        ("xCoord", xcoord), ("yCoord", ycoord),
        ("atoi", atoi), ("atof", atof), ("csh", csh),
    ):
        interp.register(name, fn)
