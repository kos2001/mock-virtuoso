"""SKILL 이밸류에이터.

DB를 모른다. ``~>``는 ``SkillObject`` 프로토콜에만 의존한다.
"""

from __future__ import annotations

from typing import Callable

import time

from mock_virtuoso.skill import ast_nodes as A
from mock_virtuoso.skill.errors import (
    EvaluationTimeout,
    SkillError,
    StepBudgetExceeded,
    UnknownFunction,
)
from mock_virtuoso.skill.reader import read_all
from mock_virtuoso.skill.values import NIL, TRUE, Symbol, SkillObject, is_truthy

Builtin = Callable[["Interpreter", list, dict], object]

_UNSET = object()


class _ProgReturn(Exception):
    """``return(...)``이 가장 가까운 ``prog``를 탈출하는 신호."""

    def __init__(self, value: object) -> None:
        super().__init__("return outside prog")
        self.value = value


class Environment:
    __slots__ = ("_vars", "_parent")

    def __init__(self, parent: "Environment | None" = None) -> None:
        self._vars: dict[str, object] = {}
        self._parent = parent

    def child(self) -> "Environment":
        return Environment(self)

    def define(self, name: str, value: object) -> None:
        self._vars[name] = value

    def get(self, name: str) -> object:
        env: Environment | None = self
        while env is not None:
            if name in env._vars:
                return env._vars[name]
            env = env._parent
        raise SkillError(f"unbound variable: {name}")

    def set(self, name: str, value: object) -> None:
        env: Environment | None = self
        while env is not None:
            if name in env._vars:
                env._vars[name] = value
                return
            env = env._parent
        # SKILL은 선언되지 않은 이름에 대입하면 전역에 만든다.
        root = self
        while root._parent is not None:
            root = root._parent
        root._vars[name] = value


class Lambda:
    __slots__ = ("params", "body", "env")

    def __init__(self, params: list[str], body: list[A.Node],
                 env: Environment) -> None:
        self.params = params
        self.body = body
        self.env = env


