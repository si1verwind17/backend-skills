# Stack selection: locker-rental service

Status: DRAFT · 2026-08-16
Form: design
Builds on: architecture-design.md

Source: `requirements.md` §7, `architecture-design.md` decisions table.

## Existing-stack assessment

Team runs TypeScript/Node services on Cloud Run; this service fits the
estate — keep the existing stack.

## Finalized versions

| Component | Version | Source |
|---|---|---|
| Node.js | 24.9.0 LTS | nodejs.org (2026-08-15) |
| TypeScript | 5.9.3 | npm (2026-08-15) |
| fastify | 5.7.1 | npm (2026-08-15) |
| pg | 8.16.3 | npm (2026-08-15) |
| @google-cloud/pubsub | 4.11.0 | npm (2026-08-15) |
