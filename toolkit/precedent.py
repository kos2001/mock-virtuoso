"""What the knowledge base already knows, reaching the prompt that needs it.

Seventeen cases record how this floor has failed and succeeded. Until now not
one of them reached the planner: every request was planned cold, free to
repeat a mistake this repository had already written down twice. The evidence
existed; it just never arrived where a decision was being made.

Two paths, both borrowed from `ppa-eda-agent/pipeline/case_retrieval.py`:

    guidance   before planning  — the standing lessons a plan can act on
    precedent  after a refusal  — the cases whose signature matches this error

Retrieval is exact matching on a case's `signature` regex rather than
similarity over prose. The corpus is seventeen cases whose failures are
labelled by the tools themselves, so a regex is more precise than a score,
needs no model, no index and no dependency, and — the part that matters — it
can say *why* a case was retrieved.

A case says who it is for. Most are lessons for an agent writing SKILL by
hand (`foreach` cannot count, a bare name is a variable) and would be noise in
a prompt that emits JSON ops. Only `audience: planner` cases go to the
planner, so the block stays short enough to be read.
"""

from __future__ import annotations

import re
from pathlib import Path

CASES = Path(__file__).resolve().parent.parent / "skills" / "design-floor" / "kb" / "cases"

# Who a case is written for. `agent` writes SKILL on the floor, `planner` turns
# a request into JSON ops, `floor` is the screen itself.
AUDIENCES = ("agent", "planner", "floor")


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


def audiences(case: dict) -> list[str]:
    return [a.strip() for a in (case.get("audience") or "").split(",") if a.strip()]


def lesson(case: dict) -> str:
    """The one sentence a case is worth quoting for.

    A case's `rule` is the sentence it put into a skill, which is exactly the
    lesson when there is one. Cases that produced no rule still carry a title
    that says what happened, so fall back to it rather than dropping the case.
    """
    rule = (case.get("rule") or "none").strip()
    if rule and rule != "none":
        return rule
    for line in case["body"].splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return case["id"]


def guidance_block(cases: list[dict] | None = None) -> str:
    """The standing lessons a planner can act on, or "" if there are none."""
    cases = load_cases() if cases is None else cases
    lines = [f"- {lesson(c)}" for c in cases if "planner" in audiences(c)]
    if not lines:
        return ""
    return ("Lessons this floor has already paid for; do not repeat them:\n"
            + "\n".join(lines))


def matching(error: str, cases: list[dict] | None = None) -> list[dict]:
    """Cases whose signature matches this error text, in case order.

    Exact matching is the whole argument: a case retrieved here can name the
    pattern it matched on, which a similarity score cannot.
    """
    cases = load_cases() if cases is None else cases
    found = []
    for case in cases:
        signature = case.get("signature")
        if signature and re.search(signature, error, re.I):
            found.append(case)
    return found


def precedent_block(error: str, cases: list[dict] | None = None) -> str:
    """What happened the other times this floor saw this error, or ""."""
    found = matching(error, cases)
    if not found:
        return ""
    lines = [f"- {lesson(c)}  [{c['id']}]" for c in found]
    return ("This floor has seen this failure before:\n" + "\n".join(lines))
