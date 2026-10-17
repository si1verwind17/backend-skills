# Scenario 4: a change on a designed service (triage)

Fixture: the locker-rental doc set at
`eval/fixtures/rendering-design-docs/docs/backend-design/`, copied into
<workdir>, with `stack-selection.md`'s status line set to `Status: APPROVED ·
2026-08-16 · approved by Dana Reyes` before the run; `git init` and commit it.
All four documents are approved; no code exists yet.

**Prompt** (verbatim, after the arm's preamble from [`eval/README.md`](../../README.md)):

> The locker-rental service in <workdir> is designed and approved. We want a
> change: if a customer ends a rental within a couple of minutes of the
> locker opening, refund them in full — people open the wrong locker by
> mistake. Take this change through the build flow. You are working
> non-interactively: if you would ask the user something, record the exact
> question(s) prominently in your output, state your assumption, and
> proceed.
>
> When done, reply with ONLY: the files you created or changed and your
> gate presentation.

**Checks** (PASS/FAIL per run):

1. **Triage first**: the change is classified by what it touches — a new
   behavior/rule, so it enters at phase 0 — and the phases it will run are
   named (phase 0, then phase 1 for the refund write path; architecture and
   stack untouched unless argued).
2. **Change file, local**: `docs/backend-design/changes/<date>-<slug>.md`
   exists with the ids it adds/touches and the phases it runs; its path is
   in `.git/info/exclude`, and `.gitignore` is unchanged.
3. **In place, ids stable**: `requirements.md` gains a new rule with the next
   free id (R4) — no renumbering, no changelog text — and its status
   returns to DRAFT or REVIEWED; untouched documents stay APPROVED.
4. **Open item for the number**: "a couple of minutes" becomes a row in
   `open-items.md` with an owner, and the rule cites its id.
5. **Stops at the phase-0 gate**: no data-design edit beyond what phase 0
   needs, no code, no commit on the main branch; the gate presentation
   names the next phase and asks whether to render the review page.
