# Evaluations: writing-business-requirements

Turning a fuzzy ask or a business brief into `requirements.md` and `open-items.md`: ids, locked decisions, testable rules with sources, lifecycles, open items with owners, no design leakage.

## Scenarios

| Scenario | What it tests |
|---|---|
| [1](scenarios/1-interview-bakery.md) | interview mode from a fuzzy bakery ask |
| [2](scenarios/2-digest-tutor-brief.md) | digest mode from a founder's brief full of traps |

## Pending validation

- `13b64fb` — requirements split by feature past the budget, area-prefixed ids; later-release features named out of scope. Scenario 2 rerun at 34a7495 (below, no split needed); the split itself is validated through building scenario 7.

## Latest results

Each scenario's latest run, Sonnet, graded by an independent judge on Opus. `Skill@` is the commit whose skill content
was evaluated.

| Scenario | Skill@ | Arm | Result | Notes |
|---|---|---|---|---|
| 1 | 7a5898b | skill (Sonnet 5.5) | 25/27 (3 runs; 9/9 at 8772816, 1 run) | two runs wrote an exclusion both as a rule and in §9; one sourced a rule to a locked decision whose words do not contain it |
| 2 | 34a7495 | skill (Sonnet 5.5) | 25/27 (3 runs; 26/27 at 7529ee4) | every trap handled; two runs put several exclusions on one §9 line |
| 1 | — | control | 10/40 (5 runs, earlier checks 1–8) | competent prose with none of the structure |
| 2 | — | control | 16/40 (5 runs, earlier checks 1–8) | marketing phrases inside rules, design leakage |
