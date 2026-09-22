---
id: 016-a-readout-that-blocked-the-pan
outcome: failure
lanes: request
audience: floor
rule: "The readout is optional decoration and used not to be"
rule_in: code
---

# Zoom worked, panning did not

## What happened

The canvas zoomed on the wheel but would not move on a drag. Nothing in the
console until you looked during the drag itself:

```
Uncaught TypeError: Cannot set properties of null (setting 'textContent')
```

The `mousemove` handler wrote the cursor's design coordinates into `#hudX` and
`#hudY` *before* doing the pan. Those elements belonged to the Layout
Workbench, which had been retired; the floor has no such ids. So every
`mousemove` threw on the first line and the drag code below it never ran.
`wheel` is a separate handler that touches neither, which is why zoom was
unaffected — and why the failure looked like "panning is broken" rather than
"the renderer is throwing".

## The same mistake, twice

`draw()` had the identical problem with `#hudShapes`/`#hudInsts` when the
renderer was first shared between two pages, and it was fixed there by
guarding the writes. The mousemove readout was missed because `draw()` is
exercised by the test suite on every geometry read and `mousemove` is not.
Retiring the workbench then removed the page that had been keeping these ids
alive.

## Resolution

The pan runs first and the readout is guarded, so optional decoration can
never again stop the interaction it decorates. The floor also grew the
readout back — `x` and `y` in the status bar — because it is useful and its
absence is what set the trap.

Verified by dispatching the events: a drag pans, a move with the button up
does not, releasing stops it, the readout updates, and no error is thrown.
