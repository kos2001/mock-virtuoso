---
id: 018-a-knowledge-base-nobody-read
outcome: failure
lanes: request
audience: floor
rule: "a lesson nobody reads is a diary entry"
rule_in: code
---

# Seventeen cases, none of them in the prompt

## What happened

This directory had seventeen cases. The planner had none of them. Every
request in words was planned cold: the model was free to repeat a mistake this
repository had written down, tested, and in one case written down twice.

The gap was invisible because both halves looked healthy. The cases were
harvested from real transcripts, each one naming a rule that a test proves is
still in the file it claims. `floor/harvest.py` matched new failures against
them. What nobody checked was whether any of it reached a decision.

## Where it was named

`ppa-eda-agent/pipeline/case_retrieval.py` states the same problem in its own
first paragraph — a reviewer asked to judge an `RSZ-0090` failure with no sight
of the other four times that pipeline hit `RSZ-0090`:

> The evidence exists in reference-db; it just never reaches the prompt.

Reading that is what found this. The two systems had built the same store and
left the same wire unconnected.

## Resolution

`toolkit/precedent.py`, two paths, both matching that repository's design:

- **guidance** — before planning, the standing lessons a plan can act on.
- **precedent** — after a refusal, the cases whose `signature` matches the
  error, cited by id so the claim can be checked.

Retrieval is a regex over recorded signatures rather than similarity over
prose. The corpus is small and its failures are labelled by the tools
themselves, so exact matching is more precise, needs no model or index, and can
say *why* a case came back.

## The part that was not obvious

A blanket dump would have been worse than nothing. Most cases teach an agent
writing SKILL by hand — `foreach` cannot count, a bare name is a variable — and
in a prompt that emits JSON ops that is noise. So every case now declares an
`audience`, and only `planner` cases reach the planner. Two of seventeen
qualify today. That is honest: the mechanism is the point, and it fills as the
knowledge base grows.
