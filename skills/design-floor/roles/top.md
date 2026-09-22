# Lane `top` — integrator

You own `STDLIB/CORE`, the top-level floorplan. It holds instances and
top-level routing, not transistor geometry.

## Before placing anything

Read each master and take its size from its own `bBox`. Colleagues quote
numbers in their reports; those are a starting point, not a measurement, and
they may predate the master's last edit.

```
let((cv)
  cv = dbOpenCellViewByType("STDLIB" "INV" "layout" "maskLayout" "r")
  sprintf(nil "%d shapes bBox %L" length(cv~>shapes) cv~>bBox))
```

If a master is missing or empty, its designer has not finished. Say so rather
than inventing a placeholder — placing what your colleagues actually drew is
the whole point.

## What to build

1. A row of at least six instances alternating `INV` and `NAND2`, abutted
   left-to-right on the measured widths so cells touch with no gap and no
   overlap, all on one baseline, alternate cells mirrored `MY`.
2. One `BIAS` instance beside the row, on the same baseline.
3. One `PG` instance over the row, if the power-grid agent has built it.
4. `text` labels naming the block and marking the row.

Give every instance a distinct name (`I0`, `I1`, …).

## The mirroring trap

`MY` mirrors about the origin, so a mirrored cell's placement point is **not**
its left edge. Work out which coordinate puts the cell where you want it, then
confirm by reading the instance's resulting `bBox` — do not assume it.

## Report

Each master's bbox as *you* measured it and the pitch you derived. Then the
instance list — name, master, placement coordinate, orientation, resulting
bbox — quoted from your read-back, and `STDLIB/CORE`'s overall bounding box.
