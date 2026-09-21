"""RAMIC 브릿지 프로토콜을 말하는 TCP 서버.

바이트 계약은 실제 데몬(ramic_bridge_daemon_3.py)에서 확인한 것이다:
성공은 0x02 + %L 포맷 결과, 실패는 0x15 + 메시지, 종료 마커는 없다.
"""

from __future__ import annotations

import json
import socket
import threading

from mock_virtuoso.session import Session
from mock_virtuoso.skill.errors import SkillError
from mock_virtuoso.skill.values import skill_repr

STX = b"\x02"
NAK = b"\x15"
_RECV = 65536


def build_response(session: Session, skill_code: str, timeout: float) -> bytes:
    if timeout <= 0:
        return NAK + b"TimeoutError"
    try:
        value = session.evaluate(skill_code)
    except SkillError as exc:
        return NAK + str(exc).encode("utf-8")
    except Exception as exc:  # 예기치 못한 내부 오류도 NAK로 내보낸다
        return NAK + f"{type(exc).__name__}: {exc}".encode("utf-8")
    return STX + skill_repr(value).encode("utf-8")


class MockVirtuosoServer:
    def __init__(self, session: Session, host: str = "127.0.0.1",
                 port: int = 0) -> None:
        self.session = session
        self._host = host
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((host, port))
        self._socket.listen(1)
        self.port = self._socket.getsockname()[1]
        self._thread: threading.Thread | None = None
        self._stopping = threading.Event()

    # -- 수명 ------------------------------------------------------------

    def start(self) -> None:
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stopping.set()
        try:
            self._socket.close()
        except OSError:
            pass
        if self._thread is not None:
            self._thread.join(timeout=2)

    def __enter__(self) -> "MockVirtuosoServer":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()

    # -- 루프 ------------------------------------------------------------

    def _serve(self) -> None:
        while not self._stopping.is_set():
            try:
                conn, _ = self._socket.accept()
            except OSError:
                return
            with conn:
                try:
                    self._handle(conn)
                except OSError:
                    pass

    def _handle(self, conn: socket.socket) -> None:
        chunks: list[bytes] = []
        while True:
            chunk = conn.recv(_RECV)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)

        try:
            request = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            conn.sendall(NAK + f"JSONDecodeError: {exc}".encode("utf-8"))
            return

        response = build_response(
            self.session,
            request.get("skill", ""),
            request.get("timeout", 30),
        )
        conn.sendall(response)
