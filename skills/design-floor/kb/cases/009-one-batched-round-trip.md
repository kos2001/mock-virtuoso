---
id: 009-one-batched-round-trip
outcome: success
lanes: cells, analog
rule: "none"
rule_in: none
---

# Building a whole cell in one round trip

The strongest cells came from agents that composed the entire cell — 17 and 23
shapes, vias and labels included — and sent it as one batch, then read it back
in a second call.

Two calls per cell against a dozen or more. The transcript shows the difference
plainly: the lanes that batched finished with 9 and 20 calls; the lane that
worked shape by shape spent 34.

No rule has been written for this yet. It is an efficiency observation, not a
correctness one, and it is not yet clear whether telling agents to batch would
cost them the incremental read-back that caught real mistakes elsewhere.
