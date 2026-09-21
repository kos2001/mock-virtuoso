"""SKILL 소스를 토큰으로 자른다."""

from __future__ import annotations

import re

from mock_virtuoso.skill.errors import ParseError

# 긴 연산자를 먼저 시도해야 "==" 가 "=" 두 개로 잘리지 않는다.
_OPERATORS = (
    "~>", "==", "!=", "<=", ">=", "&&", "||",
    "=", "<", ">", "+", "-", "*", "/", "!", ":",
)

_HANDLE_RE = re.compile(r"db:0x[0-9a-fA-F]+")
_NUMBER_RE = re.compile(r"-?(?:\d+\.\d*|\.\d+|\d+)")
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

_STRING_ESCAPES = {
    "n": "\n", "t": "\t", "r": "\r",
    '"': '"', "\\": "\\",
}


class Token:
    __slots__ = ("kind", "text", "pos")

    def __init__(self, kind: str, text: str, pos: int) -> None:
        self.kind = kind
        self.text = text
        self.pos = pos

    def __repr__(self) -> str:
        return f"Token({self.kind}, {self.text!r})"


def _read_string(source: str, i: int) -> tuple[str, int]:
    out: list[str] = []
    i += 1  # 여는 따옴표
    while True:
        if i >= len(source):
            raise ParseError("unterminated string literal")
        ch = source[i]
        if ch == '"':
            return "".join(out), i + 1
        if ch == "\\":
            if i + 1 >= len(source):
                raise ParseError("unterminated escape sequence")
            out.append(_STRING_ESCAPES.get(source[i + 1], source[i + 1]))
            i += 2
            continue
        out.append(ch)
        i += 1


def _number_is_sign_here(tokens: list[Token]) -> bool:
    """직전 토큰이 값이면 '-'는 이항 연산자, 아니면 음수 부호다."""
    if not tokens:
        return False
    last = tokens[-1]
    return last.kind in ("number", "string", "ident", "handle", "rparen")


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    n = len(source)
    while i < n:
        ch = source[i]

        if ch in " \t\r\n":
            i += 1
            continue

        if ch == ";":  # 줄 끝까지 주석
            while i < n and source[i] != "\n":
                i += 1
            continue

        if ch == '"':
            text, i = _read_string(source, i)
            tokens.append(Token("string", text, i))
            continue

        if ch == "(":
            tokens.append(Token("lparen", "(", i))
            i += 1
            continue

        if ch == ")":
            tokens.append(Token("rparen", ")", i))
            i += 1
            continue

        if ch == "'":
            tokens.append(Token("quote", "'", i))
            i += 1
            continue

        if ch == "?":
            m = _IDENT_RE.match(source, i + 1)
            if not m:
                raise ParseError(f"'?' must be followed by a name at {i}")
            tokens.append(Token("keyword", m.group(0), i))
            i = m.end()
            continue

        handle = _HANDLE_RE.match(source, i)
        if handle:
            tokens.append(Token("handle", handle.group(0), i))
            i = handle.end()
            continue

        if ch.isdigit() or (ch == "." and i + 1 < n and source[i + 1].isdigit()):
            m = _NUMBER_RE.match(source, i)
            tokens.append(Token("number", m.group(0), i))
            i = m.end()
            continue

        if ch == "-" and not _number_is_sign_here(tokens):
            m = _NUMBER_RE.match(source, i)
            if m and m.group(0) != "-":
                tokens.append(Token("number", m.group(0), i))
                i = m.end()
                continue

        ident = _IDENT_RE.match(source, i)
        if ident:
            tokens.append(Token("ident", ident.group(0), i))
            i = ident.end()
            continue

        for op in _OPERATORS:
            if source.startswith(op, i):
                tokens.append(Token("op", op, i))
                i += len(op)
                break
        else:
            raise ParseError(f"unexpected character {ch!r} at {i}")

    return tokens