class Interpreter:
    def __init__(self, *, step_budget: int = 2_000_000) -> None:
        self.globals = Environment()
        self._builtins: dict[str, Builtin] = {}
        self._step_budget = step_budget
        self._steps = 0
        self._deadline: float | None = None
        self._step_check_counter = 0  # Check deadline every N steps for efficiency
        self._install_operators()
        from mock_virtuoso.skill import builtins_core
        builtins_core.install(self)

    # -- 등록 ------------------------------------------------------------

    def register(self, name: str, fn: Builtin) -> None:
        self._builtins[name] = fn

    def has(self, name: str) -> bool:
        return name in self._builtins

    def resolve_handle(self, text: str) -> object:
        raise SkillError(f"no object registry for handle {text}")

    # -- 진입점 ----------------------------------------------------------

    def evaluate_source(self, source: str, deadline: float | None = None) -> object:
        self._steps = 0
        self._deadline = deadline
        self._step_check_counter = 0
        forms = read_all(source)
        result: object = NIL
        try:
            for form in forms:
                result = self.eval_node(form, self.globals)
        except _ProgReturn:
            # A return() that escaped every enclosing prog (or a call_lambda
            # boundary) is a user error in the SKILL program, not an
            # interpreter crash: surface it as a SkillError like any other
            # runtime mistake, instead of leaking the internal control-flow
            # exception type.
            raise SkillError("return outside prog") from None
        finally:
            self._deadline = None
        return result

    # -- 평가 ------------------------------------------------------------

    def eval_node(self, node: A.Node, env: Environment) -> object:
        self._steps += 1
        if self._steps > self._step_budget:
            raise StepBudgetExceeded(
                f"evaluation exceeded {self._step_budget} steps")

        # Check deadline every 20 steps for efficiency, but if very short deadline, check more frequently
        if self._deadline is not None:
            self._step_check_counter += 1
            # For tight deadlines, check more often
            check_freq = 2 if time.monotonic() + 0.01 >= self._deadline else 20
            if self._step_check_counter >= check_freq:
                self._step_check_counter = 0
                if time.monotonic() >= self._deadline:
                    raise EvaluationTimeout()

        if isinstance(node, A.Const):
            return node.value
        if isinstance(node, A.Var):
            return env.get(node.name)
        if isinstance(node, A.Quote):
            return Symbol(node.name)
        if isinstance(node, A.Handle):
            return self.resolve_handle(node.text)
        if isinstance(node, A.Prop):
            return self._eval_prop(node, env)
        if isinstance(node, A.Group):
            result: object = NIL
            for item in node.items:
                result = self.eval_node(item, env)
            return result
        if isinstance(node, A.If):
            return self._eval_if(node, env)
        if isinstance(node, A.Call):
            return self._eval_call(node, env)
        raise SkillError(f"cannot evaluate node {node!r}")

    def _eval_prop(self, node: A.Prop, env: Environment) -> object:
        target = self.eval_node(node.target, env)
        if target is NIL:
            return NIL
        if not isinstance(target, SkillObject):
            raise SkillError(
                f"'~>{node.name}' applied to a non-object value")
        return target.get_prop(node.name)

    def _eval_if(self, node: A.If, env: Environment) -> object:
        if is_truthy(self.eval_node(node.cond, env)):
            return self.eval_node(node.then_node, env)
        if node.else_node is None:
            return NIL
        return self.eval_node(node.else_node, env)

    def _eval_call(self, node: A.Call, env: Environment) -> object:
        special = _SPECIAL_FORMS.get(node.name)
        if special is not None:
            return special(self, node, env)

        fn = self._builtins.get(node.name)
        if fn is None:
            raise UnknownFunction(node.name)
        args = [self.eval_node(a, env) for a in node.args]
        kwargs = {k: self.eval_node(v, env) for k, v in node.kwargs.items()}
        try:
            return fn(self, args, kwargs)
        except SkillError:
            # Covers StepBudgetExceeded/UnknownFunction/ParseError too
            # (all subclass SkillError) as well as any SkillError a
            # builtin raises deliberately: pass those through unchanged.
            raise
        except (IndexError, TypeError, ValueError, KeyError) as exc:
            # A malformed SKILL call (too few/wrong-typed arguments) must
            # surface as a SkillError, not leak the builtin's raw Python
            # exception. _ProgReturn is deliberately not caught here: it
            # is control flow, not an error, and must keep unwinding to
            # its enclosing prog/lambda boundary.
            raise SkillError(f"{node.name}: {exc}") from exc

    def call_lambda(self, fn: Lambda, args: list) -> object:
        env = fn.env.child()
        for name, value in zip(fn.params, args):
            env.define(name, value)
        # Deliberate contract: a lambda call is itself a return() boundary,
        # like prog. Without this, _ProgReturn would unwind dynamically to
        # whatever prog frame happens to be on the Python call stack rather
        # than the frame lexically enclosing the lambda (or escape entirely
        # if none is on the stack). Real virtuoso_bridge lambdas never use
        # return(), so this choice is unconstrained by real usage; it is
        # picked now, before Task 5's mapcar makes it reachable.
        try:
            result: object = NIL
            for form in fn.body:
                result = self.eval_node(form, env)
            return result
        except _ProgReturn as ret:
            return ret.value

    # -- 연산자 ----------------------------------------------------------

    def _install_operators(self) -> None:
        def arith(op):
            def run(it, args, kwargs):
                a, b = args[0], args[1]
                if op == "+":
                    return a + b
                if op == "-":
                    return a - b
                if op == "*":
                    return a * b
                if b == 0:
                    raise SkillError("division by zero")
                return a / b
            return run

        for op in ("+", "-", "*", "/"):
            self.register(op, arith(op))

        def compare(op):
            def run(it, args, kwargs):
                a, b = args[0], args[1]
                if op == "==":
                    ok = _skill_equal(a, b)
                elif op == "!=":
                    ok = not _skill_equal(a, b)
                elif op == "<":
                    ok = a < b
                elif op == ">":
                    ok = a > b
                elif op == "<=":
                    ok = a <= b
                else:
                    ok = a >= b
                return TRUE if ok else NIL
            return run

        for op in ("==", "!=", "<", ">", "<=", ">="):
            self.register(op, compare(op))

        self.register("!", lambda it, args, kwargs:
                      NIL if is_truthy(args[0]) else TRUE)
        # 점 리터럴 a:b 는 2원소 리스트다.
        self.register(":", lambda it, args, kwargs: [args[0], args[1]])


def _skill_equal(a: object, b: object) -> bool:
    if isinstance(a, Symbol) and isinstance(b, Symbol):
        return a.name == b.name
    if a is NIL or b is NIL:
        return a is b
    if a is TRUE or b is TRUE:
        return a is b
    return a == b


# -- 특수형 ---------------------------------------------------------------

def _sf_progn(it: Interpreter, node: A.Call, env: Environment) -> object:
    result: object = NIL
    for form in node.args:
        result = it.eval_node(form, env)
    return result


def _sf_prog(it: Interpreter, node: A.Call, env: Environment) -> object:
    if not node.args:
        raise SkillError("prog requires a variable list")
    inner = env.child()
    for name, _ in _collect_bindings(node.args[0]):
        inner.define(name, NIL)
    try:
        result: object = NIL
        for form in node.args[1:]:
            result = it.eval_node(form, inner)
        return result
    except _ProgReturn as ret:
        return ret.value


def _sf_let(it: Interpreter, node: A.Call, env: Environment) -> object:
    if not node.args:
        raise SkillError("let requires a binding list")
    inner = env.child()
    for name, value_node in _collect_bindings(node.args[0]):
        inner.define(
            name, NIL if value_node is None else it.eval_node(value_node, env))
    result: object = NIL
    for form in node.args[1:]:
        result = it.eval_node(form, inner)
    return result


