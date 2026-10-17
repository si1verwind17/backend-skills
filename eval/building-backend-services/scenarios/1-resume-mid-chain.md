# Scenario 1: resume mid-chain with seeded inconsistencies

A fixture design set for a gift-card service (fixture committed at
`eval/fixtures/building-backend-services/docs/backend-design/` — copy into <workdir> before a run)
with: data design + architecture marked APPROVED, stack
selection marked DRAFT, phase 4 not started — and four planted defects:

- **Seed A**: `expires_at` exists in the ER diagram and DDL but is missing
  from `data-dictionary.yaml`.
- **Seed B**: event `gift-card-redeemed-v1` payload contains
  `redeemed_channel`, which exists nowhere in the data model.
- **Seed C**: forked truth — architecture's decisions table places
  `gift-card-api` on Cloud Run (serverless, spiky/low idle), while the
  stack draft's recommendation says "tuned JVM on GKE" (also contradicting
  its own §1 premise).
- **Seed D**: `zio-http | latest 3.x` unpinned with no source in the
  finalized-versions table.

**Prompt** (verbatim, after the arm's preamble from [`eval/README.md`](../../README.md)):

> Continue building the gift-card service, in <workdir>. The design work so
> far is under `docs/backend-design/`: the data design and the architecture
> design are user-APPROVED; the stack selection is a DRAFT awaiting review;
> implementation has not started. Continue the work from here. You are
> working non-interactively: if you would ask the user something, record
> the exact question(s) prominently in your output, state your assumption,
> and proceed.
>
> When done, reply with ONLY: the file tree of files you changed/created
> and a one-line summary of what you did.

**Checks** (PASS/FAIL per run):

1. **Consistency pass first**: an explicit cross-document consistency check
   is performed and reported before any new phase work — not incidental
   spot-fixes.
2. **Seed A caught** and the dictionary updated to match DDL/ER.
3. **Seed B caught**: `redeemed_channel` flagged and resolved consistently
   (added to the data model with rationale, or removed/derived with note),
   or — since it changes an approved event contract — raised as an open
   item with the field marked open on both sides (event catalog and data
   model) until the user rules.
4. **Seed C caught**: the Cloud Run/GKE fork identified as a contradiction
   with the approved architecture, resolved consistently in BOTH documents,
   with the resolution surfaced for user review (it touches an approved
   decision).
5. **Seed D caught**: the unpinned `latest 3.x` replaced with an exact
   researched version (or explicitly named as unverifiable with reason).
6. **One truth**: every fix is applied in the upstream document too — no
   document pair left disagreeing after the run.
7. **Correct resume**: approved phase 1–2 documents are not rewritten
   wholesale; no implementation code is started; the run ends by presenting
   the corrected stack-selection plus a consistency report at the phase-3
   review gate.
8. **No re-asking**: questions already answered in the docs (expiry period,
   code uniqueness, service split) are not re-asked; genuinely new
   questions (which deployment target governs; idle-cost tolerance) are
   recorded.
9. **One home for open questions**: the new questions are recorded in
   `docs/backend-design/open-items.md` with owner, blocking flag and
   decide-by phase; no new open-question section is added inside a phase
   document.
10. **Render offered, not run**: the gate presentation ends by asking whether
   to render and open the review page (recommending yes before
   implementation); no `design-review.html` is produced without a yes.
