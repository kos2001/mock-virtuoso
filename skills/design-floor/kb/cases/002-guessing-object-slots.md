---
id: 002-guessing-object-slots
outcome: failure
signature: "has no slot"
lanes: cells, top, analog
rule: "shapes carry `lpp`, a (layer purpose) pair — there is no `layerName`"
rule_in: SKILL.md
---

# Guessing at slot names

Seen 8 times. Agents reached for `shape~>layerName`, `shape~>purpose`,
`viaDef~>defWidth`, `inst~>master~>…` — plausible Cadence names that this
session does not carry.

## What happened

The refusal used to name only the slot that was missing, so each guess bought
one bit of information and the next guess was another round trip.

## Resolution

Two changes, one in the mock and one here.

The mock now lists the alternatives, which turns a wrong guess into the
documentation the agent was reaching for:

```
Shape has no slot 'layerName'; it has objType, lpp, bBox, points, xy,
orient, theLabel, net, width, viaDef
```

And the shared skill states the one that keeps being guessed wrong, so the
round trip is not needed at all.
