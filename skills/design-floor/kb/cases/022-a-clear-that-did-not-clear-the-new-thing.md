---
id: 022-a-clear-that-did-not-clear-the-new-thing
outcome: failure
lanes: cells, gates, request
audience: agent, floor
rule: "A pin is a shape offered to a net."
rule_in: code
---

# The cell emptied, except for the part added last week

## What happened

Nets, terminals and pins were added to the database. Every path that *creates*
a cell was taught about them. The path that *empties* one was not.

```
build 1: shapes=1 nets=1 terms=1 pins=1
build 2: shapes=1 nets=1 terms=2 pins=2
build 3: shapes=1 nets=1 terms=3 pins=3
```

Three builds of the same cell left one shape and three pins, two of them
offering a connection point at a rectangle that had just been deleted. The
floor clears and rebuilds on every request and on every rule correction, so
this accumulated on the live design rather than in a corner case.

Two causes, and they are different bugs:

- `dbDeleteObject` on a shape removed the shape and left any pin that offered
  it. A pin whose figure is gone is not a pin.
- The clear expression deleted shapes and instances and never looked at nets,
  so the next `dbCreateNet` found the old net and added to it.

## Why it was not caught

The test written alongside the feature asserted:

```python
assert session.evaluate("length(… ~>nets)") in (0, 1)
```

A test that accepts both answers has decided in advance not to find out. It
passed on the day it was written and on every day the behaviour was wrong.
That is worse than no test: the suite reported coverage of exactly the thing
it was not checking.

It is now three assertions that each name one number, plus one that runs the
build three times and requires every round to look the same.

## The shape of it

This is the third time this repository has emptied a cell incompletely —
`dbClose` once left the contents behind, `forget_cell` once kept a deleted
cell's views. Each time the fix was correct and each time the *next* thing
added to a cellview was not included in it.

So the rule is about where to look, not about nets: **when a cellview gains a
new kind of contents, the clear, the delete and the reopen all have to learn
about it on the same day.** `clear_contents`, `adopt_contents`,
`dbDeleteObject` and `_CLEAR_SKILL` are the four places, and a rebuild run
three times over is the test that catches missing any of them.
