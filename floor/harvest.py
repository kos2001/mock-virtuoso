"""Harvest a design-floor session into knowledge-base candidates.

The floor records every SKILL expression that crossed the wire and every reply.
That transcript is the only honest account of what agents actually tried, so
new cases come from it rather than from anyone's memory of the session.

Each case in `skills/design-floor/kb/cases/` carries a `signature` regex. This
groups a session's failures, matches each group against those signatures, and
prints what is already known and what is not. The unmatched groups are the
cases worth writing.

    .venv/bin/python floor/harvest.py                     # the live floor
    .venv/bin/python floor/harvest.py --feed saved.json   # a saved feed
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

CASES = Path(__file__).resolve().parent.parent / "skills" / "design-floor" / "kb" / "cases"


def load_cases(directory: Path = CASES) -> list[dict]:
    """Every case, with its front matter parsed. Order is the filename's."""
    cases = []
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            raise ValueError(f"{path.name}: no front matter")
        front, _, body = text[4:].partition("\n---\n")
        fields: dict = {"path": path, "body": body.strip()}
        for line in front.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip().strip('"')
        cases.append(fields)
    return cases


def fetch_feed(source: str) -> dict:
    if source.startswith("http"):
        with urllib.request.urlopen(source + "/api/feed?since=0", timeout=10) as response:
            return json.load(response)
    return json.loads(Path(source).read_text(encoding="utf-8"))


def group_failures(events: list[dict]) -> Counter:
    """Failures grouped by their reply, with quoted detail blanked out.

    Two agents guessing two different slot names are one lesson, not two, so
    the quoted part of a message is what gets collapsed.
    """
    grouped: Counter = Counter()
    for event in events:
        if event.get("ok"):
            continue
        grouped[re.sub(r"'[^']*'", "'…'", (event.get("reply") or "").strip())[:120]] += 1
    return grouped


def match_case(reply: str, cases: list[dict]) -> dict | None:
    for case in cases:
        pattern = case.get("signature")
        if pattern and re.search(pattern, reply):
            return case
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feed", default="http://127.0.0.1:8900",
                        help="a running floor's base URL, or a saved feed JSON file")
    args = parser.parse_args()

    try:
        feed = fetch_feed(args.feed)
    except OSError as exc:
        print(f"cannot read the feed at {args.feed}: {exc}", file=sys.stderr)
        return 1

    cases = load_cases()
    events = feed.get("events", [])
    grouped = group_failures(events)
    total = feed.get("seq", len(events))

    print(f"{total} calls, {sum(grouped.values())} failures, "
          f"{len(grouped)} distinct, {len(cases)} cases on file\n")

    known, unknown = [], []
    for reply, count in grouped.most_common():
        case = match_case(reply, cases)
        (known if case else unknown).append((count, reply, case))

    if known:
        print("Already a case:")
        for count, reply, case in known:
            print(f"  {count:3d}x  {case['id']:<28} {reply[:64]}")
    if unknown:
        print("\nNot yet a case — these are the ones worth writing:")
        for count, reply, _ in unknown:
            print(f"  {count:3d}x  {reply[:76]}")
    else:
        print("\nEvery failure in this session is already a case.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
