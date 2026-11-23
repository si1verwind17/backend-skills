# Evaluations: backend-architecture

Architecture: service boundaries, state, caching, sync versus async, events, failure paths, deployment targets.

## Scenarios

| Scenario | What it tests |
|---|---|
| [1](scenarios/1-ticketing-gcp.md) | a live-support ticketing platform on GCP |
| [2](scenarios/2-delivery-tracking-aws.md) | food-delivery order tracking on AWS |

## Pending validation

None: `a9c600b` (with `13b64fb`) validated on scenarios 1 and 2 (below) and building scenario 9.

## Latest results

Each scenario's latest run, Sonnet, graded by an independent judge on Opus. `Skill@` is the commit whose skill content
was evaluated.

| Scenario | Skill@ | Arm | Result | Notes |
|---|---|---|---|---|
| 1 | 7a5898b | skill (Sonnet 5.5) | 25/27 (3 runs; 26/27 at c2c7298) | publishing events an `agent` AD row 3/3; one run copied its questions into the design document and wrote an OpenAPI skeleton no consumer asked for |
| 2 | efc316f | skill (plugin, Sonnet 5.5) | 26/27 (3 runs; 40/40 at 4fbc971, earlier checks) | publishing every transition with no consumer yet an `agent` AD row 3/3, broker chosen as an `agent` row, never tied to a paid-broker question; miss (borderline): one run left the engine per service as an owner question; AWS facts spot-checked |
| 1 | — | control | 29/40 (5 runs, earlier checks) | contract 0/5 |
