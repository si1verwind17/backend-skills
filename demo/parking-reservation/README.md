# Demo: parking-reservation (one run of the whole chain)

> **For human readers only.** This directory shows what the
> `building-backend-services` chain produces. It is NOT reference material
> for agents: agents running the chain or any phase skill must not read,
> copy or imitate anything here — every choice below came from this
> scenario's context, and the right choices for your service come from
> yours, through the skills' own rules.

One headless agent run (Sonnet 5.5, with the plugin's review agents on Opus 5.5, skills at `v1.1.0`) took the chain
end to end from this ask, in 69 minutes. The run mode was chosen before the start sitting: **auto until done**, so
the run stopped at no gate and ended at the stop's sitting, with everything awaiting approval (everything else the
skill requires still applied):

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
  <https://si1verwind17.github.io/backend-skills/demo/>), `plan.md` with the
  chunk and the run mode, and `open-items.md` with every question the run
  could not ask, each with the assumption in force. Every document is
  `REVIEWED`, none `APPROVED`: an auto run never approves its own work. The
  data design, architecture and stack documents are in `Form: built`: they
  point to the code for what the code says.
- `src/`, `migrations/`, `tests/` — the service, built in three slices on a
  local branch, one commit per slice after one commit per design phase:
  (1) the foundation, reserving a spot and viewing a reservation,
  (2) check-in, check-out, cancel and the staff day lookup, (3) the billing
  feed (an outbox swept by Cloud Scheduler to Pub/Sub), the container image
  and the README. Each phase and each slice had an independent review: the
  design reviews raised 7, 4, 3 and 4 blocking findings, the slice reviews
  3, 0 and 4, all fixed.
- Verified: 245 tests pass (1 skipped: the Pub/Sub emulator test), including
  concurrent races for the last free spot against Postgres (exactly one
  booking wins) and a database constraint that refuses a double booking on
  its own; ruff and strict mypy clean; the image built and checked. An
  independent grader re-ran them from a fresh clone with the same result
  and scored the run 8/8 on the implementation-phase scenario.

Where it stopped: one blocking open item (OI-22 — the per-garage lock casts the garage id to a 32-bit key, so an id
of 2^31 or more could never be booked; the run capped ids at the API edge meanwhile), five hard-to-reverse unknowns
recorded as open items with its recommendation in force (the cloud and paid services: Pub/Sub, the authenticating
front end, Cloud SQL, Cloud Scheduler, scale to zero), and the decisions and build-time changes awaiting approval.

What its grading found against the skill's rules — kept, not hidden:

- Slices changed decisions in the reviewed documents (the reserve path's order, the check-out stamp, the relay's
  claim budget, a new error code, the wire status names). Each is listed in its slice's commit and under "changes
  made while building" at the stop, which is what an auto run does with them; a strict reader may still see the
  design edited to match the code.
- Slice 1's last blocking finding was committed after the final verdict, INSUFFICIENT only because the repair was
  not yet staged, without sending the staged repair back; the phase 0 review's new blocking-grade observation was
  fixed but not re-verified.
- The stack phase was committed, then amended ten seconds later with its minor fixes and the `REVIEWED` header.

The previous demo, made with 1.0 with the gates waived, is kept at tag `v1.1.0`.

---

## The service

Drivers reserve a garage spot for a time window, check in and out, or cancel. Garage staff list a
garage's reservations for a date. Each completed reservation is published for billing.

Design record: `docs/backend-design/` (requirements, data design, architecture, stack, open items).
`docs/backend-design/open-items.md` lists what still needs a decision from the business or tech owner.

### Layout

| Path | What |
|---|---|
| `src/parking_reservation/domain/` | business rules and ports, no I/O |
| `src/parking_reservation/service/` | one class per use case |
| `src/parking_reservation/repo/` | Postgres access; SQL lives in `repo/sql/*.sql` |
| `src/parking_reservation/adapters/` | Pub/Sub, Google token verification, clock |
| `src/parking_reservation/api/` | FastAPI routes, wire models, auth, error mapping |
| `migrations/` | numbered schema files, applied once each |

### Run

Python 3.14. Install the pinned dependencies, set the variables of `.env.template`, migrate, serve:

```sh
python -m venv .venv && .venv/bin/pip install -r requirements.lock
export DATABASE_URL=... GCP_PROJECT=... AUTH_AUDIENCE=... \
       FRONT_END_SERVICE_ACCOUNT=... SCHEDULER_SERVICE_ACCOUNT=...
PYTHONPATH=src .venv/bin/python -m parking_reservation.migrate migrations
PYTHONPATH=src .venv/bin/uvicorn parking_reservation.asgi:app
```

The service refuses to start when a variable is missing or empty. Every call except `GET /health`
carries a Google ID token: `/v1/*` only from the front end's service account (which sets
`X-Actor-Id` and `X-Actor-Role`, `driver` or `staff`), `/internal/*` only from Cloud Scheduler's.

### Tests

```sh
nice -n 19 .venv/bin/pytest                     # unit, stubbed and Docker-backed integration
.venv/bin/ruff check src tests && .venv/bin/ruff format --check src tests && .venv/bin/mypy
```

Integration tests start `postgres:17.11` with `docker run` on a free host port in 55432-55499 and
remove it afterwards. `tests/integration/test_pubsub_emulator.py` runs only with
`PUBSUB_EMULATOR_HOST` set.

### Operating the billing feed

Cloud Scheduler calls `POST /internal/outbox/relay` every minute. A pending row that has failed 10 times or more is logged as an error on every sweep; a row the
broker rejected as invalid or oversize is `parked` and logged once with its reason. To
publish a `published` or `parked` outbox row again (consumers deduplicate on `event_id`):

```sql
UPDATE outbox SET status = 'pending', published_at = NULL, attempts = 0,
                  next_attempt_at = now(), updated_at = now()
WHERE outbox_id = :id;
```

Billing's subscription on `reservation-completed-v1` must exist before the first completion is
published; its message retention (7 days by default) bounds how long billing may be down.

### Deploy

Build the image from `Dockerfile` and run it on Cloud Run with IAM authentication required, invoker
granted only to the front end's and the scheduler's service accounts, as its own service account,
maximum instances 10, request concurrency 10. Nothing in this repository creates cloud resources.
