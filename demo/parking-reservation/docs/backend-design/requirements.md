# Requirements: parking-reservation
Status: APPROVED · 2026-10-17 · approved by user (review gates waived for this run)
Form: design
Builds on: the business ask (quoted in LD sources below)

Drivers reserve a spot at a garage for a time window from the mobile app. Garage staff look up a garage's reservations for a day on site. Drivers check in and out, may cancel before checking in, and a completed reservation must reach billing so the driver can be charged.

## 1. Summary & business goal

A service that guarantees a spot is never double-booked, gives on-site staff a reliable daily view, and hands billing a trustworthy completion signal. Small team (4 engineers), Python, Cloud Run, Postgres.

## 2. Locked decisions

| Id | Decision | Source |
|---|---|---|
| LD1 | Python service on Cloud Run with Postgres | Business: "4-engineer team building Python services on Cloud Run with Postgres" |
| LD2 | Reservations are made from the mobile app by drivers | Business: "Drivers reserve a parking spot … from our mobile app" |
| LD3 | Billing is an external system told on completion | Business: "our billing system has to be told so it can charge the driver" |

## 3. Actors & roles

| Actor | Goal |
|---|---|
| Driver (mobile app) | Reserve, check in, check out, cancel own reservations |
| Garage staff (on site) | Look up a garage's reservations for a date |
| Billing system | Learn of completed reservations |

Roles: drivers act only on their own reservations (R12); staff read reservations (R13). How callers are authenticated is OI-5.

## 4. Use cases

**Lifecycle.** States: `reserved` → `checked_in` → `completed`; `reserved` → `cancelled`. Terminal: `completed`, `cancelled`. A repeat of the call that produced the current state is allowed and changes nothing (idempotent retry). Forbidden transitions: cancel from `checked_in` or `completed`; check-in from `cancelled` or `completed`; check-out from `reserved` or `cancelled`; any move out of a terminal state. A `reserved` reservation never checked in stays `reserved` after its window ends and may still be cancelled (OI-14).

**UC1 Reserve a spot.** Driver gives garage, start, end (and a retry key, R10). Service assigns a free spot of that garage for the window (OI-1).
- AC: success returns reservation id, spot, window, status `reserved`.
- AC: when no single spot of the garage is free for the whole window, rejected with error `NO_SPOT_AVAILABLE`.
- AC: two concurrent requests for the last free spot: exactly one succeeds, the other gets `NO_SPOT_AVAILABLE`.
- AC: end not after start (R6), window over 24 h (R14), or start earlier than now minus 5 minutes (R15) → `INVALID_WINDOW`; unknown garage → `GARAGE_NOT_FOUND`.
- AC: repeating a request with the same retry key returns the original reservation and creates no second one.
- AC: the same retry key with a different garage or window → `IDEMPOTENCY_KEY_REUSED`.
- AC: back-to-back windows on one spot (end of one = start of next) both succeed (R19).

**UC2 Look up the day's reservations.** Staff give garage and date.
- AC: returns every reservation of that garage whose window overlaps that calendar date in the garage's local time, with spot, driver reference, window, status, ordered by start then spot (OI-16).
- AC: includes cancelled and completed reservations, flagged by status (OI-16).
- AC: unknown garage → `GARAGE_NOT_FOUND`.

**UC3 Check in.** Driver arrives.
- AC: `reserved` → `checked_in`, records check-in instant.
- AC: repeating the call on a `checked_in` reservation returns it unchanged with no error.
- AC: check-in before the window's start succeeds (OI-6).
- AC: check-in after the window's end → `CHECKIN_WINDOW_CLOSED` (R16).
- AC: another driver's or unknown reservation → `RESERVATION_NOT_FOUND` (R12; same for UC4, UC5).
- AC: on `cancelled` or `completed` → `INVALID_TRANSITION`.

**UC4 Check out.** Driver leaves.
- AC: `checked_in` → `completed`, records check-out instant, and billing is told (R9).
- AC: repeating on `completed` returns it unchanged and creates no second completion; any re-delivery to billing carries the same dedup id (OI-8).
- AC: on `reserved` or `cancelled` → `INVALID_TRANSITION`.

