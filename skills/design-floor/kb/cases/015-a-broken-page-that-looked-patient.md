---
id: 015-a-broken-page-that-looked-patient
outcome: failure
lanes: request
rule: "none"
rule_in: none
---

# A dead page that looked like it was waiting

## What happened

After a refactor moved `render.js` and `about.js` into `toolkit/static/`, the
floor served the page but not its scripts. With no JavaScript the transcript
never rendered, so the panel kept its empty state:

> Listening — no agent has sent anything yet.

The database had 27 calls in it at the time. The screen said the floor was
idle; the truth was that nothing on the page was running at all.

It was read as an error twice by the person looking at it — correctly, both
times. The first time I had "fixed" it by making the empty state friendlier,
which made a broken page look calmer rather than making it say anything true.

## The second mistake, which was mine

The stale process. My restart command was `lsof -ti:8900 8750 | xargs kill`,
which `lsof` rejects — it printed usage and killed nothing. The new server
failed to bind and died; the old one kept answering.

Then I verified by checking the port was open, saw `✓ floor :8900`, and
reported success. **A port being open is not evidence that your code is
running.** The check has to be for something only the new build serves — a new
route, a new lane, a string that did not exist before.

## Resolution

Two guards on the page, no rule for agents:

- if `draw` or `mountAbout` is missing when the page script runs, it replaces
  the transcript with a red notice saying the scripts did not arrive and that
  what you see is not an empty floor but a broken page;
- five consecutive failed polls raise a banner saying contact with the floor
  was lost, since a transcript that simply stops growing looks identical to a
  quiet one.

Verified by stripping the `<script src>` tags from the served HTML and
rendering it: the notice appears.
