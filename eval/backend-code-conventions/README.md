# Evaluations: backend-code-conventions

Code conventions: layering, business rules as pure functions, errors and logging, tests, config at boot.

## Scenarios

| Scenario | What it tests |
|---|---|
| [1](scenarios/1-cancel-order-python.md) | a cancel-order feature in Python |
| [2](scenarios/2-cancel-order-scala.md) | the same feature in Scala 3 |
| [3](scenarios/3-signed-requests-config.md) | signed requests under config pressure |

## Pending validation

None.

## Latest results

Each scenario's latest run, Sonnet, graded by an independent judge on Opus. `Skill@` is the commit whose skill content
was evaluated.

| Scenario | Skill@ | Arm | Result | Notes |
|---|---|---|---|---|
| 1 | bfabde3 | skill | 34/35 (5 runs) | one rule left as a private service method |
| 2 | 1312cf9 | skill | 35/35 (5 runs) | Scala transfer |
| 3 | 47b46ae | skill | 24/27 (3 runs) | config validated at boot 2/3 |
| 1 | — | control | 21/35 (5 runs) | sizing, logging and the injected clock missed |
