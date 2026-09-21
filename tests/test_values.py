import pytest

from mock_virtuoso.skill.errors import SkillError
from mock_virtuoso.skill.values import NIL, TRUE, Symbol, skill_repr, is_truthy


def test_repr_integer():
    assert skill_repr(3) == "3"


def test_repr_float_keeps_decimal():
    assert skill_repr(1.0) == "1.0"
    assert skill_repr(2.5) == "2.5"


def test_repr_string_is_quoted():
    assert skill_repr("hello") == '"hello"'


def test_repr_string_escapes_quote_and_backslash():
    assert skill_repr('a"b\\c') == '"a\\"b\\\\c"'


def test_repr_nil_and_true():
    assert skill_repr(NIL) == "nil"
    assert skill_repr(TRUE) == "t"


def test_repr_symbol_is_bare():
    assert skill_repr(Symbol("rect")) == "rect"


def test_repr_list_is_space_separated_in_parens():
    assert skill_repr([1, 2, 3]) == "(1 2 3)"


def test_repr_nested_list():
    assert skill_repr([[0.0, 0.0], [2.5, 1.0]]) == "((0.0 0.0) (2.5 1.0))"


def test_repr_empty_list_is_nil():
    assert skill_repr([]) == "nil"


def test_is_truthy_only_nil_is_false():
    assert is_truthy(TRUE) is True
    assert is_truthy(0) is True
    assert is_truthy("") is True
    assert is_truthy([]) is True
    assert is_truthy(NIL) is False


# --- Final fix wave: no Python repr on the wire (finding 6) ---------------


def test_repr_of_value_with_no_wire_representation_raises_skill_error():
    class NoWireRepr:
        pass

    with pytest.raises(SkillError):
        skill_repr(NoWireRepr())
