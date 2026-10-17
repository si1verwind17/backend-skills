# Evaluations: backend-stack-selection

Stack selection: the existing stack first, shape mismatches, researched and cited claims, ecosystem checks, exact pins.

## Scenarios

| Scenario | What it tests |
|---|---|
| [1](scenarios/1-scala-estate-two-services.md) | two new services on an existing Scala estate: one mission-critical, one thin serverless |

## Pending validation

None.

## Latest results

Each scenario's latest run, Sonnet, graded by an independent judge on Opus. `Skill@` is the commit whose skill content
was evaluated.

| Scenario | Skill@ | Arm | Result | Notes |
|---|---|---|---|---|
| 1 | 8772816 | skill | 8/8 (1 run) | pins checked against the poms they are built against (tapir → zio-json 1.0.0, zio-pubsub → google-cloud-pubsub 1.154.0); two services in one build pin different zio-json versions, unreconciled |
| 1 | — | control | 33/40 (5 runs, earlier checks) | strong control; citations and pins were the gap |
