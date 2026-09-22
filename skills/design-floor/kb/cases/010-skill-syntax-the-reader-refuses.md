---
id: 010-skill-syntax-the-reader-refuses
outcome: failure
signature: "unexpected character|unterminated argument list|must be followed by a name"
lanes: cells, verify
audience: agent
rule: "none"
rule_in: none
---

# Syntax the reader will not take

Three shapes of this, once or twice each.

**A subscript.** An agent tallied shapes by layer with `makeTable` and then
`counts[layer]`, and the reader stopped at the bracket:

```
unexpected character '[' at 154
```

SKILL does have table subscripts; this reader does not implement them, and
`makeTable` is absent anyway (see 004). The agent switched to accumulating with
`strcat`, which is what the bridge's own readers do.

**An unbalanced expression.** One agent sent a `progn` whose parens did not
close, usually after building SKILL by string concatenation in the shell:

```
unterminated argument list for progn
```

**A stray `?` or `~>`.** An agent probing an object's slots wrote a trailing
`~>?` and got `'?' must be followed by a name at 183`; another hit the same at
a different offset while building a read-back expression.

All of these point at the offending position, which is what an error of this
kind should do, and each was fixed on the next call.

## Not acted on

No rule written. Neither cost more than one round trip, and the reader's
messages are already specific enough to act on. Worth revisiting only if a
session shows agents losing several calls to quoting — in which case the lesson
is probably "use `--stdin` for anything with nested quotes", which the shared
skill already says.
