# Evaluations: backend-architecture

Architecture: service boundaries, state, caching, sync versus async, events, failure paths, deployment targets.

## Scenarios

| Scenario | What it tests |
|---|---|
| [1](scenarios/1-ticketing-gcp.md) | a live-support ticketing platform on GCP |
| [2](scenarios/2-delivery-tracking-aws.md) | food-delivery order tracking on AWS |

## Pending validation

None.

## Latest results

Each scenario's latest run, Sonnet, graded by an independent judge on Opus. `Skill@` is the commit whose skill content
was evaluated.

| Scenario | Skill@ | Arm | Result | Notes |
|---|---|---|---|---|
| 1 | c2c7298 | skill | 26/27 (3 runs) | header, ids and open items 3/3; one run left an assumed load figure without a row |
| 2 | 4fbc971 | skill | 40/40 (5 runs, earlier checks) | AWS transfer; not re-run since the shared document format |
| 1 | — | control | 29/40 (5 runs, earlier checks) | contract 0/5 |
