# Evaluations: backend-stack-selection

Stack selection: the existing stack first, shape mismatches, researched and cited claims, ecosystem checks, exact pins.

## Scenarios

| Scenario | What it tests |
|---|---|
| [1](scenarios/1-scala-estate-two-services.md) | two new services on an existing Scala estate: one mission-critical, one thin serverless |

## Pending validation

None: `509fbe0` and `13b64fb` validated on scenario 1 (below).

## Latest results

Each scenario's latest run, Sonnet, graded by an independent judge on Opus. `Skill@` is the commit whose skill content
was evaluated.

| Scenario | Skill@ | Arm | Result | Notes |
|---|---|---|---|---|
| 1 | 7a5898b | skill (Sonnet 5.5) | 24/24 (3 runs; 8/8 at 8772816, 1 run) | existing stack kept, cold start weighed for the serverless service, pins exact; unscored: stale library coordinates (a moved group id) in two runs, a deployment choice as an SD row in one |
| 1 | — | control | 33/40 (5 runs, earlier checks) | strong control; citations and pins were the gap |
