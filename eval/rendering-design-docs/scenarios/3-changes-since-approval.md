# Scenario 3: changes since approval, and the plan

Fixture: the [Scenario 1](1-locker-rental-tabs.md) doc set copied into
`<workdir>/docs/backend-design/`, with `stack-selection.md`'s status line set
to `Status: APPROVED · 2026-08-16 · approved by Dana Reyes` and this
`plan.md` added:

```markdown
# Plan: locker-rental service

Size: one chunk
Run mode: auto until feature done
Reviewer: agent dispatch

| Chunk | Code | Covers | Depends on | State |
|---|---|---|---|---|
| locker-rental | — | requirements.md | — | awaiting approval |
```

`git init`, commit as `Approved by Dana Reyes`. Then a second commit,
`Record the grace-period ruling (Dana Reyes, 2026-08-20)`: in
`requirements.md`, R2 gains ", counted from the end of the 3-minute grace
period (R4)" before its source, and a new rule follows R3 —
`- **R4** — Billing starts 3 minutes after the rental starts. *(Dana Reyes ruling, 2026-08-20)*` —
and the OI-1 row leaves `open-items.md`. Ground truth: all four documents are
APPROVED; only `requirements.md` has changes since its approval (one commit:
adds R4, changes R2).

**Prompt**: same as [Scenario 1](1-locker-rental-tabs.md), with "before
implementation starts" replaced by "at this gate".

**Checks** (PASS/FAIL per run):

1. **Marker on the changed tab only**: the Requirements tab carries the
   changes marker; the other three step tabs do not.
2. **Changes since approval**: the Requirements panel lists the approval it
   counts from (2026-08-14 and the first commit) and one line for the second
   commit — its date and subject, adds R4, changes R2, both linked; no other
   panel has the list.
3. **No judgment on the page**: the changes are listed, not sorted into
   "needs approval" or "needs none".
4. **Gate tab**: the Requirements tab opens on load (the earliest document
   with changes since approval).
5. **Plan tab**: present after the step tabs and before Context, styled like
   Context, with no number or badge, rendering the plan as written.
6. **Faithful content and hygiene**: R2 and R4 rendered exactly; sources
   untouched; the generated-for-humans notice present.
