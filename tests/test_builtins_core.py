from mock_virtuoso.skill.evaluator import Interpreter
from mock_virtuoso.skill.values import NIL, TRUE


def run(source):
    return Interpreter().evaluate_source(source)


def test_sprintf_string_and_integer():
    assert run('sprintf(nil "%s has %d" "box" 3)') == "box has 3"


def test_sprintf_fixed_precision_float():
    assert run('sprintf(nil "%.3f" 1.5)') == "1.500"


def test_sprintf_percent_L_on_list():
    assert run('sprintf(nil "%L" list(1 2))') == "(1 2)"


def test_sprintf_percent_L_on_nested_list():
    assert run('sprintf(nil "%L" list(list(0.0 0.0) list(2.5 1.0)))') \
        == "((0.0 0.0) (2.5 1.0))"


def test_sprintf_percent_L_on_string_keeps_quotes():
    assert run('sprintf(nil "%L" "hi")') == '"hi"'


def test_sprintf_percent_L_on_nil():
    assert run('sprintf(nil "%L" nil)') == "nil"


def test_strcat_joins():
    assert run('strcat("a" "b" "c")') == "abc"


def test_list_and_length():
    assert run("length(list(1 2 3))") == 3


def test_length_of_nil_is_zero():
    assert run("length(nil)") == 0


def test_car_and_cadr():
    assert run("car(list(10 20 30))") == 10
    assert run("cadr(list(10 20 30))") == 20


def test_car_of_nil_is_nil():
    assert run("car(nil)") is NIL


def test_xcoord_and_ycoord():
    assert run("xCoord(list(1.5 2.5))") == 1.5
    assert run("yCoord(list(1.5 2.5))") == 2.5


def test_nth_is_zero_based():
    assert run("nth(1 list(10 20 30))") == 20


def test_mapcar_with_lambda():
    assert run("mapcar(lambda((x) x * 2) list(1 2 3))") == [2, 4, 6]


def test_member_returns_tail_or_nil():
    assert run("member(2 list(1 2 3))") == [2, 3]
    assert run("member(9 list(1 2 3))") is NIL


def test_boundp_reports_definition():
    assert run("boundp('nope)") is NIL
    assert run("x = 1 boundp('x)") is TRUE


def test_atoi_and_atof():
    assert run('atoi("42")') == 42
    assert run('atof("1.5")') == 1.5


def test_printf_returns_t_and_does_not_crash():
    assert run('printf("hello %d\\n" 1) ') is TRUE