def _collect_bindings(spec: A.Node) -> list[tuple[str, A.Node | None]]:
    """``prog((a b))`` / ``let(((r 1)))``의 바인딩을 (이름, 초기값) 목록으로.

    리더는 괄호 그룹을 ``Group``으로, 단일 이름을 ``Var``로 준다.
    ``(r 1)`` 처럼 이름 뒤에 값이 오면 초기값이 있는 바인딩이다.
    """
    if isinstance(spec, A.Var):
        return [(spec.name, None)]

    if isinstance(spec, A.Group):
        items = spec.items
        if (len(items) == 2 and isinstance(items[0], A.Var)
                and not isinstance(items[1], (A.Var, A.Group))):
            return [(items[0].name, items[1])]
        out: list[tuple[str, A.Node | None]] = []
        for item in items:
            out.extend(_collect_bindings(item))
        return out

    raise SkillError("malformed binding list")


def _sf_return(it: Interpreter, node: A.Call, env: Environment) -> object:
    value = it.eval_node(node.args[0], env) if node.args else NIL
    raise _ProgReturn(value)


def _sf_setq(it: Interpreter, node: A.Call, env: Environment) -> object:
    target = node.args[0]
    if not isinstance(target, A.Quote):
        raise SkillError("setq target must be a symbol")
    value = it.eval_node(node.args[1], env)
    env.set(target.name, value)
    return value


def _sf_when(it: Interpreter, node: A.Call, env: Environment) -> object:
    if not is_truthy(it.eval_node(node.args[0], env)):
        return NIL
    result: object = NIL
    for form in node.args[1:]:
        result = it.eval_node(form, env)
    return result


def _sf_unless(it: Interpreter, node: A.Call, env: Environment) -> object:
    if is_truthy(it.eval_node(node.args[0], env)):
        return NIL
    result: object = NIL
    for form in node.args[1:]:
        result = it.eval_node(form, env)
    return result


def _sf_foreach(it: Interpreter, node: A.Call, env: Environment) -> object:
    if len(node.args) < 2:
        raise SkillError("foreach requires a variable and a list")
    var = node.args[0]
    if not isinstance(var, A.Var):
        raise SkillError("foreach variable must be a name")
    sequence = it.eval_node(node.args[1], env)
    if sequence is NIL:
        return NIL
    if not isinstance(sequence, list):
        raise SkillError("foreach needs a list")
    inner = env.child()
    for item in sequence:
        inner.define(var.name, item)
        for form in node.args[2:]:
            it.eval_node(form, inner)
    return NIL


def _sf_and(it: Interpreter, node: A.Call, env: Environment) -> object:
    result: object = TRUE
    for form in node.args:
        result = it.eval_node(form, env)
        if not is_truthy(result):
            return NIL
    return result


def _sf_or(it: Interpreter, node: A.Call, env: Environment) -> object:
    for form in node.args:
        result = it.eval_node(form, env)
        if is_truthy(result):
            return result
    return NIL


def _sf_cond(it: Interpreter, node: A.Call, env: Environment) -> object:
    for clause in node.args:
        if isinstance(clause, A.Group):
            test_node, body = clause.items[0], clause.items[1:]
        else:
            test_node, body = clause, []
        if not is_truthy(it.eval_node(test_node, env)):
            continue
        result: object = NIL
        for form in body:
            result = it.eval_node(form, env)
        return result
    return NIL


def _sf_lambda(it: Interpreter, node: A.Call, env: Environment) -> object:
    if not node.args:
        raise SkillError("lambda requires a parameter list")
    params = [name for name, _ in _collect_bindings(node.args[0])]
    return Lambda(params, list(node.args[1:]), env)


def _sf_quote(it: Interpreter, node: A.Call, env: Environment) -> object:
    target = node.args[0]
    if isinstance(target, A.Var):
        return Symbol(target.name)
    return it.eval_node(target, env)


def _sf_boundp(it: Interpreter, node: A.Call, env: Environment) -> object:
    if not node.args:
        raise SkillError("boundp requires a symbol")
    target = node.args[0]
    if not isinstance(target, A.Quote):
        raise SkillError("boundp requires a quoted symbol")
    name = target.name
    try:
        env.get(name)
    except SkillError:
        return NIL
    return TRUE


_SPECIAL_FORMS = {
    "progn": _sf_progn,
    "prog": _sf_prog,
    "let": _sf_let,
    "return": _sf_return,
    "setq": _sf_setq,
    "when": _sf_when,
    "unless": _sf_unless,
    "foreach": _sf_foreach,
    "and": _sf_and,
    "&&": _sf_and,
    "or": _sf_or,
    "||": _sf_or,
    "cond": _sf_cond,
    "lambda": _sf_lambda,
    "quote": _sf_quote,
    "boundp": _sf_boundp,
}
