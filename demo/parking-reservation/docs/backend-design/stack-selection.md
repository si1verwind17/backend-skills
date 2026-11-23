# Stack selection: parking-reservation
Status: REVIEWED · 2026-11-23
Form: built
Builds on: requirements.md (LD1–LD3, NF1–NF3), architecture-design.md (AD2, AD4–AD9), data-design.md (DD1–DD3, DD5, DD6)

Python on Cloud Run with Postgres, as the team already runs it (LD1–LD3). FastAPI serves the REST API, psycopg 3 talks to Postgres with SQL kept in `.sql` files, and the Pub/Sub client publishes events.

## Basis
The stack is the team's (LD1–LD3); which Python version and framework its other services use is unrecorded (assumed — OI-21). Python was kept over Go 1.27.4 with pgx v5.13.0 for a mission-critical service on LD1; the accepted risks are run-time type errors in paths the type checker cannot see (mitigated by SD8, the database constraint of DD2, the test tiers and boot-time configuration validation) and a slower start than a static binary (AD4, OI-15). Import time of the full dependency set was measured at 0.25–0.38 s on a workstation (2026-11-23); container start, the first connection and the first key fetch were not measured. Sources: Go runtime support https://docs.cloud.google.com/run/docs/runtimes/go, pgx https://pkg.go.dev/github.com/jackc/pgx/v5, `btree_gist` 1.7 on Cloud SQL for PostgreSQL 15–17 https://docs.cloud.google.com/sql/docs/postgres/extensions (all 2026-11-23).

## Decisions
| Id | Decision | By | Why | Beat | Serves |
|---|---|---|---|---|---|
| SD1 | Python 3.14 (assumed — OI-21) | agent | the team's language (LD1); `uuid.uuid7()` is in the standard library from 3.14, so DD3 needs no package | Python 3.12 | LD1, DD3 |
| SD2 | FastAPI with synchronous endpoints (assumed — OI-21) | agent | typed request models and generated OpenAPI; synchronous code keeps psycopg transactions explicit, and FastAPI's default 40-thread pool covers AD4's concurrency of 10 | async endpoints | AD5 |
| SD3 | psycopg 3 with `psycopg-pool`, pool of 5 and a 5 s wait for a connection; SQL in `.sql` files loaded at startup | agent | the code conventions put raw SQL in `.sql` files (`backend-code-conventions/SKILL.md`, "Layer by responsibility"); the booking CTE and guarded updates are hand-written; the 5 s wait matches AD4's timeouts | SQLAlchemy ORM; the pool's default 30 s wait | DD5, DD6, AD4 |
| SD4 | PostgreSQL 17: tests on 17.11 (the minor Cloud SQL lists), Cloud SQL for PostgreSQL 17 in production (assumed — OI-14) | agent | supports exclusion constraints and `btree_gist`; the DDL was checked on 17.12 and runs on 17.11 in the suite | PostgreSQL 18, Cloud SQL's default | DD1, LD3 |
| SD5 | pytest; Postgres for repo tests started by a conftest fixture with `docker run` on a host port in 55432–55499 and a uniquely named container, removed only by its starter | agent | a real engine in a container is the first-choice tier; Testcontainers picks random ports, and this host allows only that range | an embedded fake | DD2 |
| SD6 | `ruff` for lint and format checks | agent | one tool for both, enforced by script | flake8 plus black | LD1 |
| SD7 | One container image on `python:3.14.8-slim-trixie` running uvicorn | agent | Cloud Run runs containers; a slim exact-tag base | a buildpack | AD4 |
| SD8 | `mypy` in strict mode over the package | agent | the mitigation for run-time type errors named in the comparison | no type checker | NF1 |
| SD9 | Dependencies installed by pip from `requirements.lock`, a pip requirements file with `==` pins for every runtime, dev and transitive package, no hashes | agent | the build is repeatable and nothing floats in the image | unpinned transitive packages | NF1 |
| SD10 | Migrations applied by an in-repo runner script over psycopg that runs the numbered files in `migrations/` once each, in order, recording them in its own bookkeeping table `schema_migration` | agent | no extra dependency for a four-table schema | Alembic or Flyway | DD1 |
| SD11 | The Pub/Sub adapter is tested with its client stubbed for error classification; a test against the official emulator exists and is skipped unless `PUBSUB_EMULATOR_HOST` is set | agent | the emulator image is large; the skip rule is the code conventions' CI-only tier | none | UC6 |
| SD12 | The ID-token verifier caches Google's public certificates for one hour: read-only derived data, not service state (AD2) | agent | one HTTPS fetch an hour instead of one per request, protecting NF3 and the availability of every `/v1/*` call | the library default, a fetch per request | AD6, NF3 |

## Finalized versions
| Component | Pin | Source (checked 2026-11-23) |
|---|---|---|
| Python, image and local dev | image `python:3.14.8-slim-trixie` (3.14.8); the workstation's 3.14.7 runs the tests locally (a recorded patch-level gap) | Docker Hub tag `python:3.14.8-slim-trixie` pulled on this host |
| pip (installer) | 26.2.1 | `pip --version` in the build venv |
| FastAPI | 0.165.0 | https://pypi.org/project/fastapi/ |
| Starlette | 1.10.0 (FastAPI requires 1.6.0 or later; pinned independently) | https://pypi.org/project/starlette/ |
| uvicorn | 0.54.0 | https://pypi.org/project/uvicorn/ |
| pydantic | 2.14.4 | https://pypi.org/project/pydantic/ |
| psycopg with `binary` extra | 3.3.9 | https://pypi.org/project/psycopg/ |
| psycopg-pool | 3.3.3 (declares no psycopg requirement; its `close_returns` option needs psycopg 3.3 or later, met by 3.3.9) | https://pypi.org/project/psycopg-pool/ |
| google-cloud-pubsub | 2.44.0 | https://pypi.org/project/google-cloud-pubsub/ |
| google-auth | 2.63.1 | https://pypi.org/project/google-auth/ |
| requests | 2.34.2 | https://pypi.org/project/requests/ |
| pytest | 9.2.0 | https://pypi.org/project/pytest/ |
| httpx (test client) | 0.28.1 | https://pypi.org/project/httpx/ |
| ruff | 0.17.6 | https://pypi.org/project/ruff/ |
| mypy | 2.4.1 | https://pypi.org/project/mypy/ |
| types-requests | 2.33.0.20261030 | https://pypi.org/project/types-requests/ |
| Transitive packages | pinned in `requirements.lock` (SD9) | `pip freeze` of the build venv |
| PostgreSQL (tests) | 17.11, image `postgres:17.11` | image pulled on this host |
| PostgreSQL (production) | 17, Cloud SQL (assumed — OI-14) | https://docs.cloud.google.com/sql/docs/postgres/db-versions lists 17 at 17.11 |
| Docker (host) | 29.8.2 | `docker --version` |
