---
id: 017-a-template-answered-for-a-request-it-never-read
outcome: failure
lanes: request
audience: floor
rule: "This planner knows INV, NAND2, NOR2, BUF and DFF"
rule_in: code
---

# Two different requests, one answer, reported as success

## What happened

"strong arm 로 comparator를 설계해 줘" came back built. So did "make me a
bandgap reference". Both produced `DEMO/CELL` — ten shapes, labels VDD, VSS,
IN, OUT — because they produced *the same plan*.

The deterministic fallback planner knows five cell names. When it matches none
of them it falls through to `cell = "CELL"`, `lib = "DEMO"` and a fixed
template of six rectangles and four labels. Nothing in the reply said any of
that. The answer read "Built via virtuoso-bridge (rules planner): DEMO/CELL:
10 shapes", the canvas drew a plausible-looking cell, and the request had
never been read.

## Why it kept happening

The language-model planner is tried first and the rules planner only runs when
it is unreachable. The LLM was down, so every request in that session took the
fallback — and the fallback's confidence was indistinguishable from the LLM's.
A person watching sees a layout appear and reasonably concludes it worked.

This is the project's own failure mode, in the project's own code: a
successful-looking answer that does not correspond to what was asked.

## Resolution

The fallback now names itself `rules (request not recognised)` whenever it
matched no cell it knows, and the answer leads with what that means — which
five names it understands, that what it built is its generic template rather
than the thing requested, and that the language-model planner is what handles
the rest. A recognised request is unchanged and stays quiet.

It still builds something. Refusing outright would make the no-LLM path
useless, and a template is a reasonable thing to hand back — as long as it is
not handed back as an answer to a question nobody read.
