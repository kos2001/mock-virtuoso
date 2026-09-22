---
id: 021-a-layout-with-no-connectivity
outcome: failure
lanes: verify, top, cells
audience: agent, floor
rule: "A label is not a pin."
rule_in: SKILL.md
---

# Shapes, labels, and nothing joining them

## What happened

Asked which Virtuoso features this session should support, the answer came
from diffing the functions the bridge calls against the functions the mock
registers. The layout and database surface matched completely; the only names
missing were `hiCreateAppForm` and its family, which belong to the daemon's
own monitor GUI running inside Virtuoso and are never sent by a client.

So the surface was complete, and a whole concept was absent from it.
Connectivity. A cell drew shapes, and labels, and nothing said which of them
were the same signal.

Two marks it had left in the repository, both read as normal until you look
for the cause:

- `roles/verify.md` told the verifier to "count `text` shapes per cell … so a
  missing pin name shows up". Counting annotation is a stand-in for checking
  pins, written because there were no pins to check.
- `Shape` declared a `net` slot in `_SLOTS` and nothing ever assigned it.

## The call that could not fail

`leMarkNet` was registered as `accept` — return `t`, whatever the arguments.
Its test asserted exactly that and its comment said the thinness was
intentional. It was not. The bridge's net-highlight operation reads
`shape~>net~>name` over `cv~>shapes`, so against this mock that loop could
never match and the operation could only ever answer `ERROR: net not found` —
untestable in precisely the way this mock exists to prevent, while reporting
success from the `leMarkNet` call inside it.

The `csh` failure again, and `dbPurge`'s: a call that always succeeds teaches
an agent it did something.

## Resolution

`dbCreateNet`, `dbCreateTerm` and `dbCreatePin`, with `cv~>nets`,
`cv~>terminals`, `net~>pins`, `pin~>term` and `shape~>net` reading them back.
Naming a net twice returns the one that exists; a cell with two `VDD`s is not
a thing to model. An unknown terminal direction is refused with the six that
exist, and a pin needs a shape, not a layer name.

`leMarkNet` now returns the net under a point, and refuses three ways with the
reason: no cellview open, the cell has no nets (naming the two functions that
give it some), or nothing at that point carries one.

The bridge's own `layout_highlight_net` now runs against this mock end to end
and is tested doing it — `highlighted net: VDD` for a wired cell, `ERROR: net
not found: GND` for a name that is not there.

`roles/verify.md` still counts labels, and now also reads `cv~>nets` and
`cv~>terminals`, and reports the two separately. Where they disagree the cell
has names but no connectivity: it places, it draws, and nothing can be traced
through it.

## The floor was still building cells without any

Adding the functions was not the same as using them. Asked, in words, for "an
INV cell with VDD/GND/A/Y pins", the floor answered with four `text` labels
and zero nets, and the answer read as a success — the planner had no way to
express a pin, the read-back never looked for one, and nothing said the cell
could not be traced.

A `pin` op now draws its rectangle *and* gives the cell connectivity in one
operation, because splitting them is exactly how a cell ends up with port
names and nothing behind them. It is refused on the `text` layer, its `dir`
must be one `dbCreateTerm` takes, and its net name must be an identifier
since it is interpolated into SKILL.

The read-back reports `nets: VDD(1) GND(1) A(1) Y(1)`, and where a cell has
text labels and no nets it says so in those words rather than leaving the
reader to notice an absence.
