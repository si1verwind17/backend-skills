# Evaluations: backend-architecture

Architecture: service boundaries, state, caching, sync versus async, events, failure paths, deployment targets.

## Scenarios

| Scenario | What it tests |
|---|---|
| [1](scenarios/1-ticketing-gcp.md) | a live-support ticketing platform on GCP |
| [2](scenarios/2-delivery-tracking-aws.md) | food-delivery order tracking on AWS |

## Pending validation

- `a9c600b` (with `13b64fb`) — publishing events with no consumer yet is an `agent` AD row (owner's ruling); a choice the requirements leave to design is an `agent` AD row. Validated on scenario 1 (below) and building scenario 9 (two of three runs; one tied publishing to the paid-broker question); scenario 2 not rerun.

## Latest results

Each scenario's latest run, Sonnet, graded by an independent judge on Opus. `Skill@` is the commit whose skill content
was evaluated.

| Scenario | Skill@ | Arm | Result | Notes |
|---|---|---|---|---|
| 1 | 7a5898b | skill (Sonnet 5.5) | 25/27 (3 runs; 26/27 at c2c7298) | publishing events an `agent` AD row 3/3; one run copied its questions into the design document and wrote an OpenAPI skeleton no consumer asked for |
| 2 | 4fbc971 | skill | 40/40 (5 runs, earlier checks) | AWS transfer; not re-run since the shared document format |
| 1 | — | control | 29/40 (5 runs, earlier checks) | contract 0/5 |
