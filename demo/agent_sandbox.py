"""Put mock-virtuoso where a local Cadence Virtuoso would be, then stay running.

`virtuoso-bridge` already supports a LOCAL mode: when its tunnel-state file says
mode="local", the client connects straight to 127.0.0.1:<port> with no SSH. This
script starts the mock on a fixed port and writes exactly that state, so the
bridge's CLI, its Python API and its shipped agent skills all work unmodified —
they simply find the mock listening where Virtuoso would be.

Run:  .venv/bin/python demo/agent_sandbox.py [--port 65432]
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
import tempfile
import time
from pathlib import Path

from mock_virtuoso.auth import Authenticator
from mock_virtuoso.server import MockVirtuosoServer
from mock_virtuoso.session import Session


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=65432)
    ap.add_argument("--artifact-dir", default=None)
    args = ap.parse_args()

    artifacts = Path(args.artifact_dir) if args.artifact_dir else Path(
        tempfile.mkdtemp(prefix="virtuoso-agent-"))

    server = MockVirtuosoServer(Session(artifact_dir=artifacts), port=args.port)
    # Agents here reach the daemon as separate processes through the bridge CLI,
    # so there is no client object to take a token from. Read the same file the
    # bridge's clients read: a bridge new enough to have token auth gives an
    # authenticated daemon sharing their secret, an older one gives the legacy
    # wire its clients expect.
    try:
        from virtuoso_bridge import daemon_auth
        server.auth = Authenticator(daemon_auth.read_or_create_local_token())
    except ImportError:
        server.auth = Authenticator(None)
    server.start()

    # Write the bridge's own local-mode state, using the bridge's own path helper
    from virtuoso_bridge.transport.tunnel import _state_file  # noqa: PLC2701
    state_path = _state_file(None)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({
        "mode": "local",
        "port": server.port,
        "tunnel_pid": None,
        "remote_host": "localhost",
        "setup_path": None,
        "profile": None,
        "started_at": time.time(),
    }, indent=2), encoding="utf-8")

    env_path = Path.home() / ".virtuoso-bridge" / ".env"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(
        "# written by mock-virtuoso demo/agent_sandbox.py\n"
        "VB_REMOTE_HOST=localhost\n"
        f"VB_LOCAL_PORT={server.port}\n"
        f"VB_REMOTE_PORT={server.port}\n", encoding="utf-8")

    print(f"mock-virtuoso listening on 127.0.0.1:{server.port}")
    print(f"bridge state : {state_path}")
    print(f"bridge env   : {env_path}")
    print(f"artifacts    : {artifacts}")
    print("\nThe bridge now believes a local Virtuoso is running. Try:")
    print("  virtuoso-bridge status")
    print("  virtuoso-bridge eval '1+2'")
    print("  virtuoso-bridge windows")
    print("\nCtrl-C to stop.")

    stop = {"v": False}
    signal.signal(signal.SIGINT, lambda *_: stop.__setitem__("v", True))
    signal.signal(signal.SIGTERM, lambda *_: stop.__setitem__("v", True))
    try:
        while not stop["v"]:
            time.sleep(0.4)
    finally:
        server.stop()
        try:
            state_path.unlink()
        except OSError:
            pass
        print("\nstopped; bridge state file removed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
