# Lane `slice` — datapath bit slice

You own `STDLIB/GCDSLICE`, one bit of a subtractive GCD datapath. It holds
instances of leaf cells, not transistor geometry.

## The bit slice

A subtractive GCD repeats: while `a != b`, subtract the smaller from the larger.
One bit of that datapath needs, per bit:

- two registers, `DFF` instances, holding `a[i]` and `b[i]`;
- a one-bit full subtractor built from `XOR2` and `NAND2`/`NOR2`, producing the
  difference and the borrow;
- two `MUX2` instances choosing whether this bit's register loads the
  difference or keeps its value.

Roughly eight instances. Abut them in a single row on the measured widths of
the masters, alternate cells mirrored `MY`, all on one baseline — the same row
discipline a placer would use.

Measure every master yourself. `STDLIB/INV` and `STDLIB/NAND2` exist already;
`NOR2`, `XOR2`, `MUX2` and `DFF` come from the `gates` lane and may not be
drawn when you start. Your brief in the shared skill says what to do about a
master that is not there yet.

## Naming carries the intent

There is no netlist here, so instance names and `text` labels are the only
record of what connects to what. Name instances for their function —
`AREG` `BREG` `DIFF0` `BRW0` `SELA` `SELB` — and label the slice's boundary
signals on `met1`: `A` `B` `CK` `BIN` `BOUT` `DOUT`. Someone reading this cell
later has nothing else to go on.

## Report

Each master's measured bbox, the row pitch, the instance list with names,
masters, coordinates and orientations from your read-back, and the slice's
overall bounding box.
