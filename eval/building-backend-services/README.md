# Evaluations: building-backend-services

Orchestration: the per-phase cycle and its gates, the shared document format, open items, changes after the build, importing an existing repository, and the implementation phase.

## Scenarios

| Scenario | What it tests |
|---|---|
| [1](scenarios/1-resume-mid-chain.md) | resume with four planted inconsistencies across approved and draft documents |
| [2](scenarios/2-greenfield-phase-0.md) | greenfield phase 0 only; no context sources, so no `context.md` |
| [3](scenarios/3-import-small-repo.md) | import a 2,400-line repository with a planted defect (full import) |
| [4](scenarios/4-change-triage.md) | a change on an approved design: triage, local change file, in-place edits |
| [5](scenarios/5-import-large-repo.md) | import a 6,261-line repository: the light pass, a second defect it must not read |
| [6](scenarios/6-implementation-phase.md) | the implementation phase, graded on the demo run: branch, slice commits, no push |
| [7](scenarios/7-large-prd-sizing.md) | a PRD too large for one requirements document: feature map, foundation chunk, later features listed, the start sitting |
| [8](scenarios/8-rulings-on-approved-docs.md) | rulings recorded in approved documents: no flip to DRAFT, write-downs need no approval, consequences kept apart |
| [9](scenarios/9-auto-until-design-done.md) | an auto run until design done: no intermediate gates, agent decisions, a requirement that can't be built as written |

## Pending validation

- `509fbe0` — `check_docs.py --gate` prints the shape to present (the start sitting's or the stop's sitting's template, or the phase gate's parts) and flags a document left in DRAFT at a gate; writing a ruling down runs the whole cycle; the review's result in a commit message spelled out; the path building the assumption in force marked contested; the stop sets `awaiting approval`; stack choices are `agent` rows, not open items. Validates on scenarios 7, 8 and 9 with Sonnet 4.6, then all scenarios with Sonnet.
- `de54434` (with `7702bb9`) — `check_docs.py` in the self-check and at every gate, sizing and modes moved to `run-modes.md`, fixed shapes for the start and stop sittings, ruling rows without invented reasons, the review on every change set, a branch for every run. Sonnet 4.6 rerun below (8: 15 → 20/21; 7 unchanged at 13/21; 9 at 7/24); all scenarios with Sonnet still to run.
- `49c9f39` — fixes from the second round: every offered mode named, one chunk always gets three; a run mode written into a new `plan.md` is not a choice; one commit per phase cycle; the stop's sitting recommends the implementation mode; scenario 4 check 3 and scenario 9 checks 4 and 5 tightened. Validates on scenarios 2, 4 and 9 (skill arm), then 1 and 6 at the next demo run.
- `6abb917` — a slice never changes an approved decision (not to match the code, not as a change for the re-approval to cover); the branch's first commit holds the approved design documents; under a waiver a blocking item passes the gate with the approved text in force. Validates on scenario 6 at the next demo run.

## Latest results

Each scenario's latest run, Sonnet, graded by an independent judge on Opus. `Skill@` is the commit whose skill content
was evaluated.

| Scenario | Skill@ | Arm | Result | Notes |
|---|---|---|---|---|
| 1 | fcc1288 | skill (plugin) | 10/10 (1 run) | the author's own pass found seeds A and B; every blocking fix re-verified until SUFFICIENT (two rounds); reviewer given absolute paths; the brief listed findings only, not every pass item |
| 2 | 88f14b2 | skill (plugin) | 25/27 (3 runs) | sized one chunk, unknowns recommended, plan.md written 3/3; one run offered two modes, not three; one run named the absent context twice |
| 3 | 3d078c5 | skill | 15/16 (2 runs) | read plan first, full import under the threshold; comment intent beside a data-design row once |
| 3 | — | control | 12/24 (3 runs) | caught the defect without fixing it, but no header, no `file:line`, questions scattered, DDL reconstructed |
| 4 | 88f14b2 | skill (plugin) | 17/18 (3 runs) | Status line kept, R4 listed as awaiting approval, local branch 3/3; one run wrote `Run mode: gated` into its new plan.md and never asked; one run added an inferred rule (check since tightened) |
| 5 | e8db71d | skill (plugin) | 10/10 (2 runs) | plan row stays first; every blocking fix re-verified until SUFFICIENT; no decision row on README/config alone in one run, one borderline row in the other; residual: plan written after reading, an edit after a SUFFICIENT ruling not sent back, the author's pass under-reported the README item (the reviewer caught it) |
| 6 | 9bdae75 | skill (plugin) | 6/6 (1 run, checks 1–6; 7 and 8 added after it) | 291 tests re-run green from a fresh clone; every blocking fix re-verified until SUFFICIENT; review result in each slice commit; render offered; missed: approved decisions (W1, an API error code, SD10) rewritten in place during slices and re-approved under the waiver instead of an open item, requirements.md left uncommitted on the branch |
| 2 | 88f14b2 | skill (plugin, Sonnet 4.6) | 23/27 (3 runs) | one chunk and three modes 3/3; the stack constraint answered "none" (2/3); review findings queued in the gate instead of open items (2/3) |
| 7 | de54434 | skill (plugin, Sonnet 4.6) | 13/21 (3 runs; 13/21 at 88f14b2) | map, foundation, later features and budget 3/3, `check_docs.py` clean; two runs presented a phase gate in place of the start sitting (no size line, unknowns shown as assumptions, modes missing or three); one merged two features into a chunk |
| 8 | de54434 | skill (plugin, Sonnet 4.6) | 20/21 (3 runs; 15/21 at 88f14b2) | rulings worded as given, citations re-pointed, Status and `Builds on:` right 3/3; one committed on main; unscored: no agent review and no `check_docs.py` run (0/3), the write-down treated as outside the cycle, consequences (mTLS termination on Cloud Run, certificates) never raised |
| 9 | de54434 | skill (plugin, Sonnet 4.6) | 7/24 (3 runs) | one run ended mid data design, saying it waited for a reviewer it never sent; framework, versions, instances, auth filed as open items (the stack-selection checklist and its reviewer asked for them); refund path never marked contested; review result missing from later commits; plan state never `awaiting approval`; one stop's sitting lost its shape after two compactions |
| 7 | 88f14b2 | skill (plugin) | 20/21 (3 runs) | split, foundation, later features, `CORE-` ids, recommended unknowns 3/3; one run named only its recommended mode |
| 8 | 88f14b2 | skill (plugin) | 21/21 (3 runs) | `Builds on:` cleaned and an agent review of the change set in every run; one run filed a redrawn diagram as needing no approval |
| 9 | 88f14b2 | skill (plugin) | 21/24 (3 runs) | two runs 8/8; one committed every draft and fix round, filed minor findings as rows, and asked the render question before the mode |
| 7 | — | control | 0/21 (3 runs) | a discovery note, no plan, no requirements document, no modes |
| 8 | — | control | 5/21 (3 runs) | rulings left beside "RESOLVED" rows, citations kept, re-approval asked; check 6 passed by every control |
| 9 | — | control | 6/24 (3 runs) | one combined design, no stack selection, no per-phase review, commits on main; checks 4 (as first worded) and 6 passed by every control |
