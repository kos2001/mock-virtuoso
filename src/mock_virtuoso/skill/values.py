"""SKILL 값 모델과 ``%L`` 출력 표현.

``%L``은 SKILL의 리스트 출력 포맷이다. RAMIC 데몬이 결과를
``sprintf(nil "%c%L%c" ...)``로 감싸 보내므로, 이 함수의 출력이 곧 TCP
응답 바이트가 된다.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


class _Nil:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "NIL"

    def __bool__(self) -> bool:
        return False


class _True:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "TRUE"


NIL = _Nil()
TRUE = _True()


class Symbol:
    """인용 심볼 ``'name``, 그리고 ``objType`` 같은 심볼 값."""

    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Symbol) and other.name == self.name

    def __hash__(self) -> int:
        return hash(("Symbol", self.name))

    def __repr__(self) -> str:
        return f"Symbol({self.name!r})"


@runtime_checkable
class SkillObject(Protocol):
    """``~>`` 속성 접근과 핸들 표현을 지원하는 객체.

    이밸류에이터는 DB 타입을 모른다. 이 프로토콜만 안다.
    """

    handle: str

    def get_prop(self, name: str) -> object: ...


def is_truthy(value: object) -> bool:
    """SKILL에서 거짓은 ``nil`` 하나뿐이다. 0도 빈 문자열도 참이다."""
    return value is not NIL


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )


def skill_repr(value: object) -> str:
    """``%L`` 포맷. 이 문자열이 TCP 응답 본문이 된다."""
    if value is NIL:
        return "nil"
    if value is TRUE:
        return "t"
    if isinstance(value, Symbol):
        return value.name
    if isinstance(value, bool):
        # bool은 int의 하위 타입이라 int보다 먼저 걸러야 한다.
        return "t" if value else "nil"
    if isinstance(value, str):
        return f'"{_escape(value)}"'
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, (list, tuple)):
        if not value:
            return "nil"
        return "(" + " ".join(skill_repr(v) for v in value) + ")"
    if isinstance(value, SkillObject):
        return value.handle
    return str(value)
