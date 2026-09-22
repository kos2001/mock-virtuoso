---
name: design-floor
description: "Design layout in a shared mock Virtuoso through virtuoso-bridge, one agent per lane. TRIGGER when working on the mock-virtuoso design floor, when given a lane name (cells, analog, power, top, verify), or when asked to draw/place/audit layout in library STDLIB through floor/lanes.env."
---

# Design Floor

Several agents design into **one** Virtuoso session at the same time. You get a
lane; your colleagues get theirs; the design database is shared.

Read this file, then `roles/<your-lane>.md`. Those two are your brief. Everything you need to know about the session is here — probe
it with SKILL to learn more, but do not read the implementation on the other
end. It is a tool you drive, not code you inspect.

## Reaching the session

```bash
cd /Volumes/T9-Workspace/gitspace/virtuso_bridge/mock-virtuoso
.venv/bin/virtuoso-bridge eval --env floor/lanes.env -p <your-lane> '<SKILL>'
```

Use **your** lane and no other. For SKILL with awkward quoting, feed it on stdin:

```bash
.venv/bin/virtuoso-bridge eval --env floor/lanes.env -p <your-lane> --stdin <<'EOF'
<SKILL here>
EOF
```

`--env floor/lanes.env` points the bridge profile at your lane's port. The CLI
is the one that ships with virtuoso-bridge, unmodified; only where it dials
differs. Its API documentation is `skills/virtuoso/SKILL.md` in the
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

## What this session will and will not do

It covers the **layout** domain. Schematic (`sch*`) and Maestro (`mae*`)
functions are not implemented and say so. It interprets a subset of SKILL:
`car` `cdr` `cadr` `cons` `nth` `member` `mapcar` `foreach` `length` `list`
`strcat` `sprintf` `let` `prog` `if` `when` `unless` and the `db*`/`ge*`/`hi*`
layout calls. `ddGetLibList` and `dbCreateParamInst` are among the things it
does not have.

Absences agents keep reaching for: `while` `println` `copy` `equal` `makeTable`
and `ddGetLibList` are not here, and neither is `dbCreateParamInst` — place
instances with `dbCreateParamInstByMasterName`. Probe for a function by calling
it. A bare name is a variable, so writing `someFunction` on its own answers
"is there a variable called that", which is a different question and always no.

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
- If the cell you own already has content when you start, clear it first rather
  than layering a second design over the first.

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

Reading a cell back, including one you do not own:

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
