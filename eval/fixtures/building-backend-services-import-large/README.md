# parking-reservation-service

HTTP API for parking reservations, garage administration, pricing, driver
accounts, operator reports and reservation reminders. FastAPI on Python 3.14,
PostgreSQL 16, Google Cloud Pub/Sub, deployed to Cloud Run.

## Layout

```
app/
  api/        routes and request/response schemas; app/api/router.py registers every route
  domain/     domain types and pure business rules
  services/   orchestration per area
  repo/       data access; SQL lives in app/repo/sql/*.sql
  events/     Pub/Sub publishers (billing, driver notifications)
  main.py     app factory and wiring
  migrate.py  migration runner
migrations/   numbered SQL migrations (NNNN_name.sql)
deploy/       Cloud Run service and migration job manifests, Cloud Scheduler setup
tests/        unit/ (no I/O) and integration/ (Postgres via Testcontainers)
```

## Running locally

Requires Python 3.14 and Docker.

```sh
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt

docker run -d --name parking-pg -e POSTGRES_PASSWORD=dev -p 5432:5432 postgres:16-alpine
export DATABASE_URL=postgresql://postgres:dev@localhost:5432/postgres
export INTERNAL_ENDPOINT_TOKEN=dev-token

python -m app.migrate     # apply migrations
python -m app             # serve on :8080 (RELOAD=1 for auto-reload)
```

Without `GCP_PROJECT_ID` the service logs a warning and publishes events to
an in-memory fake instead of Pub/Sub.

OpenAPI docs are served at `http://localhost:8080/docs`.

## Configuration

| Variable | Default | |
|---|---|---|
| `DATABASE_URL` | (required) | Postgres connection string |
| `GCP_PROJECT_ID` | empty | Pub/Sub project; empty uses the in-memory publishers |
| `INTERNAL_ENDPOINT_TOKEN` | empty | required `X-Internal-Token` for `/internal/*`; empty rejects every call |
| `OUTBOX_BATCH_SIZE` | 100 | billing outbox rows per publish run |
| `SETTLEMENT_BATCH_SIZE` | 200 | completed reservations priced per settlement run |
| `QUOTE_TTL_MINUTES` | 30 | how long a price quote stays valid |
| `MAX_QUOTE_DAYS` | 30 | longest stay a quote can cover |
| `REMINDER_LEAD_MINUTES` | 60 | reminder is sent this long before the window starts |
| `REMINDER_HORIZON_MINUTES` | 1440 | how far ahead each scheduling run looks |
| `NOTIFICATION_BATCH_SIZE` | 200 | reminders per dispatch run |
| `NOTIFICATION_MAX_ATTEMPTS` | 8 | publish attempts before a reminder is given up on |

## Scheduled endpoints

Cloud Scheduler calls these with the `X-Internal-Token` header
(`deploy/scheduler-jobs.sh` sets them up):

| Endpoint | Schedule |
|---|---|
| `POST /internal/outbox/publish` | every minute |
| `POST /internal/pricing/settle` | every 5 minutes |
| `POST /internal/notifications/schedule-reminders` | every 15 minutes |
| `POST /internal/notifications/dispatch` | every minute |

## Tests

```sh
python -m pytest tests/unit -q                       # no external dependencies
python -m pytest tests/integration -q -m integration # needs Docker
```

## Migrations

Add a new file `migrations/NNNN_short_name.sql` with the next number; never
edit a migration that has been deployed. `python -m app.migrate` applies
pending files in order and records them in `schema_migrations`.

## Deployment

Pushes to `main` trigger `cloudbuild.yaml`: unit tests, image build and push,
the `parking-reservation-migrate` Cloud Run job (`deploy/migrate-job.yaml`),
then `gcloud run services replace deploy/service.yaml`. Pull requests run the
full test suite in GitHub Actions (`.github/workflows/ci.yml`).
