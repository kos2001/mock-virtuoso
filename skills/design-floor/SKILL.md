---
name: design-floor
description: "Design layout in a shared mock Virtuoso through virtuoso-bridge, one agent per lane. TRIGGER when working on the mock-virtuoso design floor, when given a lane name (analog, cells, gates, gcd, power, request, slice, top, verify), or when asked to draw/place/audit layout in library STDLIB through floor/lanes.env."
---

# Design Floor

Several agents design into **one** Virtuoso session at the same time. You get a
lane; your colleagues get theirs; the design database is shared.

Read this file, then `roles/<your-lane>.md` for an assigned lane. Read
[bridge-workflow.md](references/bridge-workflow.md) before connecting, selecting
an API, recovering a failed edit, or reporting DRC/LVS. It distinguishes the
mock endpoint from real Cadence and gives executable examples. A lane is an
ownership boundary, not permission to spawn agents or edit other cells.

## Reaching the session

```bash
# From this repository's root (POSIX):
echo 'mockCapabilities()' | .venv/bin/python tools/floor_skill.py --env floor/lanes.env -p <your-lane> --stdin
```

On Windows PowerShell, use the repository's authenticated lane runner:

```powershell
'mockCapabilities()' | .venv/Scripts/python.exe tools/floor_skill.py --env floor/lanes.env -p verify --stdin
```

Use your assigned lane in place of `verify`. Never print token/environment file
contents. Use **your** lane and no other. For SKILL with awkward quoting, feed it on stdin:

```bash
.venv/bin/python tools/floor_skill.py --env floor/lanes.env -p <your-lane> --stdin <<'EOF'
<SKILL here>
EOF
```

`--env floor/lanes.env` points the bridge profile at your lane's port. The runner
uses the installed bridge's `VirtuosoClient.local()` with token authentication;
it rejects remote profiles and never starts a daemon. Upstream CLI `eval` at the
audited revision can omit authentication on this local `from_env()` path.
Do not disable authentication to work around it. Bridge API documentation is `skills/virtuoso/SKILL.md` in the
`virtuoso-bridge-lite` checkout, with more under that skill's `references/`.

## The technology

Layers, all with purpose `drawing`:

| | |
|---|---|
| wells and devices | `nwell` `diff` `poly` |
| metal | `met1` `met2` `met3` |
| annotation | `text` |

Via definitions: `DIFF_M1`, `PO_M1`, `M1_M2`, `M2_M3`. Those four are all there
are. `techFindViaDefByName` answers `nil` for any other name, and `dbCreateVia`
refuses anything that is not one of them — its refusal lists the ones that
exist.

```
vd = techFindViaDefByName(techGetTechFile(cv) "M1_M2")
dbCreateVia(cv vd 4:3 "R0")
```

### Connectivity

A cell's shapes can carry nets, and a net can present terminals and offer pins.
Until a shape has a net nothing knows which pieces of metal are the same
signal, and `leMarkNet` has nothing to find.

```
n = dbCreateNet(cv "VDD")
dbCreateTerm(n "VDD" "inputOutput")     ; input output inputOutput switch jumper unused
dbCreatePin(n strap)                    ; strap is a shape you drew
```

`cv~>nets`, `cv~>terminals`, `net~>pins`, `shape~>net` read it back. Naming a
net twice returns the one that exists rather than a second of the same name.
`leMarkNet(list(x y))` returns the net under a point, and **refuses** when no
shape there carries one — it does not answer `t` for a cell that has no nets.

A label is not a pin. `dbCreateLabel` draws text on the `text` layer and
nothing more; a cell whose pins are only labels has no connectivity, and an
instance of it cannot be traced.

### Checking what you drew

`mockDrcCheck(cv)` returns a list of rule violations for one cellview, empty if
there are none. It checks minimum width, same-layer spacing, the 0.005 µm
manufacturing grid and minimum area.

```
mockDrcCheck(dbOpenCellViewByType("STDLIB" "INV" "layout" "maskLayout" "r"))
→ ("DRC-WIDTH-001 [error] met1: 0.05 µm wide < 0.14 µm minimum at (0 0) (0.05 2)")
```

Two things about it. It is **not Cadence SKILL** — the `mock` prefix is there
because you may write SKILL somewhere else afterwards, and a plausible-looking
name would be a lie that travels. And the codes are this session's own: their
meaning lives in `DRC.md` and nowhere else, so read that rather than guessing a
rule from its code. A clean result means these rules passed, not that the
layout is correct.

## What this session will and will not do

It covers layout and explicit `mockCircuit*` JSON circuit extensions. `schCheck`
is a limited ERC adapter, not full Cadence schematic checking. Other schematic
(`sch*`) and Maestro (`mae*`) functions are not implemented. Query
`mockCapabilities()` on a known mock endpoint for the installed callable names,
accepted no-ops, extension signatures and limitations. It interprets a subset of SKILL:
`car` `cdr` `cadr` `cons` `nth` `member` `mapcar` `foreach` `for` `length` `list`
`strcat` `sprintf` `let` `prog` `if` `when` `unless` and the `db*`/`ge*`/`hi*`
layout calls. `ddGetLibList` and `dbCreateParamInst` are among the things it
does not have.