**UC5 Cancel.** Driver cancels before check-in.
- AC: `reserved` → `cancelled`; the spot's window is free for others immediately.
- AC: repeating on `cancelled` returns it unchanged.
- AC: on `checked_in` or `completed` → `INVALID_TRANSITION`.

**UC6 Read one reservation (OI-16).** Driver fetches own reservation by id.
- AC: own reservation returned with spot, window, status and check-in/out instants.
- AC: other driver's or unknown id → `RESERVATION_NOT_FOUND`.

## 5. Business rules

| Id | Rule | Source |
|---|---|---|
| R1 | A spot is never double-booked | Business: "a spot must never be double-booked" |
| R2 | Two reservations of one spot that hold their windows do not overlap | Business: "a spot must never be double-booked" |
| R20 | A `reserved` or `checked_in` reservation holds its window | Business: "a spot must never be double-booked" |
| R3 | A cancelled reservation no longer holds its window | OI-15 |
| R4 | A reservation is made for one garage | Business: "at one of our garages" |
| R5 | A reservation covers a time window with a start and an end | Business: "for a time window" |
| R6 | A reservation's end is after its start | OI-3 |
| R7 | A driver can check in a reservation that is `reserved` | Business: "Drivers check in on arrival" |
| R8 | A driver can check out a reservation that is `checked_in` | Business: "check out when they leave" |
| R9 | Billing is told of each reservation that completes | Business: "When a reservation completes, our billing system has to be told" |
| R10 | A repeated create with the same retry key by the same driver returns the first reservation | OI-4 |
| R11 | A reservation can be cancelled only while `reserved` | Business: "they can cancel before checking in" |
| R12 | A driver can act only on that driver's own reservations | OI-5 |
| R13 | Staff look up reservations by garage and date | Business: "look up the day's reservations on site by garage and date" |
| R14 | A reservation window is at most 24 hours (proposed — OI-3) | OI-3 |
| R15 | A reservation's start must be at or after the current instant minus 5 minutes (proposed — OI-3) | OI-3 |
| R16 | Check-in is rejected after the reservation's end (proposed — OI-6) | OI-6 |
| R17 | A completed reservation keeps holding its window | OI-7 |
| R18 | The day of a lookup is a calendar date in the garage's local time zone | OI-2 |
| R19 | A window is half-open: it includes its start and excludes its end | OI-15 |

## 6. Integrations

| System | Direction | What |
|---|---|---|
| Mobile app | in | HTTPS JSON API for UC1, UC3–UC6 |
| On-site staff tool | in | HTTPS JSON API for UC2 |
| Billing | out | Notified on every reservation completion; transport and contract OI-8 |
| Identity | in | Authentication of drivers and staff; OI-5 |

Anticipated (not requested): other consumers of reservation lifecycle events (OI-9).

## 7. Non-functionals

- NF1 Criticality: money follows completion, so a completion is never lost, delivered at least once with a dedup id (R9, OI-8); user-facing, not life-critical.
- NF2 Sizing (proposed — OI-10): ≤ 50 garages, ≤ 5,000 spots, ≤ 20 reservation writes/s peak, ≤ 1M reservations/year.
- NF3 Latency (proposed — OI-10): p95 < 500 ms for UC1–UC6.
- NF6 Billing delay (proposed — OI-8): a completion reaches billing within 1 minute of check-out.
- NF4 Availability (proposed — OI-10): 99.9 % monthly for the API.
- NF5 Data sensitivity: the driver is stored as an opaque external id only (proposed — OI-17); retention OI-11.

## 8. Environment context

Cloud Run (serverless, scale-to-zero capable) and Postgres, Python, team of 4 (LD1). Cloud provider is GCP (Cloud Run is a GCP product); managed Postgres product, messaging product and CI are unknown (OI-8, OI-12). No existing estate is known; no external context sources.

## 9. Out of scope

Each line is an assumption to confirm: OI-13.
- Pricing, charging, invoicing (billing owns them).
- Driver accounts, registration, payment methods.
- Garage and spot administration UI (garages and spots are seeded/managed outside this API).
- No-show handling, expiry of unclaimed reservations, overstay handling.
- Modifying a reservation's window (cancel and re-book instead).
- Early release of a spot after check-out.
- Waiting lists and spot-type preferences (EV, accessible, size).

## 10. Open items

All open questions and assumptions: `open-items.md`.
