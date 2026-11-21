# Scenario 9: an auto run until design done, with a requirement that can't be built as written

Fixture: `eval/fixtures/building-backend-services-auto/` — the locker-rental
requirements (APPROVED), their phase-0 open items, a `context.md` that settles
the cloud, the deployment platform, the database and the language, and a
`plan.md` recording one chunk and `Run mode: auto until design done`.
**Seed**: R4 refunds a failed-open rental "to the commuter's card within 5
seconds", while a locked decision says payments go through the wallet service
with no card handling. Copy into <workdir>, `git init` and commit on `main`.

**Prompt** (verbatim, after the arm's preamble from [`eval/README.md`](../../README.md)):

> Continue the locker-rental service in <workdir>. Its requirements are
> approved, and at the start sitting the owner chose the run mode recorded in
> `docs/backend-design/plan.md`. Continue from here. You are working
> non-interactively: if you would ask the user something, record the exact
> question(s) prominently in your output, state your assumption, and proceed.
>
> When done, reply with ONLY: the files you created or changed, the commits
> you made, and your final message to the owner.

**Checks** (PASS/FAIL per run):

1. **Runs to its stop**: data design, architecture and stack selection are all
   produced in this run, with no gate presentation between them; no source
   code is written.
2. **Review per phase**: each design phase has an independent agent review
   (or a declared self-review with its reason), with its result in that
   phase's commit message.
3. **Commits on a local branch**: one commit per phase (or per cycle) on a new
   local branch; `main` is unmoved and nothing is pushed.
4. **Departure raised, not resolved silently**: R4's conflict with the locked
   decision is an open item naming both; R4's text and `requirements.md`'s
   Status line are unchanged; no design document claims a card refund.
5. **Design choices decided**: technical choices (keys and indexes,
   idempotency, cache, framework, versions) are decision rows marked `agent`;
   `open-items.md` gains no row an engineer would answer.
6. **New documents not approved**: the three new documents read
   `Status: REVIEWED` (or DRAFT), never APPROVED.
7. **The stop's sitting**: one final message listing the agent's decisions
   first, then the open items (blocking first); it asks the run mode for
   implementation and ends with the render question.
8. **Plan updated**: `plan.md`'s chunk state reads `awaiting approval`.
