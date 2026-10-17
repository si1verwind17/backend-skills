# Scenario 1: live-support ticketing platform (GCP)

**Prompt** (verbatim, after the arm's preamble from [`eval/README.md`](../../README.md)):

> Design the architecture for a live-support ticketing platform, in
> <workdir>. The company runs on Google Cloud. The team's existing
> services are Kotlin/JVM. Keep it practical — mid-sized system.
> Requirements:
>
> - Customers open support tickets from a web/mobile app; agents work them
>   from an operator console. Several agents sometimes act on the same
>   ticket at once (reassign, reply, change status) and today they
>   overwrite each other.
> - Ticket lifecycle: open → assigned → resolved → closed (reopen from
>   resolved). When a ticket closes, billing and the CSAT-survey system
>   must both react. Finance mentioned they "might want ticket data in the
>   warehouse next year."
> - Agent console reads the agent's profile/permissions on every request;
>   permissions change rarely (admin action).
> - The mobile app and console need APIs. An internal ML team wants a
>   high-volume feed of ticket text for real-time triage suggestions.
> - Nobody has decided whether this is one service or several; there is an
>   existing order-management microservice estate at the company.
> - Ops wants low idle cost where possible.
>
> Produce whatever design artifacts you think an engineer should review
> and a next agent could implement from. You are working non-interactively:
> if you would ask the user something, record the exact question(s)
> prominently in your output, state your assumption, and proceed.

**Checks** (PASS/FAIL per run, both scenarios; "S1:" / "S2:" mark what a check expects in each):

1. **Open questions surfaced**: the undecided service split is a row in
   `open-items.md` with a stated assumption (not silently resolved); other
   assumptions are rows too — no open-questions section inside
   `architecture-design.md` (tightened 2026-10-17).
2. **Deliverable contract**: `architecture-design.md` opening with the
   document header, decisions as `AD` rows, interactions with `I` ids and
   events with `EV` ids (added 2026-10-17), with a Mermaid
   component diagram, at least two Mermaid sequence diagrams for key flows,
   a per-service decisions table (stateless/stateful, cache + staleness
   bound, deployment target), an API inventory, an event catalog, and
   scaling notes. `openapi/` skeletons only if an early-contract need is
   argued — producing none is correct here.
3. **State & ownership**: services stateless by default with state in the
   DB; the concurrent-mutation entity (ticket / delivery assignment) is
   handled with a per-entity single-writer mechanism (sharded actor or
   equivalent serialization) or an explicitly argued alternative; no
   mutable in-process state elsewhere; no two services share a database or
   tables.
4. **Caching**: the hot stable read (agent permissions / restaurant menus)
   is cached with an explicit staleness bound (TTL or invalidation); no
   caching of volatile data (live status, courier position).
5. **Sync vs async semantics**: every interaction classified; front-facing
   APIs are REST; gRPC (or equivalent) only for justified internal
   high-volume calls (ML feed / dispatch→order); reactions to state
   changes (billing/CSAT; restaurant/customer notify) are queue-driven
   events, not HTTP call chains.
6. **Event catalog completeness**: every lifecycle transition of the core
   entity appears as a published event — including ones with no current
   consumer (warehouse / partner analytics) — with meaningful payloads, a
   PII note, `<domain>-<event>-vN`-style naming, and a versioning approach
   (new topic for breaking change or an argued alternative).
7. **Cloud-fit recommendations**: concrete managed services recommended
   from the customer's cloud with reasoning (S1: e.g. Pub/Sub, Cloud
   Run/GKE, Memorystore; S2: e.g. SNS/SQS/EventBridge/Kinesis, Lambda/
   Fargate/EKS, ElastiCache); push vs pull consumption matched to each
   consumer's deployment target.
8. **Deployment pairing**: serverless vs k8s decided per service with the
   runtime cold-start constraint addressed explicitly (S1: JVM on
   serverless flagged/mitigated; S2: Go noted as serverless-friendly); the
   24/7 aggregation/settlement consumer placed on the long-running
   runtime with pull consumption.

9. **Mermaid portability** (added 2026-10-03 for `e1a55d8`): no `;`
   inside any sequence-diagram message or note text (a statement separator
   in several renderers); every Mermaid block is syntactically valid.
