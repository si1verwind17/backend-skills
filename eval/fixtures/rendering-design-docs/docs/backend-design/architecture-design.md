# Architecture design: locker-rental service

Status: APPROVED · 2026-08-14 · approved by Dana Reyes
Form: design
Builds on: requirements.md (UC1–UC2, NF1–NF2), data-design.md

Source: `requirements.md`, `data-design.md`.

## Component diagram

```mermaid
flowchart LR
    APP[Commuter app] -->|REST| API[locker-api]
    CONSOLE[Staff console] -->|REST| API
    API --> DB[(Postgres)]
    API -->|publish| PS[(Pub/Sub)]
    VENDOR[Vendor hardware API] -->|callback| API
```

## Key flow

```mermaid
sequenceDiagram
    APP->>API: POST /v1/rentals
    API->>DB: fn_rent(locker_id, wallet_hold)
    API->>PS: locker-rental-started-v1
    API-->>APP: 201 rental
```

## Decisions table

| Service | State | Cache | Deployment target |
|---|---|---|---|
| locker-api | stateless; state in Postgres | station/locker list, invalidate-on-write | Cloud Run, min-instances=1 |

## Event catalog

| Topic | Trigger | Consumers |
|---|---|---|
| locker-rental-started-v1 | rent success | analytics (future) |
| locker-rental-ended-v1 | end success | wallet reconciliation |
