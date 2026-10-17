# Scenario 2: greenfield phase-0 micro-run (context clean-skip)

Added 2026-10-03 to validate the clean-skip half of external-context
intake (`caf406d`). No repos, paths, docs or inventory tools are named.

**Prompt** (verbatim, after the arm's preamble from [`eval/README.md`](../../README.md)):

> We want a new backend service, in <workdir> (an empty directory): a
> community tool-library where neighbours list tools they own, others
> request to borrow them for a date range, the owner approves or declines,
> and both sides confirm hand-over and return. Late returns get flagged.
> Expect a few thousand users in one city to start. Run the build flow up
> to the end of phase 0 only, then stop at the phase-0 review gate. You
> are working non-interactively: if you would ask the user something,
> record the exact question(s) prominently in your output, state your
> assumption, and proceed.
>
> When done, reply with ONLY: the files you created and your phase-0 gate
> presentation.

**Checks** (PASS/FAIL per run):

1. **No file**: no `context.md` (or equivalent estate/context document) is
   created.
2. **One line at the gate**: the phase-0 gate presentation mentions the
   absent context exactly once, in one line ("no external context
   sources; proceeding on interview alone" or equivalent).
3. **Never again**: no other deliverable or question block nags about,
   asks for, or waits on missing estate context; nothing blocks on it.
4. **No fabrication**: requirements.md invents no estate facts (sibling
   services, existing contracts, house conventions); unknown environment
   items are recorded as pending decisions with a decider.
5. **Stops at the gate**: phase 0 is complete (requirements.md with
   stable ids) and no phase-1+ deliverable is produced.
6. **Header and open items**: requirements.md opens with the document header
   (`Status: REVIEWED` or `DRAFT`, never APPROVED; `Form: design`); every
   pending decision is a row in `open-items.md` with an owner.
