---
id: 013-a-retry-that-layered-the-cell
outcome: failure
lanes: gates
rule: "A failed call is not a no-op"
rule_in: SKILL.md
---

# A cell that ended up three deep

## What happened

`STDLIB/NOR2` read back as 37 shapes, against 21 for the `NAND2` it was drawn
to match. The layer counts told the story — nwell 3, diff 6, met1 17 — and the
geometry confirmed it: the same nwell rectangle, the same two diff bands and
the same power rails, each present three times at identical coordinates.

## The cause, corrected

I assumed a careless retry: built it, did not like it, built it again. The
agent's own account was better, and different. Two of its build scripts hit
SKILL errors partway through — no numeric-range `foreach`, and no calling a
`let`-bound lambda by name — *after* the opening rectangles had already been
created. The call failed; the shapes it had already made stayed.

Nothing here is transactional. A script that dies on line nine keeps whatever
lines one through eight put in the database, and the error the caller sees says
nothing about that.

## Why it is hard to see

Identical shapes on identical coordinates look exactly like one shape. The
canvas shows a correct NOR2, the bounding box is right, every pin label is
present and placed correctly, and downstream the cell abuts and places like any
other. It is simply three cells deep, and only the shape count says so.

The agent caught it on read-back, cleared, and rebuilt to a clean 21.

## Resolution

Two sentences in the shared skill. A failed call is not a no-op, so a retry
starts from whatever the failure left behind; and clear before every build
including your own second attempt, comparing the read-back count against what
you drew — which is the check that catches this, since nothing else does.
