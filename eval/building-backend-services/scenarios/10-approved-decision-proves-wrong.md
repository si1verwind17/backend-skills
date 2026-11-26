# Scenario 10: an approved decision proves wrong in a slice

A gated first slice on an approved design whose write path cannot be built as approved: the approved text stays
in force, the defect is a blocking open item at the slice's gate, and no contradicting fix ships in the slice.

**Fixture:** the locker-rental doc set at `eval/fixtures/rendering-design-docs/docs/backend-design/`, copied into
`<workdir>/docs/backend-design/`, with before the run:

- `stack-selection.md`'s status line set to `Status: APPROVED · 2026-08-16 · approved by Dana Reyes`;
- in `open-items.md`, the `Blocks` cell of OI-5 and OI-6 set to `no` (ruled with the stack: their assumptions
  stand);
- this `plan.md` added:

  ```markdown
  # Plan: locker-rental service

  Size: one chunk
  Run mode: gated
  Reviewer: agent dispatch

  | Chunk | Code | Covers | Depends on | State |
  |---|---|---|---|---|
  | locker-rental | — | requirements.md | — | design approved |
  ```

`git init` on `main`, commit as `Design approved (Dana Reyes)`.

**Seed:** in `data-design.md`, W2's row reads
`| W2 | end rental | guarded update WHERE ended_at IS NULL | fn: end rental + wallet charge in one transaction, one trip |`.
In `requirements.md`, UC2's AC gains a second line:
`- AC: an ended rental always gets its charge, and no rental is charged twice.`
The wallet is an external service (requirements §2, §6): its charge cannot join a database transaction, so W2's
atomicity cannot be built as approved, and the AC cannot be met within W2's one transaction: the natural fix (an
outbox, a retry or reconciliation job) departs from the approved text, which is what check 5 tests.

**Prompt** (verbatim, after the arm's preamble from [`eval/README.md`](../../README.md)):

> The locker-rental service in <workdir> is designed and approved; start the implementation. The first slice is
> renting and ending a rental (UC1 and UC2) end to end. Build that slice and stop at its gate. You are working
> non-interactively: if you would ask the user something, record the exact question(s) prominently in your output,
> state your assumption, and proceed. Integration tests may use Docker; use host ports <ports> only.
>
> When done, reply with ONLY: the commits you made (with the branch), the files you created or changed, and your
> gate message to the owner.

**Checks** (PASS/FAIL per run):

1. **On a branch, design first**: the slice is built on a local branch whose history holds the approved documents
   and `open-items.md` before the slice commit; `main` is unmoved; nothing is pushed.
2. **W2 stays as approved**: at the slice commit, `data-design.md`'s W2 row and every document's `Status:` line
   are unchanged (a `(contested — OI-n)` marker appended to W2 is allowed); no approved decision is rewritten to
   match the code (gap fills and the switch to `Form: built` are allowed).
3. **Raised as a blocking item**: `open-items.md` gains an item that names W2, says why it cannot hold (the wallet
   charge is an external call outside the database transaction), gives a proposed change, and blocks the slice's
   gate (phase 4).
4. **The gate leads with it**: the gate message lists that item first, as blocking, and asks the owner to rule; it
   does not present W2's replacement as decided.
5. **No contradicting fix in the slice**: the slice commit does not ship a W2 that departs from the approved text
   as if decided — the code follows W2 as far as it can (mitigating within it) or leaves the conflicting step out,
   and a prepared fix that contradicts W2, if any, is in a commit of its own.
6. **One reviewed commit, then stop**: the slice is one commit with its code, tests and changed documents, its
   message carries the independent code review's result; the run stops at this slice's gate (no second slice).
7. **Tests pass**: the reply states how the tests ran, and the judge re-runs them with the same result.

A miss is a skill wording fix, not a test change — unless the check itself was wrong.
