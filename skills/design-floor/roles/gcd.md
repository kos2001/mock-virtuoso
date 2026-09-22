# Lane `gcd` — the GCD block

You own `STDLIB/GCD4`, a four-bit subtractive GCD assembled from bit slices.

## What to build

1. Four `GCDSLICE` instances stacked into a four-bit word. Decide whether the
   slices sit side by side in a row or one above another, measure the master,
   and abut on that measurement. Name them `BIT0`..`BIT3`.
2. A control area beside the datapath: a small group of `DFF`, `NAND2` and
   `INV` instances standing in for the state machine that decides which
   register loads. Four to six instances is enough; name them for their part
   (`STATE0` `STATE1` `LOADA` `LOADB` `DONE`).
3. A `met3` clock trunk spanning the datapath, and `met3` power straps if
   `STDLIB/PG` fits your block — measure it before assuming it does.
4. `text` labels on the block's boundary signals: `A0`..`A3`, `B0`..`B3`,
   `CK`, `START`, `DONE`.

## Measure, and say what you assumed

`GCDSLICE` comes from the `slice` lane. Read it rather than taking its reported
size. If it is missing or empty, the shared skill says what to do.

## What this is and is not

This is a floorplan of a GCD, not a GCD. There is no netlist, no connectivity
check, no timing and no simulation in this session: nothing here can tell you
the block would compute a greatest common divisor. What you can honestly claim
is the hierarchy, the instance count, the abutment and the labels.

Say that in your report. An audit follows, and a claim you cannot support is
worse than a modest one.

## Report

The slice's measured bbox and the pitch you derived, the full instance list
with names, masters, coordinates and orientations from your read-back, the
block's overall bounding box, and a plain statement of what has and has not
been verified.
