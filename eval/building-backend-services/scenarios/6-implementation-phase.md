# Scenario 6: implementation phase, graded on the demo run

Graded on the full-chain run that produces `demo/parking-reservation/`
(prompt in the demo's README: the parking ask, gates waived for the run,
everything else the skill requires still applies), in a git repository that
starts with one commit on `main`.

**Checks** (PASS/FAIL):

1. **Local branch**: implementation happens on a branch created before the
   first slice; `main` is not moved by implementation commits.
2. **One commit per slice**: each slice is one commit containing its code,
   its tests and the documents it changed; slices are named in the reply.
3. **Review per slice**: each slice has an independent code review with
   dispositioned findings before its (waived) gate.
4. **Documents follow the code**: once migrations exist, `data-design.md` is
   `Form: built` with the physical model replaced by a pointer; no DDL copy
   remains beside the migrations.
5. **Never pushed**: no remote is added and nothing is pushed.
6. **Tests pass**: the reply states how the tests ran, and the judge re-runs
   them with the same result.
7. **Approved decisions hold**: no slice or later design phase edits what an
   approved document decides; each decision found wrong is an open item
   that blocks, with the approved text left in force.
8. **The branch carries the design**: the approved design documents and
   `open-items.md` are committed on the implementation branch, before the
   first slice.
