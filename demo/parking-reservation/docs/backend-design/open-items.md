# Open items

| Id | Question | Raised in | Blocks | Decide by | Owner | Recommendation | Assumption in force |
|---|---|---|---|---|---|---|---|
| OI-1 | Does the driver pick the spot, or does the system assign one? | phase 0 | no | phase 1 | Business | System assigns | System assigns the first free spot of the garage in label order (text order) |
| OI-2 | Is "the day" the garage-local calendar date, one time zone per garage? | phase 0 | no | phase 1 | Business | Yes, IANA zone per garage | Garage-local date (R18) |
| OI-3 | Window limits: max duration, how far in the past a start may be | phase 0 | no | phase 1 | Business | 24 h max, 5 min skew | 24 h max, 5 min skew (R6, R14, R15) |
| OI-6 | Earliest/latest check-in relative to the window | phase 0 | no | phase 1 | Business | Any time before window end | Check-in allowed any time before end (R16) |
| OI-7 | Should check-out release the rest of the window for rebooking? | phase 0 | no | phase 1 | Business | No in v1 | No early release (R17) |
| OI-11 | Retention of reservation history | phase 0 | no | phase 1 | Legal | 7 years if billing needs it | Keep indefinitely, no purge job |
| OI-13 | Confirm the out-of-scope list | phase 0 | no | phase 1 | Business | Confirm | §9 stands |
| OI-15 | Does cancelling free the window immediately, and are windows half-open `[start, end)` so back-to-back bookings are allowed? | phase 0 | no | phase 1 | Business | Yes to both | Cancel frees at once (R3), half-open windows (R19) |
| OI-16 | Staff lookup contents and order, and a driver read-one endpoint — wanted? | phase 0 | no | phase 1 | Business | Include all statuses, order by start then spot, provide read-one | As written in UC2, UC6 |
| OI-17 | Data minimisation: store only an opaque driver id (no name, plate, payment data)? | phase 0 | no | phase 1 | Legal | Yes | Opaque id only (NF5) |
| OI-4 | Mobile retries: client-supplied idempotency key on create? | phase 0 | no | phase 2 | Tech | Required header `Idempotency-Key` | Required, scoped per driver (R10) |
| OI-5 | How are drivers and staff authenticated and identified? | phase 0 | no | phase 2 | Tech | Gateway verifies tokens, forwards identity | Gateway (Google Cloud API Gateway or the org's gateway) authenticates and forwards verified claims; only gateway and scheduler service accounts hold the Cloud Run invoker role; identity is read only from the gateway's verified-claims header (`sub` = driver id, `role` = staff; claim names to confirm), never from client headers; the service verifies the scheduler token on the relay route and checks ownership (R12) |
| OI-8 | How is billing told: product, contract, auth, dedup, tolerable delay? | phase 0 | no | phase 2 | Business / Billing team | Pub/Sub topic, JSON, billing dedups on event id, delay ≤ 1 min | Pub/Sub topic `parking-reservation-completed-v1`, at-least-once, dedup on `event_id`, delay ≤ 1 min (NF6); billing owns the no-expiry subscription (created before go-live), a dead-letter topic and an alert; 7-day retention on all topics (proposed) |
| OI-9 | Publish all lifecycle transitions as events even without consumers? | phase 0 | no | phase 2 | Tech | Yes | Yes, four topics |
| OI-18 | After how many failed relay runs is an outbox event parked for an operator? | phase 1 | no | phase 2 | Tech | 60 (about an hour of continuous failure) | 60 failed runs, one counted attempt per run (W5, AD8) |
| OI-19 | Is one service (API + relay) the right split? | phase 2 | no | phase 2 | Tech | Yes, one service | One service |
| OI-23 | Data design W5 changed during architecture review: the relay no longer holds row locks across publishes (the SKIP LOCKED design could not honour its own time limits). Prior W5 text, to revert: "per batch: `FOR UPDATE SKIP LOCKED` claim, publish, mark; a crash after publish and before mark re-publishes the same `event_id`". Confirm. | phase 2 | no | phase 2 | Tech | Confirm | New W5 in force |
| OI-10 | Sizing, latency, availability targets | phase 0 | no | phase 3 | Business | Confirm NF2–NF4 | NF2: ≤ 50 garages, ≤ 5,000 spots, ≤ 20 writes/s, ≤ 1M reservations/year; NF3 p95 < 500 ms; NF4 99.9 % |
| OI-12 | Managed Postgres product, CI, registry | phase 0 | no | phase 3 | Tech | Cloud SQL for PostgreSQL | Cloud SQL; Artifact Registry; no CI built in this run |
| OI-20 | Cloud Run min-instances 1 and max-instances cap for the connection limit | phase 2 | no | phase 3 | Tech | min 1, cap so instances × pool ≤ 60% of the DB connection limit | min 1, max 10, pool 5 per instance; Cloud SQL Enterprise db-custom-2-7680 (max_connections 400); peak about 20 instances × 5 = 100 connections, under 60 % |
| OI-26 | What framework and Python versions does the team run today? | phase 3 | no | phase 3 | Tech | Reuse the team's framework if it is not FastAPI | No existing framework dictates otherwise; FastAPI on Python 3.14 |
| OI-27 | Licensing, budget and organizational standards (compliance, approved libraries)? | phase 3 | no | phase 3 | Tech | State them before implementation | Open-source libraries are acceptable; no mandated standards |
| OI-14 | No-show / overstay / unclaimed-reservation policy | phase 0 | no | phase 4 | Business | Plan a follow-up | Out of scope; unclaimed reservations stay `reserved` and may be cancelled |
| OI-21 | Should staff be limited to their own garages, and may a staff identity also act as a driver? | phase 2 | no | phase 4 | Business | Yes once the identity model is known | Any staff identity reads any garage; a staff identity cannot act as a driver |
| OI-22 | Alert threshold for oldest pending event | phase 2 | no | phase 4 | Tech | 5 minutes | 5 minutes; log-based alerts on the parked-event error line and on `oldest_pending_age_seconds` of the relay request line (README, Deploy) |
| OI-24 | Cold-start time of the container for scale-out instances is not measured | phase 3 | no | phase 4 | Tech | Measure after first deploy | Order of one second, hidden by min-instances 1 |
| OI-25 | Does the transitive lock resolve with every pin above on Python 3.14.8? | phase 3 | no | phase 4 | Tech | Resolve in the first implementation slice | Yes |
| OI-28 | Is the host port range 55432–55499 the right constraint for test databases everywhere (CI included)? | phase 3 | no | phase 4 | Tech | Make the port an environment variable | Local runs use 55432 |
