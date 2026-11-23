# Requirements: parking-reservation
Status: REVIEWED · 2026-11-23
Form: design
Builds on: the business ask (start brief)

Drivers reserve a parking spot at a garage for a time window from the mobile app; garage staff look up a day's reservations on site; drivers check in, check out or cancel; a completed reservation is reported to billing.

## 1. Summary & business goal
The business lets drivers book a garage spot ahead of arrival and wants no spot ever sold twice. Staff need an on-site day list per garage. Billing charges the driver once a stay is over, so it must learn of every completed reservation.

## 2. Locked decisions
| Id | Decision | Source |
|---|---|---|
| LD1 | Services are built in Python by a 4-engineer team | ask: "a 4-engineer team building Python services" |
| LD2 | The service runs on Cloud Run | ask: "on Cloud Run with Postgres" |
| LD3 | The datastore is Postgres | ask: "on Cloud Run with Postgres" |
| LD4 | Drivers use a mobile app as their client | ask: "from our mobile app" |
| LD5 | Billing is a separate system that charges the driver | ask: "our billing system has to be told" |

## 3. Actors & roles
| Actor | Goal |
|---|---|
| Driver (mobile app) | reserve, check in, check out, cancel own reservations |
| Garage staff | look up a garage's reservations for a date, on site (read only) |
| Billing system | learn of each completed reservation so it can charge the driver |

## 4. Use cases
**Lifecycle.** `BOOKED` → `CHECKED_IN` → `COMPLETED`; `BOOKED` → `CANCELLED`. `COMPLETED` and `CANCELLED` are terminal. Forbidden: cancel once checked in; check in from any state but `BOOKED`; check out from any state but `CHECKED_IN` (repeating a command already applied is a no-op, UC3–UC5); any transition out of a terminal state; skipping `CHECKED_IN` on the way to `COMPLETED`.

**UC1 Reserve a spot.** Driver gives a garage and a window; the service books a spot there.
- Main flow: request → a free spot in the garage is booked for the window → reservation returned in `BOOKED`.
- AC1: a request for a garage with a free spot returns the reservation with its spot and status `BOOKED`.
- AC2: when every spot in the garage overlaps the window, the request is rejected with `GARAGE_FULL` and nothing is stored.
- AC3: N concurrent requests for the last free spot yield exactly one `BOOKED` reservation and N−1 `GARAGE_FULL`.
- AC4: repeating a request with the same client-generated key returns the first reservation and creates no second one (OI-11).
- AC5: a window that breaks R5, R6, R7 or R8 is rejected with `INVALID_WINDOW`.
- AC6: an unknown garage is rejected with `GARAGE_NOT_FOUND`.

**UC2 Staff day lookup.** Staff give a garage and a date and see that day's reservations.
- AC1: the result holds every reservation of the garage whose window overlaps the date, whatever its status, each with spot, window, driver id and status (OI-7, OI-13).
- AC2: a reservation whose window ends exactly when the date starts does not appear on that date (R19, OI-3).
- AC3: an unknown garage is rejected with `GARAGE_NOT_FOUND`.

**UC3 Check in.** Driver arrives and checks in.
- AC1: `BOOKED` → `CHECKED_IN`, with the check-in time recorded.
- AC2: checking in a reservation that is neither `BOOKED` nor `CHECKED_IN` is rejected with `ILLEGAL_TRANSITION`.
- AC3: checking in a reservation already `CHECKED_IN` returns it unchanged, with no second transition.
- AC4: checking in outside the reservation's window is rejected with `OUTSIDE_WINDOW` (R10, OI-4).

**UC4 Check out.** Driver leaves and checks out.
- AC1: `CHECKED_IN` → `COMPLETED`, with the check-out time recorded.
- AC2: checking out a `BOOKED` or `CANCELLED` reservation is rejected with `ILLEGAL_TRANSITION`.
- AC3: checking out a reservation already `COMPLETED` returns it unchanged and tells billing nothing new.

