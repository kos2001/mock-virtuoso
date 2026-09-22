# Lane `cells` — standard-cell designer

You own `STDLIB/INV` and `STDLIB/NAND2`. Nothing else.

## What to build

**`STDLIB/INV`** — an inverter: nwell over the PMOS half, two diff regions
(PMOS above, NMOS below), one poly gate crossing both, met1 source/drain
straps, `text` labels for `A` (input) and `Y` (output).

**`STDLIB/NAND2`** — a 2-input NAND: same cell height, wider, two poly gates on
a regular pitch, `text` labels for `A`, `B`, `Y`.

Put `DIFF_M1` contacts where met1 lands on diffusion and `PO_M1` where it lands
on poly. This is a real technology; the contacts belong there.

## The scheme is the deliverable

The integrator will abut instances of your cells, and the power-grid agent will
strap over them. Both work from your numbers, so decide them first and hold to
them:

- one cell height for both cells;
- origin at each cell's lower-left, so a cell occupies `x = 0 .. width`;
- the same met1 rail y-coordinates in both, so rails line up when abutted;
- the same nwell band y-coordinates in both;
- gates on a regular pitch.

## Report

Cell height, rail y-coordinates, nwell band, gate pitch, and the width of each
cell — as exact numbers. Then each cell's shape count, layer breakdown and
bounding box, quoted from your read-back.
