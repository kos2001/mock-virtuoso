---
id: 004-reaching-outside-the-subset
outcome: failure
signature: "unknown function"
lanes: all
audience: agent
rule: "`while` `println` `copy` `equal` `makeTable` and `ddGetLibList` are not here"
rule_in: SKILL.md
---

# Reaching for SKILL this session does not have

Seen for `println`, `while`, `copy`, `equal`, `ddGetLibList` and
`dbCreateParamInst`, each once or twice, across every lane.

## What happened

Every one failed loudly and every agent adapted within a call or two, which is
the system working. The cost was not correctness but round trips: a handful per
session spent discovering the vocabulary.

`cons` belonged on this list until two agents hit it in the same session — it
was missing by oversight rather than by scope, since `car`, `cdr`, `cadr`, `nth`
and `member` were all present, and it was added.

## Resolution

The shared skill now names both halves: what the subset has, and the specific
absences agents keep reaching for. Discovering the boundary by probing is fine;
discovering it six times a session is waste.
