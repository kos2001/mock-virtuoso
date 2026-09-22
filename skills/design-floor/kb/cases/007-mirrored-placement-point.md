---
id: 007-mirrored-placement-point
outcome: success
lanes: top
audience: agent, planner
rule: "`MY` mirrors about the origin"
rule_in: roles/top.md
---

# Getting `MY` right by reading it back

Three separate integrator runs placed a six-cell row with alternate cells
mirrored, and all three got the abutment exact — seams at 0, no floating-point
noise.

None of them assumed. Each worked out that `MY` reflects about the origin, so a
mirrored cell of width *w* whose left edge should land at *x* must be placed at
*x + w*, and then **confirmed it by reading the resulting bounding box** rather
than trusting the arithmetic.

The brief asks for exactly that, and names the trap. This is the case for
telling an agent where the trap is instead of hoping it survives it: the same
trap, three runs, no misses.
