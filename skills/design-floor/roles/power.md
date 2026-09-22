# Lane `power` — power-grid designer

You own `STDLIB/PG`, a cell holding nothing but the power grid. The integrator
will place one instance of it over the logic row.

## What to build

A met3 grid sized to the row it will cover. You cannot know that size by
assuming it — read the masters the standard-cell agent built and the top cell
the integrator is assembling, and derive it:

```
let((cv)
  cv = dbOpenCellViewByType("STDLIB" "CORE" "layout" "maskLayout" "r")
  sprintf(nil "%d instances bBox %L" length(cv~>instances) cv~>bBox))
```

If `STDLIB/CORE` is not built yet, size the grid from the leaf cells' own
heights and the row length you are told to cover, and say in your report what
you assumed.

Draw:

- horizontal met3 straps over the rail y-coordinates the standard-cell agent
  chose, so power lands where the cells expect it;
- at least one vertical met3 trunk crossing them;
- `M2_M3` vias where a trunk crosses a strap;
- `text` labels for `VDD` and `VSS` on the straps they belong to.

## Report

The strap and trunk coordinates and widths, the row extent you sized against
and where you got it, the via count, and the cell's bounding box from your
read-back.
