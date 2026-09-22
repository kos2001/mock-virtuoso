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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# One loader, because the planner reads these cases too now and two parsers
# for one file format is one parser too many.
from toolkit.precedent import AUDIENCES, load_cases  # noqa: E402


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
        print(template(len(cases) + 1))
    else:
        print("\nEvery failure in this session is already a case.")
    return 0


def template(number: int) -> str:
    """The front matter a new case has to carry, printed where it is needed.

    Six fields are required and the suite fails a case missing any of them.
    Saying so only in the README meant reading the output here, writing the
    case there, and finding out from a red test which field was forgotten.
    """
    return f"""
Front matter every case needs — the suite checks all six:

    ---
    id: {number:03d}-<short-kebab-name>       # must match the filename
    outcome: failure | success
    signature: "<regex matching the reply above>"   # optional, but it is what
                                                    # makes the case findable
    lanes: <which lanes hit it, or all>
    audience: {" | ".join(AUDIENCES)}    # who reads it; `planner` cases go
                                          # into the plan prompt, so keep that
                                          # list short enough to be read
    rule: "<the sentence you added>"   # or none
    rule_in: code | <path under skills/design-floor/> | none
    ---
"""


if __name__ == "__main__":
    raise SystemExit(main())
