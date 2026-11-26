# Evaluations: backend-design-by-data

Data design: the engine-neutral logical model and access patterns, the engine family, the physical model per family, idempotent and atomic write paths, keys and indexes.

## Scenarios

| Scenario | What it tests |
|---|---|
| [1](scenarios/1-clinic-postgres.md) | a clinic service on Postgres: ids, statuses, idempotency, atomicity, queue decisions |
| [2](scenarios/2-parcel-lockers-serverless.md) | serverless parcel lockers: key-value design, conditional writes, a guessable code |
| [3](scenarios/3-clinic-no-engine-given.md) | the clinic with no engine or deployment given: the family and its assumption |

## Pending validation

- `3edd8f0`: an id's scope is an open item only for ids people outside the service count with; surrogate keys and generated secrets are `agent` rows. Validates on scenario 2 (new check 8: the pickup code and drop key decided by design) and scenarios 1 and 3 (the business ids stay open items).

## Latest results

Each scenario's latest run, Sonnet, graded by an independent judge on Opus. `Skill@` is the commit whose skill content
was evaluated.

| Scenario | Skill@ | Arm | Result | Notes |
|---|---|---|---|---|
| 1 | 34a7495 | skill (Sonnet 5.5) | 25/27 (3 runs; 23/27 at 7a5898b, 18/18 at 3d078c5) | DDL loaded and functions exercised in Postgres; the id's scope an open item 3/3 (at 7a5898b two runs decided it as an `agent` row — fixed in 34a7495); one run filed a write-path choice as an open item and let a confirm on a completed row count as already applied |
| 2 | efc316f | skill (plugin, Sonnet 5.5) | 21/21 (3 runs; 7/7 at 9992450, 1 run) | every DD row `agent`, no design choice filed as an open item; schemas parse and agree with the dictionary; unscored: the runs split on technical ids (code scope, `drop_id`) — `agent` row in one, open item in others — so "id scope" is unclear for non-business ids; one open-items table lacked its separator row |
| 3 | efc316f | skill (plugin, Sonnet 5.5) | 12/12 (3 runs; 4/4 at b240979, 1 run) | profile-number scope an open item 3/3, the counter that implements it an `agent` row; DDL loaded into Postgres 17 and smoke-tested; unscored: summaries name the family above the engine row |
| 1 | — | control | 26/40 (5 runs, earlier checks 1–8) | contract, timestamps and the id-scope question missed |
