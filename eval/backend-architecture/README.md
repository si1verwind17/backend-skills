# Evaluations: backend-architecture

Architecture: service boundaries, state, caching, sync versus async, events, failure paths, deployment targets.

## Scenarios

| Scenario | What it tests |
|---|---|
| [1](scenarios/1-ticketing-gcp.md) | a live-support ticketing platform on GCP |
| [2](scenarios/2-delivery-tracking-aws.md) | food-delivery order tracking on AWS |

## Pending validation

- `a9c600b` — whether to publish events with no consumer yet is an `agent` AD row, not a question for the user (owner's ruling); only a broker the estate lacks is. Validates on scenario 1 and on building-backend-services scenario 9.
- `13b64fb` — open items hold business or environment questions; a choice the requirements leave to design is an `AD` row marked `agent`; AD rows name who decided. Validates on scenario 1 (check 1 reworded).

## Latest results

Each scenario's latest run, Sonnet, graded by an independent judge on Opus. `Skill@` is the commit whose skill content
was evaluated.

| Scenario | Skill@ | Arm | Result | Notes |
|---|---|---|---|---|
| 1 | c2c7298 | skill | 26/27 (3 runs) | header, ids and open items 3/3; one run left an assumed load figure without a row |
| 2 | 4fbc971 | skill | 40/40 (5 runs, earlier checks) | AWS transfer; not re-run since the shared document format |
| 1 | — | control | 29/40 (5 runs, earlier checks) | contract 0/5 |
