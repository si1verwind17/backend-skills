# Demo: parking-reservation (one run of the whole chain)

> **For human readers only.** This directory shows what the
> `building-backend-services` chain produces. It is NOT reference material
> for agents: agents running the chain or any phase skill must not read,
> copy or imitate anything here — every choice below came from this
> scenario's context, and the right choices for your service come from
> yours, through the skills' own rules.

One headless agent run (Sonnet, with the plugin's review agents) took the chain end to end from this ask, with the
review gates waived for the run (everything else the skill requires still applied):

> Drivers reserve a parking spot at one of our garages for a time window,
> from our mobile app, and a spot must never be double-booked. Garage staff
> look up the day's reservations on site by garage and date. Drivers check
> in on arrival and check out when they leave; they can cancel before
> checking in. When a reservation completes, our billing system has to be
> told so it can charge the driver. We're a 4-engineer team building Python
> services on Cloud Run with Postgres.

It is committed as the run left it, not polished:

- `docs/backend-design/` — requirements, data design, architecture and
  stack selection in the shared format (rendered for people as
  [`design-review.html`](docs/backend-design/design-review.html) — normally
  local-only, committed here as the showcase — and published at
  <https://si1verwind17.github.io/backend-skills/demo/>), and `open-items.md` with every
  question the run could not ask, each with the assumption it proceeded on.
  The data design, architecture and stack documents are in `Form: built`:
  they point to the code for what the code says.
- `src/`, `tests/`, `scripts/` — the service, built in three slices on a
  local branch, one commit per slice: (1) scaffold, migrations and reserving
  a spot, (2) reading a reservation, check-in, check-out, cancel and the
  staff day lookup, (3) the outbox relay, scheduler authentication, the
  Pub/Sub publisher, the container image and its smoke test. Each phase and
  each slice had an independent review (the slice reviews raised 5, 1 and 3
  blocking findings, all fixed and re-verified).
- Verified: 211 tests pass, including a concurrent race for the last free
  spot against Postgres 18 (one booking wins, the rest are rejected); ruff,
  strict mypy and the image smoke test clean. An independent grader re-ran
  them from a fresh clone with the same result.

What its own grading found against the skill's rules — kept, not hidden:

- During architecture the run decided an approved write path (W5, the
  relay's locking) could not meet its time limits, replaced it before any
  ruling and recorded the change as a non-blocking open item (OI-23). The
  skill now says an approved decision that proves wrong in a later design
  phase stays in force behind a blocking open item.
- The stack document was switched to `Form: built` and trimmed in a final
  commit outside any slice, while it still read APPROVED.
- Each slice was committed before its review and amended after it; the
  last small fixes of two reviews were not sent back for re-verification
  (the run said so).

---

## The service

Drivers reserve a parking spot for a time window; staff look up a garage's day; check-in, check-out and
cancel; billing is told of each completed reservation. Python 3.14 · FastAPI · Postgres 18 · Cloud Run.

Design: `docs/backend-design/` (requirements, data, architecture, stack, `open-items.md`).

### Develop

```
python3 -m venv .venv && .venv/bin/pip install --require-hashes -r requirements-dev.lock && .venv/bin/pip install -e . --no-deps
.venv/bin/pytest                     # integration tests start postgres:18.6 in Docker on host port 55432
.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy src tests
```

`TEST_DB_PORT` overrides the test database port (host ports 55432–55499 are reserved for this work).
Refresh the locks with `pip-compile --generate-hashes --allow-unsafe [--extra dev] -o <lock> pyproject.toml`.

### Configuration (environment, validated at boot)

| Variable | Meaning |
|---|---|
| `DATABASE_URL` | libpq URL; on Cloud Run `postgresql://user:pass@/db?host=/cloudsql/<connection name>` |
| `IDENTITY_HEADER` | header carrying the gateway's verified claims (base64url JSON with `sub`, optional `role`) |
| `GCP_PROJECT` | project owning the lifecycle topics |
| `SCHEDULER_SERVICE_ACCOUNT` | email of the Cloud Scheduler service account allowed to call `/internal/relay` |
| `RELAY_AUDIENCE` | audience of the scheduler's ID token (the service URL) |

Migrations: `python -m parking_reservation.migrate_main` (run as a deploy step before the new revision).
Garages and spots are not written by the API: seed them with SQL (`garage`, `spot` tables).

### Deploy (Cloud Run)

Build the `Dockerfile` (base image pinned by digest; dependencies from the hash-locked `requirements.lock`),
run the migration job from the same image before each new revision, then deploy with:
min-instances 1, max-instances 10, concurrency 20 (AD4), request timeout at least 90 s, IAM invoker only for the
gateway's and the scheduler's service accounts. Cloud Scheduler: `POST <service>/internal/relay` every minute with an
OIDC token (audience `RELAY_AUDIENCE`), attempt deadline at least 90 s.

Before go-live (AD12): create the four `parking-reservation-<event>-v1` topics with 7-day retention, and have the
billing team create their no-expiry subscription on `parking-reservation-completed-v1` with a dead-letter topic.
Parked events (error log "outbox event parked") are re-queued by setting `status = 'pending', attempts = 0` on the row.

Cloud Scheduler must be created with `--oidc-token-audience` equal to `RELAY_AUDIENCE` (its default is the full target
URL including `/internal/relay`) and the runtime service account needs `roles/pubsub.publisher` on the four topics.
A run lasts at most about 75 s (55 s loop, 10 s publish deadline, 4 s pool waits, 5 s certificate fetch), hence the
90 s timeouts.

Alerts to create from the logs (I4, OI-22): (1) any `ERROR` line "outbox event parked"; (2) the relay request line
(`route=/internal/relay`) with `relay.oldest_pending_age_seconds` above 300, or no line with a `relay` field for 3 minutes
(the scheduler or its auth is broken: those runs log 401/403 at WARNING without a `relay` field); (3) `WARNING` relay lines with `failed > 0` for several minutes in a row.

The image installs from hash-locked files (`requirements.lock`, `requirements-build.lock`). After changing
dependencies, rebuild the image and run `scripts/smoke_image.sh` (migrate, `/healthz`, relay rejects an anonymous call):
it is what proves the packaged `.sql` files are in the image.
