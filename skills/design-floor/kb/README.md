# Knowledge base

What agents actually tried on this floor, and what came of it.

Every case here was harvested from a real transcript, not remembered. The floor
records each SKILL expression that crossed the wire and each reply, so a session
leaves behind an honest account of where agents went wrong and where they went
right — and that account is the only input to this directory.

## The loop

```
run the floor  →  floor/harvest.py  →  failures with no case yet
                                    →  write the case
                                    →  put its rule where agents will read it
                                    →  a test checks the rule is really there
```

`floor/harvest.py` groups a session's failures and matches each group against
the `signature` of every case on file. What it cannot match is what nobody has
written down yet:

```bash
.venv/bin/python floor/harvest.py                    # against the running floor
.venv/bin/python floor/harvest.py --feed saved.json  # against a saved feed
```

A case is worth writing when the same thing would trip the next agent. A case
is worth *closing* when the lesson has been moved somewhere an agent reads
before working — usually `../SKILL.md`, sometimes the mock itself, if the right
answer was that the mock was wrong.

## A case

Front matter, then prose. `signature` is a regex matched against the daemon's
reply; `rule` is the sentence that must appear in the file named by `rule_in` —
a path relative to the skill root, one level above this directory —
which `tests/test_design_floor_kb.py` checks. A case whose lesson landed in code
rather than in a document sets `rule_in: code`; the body says where.

Quote a `rule` that sits on one line of its source. Comparison collapses
whitespace, so a sentence wrapped across lines still matches — but one split
across two Python string literals does not, because the quotes and comma
between them are not whitespace.

```yaml
---
id: 002-a-short-slug
outcome: failure          # or success
signature: "has no slot"  # optional; omit for cases with no error reply
lanes: cells, analog      # where it was seen
rule: "the sentence that prevents it"
rule_in: SKILL.md         # relative to the skill root; or: code, or: none
---
```

Cases are numbered in the order they were first seen, and keep their number.
