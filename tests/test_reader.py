import pytest

from mock_virtuoso.skill import ast_nodes as A
from mock_virtuoso.skill.errors import ParseError
from mock_virtuoso.skill.reader import read_all
from mock_virtuoso.skill.values import NIL, TRUE


def read_one(source):
    forms = read_all(source)
    assert len(forms) == 1
    return forms[0]


def test_number_and_string_constants():
    assert read_one("3").value == 3
    assert read_one("2.5").value == 2.5
    assert read_one('"hi"').value == "hi"


def test_nil_and_t_are_constants():
    assert read_one("nil").value is NIL
    assert read_one("t").value is TRUE


def test_call_with_positional_args():
    node = read_one("f(1 2)")
    assert isinstance(node, A.Call)
    assert node.name == "f"
    assert [a.value for a in node.args] == [1, 2]
    assert node.kwargs == {}


def test_call_with_keyword_args():
    node = read_one('hiWindowSaveImage(w ?path "p" ?toplevel t)')
    assert node.name == "hiWindowSaveImage"
    assert len(node.args) == 1
    assert set(node.kwargs) == {"path", "toplevel"}
    assert node.kwargs["path"].value == "p"


def test_property_access_chain():
    node = read_one("win~>cellView~>viewName")
    assert isinstance(node, A.Prop)
    assert node.name == "viewName"
    assert isinstance(node.target, A.Prop)
    assert node.target.name == "cellView"
    assert node.target.target.name == "win"


def test_if_then_else_keyword_form():
    node = read_one("if(a then b else c)")
    assert isinstance(node, A.If)
    assert node.cond.name == "a"
    assert node.then_node.name == "b"
    assert node.else_node.name == "c"


def test_if_without_else():
    node = read_one("if(a then b)")
    assert isinstance(node, A.If)
    assert node.else_node is None


def test_if_positional_form():
    node = read_one("if(a b c)")
    assert isinstance(node, A.If)
    assert node.cond.name == "a"
    assert node.then_node.name == "b"
    assert node.else_node.name == "c"


def test_if_positional_form_without_else():
    node = read_one("if(a b)")
    assert isinstance(node, A.If)
    assert node.cond.name == "a"
    assert node.then_node.name == "b"
    assert node.else_node is None


def test_if_positional_form_with_too_many_forms_raises():
    with pytest.raises(ParseError):
        read_all('if(t "a" "b" "c")')


def test_assignment_is_a_call_to_setq():
    node = read_one("cv = 3")
    assert isinstance(node, A.Call)
    assert node.name == "setq"
    assert isinstance(node.args[0], A.Quote)
    assert node.args[0].name == "cv"
    assert node.args[1].value == 3


def test_arithmetic_precedence():
    # (1 + 2) * 3 은 괄호 때문에 곱셈이 바깥
    node = read_one("(1 + 2) * 3")
    assert node.name == "*"
    assert node.args[0].name == "+"


def test_multiplication_binds_tighter_than_addition():
    node = read_one("1 + 2 * 3")
    assert node.name == "+"
    assert node.args[1].name == "*"


def test_point_literal_colon():
    node = read_one("0.0:1.5")
    assert node.name == ":"
    assert [a.value for a in node.args] == [0.0, 1.5]


def test_unary_not():
    node = read_one("!cv")
    assert node.name == "!"
    assert node.args[0].name == "cv"


def test_quote_symbol():
    node = read_one("'RBMon")
    assert isinstance(node, A.Quote)
    assert node.name == "RBMon"


def test_handle_literal():
    node = read_one("db:0x1f")
    assert isinstance(node, A.Handle)
    assert node.text == "db:0x1f"


def test_parenthesised_group_with_several_items():
    # let((cv editCv) ...) 의 바인딩 목록. 브릿지가 상시 쓰는 형태다.
    node = read_one("let((cv editCv) cv)")
    bindings = node.args[0]
    assert isinstance(bindings, A.Group)
    assert [b.name for b in bindings.items] == ["cv", "editCv"]


def test_binding_with_initial_value_is_a_group():
    node = read_one("let(((r 1)) r)")
    inner = node.args[0]
    assert isinstance(inner, A.Group)
    assert inner.items[0].name == "r"
    assert inner.items[1].value == 1


def test_multiple_top_level_forms():
    forms = read_all("f() g()")
    assert len(forms) == 2


def test_trailing_operator_raises():
    with pytest.raises(ParseError):
        read_all("1 +")


