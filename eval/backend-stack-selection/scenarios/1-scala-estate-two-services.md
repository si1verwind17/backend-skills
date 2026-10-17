# Scenario 1: two new services on an existing Scala estate (GCP)

**Prompt** (verbatim, after the arm's preamble from [`eval/README.md`](../../README.md)):

> Select the tech stack for two new backend services, in <workdir>. Context:
> the company runs on Google Cloud; the backend team (6 engineers, all
> Scala) operates an estate of Scala 3 + ZIO services on GKE. The
> architecture phase already decided the deployment targets below — do not
> revisit them.
>
> Service A — **settlement-reconciliation**: user-facing finance dashboards
> plus heavy domain rules (matching, dispute windows, partial refunds).
> Mission-critical. Architecture: always-on Kubernetes, Postgres, publishes
> and consumes Pub/Sub events.
>
> Service B — **carrier-webhook-forwarder**: receives delivery-carrier
> webhooks (HMAC signature verification), transforms the payload, publishes
> to Pub/Sub. Spiky traffic, near-zero idle, no domain logic beyond mapping.
> Architecture: serverless (Cloud Run), push consumption.
>
> Produce whatever stack-selection artifacts an engineer should review and a
> next agent could implement from. You are working non-interactively: if you
> would ask the user something, record the exact question(s) prominently in
> your output, state your assumption, and proceed. You have web access — use
> it where it strengthens the work.

**Checks** (PASS/FAIL per run):

1. **Existing stack first (Service A)**: the recommendation for A keeps the
   team's existing stack (or presents it as the primary recommendation),
   with rationale tied to team skills and the always-on target — no
   gratuitous language shopping.
2. **Shape mismatch caught (Service B)**: B is NOT handed the heavyweight
   default by momentum — a lighter serverless-fit option is proposed (or a
   native-image variant of the existing stack), with the concrete issue
   named (JVM cold start on scale-to-zero / stack weight vs a thin
   forwarder).
3. **Elicitation**: questions the upstream docs can't answer are rows in
   `open-items.md` (current language/framework versions, licensing/budget
   stance, org standards) — no elicitation section in the document
   (tightened 2026-10-17); already-decided items (deployment targets) are
   NOT re-asked.
4. **Deliverable contract**: a stack-selection doc opening with the document
   header, decisions as `SD` rows (added 2026-10-17), with an
   existing-stack assessment, a candidate matrix for B (criteria including
   deployment-target fit/cold start, ecosystem check, team familiarity,
   cost, runtime safety), and a recommendation with rationale per service.
5. **Research, not memory**: perishable claims (cold-start behavior,
   native-image viability, library maturity) carry decision-time research
   citations (URLs/sources), not bare assertions.
6. **Ecosystem check**: required integrations enumerated per service
   (Pub/Sub SDK, Postgres driver, HMAC/crypto for B) and verified mature
   for the recommended stack(s).
7. **Mission-critical comparison (Service A)**: an explicit pros/cons
   comparison of the existing stack vs at least one alternative for A
   (because A is mission-critical), ending in a clear recommendation.
8. **Finalized versions**: exact pinned versions for every selected
   component (language, framework, key libraries) for both services.
