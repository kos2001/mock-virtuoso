"""토큰 스트림을 AST로 읽는다.

SKILL의 표면 문법은 C 스타일이다. ``f(a b c)``는 호출, 중위 연산자가 있고,
``if``는 ``then``/``else`` 키워드를 쓰는 특수 형식이다.
"""

from __future__ import annotations

from mock_virtuoso.skill import ast_nodes as A
from mock_virtuoso.skill.errors import ParseError
from mock_virtuoso.skill.lexer import Token, tokenize
from mock_virtuoso.skill.values import NIL, TRUE

# 낮은 우선순위부터. 각 단계는 (연산자들, 왼쪽결합) 이다.
_BINARY_LEVELS = (
    ("=",),
    ("||",),
    ("&&",),
    ("==", "!=", "<", ">", "<=", ">="),
    ("+", "-"),
    ("*", "/"),
    (":",),
)


class _Reader:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._i = 0

    # -- 토큰 조작 -------------------------------------------------------

    def _peek(self) -> Token | None:
        return self._tokens[self._i] if self._i < len(self._tokens) else None

    def _next(self) -> Token:
        tok = self._peek()
        if tok is None:
            raise ParseError("unexpected end of input")
        self._i += 1
        return tok

    def _at_op(self, *texts: str) -> bool:
        tok = self._peek()
        return tok is not None and tok.kind == "op" and tok.text in texts

    def _at_ident(self, *names: str) -> bool:
        tok = self._peek()
        return tok is not None and tok.kind == "ident" and tok.text in names

    def _expect(self, kind: str) -> Token:
        tok = self._next()
        if tok.kind != kind:
            raise ParseError(f"expected {kind}, got {tok.kind} {tok.text!r}")
        return tok

    # -- 진입점 ----------------------------------------------------------

    def read_all(self) -> list[A.Node]:
        forms: list[A.Node] = []
        while self._peek() is not None:
            forms.append(self._expression())
        return forms

    # -- 식 --------------------------------------------------------------

    def _expression(self, level: int = 0) -> A.Node:
        if level >= len(_BINARY_LEVELS):
            return self._unary()

        node = self._expression(level + 1)
        ops = _BINARY_LEVELS[level]
        while self._at_op(*ops):
            op = self._next().text
            right = self._expression(level + 1)
            if op == "=":
                # 대입은 setq 호출로 정규화한다.
                if isinstance(node, A.Var):
                    node = A.Call("setq", [A.Quote(node.name), right])
                elif isinstance(node, A.Prop):
                    node = A.Call("setProp", [node.target,
                                              A.Quote(node.name), right])
                else:
                    raise ParseError("left side of '=' is not assignable")
            else:
                node = A.Call(op, [node, right])
        return node

    def _unary(self) -> A.Node:
        if self._at_op("!"):
            self._next()
            return A.Call("!", [self._unary()])
        if self._at_op("-"):
            self._next()
            return A.Call("-", [A.Const(0), self._unary()])
        return self._postfix()

    def _postfix(self) -> A.Node:
        node = self._primary()
        while self._at_op("~>"):
            self._next()
            name_tok = self._next()
            if name_tok.kind not in ("ident", "string"):
                raise ParseError(f"'~>' needs a slot name, got {name_tok.text!r}")
            node = A.Prop(node, name_tok.text)
        return node

    def _primary(self) -> A.Node:
        tok = self._next()

        if tok.kind == "number":
            text = tok.text
            value: object = float(text) if ("." in text) else int(text)
            return A.Const(value)

        if tok.kind == "string":
            return A.Const(tok.text)

        if tok.kind == "handle":
            return A.Handle(tok.text)

        if tok.kind == "quote":
            name_tok = self._next()
            if name_tok.kind != "ident":
                raise ParseError("quote must be followed by a symbol")
            return A.Quote(name_tok.text)

        if tok.kind == "lparen":
            # 괄호 안에는 식이 여러 개 올 수 있다. ``(1 + 2)``는 그룹화지만
            # ``(cv buf bb)``는 prog/let의 바인딩 목록이다. 하나면 그대로,
            # 아니면 Group으로 감싼다.
            items: list[A.Node] = []
            while not (self._peek() is not None
                       and self._peek().kind == "rparen"):
                if self._peek() is None:
                    raise ParseError("unterminated parenthesised group")
                items.append(self._expression())
            self._expect("rparen")
            if len(items) == 1:
                return items[0]
            return A.Group(items)

        if tok.kind == "ident":
            if self._peek() is not None and self._peek().kind == "lparen":
                return self._call(tok.text)
            if tok.text == "nil":
                return A.Const(NIL)
            if tok.text == "t":
                return A.Const(TRUE)
            return A.Var(tok.text)

        raise ParseError(f"unexpected token {tok.kind} {tok.text!r}")

    def _call(self, name: str) -> A.Node:
        self._expect("lparen")
        if name == "if":
            return self._if_body()

        args: list[A.Node] = []
        kwargs: dict[str, A.Node] = {}
        while not (self._peek() is not None and self._peek().kind == "rparen"):
            if self._peek() is None:
                raise ParseError(f"unterminated argument list for {name}")
            tok = self._peek()
            if tok.kind == "keyword":
                self._next()
                kwargs[tok.text] = self._expression()
            else:
                args.append(self._expression())
        self._expect("rparen")
        return A.Call(name, args, kwargs)

    def _if_body(self) -> A.Node:
        cond = self._expression()
        if not self._at_ident("then"):
            raise ParseError("if(...) requires a 'then' keyword")
        self._next()

        then_forms: list[A.Node] = []
        while not (self._at_ident("else")
                   or (self._peek() is not None
                       and self._peek().kind == "rparen")):
            then_forms.append(self._expression())
        if not then_forms:
            raise ParseError("if(...) has an empty 'then' branch")
        then_node = (then_forms[0] if len(then_forms) == 1
                     else A.Call("progn", then_forms))

        else_node: A.Node | None = None
        if self._at_ident("else"):
            self._next()
            else_forms: list[A.Node] = []
            while not (self._peek() is not None
                       and self._peek().kind == "rparen"):
                else_forms.append(self._expression())
            if not else_forms:
                raise ParseError("if(...) has an empty 'else' branch")
            else_node = (else_forms[0] if len(else_forms) == 1
                         else A.Call("progn", else_forms))

        self._expect("rparen")
        return A.If(cond, then_node, else_node)


def read_all(source: str) -> list[A.Node]:
    """SKILL 소스의 최상위 form들을 순서대로 읽는다."""
    return _Reader(tokenize(source)).read_all()
