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

## Pending validation

- `6abb917` — a slice never changes an approved decision (not to match the code, not as a change for the re-approval to cover); the branch's first commit holds the approved design documents; under a waiver a blocking item passes the gate with the approved text in force. Validates on scenario 6 at the next demo run.

## Latest results

Each scenario's latest run, Sonnet, graded by an independent judge on Opus. `Skill@` is the commit whose skill content
was evaluated.

| Scenario | Skill@ | Arm | Result | Notes |
|---|---|---|---|---|
| 1 | fcc1288 | skill (plugin) | 10/10 (1 run) | the author's own pass found seeds A and B; every blocking fix re-verified until SUFFICIENT (two rounds); reviewer given absolute paths; the brief listed findings only, not every pass item |
| 2 | 9a8e14b | skill | 17/18 (3 runs) | clean skip held 3/3; one provisional figure without an open-item row |
| 3 | 3d078c5 | skill | 15/16 (2 runs) | read plan first, full import under the threshold; comment intent beside a data-design row once |
| 3 | — | control | 12/24 (3 runs) | caught the defect without fixing it, but no header, no `file:line`, questions scattered, DDL reconstructed |
| 4 | 8772816 | skill (plugin) | 5/5 (1 run) | REVIEWED keeps the last approval; reviewer suggestions beyond the request queued as open items; the reviewer got the author's findings first |
| 5 | e8db71d | skill (plugin) | 10/10 (2 runs) | plan row stays first; every blocking fix re-verified until SUFFICIENT; no decision row on README/config alone in one run, one borderline row in the other; residual: plan written after reading, an edit after a SUFFICIENT ruling not sent back, the author's pass under-reported the README item (the reviewer caught it) |
| 6 | 9bdae75 | skill (plugin) | 6/6 (1 run, checks 1–6; 7 and 8 added after it) | 291 tests re-run green from a fresh clone; every blocking fix re-verified until SUFFICIENT; review result in each slice commit; render offered; missed: approved decisions (W1, an API error code, SD10) rewritten in place during slices and re-approved under the waiver instead of an open item, requirements.md left uncommitted on the branch |
