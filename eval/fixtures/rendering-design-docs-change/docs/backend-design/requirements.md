# Requirements: locker-rental service

Status: REVIEWED · 2026-10-17
Form: design
Builds on: —

## 1. Summary

Commuters rent station lockers by the hour via app; station staff manage
lockers via a small console.

## 2. Locked decisions

- Payments via existing wallet service (no card handling here).
- Locker hardware API is vendor-provided (REST callback on open/close).

## 3. Actors

Commuter (rents, opens, ends rental); Station staff (marks lockers out of
service).

## 4. Use cases

- **UC1** — Rent a locker. Commuter picks a free locker, rental starts.
  - AC: a locker cannot be rented by two commuters at once; rental start
    is recorded with locker id and wallet hold id.
- **UC2** — End rental. Commuter ends; wallet charged by elapsed hours.
  - AC: ending an already-ended rental is a no-op returning the final
    price.

## 5. Business rules

- **R1** — One active rental per locker. *(stakeholder)*
- **R2** — Charge rounds up to the next full hour. *(stakeholder)*
- **R3** — Lockers out of service are never rentable. *(staff workshop)*
- **R4** — A rental ended within 2 minutes (proposed — OI-7) of opening is refunded in full. *(refunds change request, 2026-10-17)*

## 6. Integrations

Wallet service (hold + charge); vendor locker hardware API (callbacks).

## 7. Non-functionals

- **NF1** — User-facing, revenue-bearing; target p99 rent/open < 800ms.
- **NF2** — Growth: 3 stations now, 40 within two years.

## 8. Out of scope

Subscriptions; multi-day storage; refunds beyond failed-open auto-refund.

## 9. Open items

See `open-items.md`.
