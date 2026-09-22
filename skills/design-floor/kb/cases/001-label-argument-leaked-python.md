---
id: 001-label-argument-leaked-python
outcome: failure
signature: "unsupported operand type|object is not iterable"
lanes: analog, power
rule: "must be a number, got"
rule_in: mock
---

# A Python exception reached the wire

**Seen 11 times in one session**, more than every other failure combined.

## What happened

`dbCreateLabel` takes its origin as a point and its height as a number. Agents
put a string in one of those places and got back:

```
dbCreateLabel: unsupported operand type(s) for -: 'str' and 'float'
```

The guard named the function, which is how an unexpected Python error is meant
to surface here, but the wording underneath was Python's. It named neither the
argument nor what the argument should have been.

## Why it mattered more than the failure itself

Two agents reasoned from that message to a conclusion about the tool, and both
were wrong:

- one reported that this session takes `dbCreateLabel`'s arguments in a
  non-Cadence order — it does not; the bridge's own builder emits
  `dbCreateLabel(cv lpp list(x y) text …)` and the mock matches it;
- one reported that the font `"roman"` is unsupported — it is not; that agent
  had put the font where the height goes.

A bad error message does not just cost the call it came from. It produces
confident, wrong documentation about the tool.

## Resolution

Fixed in the mock. Points and numbers are checked where they arrive:

```
expected a point like list(x y), got "2.0"
height must be a number, got "roman"
```
