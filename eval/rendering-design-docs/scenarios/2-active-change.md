# Scenario 2: an active change, two steps so far

Fixture: `eval/fixtures/rendering-design-docs-change/docs/backend-design/` —
`requirements.md` (REVIEWED, with new R4), `data-design.md` (APPROVED),
`open-items.md` (OI-1, OI-3, OI-7, OI-8), and
`changes/2026-10-17-add-refunds.md`; no architecture, stack or context
documents. Ground truth: OI-7 blocks phase 0; OI-8 is due at phase 1;
OI-1 and OI-3 at phase 4; the change touches R4, UC2 and W2.

**Prompt**: same as [Scenario 1](1-locker-rental-tabs.md), with "for the locker-rental service"
kept and "before implementation starts" replaced by "at this gate".

**Checks** (PASS/FAIL per run):

1. **Tabs**: Change first, then exactly two step tabs (Requirements
   REVIEWED, Data design APPROVED) — no architecture, stack, context or
   implementation tab.
2. **Gate tab**: the Requirements tab opens on load (its document is not
   approved).
3. **Change tab**: the change file rendered; R4, UC2 and W2 link to their
   definitions; the Requirements and Data design tabs carry a "touched by
   the change" marker.
4. **Decisions where they belong**: OI-7 at the top of the Requirements tab
   and in the banner; OI-8 on the Data design tab; OI-1 and OI-3 in the
   gate tab's "later steps" list.
5. **Faithful content and hygiene**: R4 rendered exactly with its OI-7
   link; sources untouched; the generated-for-humans notice present.
