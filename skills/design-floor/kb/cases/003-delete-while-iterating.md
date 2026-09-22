---
id: 003-delete-while-iterating
outcome: failure
lanes: power, top, cells
audience: agent
rule: "builds a list and hands it over"
rule_in: code
---

# `foreach` over a list that was being deleted from

## What happened

Three agents, independently, wrote the obvious thing:

```
foreach(s cv~>shapes dbDeleteObject(s))
```

and found it had deleted every *other* shape. Each invented a different
workaround: one looped on `car(cv~>shapes)` until the cell was empty, one
snapshotted with `mapcar` first, and the workbench had grown a
clear-until-empty loop for the same reason months earlier.

Four workarounds for one cause is the signal that the tool is wrong, not the
callers.

## Why

`~>shapes` was handing out the cellview's own list. `foreach` walked it while
`dbDeleteObject` shrank it underneath, so the loop stepped over every second
entry.

## Resolution

Fixed in the mock. A `~>` traversal builds a list and hands it over; the caller
holds a value, and the database changing underneath does not rewrite it.
