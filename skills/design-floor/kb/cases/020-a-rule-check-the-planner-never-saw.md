---
id: 020-a-rule-check-the-planner-never-saw
outcome: failure
lanes: request
audience: floor, planner
rule: "A shape exactly at a minimum is legal; only below it is not."
rule_in: code
---

# The check ran, and told only the user

## What happened

The rule check landed and immediately had the shape of the problem it was
meant to solve. Asked for two 0.05 µm wires 0.06 µm apart, the floor built
them, checked them, and answered with three violations and an illegal layout.
Correct, and useless: someone who asks for a layout and receives a complaint
has less than they started with, and the planner — the only thing that could
have drawn it differently — never saw a violation it had caused.

The same gap as case 018, one step further down the loop. There, lessons
existed and did not reach the prompt. Here a *measurement of this very
request* existed and did not reach it.

## Where the rule came from

`ip-dev-fde/strongarm_sim/hermes/skills/strongarm-lessons/SKILL.md` keeps the
lessons a self-test loop has accumulated, and its first one is this:

> **증상**: "오프셋 마진이 크니 input m 을 절반으로" — 논리적으로 들리는
> 제안이 실측에서 530→**1063 ps 악화**.
> **규칙**: 사이징 제안은 반드시 실측 후에만 제시.

A proposal that sounds right is not evidence. The measurement is, and it has
to come back before the answer does.

## Resolution

`build_and_check` builds, and if the errors are non-empty sends them back to
the planner once and builds again. Four boundaries, each deliberate:

- **Errors only.** A minimum-area warning is not worth a second model call.
- **A rebuild is safe here.** `execute` clears each cell before filling it, so
  the second build replaces the geometry rather than layering on it — the
  hazard case 013 records.
- **A correction that is not better is not kept.** If the second attempt has
  as many errors as the first, the original is rebuilt and reported. Shipping
  a worse layout quietly is a worse failure than reporting a bad one.
- **The correction is stated.** The request asked for 0.05 µm wires and got
  legal ones. The answer now says so and quotes what was not buildable. A
  substitution the reader cannot see is the failure case 019 is about.

## A second thing the same file was right about

Reading `ip-dev-fde/strongarm_sim/layout.py` found a real defect in the check
itself: its width comparison carries a `- 1e-6` that this one did not. Of the
2001 grid positions a 0.14 µm wire can start at, 919 subtract to
0.13999999999999999 — so nearly half of all minimum-width geometry was
reported as a violation. A checker that calls correct work wrong is a checker
that gets switched off, which would have cost more than having no check.
