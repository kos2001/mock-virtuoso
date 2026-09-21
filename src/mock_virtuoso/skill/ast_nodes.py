"""SKILL AST 노드. 데이터만 담는다."""

from __future__ import annotations


class Node:
    __slots__ = ()


class Const(Node):
    __slots__ = ("value",)

    def __init__(self, value: object) -> None:
        self.value = value


class Var(Node):
    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name


class Quote(Node):
    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name


class Handle(Node):
    __slots__ = ("text",)

    def __init__(self, text: str) -> None:
        self.text = text


class Call(Node):
    __slots__ = ("name", "args", "kwargs")

    def __init__(self, name: str, args: list[Node],
                 kwargs: dict[str, Node] | None = None) -> None:
        self.name = name
        self.args = args
        self.kwargs = kwargs or {}


class Prop(Node):
    __slots__ = ("target", "name")

    def __init__(self, target: Node, name: str) -> None:
        self.target = target
        self.name = name


class Group(Node):
    """괄호로 묶인 식들. ``let((a b))``의 바인딩 목록처럼 호출이 아닌 괄호.

    식이 정확히 하나면 리더가 그 식을 그대로 돌려주므로, 이 노드는 0개
    또는 2개 이상일 때만 만들어진다.
    """

    __slots__ = ("items",)

    def __init__(self, items: list[Node]) -> None:
        self.items = items


class If(Node):
    __slots__ = ("cond", "then_node", "else_node")

    def __init__(self, cond: Node, then_node: Node,
                 else_node: Node | None) -> None:
        self.cond = cond
        self.then_node = then_node
        self.else_node = else_node
