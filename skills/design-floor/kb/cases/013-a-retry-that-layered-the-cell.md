---
id: 013-a-retry-that-layered-the-cell
outcome: failure
lanes: gates
rule: "Clear before every build, not just the first"
rule_in: SKILL.md
---

# Building a cell three times into the same cell

## What happened

`STDLIB/NOR2` read back as 37 shapes, against 21 for the `NAND2` it was drawn
to match. The layer counts told the story — nwell 3, diff 6, met1 17 — and the
geometry confirmed it: the same nwell rectangle, the same two diff bands and the
same power rails, each present three times at identical coordinates.

The agent had built the cell, found something wrong, and built it again. Twice.

## Why it is hard to see

Identical shapes stacked on identical coordinates look exactly like one shape.
The canvas shows a correct NOR2. The bounding box is correct. Every pin label is
present and in the right place. Nothing is visibly wrong, and an agent reading
back "37 shapes" has no reason to find that surprising unless it counted what it
drew.

Downstream, the cell abuts and places like any other — it is simply three cells
deep, which no amount of looking at the floorplan would reveal.

## Resolution

The house rule said to clear the cell "when you start", and a retry does not
feel like starting. It now says to clear before every build including your own
second attempt, and to compare the read-back count against what you drew —
which is the check that catches this, since nothing else does.
