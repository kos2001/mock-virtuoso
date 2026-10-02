"""Explicit circuit extensions for agents using the existing SKILL bridge."""
import json

from mock_virtuoso.circuit import check_circuit, netlist, validate_circuit
from mock_virtuoso.db.objects import CellView
from mock_virtuoso.simulation import simulate
from mock_virtuoso.skill.errors import SkillError
from mock_virtuoso.skill.values import TRUE


def install(session):
    def cv_arg(args, *, loaded=True):
        if not args or not isinstance(args[0], CellView) or args[0].view_type != "schematic":
            raise SkillError("expected a schematic cellView")
        cv = args[0]
        if loaded and not cv.circuit:
            raise SkillError("No circuit loaded; use mockCircuitLoad with validated circuit JSON")
        return cv

    def load(it, args, kwargs):
        cv = cv_arg(args, loaded=False)
        if cv.mode == "r":
            raise SkillError("cannot edit a read-only schematic")
        if len(args) != 2 or not isinstance(args[1], str):
            raise SkillError("mockCircuitLoad expects a cellView and a JSON string")
        try:
            circuit = validate_circuit(json.loads(args[1]))
        except ValueError as exc:
            raise SkillError(str(exc)) from exc
        cv.circuit.clear()
        cv.circuit.update(circuit)
        cv.saved = False
        return TRUE

    def read(it, args, kwargs):
        return json.dumps(cv_arg(args).circuit)

    def check(it, args, kwargs):
        return json.dumps(check_circuit(cv_arg(args).circuit))

    def sch_check(it, args, kwargs):
        report = check_circuit(cv_arg(args).circuit)
        return [len(report["issues"]), 0]

    def export(it, args, kwargs):
        return netlist(cv_arg(args).circuit)

    def run(it, args, kwargs):
        return json.dumps(simulate(cv_arg(args).circuit, output=session.artifact_dir / "simulation-runs"))

    for name, fn in (("mockCircuitLoad", load), ("mockCircuitRead", read),
                     ("mockCircuitERC", check), ("mockCircuitNetlist", export),
                     ("mockCircuitSimulate", run), ("schCheck", sch_check)):
        session.interp.register(name, fn)
