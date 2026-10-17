# Evaluations: writing-business-requirements

Turning a fuzzy ask or a business brief into `requirements.md` and `open-items.md`: ids, locked decisions, testable rules with sources, lifecycles, open items with owners, no design leakage.

## Scenarios

| Scenario | What it tests |
|---|---|
| [1](scenarios/1-interview-bakery.md) | interview mode from a fuzzy bakery ask |
| [2](scenarios/2-digest-tutor-brief.md) | digest mode from a founder's brief full of traps |

## Pending validation

None.

## Latest results

Each scenario's latest run, Sonnet, graded by an independent judge on Opus. `Skill@` is the commit whose skill content
was evaluated.

| Scenario | Skill@ | Arm | Result | Notes |
|---|---|---|---|---|
| 1 | 8772816 | skill | 9/9 (1 run) | the LD-sourced rule quotes the decision's words; no rule joins two obligations with "and"; non-goals only in §9 |
| 2 | 7529ee4 | skill | 26/27 (3 runs) | every trap handled; one "clear conflict" in an acceptance criterion |
| 1 | — | control | 10/40 (5 runs, earlier checks 1–8) | competent prose with none of the structure |
| 2 | — | control | 16/40 (5 runs, earlier checks 1–8) | marketing phrases inside rules, design leakage |
