import pytest

from mock_virtuoso.skill.errors import ParseError
from mock_virtuoso.skill.lexer import tokenize


def kinds(source):
    return [(t.kind, t.text) for t in tokenize(source)]


def test_simple_call():
    assert kinds("f(1 2)") == [
        ("ident", "f"), ("lparen", "("),
        ("number", "1"), ("number", "2"), ("rparen", ")"),
    ]


def test_string_with_escapes():
    toks = tokenize(r'"a\"b\\c\n"')
    assert len(toks) == 1
    assert toks[0].kind == "string"
    assert toks[0].text == 'a"b\\c\n'


def test_negative_and_float_numbers():
    assert kinds("-1.5 2 0.0") == [
        ("number", "-1.5"), ("number", "2"), ("number", "0.0"),
    ]


def test_arrow_is_single_operator():
    assert kinds("cv~>shapes") == [
        ("ident", "cv"), ("op", "~>"), ("ident", "shapes"),
    ]


def test_two_char_operators():
    assert kinds("a == b != c && d || !e") == [
        ("ident", "a"), ("op", "=="), ("ident", "b"), ("op", "!="),
        ("ident", "c"), ("op", "&&"), ("ident", "d"), ("op", "||"),
        ("op", "!"), ("ident", "e"),
    ]


def test_keyword_argument():
    assert kinds('?path "x"') == [("keyword", "path"), ("string", "x")]


def test_object_handle():
    assert kinds("db:0x1f2a~>name") == [
        ("handle", "db:0x1f2a"), ("op", "~>"), ("ident", "name"),
    ]


def test_point_literal_colon_is_operator():
    assert kinds("0.0:1.5") == [
        ("number", "0.0"), ("op", ":"), ("number", "1.5"),
    ]


def test_quote_symbol():
    assert kinds("'RBMonInstalled") == [
        ("quote", "'"), ("ident", "RBMonInstalled"),
    ]


def test_comment_to_end_of_line_is_skipped():
    assert kinds("1 ; a comment\n2") == [("number", "1"), ("number", "2")]


def test_unterminated_string_raises():
    with pytest.raises(ParseError):
        tokenize('"abc')
