"""mock-virtuoso 명령줄 진입점."""

from __future__ import annotations

import argparse
import json
import signal
import sys
import threading

from mock_virtuoso.server import MockVirtuosoServer
from mock_virtuoso.session import Session
from mock_virtuoso.skill.errors import SkillError
from mock_virtuoso.skill.values import skill_repr


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mock-virtuoso")
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="RAMIC 프로토콜 서버를 띄운다")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=65432)
    serve.add_argument("--artifact-dir", default=None)

    ev = sub.add_parser("eval", help="SKILL 식 하나를 실행하고 결과를 출력한다")
    ev.add_argument("expression")

    circuit = sub.add_parser("circuit", help="Validate, export or simulate a circuit JSON file")
    circuit.add_argument("file")
    circuit.add_argument("--action", choices=("check", "netlist", "simulate"), default="check")
    circuit.add_argument("--ngspice")
    circuit.add_argument("--output", default="simulation-runs")

    verify = sub.add_parser("verify", help="Run open-source SKY130 DRC/LVS with KLayout")
    verify.add_argument("--klayout", required=True, help="KLayout batch executable")
    verify.add_argument("--gds", required=True)
    verify.add_argument("--top", required=True)
    verify.add_argument("--netlist", help="Self-contained reference SPICE netlist")
    verify.add_argument("--substrate", default="sky130_gnd", help="LVS substrate net name, e.g. VNB")
    verify.add_argument("--spice-units", choices=("micron", "si"), default="micron",
                        help="SKY130 micron dimensions (W=0.65) or SI dimensions (W=0.65u)")
    verify.add_argument("--scope", choices=("cell", "chip"), default="cell",
                        help="Review gate: cell (DRC/LVS) or chip (also density/ERC/antenna)")
    verify.add_argument("--decks", default=".tools/sky130")
    verify.add_argument("--output", default="verification-runs")
    verify.add_argument("--timeout", type=int, default=300)
    verify.add_argument("--constraints", help="JSON file containing rules and optional max_width_um/max_height_um")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "circuit":
        from mock_virtuoso.circuit import check_circuit, netlist
        from mock_virtuoso.simulation import simulate
        try:
            with open(args.file, encoding="utf-8") as stream:
                circuit = json.load(stream)
            if args.action == "netlist":
                print(netlist(circuit))
                return 0
            result = (check_circuit(circuit) if args.action == "check" else
                      simulate(circuit, executable=args.ngspice, output=args.output))
            print(json.dumps(result, indent=2))
            return 0 if result["status"] == "pass" else 1
        except (ValueError, OSError) as exc:
            print(json.dumps({"status": "error", "reason": str(exc)}))
            return 2

    if args.command == "verify":
        from mock_virtuoso.verification import run_verification
        try:
            constraints = None
            if args.constraints:
                with open(args.constraints, encoding="utf-8") as stream:
                    constraints = json.load(stream)
            result = run_verification(executable=args.klayout, gds=args.gds,
                                      top=args.top, decks=args.decks,
                                      output=args.output, netlist=args.netlist,
                                      timeout=args.timeout, substrate=args.substrate, scope=args.scope,
                                      spice_units=args.spice_units, project_constraints=constraints)
        except (ImportError, OSError, ValueError, RuntimeError) as exc:
            print(json.dumps({"status": "error", "reason": str(exc)}))
            return 2
        print(json.dumps(result, indent=2))
        return 0 if result["signoff"]["status"] == "ready_for_review" else 1

    if args.command == "eval":
        session = Session()
        try:
            print(skill_repr(session.evaluate(args.expression)))
        except SkillError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0

    if args.command == "serve":
        session = Session(artifact_dir=args.artifact_dir)
        server = MockVirtuosoServer(session, host=args.host, port=args.port)
        server.start()
        print(f"mock-virtuoso listening on {args.host}:{server.port}", flush=True)
        print("point the bridge at it with "
              f"VirtuosoClient.local(port={server.port})", flush=True)
        stop_event = threading.Event()

        def _on_signal(_signum: int, _frame: object) -> None:
            stop_event.set()

        signal.signal(signal.SIGINT, _on_signal)
        try:
            while not stop_event.wait(timeout=0.5):
                pass
        finally:
            server.stop()
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
