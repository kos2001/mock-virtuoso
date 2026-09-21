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


def test_if_positional_form_true():
    assert run('if(t "yes" "no")') == "yes"


def test_if_positional_form_false():
    assert run('if(nil "yes" "no")') == "no"


def test_if_positional_form_true_no_else():
    assert run('if(t "yes")') == "yes"


def test_if_positional_form_false_no_else():
    assert run('if(nil "yes")') is NIL


def test_if_keyword_form_still_works_with_multi_form_branches():
    assert run('if(t then 1 2 3 else 4)') == 3
    assert run('if(nil then 1 else 4 5 6)') == 6


def test_if_positional_form_too_many_forms_raises():
    with pytest.raises(SkillError):
        run('if(t "a" "b" "c")')


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


def test_return_outside_prog_raises_skill_error():
    with pytest.raises(SkillError) as exc:
        run("return(1)")
    assert "return" in str(exc.value)
    assert "prog" in str(exc.value)


def test_return_outside_prog_in_foreach_raises_skill_error():
    with pytest.raises(SkillError):
        run("foreach(x list(1 2) return(9))")


# --- Final fix wave: special forms must go through the error boundary too
# (finding 4), and AttributeError/OSError must convert like the other
# malformed-call exceptions (finding 5). ------------------------------


@pytest.mark.parametrize("source", ["setq('a)", "when()", "cond(())"])
def test_malformed_special_form_call_raises_skill_error_not_raw_exception(source):
    # Previously these leaked a raw IndexError straight out of
    # evaluate_source (and printed a stderr traceback at the server
    # layer), because the try/except SkillError-conversion boundary in
    # _eval_call only wrapped the builtin dispatch branch, not the
    # _SPECIAL_FORMS branch.
    with pytest.raises(SkillError):
        run(source)


def test_attribute_error_from_a_builtin_converts_to_skill_error():
    it = Interpreter()

    def boom(interp, args, kwargs):
        return args[0].no_such_attribute

    it.register("boom", boom)
    with pytest.raises(SkillError):
        it.evaluate_source("boom(1)")


def test_prog_return_still_survives_the_error_boundary_change():
    # Task 10 contract: _ProgReturn is control flow, not an error, and
    # must keep unwinding to its enclosing prog even after the
    # try/except was widened to cover special forms.
    result = run(
        'prog((cv) unless(cv return("ERROR")) return("ok"))')
    assert result == "ERROR"


def test_lambda_is_a_return_boundary():
    interp = Interpreter()
    interp.register("applyOne",
                     lambda it, args, kwargs: it.call_lambda(args[0], [args[1]]))
    result = interp.evaluate_source(
        'prog((a) a = applyOne(lambda((x) return(x + 1)) 5) a + 100)')
    assert result == 106


def test_errset_returns_value_on_success():
    assert run("errset(1 + 2)") == 3


def test_errset_returns_nil_on_skill_error():
    assert run("errset(noSuchFn())") is NIL


def test_errset_ignores_optional_second_argument():
    assert run("errset(1 + 2 t)") == 3


def test_errset_does_not_swallow_prog_return():
    # A return() destined for an enclosing prog must keep unwinding
    # through errset, not be caught as an error.
    result = run('prog((cv) errset(return("ERROR")) return("ok"))')
    assert result == "ERROR"


def test_errset_does_not_swallow_step_budget_exceeded():
    with pytest.raises(StepBudgetExceeded):
        run("errset(foreach(i list(1 2 3) x = 1))", step_budget=5)


def test_errset_does_not_swallow_timeout():
    import time

    from mock_virtuoso.skill.errors import EvaluationTimeout

    interp = Interpreter()
    with pytest.raises(EvaluationTimeout):
        interp.evaluate_source(
            'errset(foreach(x list(1 2 3 4 5 6 7 8 9 10) x + 1))',
            deadline=time.monotonic() - 1,
        )
