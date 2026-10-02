"""Run SKILL through the authenticated bridge on an explicit local floor lane."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def lane_port(path: Path, profile: str) -> int:
    from dotenv import dotenv_values

    values = dotenv_values(path, interpolate=False)
    if values.get(f"VB_REMOTE_HOST_{profile}") not in ("localhost", "127.0.0.1"):
        raise ValueError("Expected an explicitly configured local floor lane")
    port = int(values.get(f"VB_LOCAL_PORT_{profile}") or "0")
    remote = int(values.get(f"VB_REMOTE_PORT_{profile}") or "0")
    if not 1 <= port <= 65535 or port != remote:
        raise ValueError("Local floor lane requires matching valid local/remote ports")
    return port


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=Path(__file__).resolve().parents[1] / "floor/lanes.env")
    parser.add_argument("-p", "--profile", required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--stdin", action="store_true")
    source.add_argument("--file", type=Path)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    try:
        from virtuoso_bridge import VirtuosoClient

        port = lane_port(args.env, args.profile)
        skill = sys.stdin.read() if args.stdin else args.file.read_text(encoding="utf-8")
        if not skill.strip() or len(skill.encode("utf-8")) > 256 * 1024:
            raise ValueError("Provide nonempty SKILL up to 256 KiB")
        if not 1 <= args.timeout <= 600:
            raise ValueError("Timeout must be 1..600 seconds")
        client = VirtuosoClient.local(port=port, timeout=args.timeout)
        result = client.execute_skill(f"progn(\n{skill}\n)", timeout=args.timeout)
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=True))
        return 0 if result.status.value == "success" else 1
    except (OSError, ValueError, ImportError) as exc:
        print(json.dumps({"status": "error", "errors": [str(exc)]}, ensure_ascii=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
