# Context: locker-rental service

- **Constraint** — the company runs on Google Cloud; all services deploy to Cloud Run (platform team inventory, 2026-08-10).
- **Convention** — services log JSON to stdout with a `trace_id` field (sibling `parcel-api`, 2026-08-10).
- **Wart** — sibling services store money as floating-point dollars; never copy this (sibling `parcel-api` schema, 2026-08-10).