Absences agents keep reaching for: `while` `println` `copy` `equal` `makeTable`
and `ddGetLibList` are not here, and neither is `dbCreateParamInst` — place
instances with `dbCreateParamInstByMasterName`. Check `mockCapabilities()` rather
than executing an unknown mutating function as a probe. On real Cadence, use
the installed documentation finder described in the workflow reference.
A bare name is a variable, so writing `someFunction` on its own answers
"is there a variable called that", which is a different question and always no.

`foreach` walks a list and cannot count — `for(i 0 3 …)` counts, inclusive at
both ends, and is how you place four of something without writing the list out.

Slot names worth knowing before you guess: shapes carry `lpp`, a
(layer purpose) pair — there is no `layerName` and no `purpose` — along with
`bBox` `points` `xy` `orient` `theLabel` `net` `width` and `viaDef`. Any slot
you ask for that does not exist will list the ones that do.

**Errors are loud on purpose.** A function it lacks raises `unknown function`
rather than returning `nil`; a slot an object lacks names the slots it has; a
via definition that does not exist is refused rather than drawn. Treat every
refusal as information and adapt — never paper over one, and never report
success you have not read back.

## House rules

- **Do not `dbClose` a cellview you edited.** Build, save, read back — no close.
- **Touch only the cells your role owns.** Reading a colleague's cell is fine
  and often necessary; writing to it is not.
- **A build you have not read back is not done.** After building, reopen and
  confirm the shape count, the layers and the bounding box. Quote those numbers
  in your report; they are what the next agent works from.
- **Measure, do not assume.** When you need a cell's size, read its `bBox`. The
  number a colleague quoted may be from before their last edit.
- **A failed call is not a no-op.** Nothing here is transactional: a script
  that dies partway keeps whatever it had already created, and the error says
  nothing about that. After any failure, assume the cell holds debris.
- For an authorized replacement of your owned cell, **Clear before every build, not just the first**, including your own second
  attempt. Skip it and you layer a whole cell on top of the last one — the
  shapes are identical, so the canvas, the bounding box and the pin labels all
  look right, and only the count gives it away. Read the count back and compare
  it to what you drew. This does not authorize clearing during an incremental
  edit or audit. After an uncertain timeout, inspect before deciding whether
  to retry; the previous mutation may already have completed.

## What the session keeps

The design database lives in the running daemon and does not survive a restart.
Within one session your edits persist across separate `eval` invocations — you
can build in one call and read back in the next, with or without `dbSave` — but
a restarted floor only has what its startup loader restores, and a cell that existed an hour ago may simply
not be there. If something you were told exists reads as `0 shapes` with a
degenerate bounding box, that is one of the reasons.

## When a colleague's work is not there yet

Lanes run at the same time, so the cell you need may be empty when you look. Do
not guess its numbers, and do not build a placeholder — placing what your
colleagues actually drew is the point of working this way.

Read the cell once more after a short wait, using a plain shell `sleep` between
reads, and give it a few tries. If it is still empty, **hand back and say so**:
report which cells you found empty, what you would have done with them, and the
numbers you were waiting for. Whoever dispatched you is sequencing the floor and
will wake you when the cell exists.

Do not start a long-running watcher to wait for it. A lane that parks itself
polling holds a seat and produces nothing; a lane that reports what it found
gets resumed the moment its input is ready.

## A worked round trip

```
let((cv)
  cv = dbOpenCellViewByType("STDLIB" "MYCELL" "layout" "maskLayout" "a")
  dbCreateRect(cv list("met1" "drawing") list(0:0 4:2))
  dbSave(cv)
  sprintf(nil "%d shapes, bBox %L" length(cv~>shapes) cv~>bBox))
```

Inspecting a cell without opening it or creating a missing cell:

```skill
mockInspectCell("STDLIB" "INV" "layout")
```

The JSON string distinguishes `exists: false` from a present empty cell and
reports shape/instance/net/terminal/pin counts, layers and bbox. Its
`verification: "not_run"` is deliberate: geometry inspection is not DRC/LVS.
An audit should use this instead of opening a cell: this mock's read-mode open
can create an absent cell and changes the shared cellview's access mode.

For an existing cell where opening is intended, detailed read-back is:

```
let((cv)
  cv = dbOpenCellViewByType("STDLIB" "INV" "layout" "maskLayout" "r")
  sprintf(nil "%d shapes %d instances bBox %L"
          length(cv~>shapes) length(cv~>instances) cv~>bBox))
```

## Your report

Keep it under twenty lines and make it useful to whoever works next:

- the coordinates, sizes or pitches you chose, as exact numbers;
- what the read-back actually said, quoted;
- anything the session refused, and what you did instead.
