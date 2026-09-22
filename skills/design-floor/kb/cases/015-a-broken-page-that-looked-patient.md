---
id: 015-a-broken-page-that-looked-patient
outcome: failure
lanes: request
audience: floor
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

## The wording, a fourth time

Even once all three causes were gone, the idle panel still opened with
"Listening — no agent has sent anything yet" and a CLI command. That describes
joining a lane as an agent, which is not what the person at this screen does
any more — the floor has a request box now. A message explaining a workflow
you are not using reads as something having gone wrong, which is exactly how
it was read, twice.

The idle state now says "Ready. Nothing has been built yet", points at the box
under the canvas in both languages, and folds the CLI instructions into a
collapsed "Agents can join too". Same information, ordered by who is actually
reading it.

## And a third cause, underneath both

The floor sent no cache headers at all, so the browser kept whatever it had
fetched first. Even once the server was fixed, a tab that had already loaded
the page went on running the old one — the fix arrived and nothing asked for
it. These files are edited while the floor is running, so they are now served
`no-store, must-revalidate`.

Checking that took one more wrong turn: `curl -sI` sends HEAD, which this
server does not implement, so the header looked absent when it was there. A
negative result from a request the server never answers is not a negative
result.

## Resolution

Three guards, no rule for agents:

- if `draw` or `mountAbout` is missing when the page script runs, it replaces
  the transcript with a red notice saying the scripts did not arrive and that
  what you see is not an empty floor but a broken page;
- five consecutive failed polls raise a banner saying contact with the floor
  was lost, since a transcript that simply stops growing looks identical to a
  quiet one.

- every served file carries `Cache-Control: no-store`, so a running tab cannot
  hold a stale copy of a page that is being edited underneath it.

Verified by stripping the `<script src>` tags from the served HTML and
rendering it — the notice appears — and by loading the real page afterwards:
scripts present, no notice, transcript filling, a request planned by hermes
building `DEMO/INV` and `DEMO/TOP`.
