---
id: 014-no-way-to-count
outcome: failure
signature: "foreach needs a list"
lanes: gates, gcd
rule: "`foreach` walks a list and cannot count"
rule_in: SKILL.md
---

# Nothing to count with

## What happened

`foreach` walks a list. Agents wanting four of something wrote `foreach(i 0 3 …)`
and got `foreach needs a list`, then reached for `for(i 0 3 …)` and got
`unknown function: for`. Neither existed, so the only way to repeat an
operation a fixed number of times was to write the list out by hand.

Two lanes hit it. One of them hit it *inside a build script*, which died partway
and left the opening rectangles of a cell behind — the partial write that made
`STDLIB/NOR2` three cells deep (013). A missing loop cost a corrupted cell.

## Resolution

`for` added, and it is a real absence rather than a scope decision: SKILL has
it, `car`/`cdr`/`cadr`/`cons`/`nth`/`member`/`mapcar`/`foreach` were all here,
and the thing agents kept needing was the one that counts. Same argument as
`cons` in 004.

`foreach` still refuses a number, as it does in SKILL — counting is `for`'s job,
and a `foreach` that quietly accepted a bound would teach the wrong thing.
