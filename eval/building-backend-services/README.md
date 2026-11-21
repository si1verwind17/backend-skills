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

- `de54434` (with `7702bb9`) — `check_docs.py` in the self-check and at every gate, sizing and modes moved to `run-modes.md`, fixed shapes for the start and stop sittings, ruling rows without invented reasons, the review on every change set, a branch for every run. Validates on scenarios 7, 8 and 9 with Sonnet 4.6, then all scenarios with Sonnet.
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
| 7 | 88f14b2 | skill (plugin, Sonnet 4.6) | 13/21 (3 runs) | features merged into chunks (2/3); the foundation over budget or missing companies; the size or the language unknown dropped from the start sitting; three modes instead of four once |
| 8 | 88f14b2 | skill (plugin, Sonnet 4.6) | 15/21 (3 runs) | no flip and write-downs filed right 3/3; no agent review of the change set (0/3); committed on main (2/3); closed open-item ids kept as provenance; invented reasons in ruling rows |
| 7 | 88f14b2 | skill (plugin) | 20/21 (3 runs) | split, foundation, later features, `CORE-` ids, recommended unknowns 3/3; one run named only its recommended mode |
| 8 | 88f14b2 | skill (plugin) | 21/21 (3 runs) | `Builds on:` cleaned and an agent review of the change set in every run; one run filed a redrawn diagram as needing no approval |
| 9 | 88f14b2 | skill (plugin) | 21/24 (3 runs) | two runs 8/8; one committed every draft and fix round, filed minor findings as rows, and asked the render question before the mode |
| 7 | — | control | 0/21 (3 runs) | a discovery note, no plan, no requirements document, no modes |
| 8 | — | control | 5/21 (3 runs) | rulings left beside "RESOLVED" rows, citations kept, re-approval asked; check 6 passed by every control |
| 9 | — | control | 6/24 (3 runs) | one combined design, no stack selection, no per-phase review, commits on main; checks 4 (as first worded) and 6 passed by every control |
