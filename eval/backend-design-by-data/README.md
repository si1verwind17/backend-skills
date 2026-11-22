# Evaluations: backend-design-by-data

Data design: the engine-neutral logical model and access patterns, the engine family, the physical model per family, idempotent and atomic write paths, keys and indexes.

## Scenarios

| Scenario | What it tests |
|---|---|
| [1](scenarios/1-clinic-postgres.md) | a clinic service on Postgres: ids, statuses, idempotency, atomicity, queue decisions |
| [2](scenarios/2-parcel-lockers-serverless.md) | serverless parcel lockers: key-value design, conditional writes, a guessable code |
| [3](scenarios/3-clinic-no-engine-given.md) | the clinic with no engine or deployment given: the family and its assumption |

## Pending validation

- `34a7495` (with `13b64fb`) — a choice the requirements leave to design is an `agent` DD row, except an id's scope, which stays the business's question. Validated on scenario 1 (below); scenarios 2 and 3 not rerun.

## Latest results

Each scenario's latest run, Sonnet, graded by an independent judge on Opus. `Skill@` is the commit whose skill content
was evaluated.

| Scenario | Skill@ | Arm | Result | Notes |
|---|---|---|---|---|
| 1 | 34a7495 | skill (Sonnet 5.5) | 25/27 (3 runs; 23/27 at 7a5898b, 18/18 at 3d078c5) | DDL loaded and functions exercised in Postgres; the id's scope an open item 3/3 (at 7a5898b two runs decided it as an `agent` row — fixed in 34a7495); one run filed a write-path choice as an open item and let a confirm on a completed row count as already applied |
| 2 | 9992450 | skill | 7/7 (1 run) | attempt reserved by the conditional increment first, successes not refunded, guess arithmetic correct (0.096/locker/day) and raised as an open item; pickup-peak sizing asserted rather than derived |
| 3 | b240979 | skill | 4/4 (1 run) | open item names "Relational, Postgres dialect", decided by phase 2; no product pinned; DDL loaded into Postgres and behaviour-tested by the judge |
| 1 | — | control | 26/40 (5 runs, earlier checks 1–8) | contract, timestamps and the id-scope question missed |