**UC5 Cancel.** Driver cancels before checking in.
- AC1: `BOOKED` → `CANCELLED`.
- AC2: cancelling a `CHECKED_IN` or `COMPLETED` reservation is rejected with `ILLEGAL_TRANSITION`.
- AC3: after a cancel the spot can be booked for the same window by another request.
- AC4: cancelling a reservation already `CANCELLED` returns it unchanged.

**UC6 Tell billing.** A completed reservation is reported to billing.
- AC1: each completion is delivered to billing at least once, with the reservation id, driver id, garage, spot, window, and actual check-in and check-out times (OI-1).
- AC2: a billing outage delays delivery and loses nothing.
- AC3: one completion never produces two different notifications.

**UC7 View a reservation (OI-16).** Driver reads one own reservation by id.
- AC1: the owner gets its current state; anyone else gets `NOT_FOUND`.

## 5. Business rules
| Id | Rule | Source |
|---|---|---|
| R1 | A spot is never double-booked | ask: "a spot must never be double-booked" |
| R2 | A reservation holds one spot of one garage for one time window | ask: "reserve a parking spot at one of our garages for a time window" |
| R3 | Two windows on one spot overlap when they share any instant | OI-3 |
| R4 | A `BOOKED` or `CHECKED_IN` reservation holds its spot for its window only | OI-5 |
| R5 | A window ends after it starts | OI-3 |
| R6 | A window starts no earlier than the request time | OI-3 |
| R7 | A window lasts at most 24 hours (proposed — OI-17) | OI-17 |
| R8 | A window starts at most 30 days after the request time (proposed — OI-17) | OI-17 |
| R9 | The service chooses the spot for a reservation | OI-2 |
| R10 | A driver checks in only within the reservation's window | OI-4 |
| R11 | A driver may check out at any time after checking in | OI-4 |
| R12 | A driver may cancel only before checking in | ask: "they can cancel before checking in" |
| R13 | Only the reserving driver may change a reservation's state | OI-16 |
| R14 | Each completed reservation is reported to billing | ask: "When a reservation completes, our billing system has to be told" |
| R15 | A reservation completes when its driver checks out | OI-12 |
| R16 | A date means the calendar day in the garage's own time zone | OI-7 |
| R17 | Garage staff may read the reservations of any garage | OI-6 |
| R18 | The same reserve request, repeated by the app, books one spot | OI-11 |
| R19 | A window includes its start instant | OI-3 |
| R20 | A window excludes its end instant | OI-3 |
| R21 | Only the reserving driver may view a reservation | OI-16 |

## 6. Integrations
| System | Direction | What |
|---|---|---|
| Mobile app | in | driver commands and reads (request/response) |
| Staff tool | in | day lookup (REST) |
| Billing | out | completed reservations: reservation id, driver id, garage, spot, window, check-in and check-out times; channel and contract unconfirmed (OI-1) |
| Identity | in | who the caller is and whether driver or staff (OI-6) |

## 7. Non-functionals
- NF1: criticality — a booking is never lost or double-sold, and a completion is never lost (billing revenue); user-facing through the app.
- NF2: sizing — up to 50 garages, 500 spots per garage, 5,000 reservations per day (proposed — OI-8).
- NF3: latency — p95 under 500 ms for every request (proposed — OI-8).
- NF4: personal data — the service holds only an opaque driver id and no name, contact or plate (assumed — OI-13).
- NF5: retention — reservations are kept indefinitely (proposed — OI-9).

## 8. Environment context
Cloud Run (LD2) with Postgres (LD3); the cloud is assumed to be GCP (OI-14) and Postgres is assumed hosted as Cloud SQL (OI-14); Cloud Run may scale to zero (assumed — OI-15); team of four Python engineers (LD1); no other estate is known.

## 9. Out of scope
Confirmation requested in OI-10:
- price calculation, payment and invoicing (billing's job)
- garage and spot administration (reference data arrives out of band — OI-7)
- no-show handling and automatic expiry
- overstay handling
- a driver's list of own reservations
- notifications to drivers
- modifying a reservation's window
- staff check-in or cancel on a driver's behalf
- the identity provider itself

## 10. Open items
All in `open-items.md`.
