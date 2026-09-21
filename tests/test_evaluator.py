import pytest

from mock_virtuoso.skill.errors import SkillError, StepBudgetExceeded, UnknownFunction
from mock_virtuoso.skill.evaluator import Interpreter
from mock_virtuoso.skill.values import NIL, TRUE


def run(source, **kw):
    return Interpreter(**kw).evaluate_source(source)


def test_arithmetic():
    assert run("1 + 2") == 3
    assert run("(1 + 2) * 3") == 9
    assert run("7 / 2") == 3.5


def test_comparison_returns_t_or_nil():
    assert run("1 == 1") is TRUE
    assert run("1 == 2") is NIL


def test_logical_and_short_circuits():
    # 두 번째 인자가 평가되면 UnknownFunction이 터질 것이다.
    assert run("nil && boom()") is NIL


def test_logical_or_short_circuits():
    assert run("t || boom()") is TRUE


def test_setq_and_variable_lookup():
    assert run("x = 5 x + 1") == 6


def test_progn_returns_last():
    assert run("progn(1 2 3)") == 3


def test_let_scopes_bindings():
    assert run("x = 1 let((x) x = 9 x) + x") == 10


def test_prog_declares_nil_locals():
    assert run("prog((a) a)") is NIL


def test_return_escapes_prog():
    assert run('prog((a) return("early") a = 1 a)') == "early"


def test_return_escapes_only_nearest_prog():
    assert run('prog((a) a = prog((b) return(1) 2) a + 10)') == 11


def test_unless_runs_body_when_false():
    assert run('prog((cv) unless(cv return("ERROR")) return("ok"))') == "ERROR"


def test_when_runs_body_when_true():
    assert run("when(t 42)") == 42


def test_when_returns_nil_when_false():
    assert run("when(nil 42)") is NIL


def test_if_then_else():
    assert run("if(1 == 1 then 10 else 20)") == 10
    assert run("if(1 == 2 then 10 else 20)") == 20


def test_if_without_else_returns_nil():
    assert run("if(nil then 10)") is NIL


def test_foreach_iterates_and_returns_nil():
    assert run("total = 0 foreach(x list(1 2 3) total = total + x) total") == 6


def test_cond_picks_first_true_clause():
    assert run("cond((nil 1) (t 2) (t 3))") == 2


def test_unknown_function_raises():
    with pytest.raises(UnknownFunction) as exc:
        run("noSuchFunction(1)")
    assert "unknown function: noSuchFunction" in str(exc.value)


def test_unbound_variable_raises():
    with pytest.raises(SkillError):
        run("someUndefinedVar")


def test_step_budget_stops_runaway_loop():
    with pytest.raises(StepBudgetExceeded):
        run("x = 0 foreach(i list(1 2 3) x = x + 1)", step_budget=5)


def test_registered_builtin_is_callable():
    interp = Interpreter()
    interp.register("double", lambda it, args, kwargs: args[0] * 2)
    assert interp.evaluate_source("double(21)") == 42


def test_builtin_receives_keyword_arguments():
    seen = {}
    interp = Interpreter()

    def grab(it, args, kwargs):
        seen.update(kwargs)
        return NIL

    interp.register("grab", grab)
    interp.evaluate_source('grab(1 ?path "p")')
    assert seen == {"path": "p"}
