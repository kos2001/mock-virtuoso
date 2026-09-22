---
id: 005-naming-a-function-instead-of-calling-it
outcome: failure
signature: "unbound variable"
lanes: cells
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

The skill says to probe by calling. `unknown function: X` is the answer to "does
X exist"; `unbound variable: X` only says that no variable X is set.
