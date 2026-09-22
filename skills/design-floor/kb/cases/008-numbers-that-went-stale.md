---
id: 008-numbers-that-went-stale
outcome: failure
lanes: verify, top
audience: agent
rule: "The number a colleague quoted may be from before their last edit"
rule_in: SKILL.md
---

# Reading a cell while a colleague was rebuilding it

## What happened

The power-grid agent cleared `STDLIB/PG` and redrew it. Two readers caught it
mid-rebuild:

- the integrator had already placed a `PG` instance, so `CORE` briefly held an
  instance of an *empty* master — which places cleanly and draws nothing, a
  failure that looks exactly like success;
- a verification pass read `PG` as 6 shapes; its author reported 7. Both were
  true at the time they were read.

## Resolution

Sequencing, not a document: the integrator was re-run after the grid settled,
and the verifier after that. The rebuilt `CORE` was then audited by enumerating
instances and labels by name rather than counting them, because a stale
instance hides inside a shape count that happens to match.

The skill carries the rule that made this recoverable — measure, do not take a
colleague's number — and the verifier's brief carries the check that catches it:
every instance must have a master with geometry.
