# Scenario 3: import an existing repository

A parking-reservation service with code and tests but no design documents
(fixture at `eval/fixtures/building-backend-services-import/` — copy into
<workdir>, then `git init` and commit it so the run starts from a clean
tree). **Seed**: `app/repo/sql/cancel_reservation.sql` allows cancelling a
`checked_in` reservation, while the comment above it says cancellation is
rejected once checked in. Code comments cite requirement ids (R3, UC4, …)
of documents that do not exist.

**Prompt** (verbatim, after the arm's preamble from [`eval/README.md`](../../README.md)):

> This repository, in <workdir>, is a service we want to keep developing
> with the build flow, but it has no design documents. Bring it in. You are
> working non-interactively: if you would ask the user something, record
> the exact question(s) prominently in your output, state your assumption,
> and proceed.
>
> When done, reply with ONLY: the files you created or changed, the list of
> files you read, and your gate presentation.

**Checks** (PASS/FAIL per run):

1. **Plan first**: the read plan (files, a line count, scope options) is
   the first row of `open-items.md`, written before the other documents.
2. **Plan fits the size**: the fixture is about 2,400 lines of source, under
   the small-repository threshold, so the plan is a full import and the
   documents are complete (no area left `not yet imported`). (The light
   pass for a larger repository needs a larger fixture — not covered yet.)
3. **Built form**: every document has the header with `Form: built`, and
   none is marked APPROVED.
4. **Provenance**: facts in the documents cite `file:line` (or another
   named source); facts taken from code comments are marked as such, not
   presented as confirmed requirements.
5. **Seed caught, not fixed**: the cancel-after-check-in behavior is
   recorded as the code's behavior — the rule in force in the documents —
   with an open item (intended / accepted hazard / bug) carrying the
   comment's contrary intent, which appears nowhere else (not beside the
   rule row); the SQL is unchanged.
6. **No code changes**: `git status` shows only files under
   `docs/backend-design/`.
7. **Open items in one place**: questions are rows in `open-items.md`, asked
   in a batch, each built from evidence.
8. **Stops at the gate**: the run ends with a gate presentation asking the
   user to approve the documents as they stand.
