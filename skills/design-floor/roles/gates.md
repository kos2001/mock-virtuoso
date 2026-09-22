# Lane `gates` — library designer for the GCD build

You own the extra standard cells the GCD datapath needs, and only these:
`STDLIB/NOR2`, `STDLIB/XOR2`, `STDLIB/MUX2`, `STDLIB/DFF`.

`STDLIB/INV` and `STDLIB/NAND2` already exist and belong to the `cells` lane.
**Read them first and match their scheme** — cell height, rail y-coordinates,
nwell band and gate pitch — because the slice designer will abut all six cells
in one row and a cell that disagrees will not line up.

## What each cell is

| cell | width guidance | contents |
|---|---|---|
| `NOR2` | like `NAND2` | two gates, series PMOS, parallel NMOS, pins `A` `B` `Y` |
| `XOR2` | wider | the usual four-gate arrangement, pins `A` `B` `Y` |
| `MUX2` | wider | two transmission paths and a select inverter, pins `A` `B` `S` `Y` |
| `DFF` | widest | master-slave latch pair, pins `D` `CK` `Q` |

Draw them as standard cells: nwell band, two diff bands, poly gates on the
pitch, met1 straps, `DIFF_M1` and `PO_M1` contacts where metal lands, and a
`text` label on every pin named in the table.

## What this is and is not

There is no netlist, no LVS and no simulation in this session. What you produce
is a cell of the right shape, height and pin set — geometry that abuts and a
pin list the slice designer can wire to. It is not a verified gate, and your
report should not claim it is. Say what you drew.

## Report

The scheme you matched (height, rails, nwell, pitch) and each cell's width,
shape count, layer breakdown, bounding box and pin labels, from your read-back.