def test_chained_assignment_is_right_associative():
    # a = b = c should parse as a = (b = c)
    node = read_one("a = b = c")
    assert isinstance(node, A.Call)
    assert node.name == "setq"
    assert isinstance(node.args[0], A.Quote)
    assert node.args[0].name == "a"
    # The value should be another setq for b = c
    inner = node.args[1]
    assert isinstance(inner, A.Call)
    assert inner.name == "setq"
    assert isinstance(inner.args[0], A.Quote)
    assert inner.args[0].name == "b"
    assert isinstance(inner.args[1], A.Var)
    assert inner.args[1].name == "c"


def test_invalid_assignment_left_side_raises():
    # Literal numbers cannot be assigned to
    with pytest.raises(ParseError):
        read_one("1 = 2")


def test_property_assignment():
    # obj~>slot = 5 should produce Call("setProp", [Var("obj"), Quote("slot"), Const(5)])
    node = read_one("obj~>slot = 5")
    assert isinstance(node, A.Call)
    assert node.name == "setProp"
    assert len(node.args) == 3
    assert isinstance(node.args[0], A.Var)
    assert node.args[0].name == "obj"
    assert isinstance(node.args[1], A.Quote)
    assert node.args[1].name == "slot"
    assert isinstance(node.args[2], A.Const)
    assert node.args[2].value == 5


def test_chained_property_assignment():
    # a~>b~>c = 5 should produce setProp with target a~>b
    node = read_one("a~>b~>c = 5")
    assert isinstance(node, A.Call)
    assert node.name == "setProp"
    assert len(node.args) == 3
    target = node.args[0]
    assert isinstance(target, A.Prop)
    assert target.name == "b"
    assert isinstance(target.target, A.Var)
    assert target.target.name == "a"
    assert isinstance(node.args[1], A.Quote)
    assert node.args[1].name == "c"
    assert isinstance(node.args[2], A.Const)
    assert node.args[2].value == 5


def test_assignment_in_progn_argument():
    # progn(cv = 3 foo()) — the first argument must be setq, not Call("=")
    node = read_one("progn(cv = 3 foo())")
    assert isinstance(node, A.Call)
    assert node.name == "progn"
    # First argument should be setq
    first_arg = node.args[0]
    assert isinstance(first_arg, A.Call)
    assert first_arg.name == "setq"
    assert isinstance(first_arg.args[0], A.Quote)
    assert first_arg.args[0].name == "cv"
    assert isinstance(first_arg.args[1], A.Const)
    assert first_arg.args[1].value == 3


def test_assignment_as_function_argument():
    # f(x = 5) — the argument must be setq, not Call("=")
    node = read_one("f(x = 5)")
    assert isinstance(node, A.Call)
    assert node.name == "f"
    arg = node.args[0]
    assert isinstance(arg, A.Call)
    assert arg.name == "setq"
    assert isinstance(arg.args[0], A.Quote)
    assert arg.args[0].name == "x"


def test_assignment_in_if_condition():
    # if(a = 1 then b) — the condition must be setq
    node = read_one("if(a = 1 then b)")
    assert isinstance(node, A.If)
    cond = node.cond
    assert isinstance(cond, A.Call)
    assert cond.name == "setq"
    assert isinstance(cond.args[0], A.Quote)
    assert cond.args[0].name == "a"


def test_invalid_assignment_in_function_call_raises():
    # f(1 = 2) — non-assignable left side must still raise
    with pytest.raises(ParseError):
        read_one("f(1 = 2)")


def test_property_assignment_in_function_call():
    # f(obj~>slot = 5) — must produce setProp in argument
    node = read_one("f(obj~>slot = 5)")
    assert isinstance(node, A.Call)
    assert node.name == "f"
    arg = node.args[0]
    assert isinstance(arg, A.Call)
    assert arg.name == "setProp"
    assert len(arg.args) == 3
    assert isinstance(arg.args[0], A.Var)
    assert arg.args[0].name == "obj"
    assert isinstance(arg.args[1], A.Quote)
    assert arg.args[1].name == "slot"


def test_composed_script_shape():
    # Real path from bridge: progn(cv = let(...) dbCreateRect(...))
    # The first argument must be setq, not Call("=")
    source = 'progn(cv = let((r) r) dbCreateRect(cv list("m1")))'
    node = read_one(source)
    assert isinstance(node, A.Call)
    assert node.name == "progn"
    # First arg is cv = let(...)
    first_arg = node.args[0]
    assert isinstance(first_arg, A.Call)
    assert first_arg.name == "setq"
    assert isinstance(first_arg.args[0], A.Quote)
    assert first_arg.args[0].name == "cv"
    # The value being assigned should be the let call
    assert isinstance(first_arg.args[1], A.Call)
    assert first_arg.args[1].name == "let"
