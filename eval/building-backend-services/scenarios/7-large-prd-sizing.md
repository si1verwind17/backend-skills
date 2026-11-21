# Scenario 7: a large PRD — sizing, the feature map and the start sitting

Fixture: `eval/fixtures/building-backend-services-large-prd/` — an approved PRD
(`docs/prd.md`) for a co-working member platform: eight release-1 features, two
of them cross-cutting (accounts and roles, notifications), three release-2
features, and an environment with no language, cloud or deployment target
chosen. Its release-1 requirements cannot fit one requirements document. Copy
into <workdir>, `git init` and commit.

**Prompt** (verbatim, after the arm's preamble from [`eval/README.md`](../../README.md)):

> We want the backend for the product described in `docs/prd.md`, in
> <workdir>. Run the build flow up to the end of phase 0 only, then stop at
> its gate. You are working non-interactively: if you would ask the user
> something, record the exact question(s) prominently in your output, state
> your assumption, and proceed.
>
> When done, reply with ONLY: the files you created and your phase-0 gate
> presentation.

**Checks** (PASS/FAIL per run):

1. **Split by feature**: the gate states that the release-1 requirements do
   not fit one requirements document, and `plan.md` holds a feature map: a
   foundation chunk first, then one chunk per remaining release-1 feature in
   an order that respects their dependencies.
2. **Foundation is the cross-cutting part**: the foundation chunk covers
   accounts, companies and roles and the notification delivery every
   feature uses; no release-1 feature that only one area needs (desk
   booking, rooms, visitors, events, help desk) is folded into it.
3. **Later features listed, not designed**: F9–F11 appear in `plan.md` as
   `later`; no requirement, entity or rule for parking, catering or smart
   locks is written anywhere.
4. **Phase 0 writes the foundation only**: `docs/backend-design/requirements.md`
   holds the shared part, with ids prefixed `CORE-`, and stays near its
   ~2,500-word budget; no `<area>/requirements.md` exists yet.
5. **Hard-to-reverse unknowns asked**: the gate asks the deployment target and
   the language/stack constraint (the PRD leaves both open), each with a
   recommendation, before any auto run.
6. **Mode question fits the size**: all four modes are offered, one
   recommended with one line of why, plus one short line of when an auto run
   would still stop; `plan.md` reads `Run mode: gated`.
7. **Stops at the gate**: no data design, architecture, stack selection or
   code; the gate ends with the render question.
