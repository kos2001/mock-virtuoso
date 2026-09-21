"""mock-virtuoso 명령줄 진입점."""

from __future__ import annotations

import argparse
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

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

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
