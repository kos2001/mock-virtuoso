# Lane `analog` — analog designer

You own `STDLIB/BIAS`. Nothing else.

## What to build

A current-mirror bias cell that reads as analog rather than digital:

- a matched pair of wide diff fingers under a shared nwell;
- poly gates tied together, with the tie drawn as a real poly shape;
- met1 routing for the diode-connected leg and a met2 run above it, joined by
  an `M1_M2` via;
- `DIFF_M1` contacts where met1 meets the fingers, `PO_M1` on the poly tie;
- `text` labels for `IBIAS`, `VB` and `GND`.

Use **paths** for the metal runs, not only rectangles, so the wiring reads as
wiring.

Make it taller and squarer than a logic cell — an analog block does not fit the
digital row, and the floorplan should show that. Origin at its lower-left.

## Report

Origin, width and height as exact numbers — the integrator places this cell
from them. Then the shape count, the per-layer breakdown and the bounding box,
quoted from your read-back.
