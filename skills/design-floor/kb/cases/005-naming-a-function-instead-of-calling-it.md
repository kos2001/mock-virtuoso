---
id: 005-naming-a-function-instead-of-calling-it
outcome: failure
signature: "unbound variable"
lanes: cells
audience: agent
rule: "A bare name is a variable"
rule_in: SKILL.md
---

# Probing for a function by writing its name

An agent checked whether `dbCreateTextDisplay` existed by evaluating the bare
name, and got:

```
unbound variable: dbCreateTextDisplay
```

which is correct — a bare name is a variable reference, not a function test —
but reads like "this function does not exist" and would read the same way for a
function that does.

## Resolution

Use `mockCapabilities()` on a known mock endpoint to discover callable names
without executing them. On real Cadence, use the installed SKILL Finder.
`unknown function: X` and `unbound variable: X` remain different errors, but
trial calls to mutating functions are not a safe discovery mechanism.
