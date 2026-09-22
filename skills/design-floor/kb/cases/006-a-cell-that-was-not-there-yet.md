---
id: 006-a-cell-that-was-not-there-yet
outcome: success
lanes: power, top
audience: agent, planner
rule: "Do not guess its numbers, and do not build a placeholder"
rule_in: SKILL.md
---

# Refusing to size a grid against an empty cell

## What happened — the part that went right

The power-grid agent needed the logic cells' rail coordinates and found both
cells empty. Its brief told it not to guess from an empty master, and it did
not. It reported what it found and waited.

When the cells arrived it read the met1 shapes *inside* them rather than taking
the outer bounding box as the rails, derived y 0–1 and y 9–10, and sized its
straps to land there. A later independent audit confirmed the straps sit exactly
on the rails — a grid built before the row existed, aligned to it correctly.

That is the whole argument for read-back discipline in one episode.

## What went wrong alongside it

Having correctly refused to guess, the agent had no guidance for the situation
it was in, so it invented one: it started two background watchers and handed
back three times while they polled. A lane that parks itself holds a seat and
produces nothing.

## Resolution

The shared skill now covers both halves — do not guess, *and* do not park:
re-read a few times with a plain sleep, then hand back naming the empty cells
and the numbers you were waiting for.
