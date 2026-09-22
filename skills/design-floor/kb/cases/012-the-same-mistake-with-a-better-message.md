---
id: 012-the-same-mistake-with-a-better-message
outcome: success
signature: "expected a point like|must be a number, got"
lanes: gates
rule: "none"
rule_in: none
---

# The same mistake, one call instead of eleven

The follow-up to 001, from the field.

## What happened

An agent drawing library cells put a label's text where its origin goes:

```
expected a point like list(x y), got "A"
```

Exactly the mistake that produced 001 — `dbCreateLabel`'s point and text
transposed. Under the old message it cost eleven calls across two lanes and
produced two confidently wrong claims about the tool in agents' reports. Here
it cost one call, and the agent's next call was correct.

## Why this is in the knowledge base

Because it closes the loop and shows the shape of the win. The harvester found
it as a new signature, which is right: it is a different reply, and the old
signature should not quietly absorb it. But the lesson is not "agents transpose
these arguments" — that was 001 — it is that the fix landed and can be seen
landing.

## No rule

Nothing to write down. The mock now says what it wants, and saying it is the
whole intervention. Kept as evidence that a case can be closed by changing the
tool rather than by adding a sentence for agents to remember.
