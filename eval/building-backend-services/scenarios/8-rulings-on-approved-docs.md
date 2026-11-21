# Scenario 8: rulings recorded in approved documents (change approval)

Fixture: the locker-rental doc set at
`eval/fixtures/rendering-design-docs/docs/backend-design/`, copied into
<workdir>, then edited before the run:

- `stack-selection.md`: status line `Status: APPROVED · 2026-08-16 · approved by Dana Reyes`;
- `requirements.md`: R2 reads `**R2** — Charge rounds up to the next full hour, counted from the end of the grace period (OI-1). *(stakeholder)*`;
- `architecture-design.md`: the vendor edge in the component diagram reads `VENDOR[Vendor hardware API] -->|callback, auth per OI-4| API`;
- `data-design.md`: `Builds on: requirements.md (APPROVED 2026-08-14) — UC1–UC2, R1–R3, OI-1`.

`git init` and commit on `main`. All four documents are approved; no code exists.

**Prompt** (verbatim, after the arm's preamble from [`eval/README.md`](../../README.md)):

> Dana Reyes ruled today, 2026-08-20, on two open items for the locker-rental
> service in <workdir>: OI-1 — the grace period is 3 minutes; OI-4 — vendor
> callbacks use mutual TLS instead of an HMAC header. Record the rulings in
> the design. You are working non-interactively: if you would ask the user
> something, record the exact question(s) prominently in your output, state
> your assumption, and proceed.
>
> When done, reply with ONLY: the files you changed and your gate
> presentation.

**Checks** (PASS/FAIL per run):

1. **Rulings recorded**: each ruling is written in the document it belongs
   to, attributed to Dana Reyes's ruling of 2026-08-20 (a decision row marked
   `user`, or a rule sourced to the ruling); the OI-1 and OI-4 rows are gone
   from `open-items.md`.
2. **Citations re-pointed**: no document cites OI-1 or OI-4 afterwards.
3. **No flip**: every document's Status line is byte-identical to the
   fixture's.
4. **Builds on cleaned**: `data-design.md`'s `Builds on:` no longer carries a
   status, a date or an open-item id.
5. **No approval asked for write-downs**: the gate lists the recorded rulings,
   the re-pointed citations and the cleaned header as changes that need no
   approval, and does not ask the user to approve or re-approve any document
   for them.
6. **Consequences kept apart**: anything beyond the rulings' own words — such
   as where mutual TLS terminates in front of Cloud Run, or how certificates
   are issued and rotated — is listed as awaiting approval or raised as an
   open item, never filed with the write-downs.
7. **Local branch**: the work is committed on a new local branch; `main` is
   unmoved and nothing is pushed.
