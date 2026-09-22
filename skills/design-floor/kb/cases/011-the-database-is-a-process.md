---
id: 011-the-database-is-a-process
outcome: failure
lanes: gates
audience: agent
rule: "The design database lives in the running daemon and does not survive a restart"
rule_in: SKILL.md
---

# A library that was there an hour ago

## What happened

`STDLIB/INV` and `STDLIB/NAND2` were drawn, saved and audited in one session.
The floor was then restarted to pick up new lanes, and a `gates` agent was
dispatched to draw four more cells "matching the scheme of INV and NAND2,
which are drawn and saved right now".

They were not. A restart starts a fresh session, and the design database goes
with the process. The instruction was mine and it was false.

## What went right anyway

The agent read both cells, found `0 shapes, bBox ((0.0 0.0) (0.0 0.0))`, and
refused to invent a scheme from that. It retried, waited, retried again, then
handed back naming exactly the five numbers it needed — cell height, rail
y-coordinates, nwell band, gate pitch, and a width reference.

It was told something false by someone who should have known better, and the
house rule about not guessing from an empty master is what stopped that from
becoming four cells built to an invented scheme. The rule earned its place.

## Why the trap is easy to fall into

Within a session, edits persist across separate `eval` invocations without a
`dbSave` — an agent noticed and reported that in an earlier run. It is easy to
read that as persistence. It is not: `dbSave` marks a cellview saved and the
data lives in the daemon's memory either way, and nothing outlives the process.

## Resolution

Stated in the shared skill, so an agent reading a cell that "should" exist
knows a restart is one of the reasons it might not.
