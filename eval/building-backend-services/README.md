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

- `d106e0c` — an absent consistency-pass item is left out; re-verification always by a fresh foreground reviewer, never a timer, sleep or monitor loop; a convention `context.md` records settles a start-sitting unknown; `check_docs.py` flags unprefixed ids in a split set. Validated with Sonnet on 2, 7 and 9 (below): fresh foreground re-verification in 9 of 9 runs on 7 and 9, the gate as the final reply everywhere; the one check 5 miss came from `backend-architecture` asking the user whether to publish events, against `documents.md`; the owner ruled it an `agent` decision, fixed in `backend-architecture` at `a9c600b`.
- `a7926d9` — fixes from the five-model round: `check_docs.py` flags chunk order against `Depends on` and a document committed in DRAFT; re-verification by a fresh foreground reviewer, a verdict only what a reviewer returned, no background timer; a consistency-pass item that every rule can be built as written within the locked decisions; each change grouped on its own; the reviewer reads the diff since approval itself; examples no longer hold eval data. Validated with Sonnet on 2, 4, 7, 8, 9 and rendering 3 (below); scenarios 1, 3, 5 and 6 not rerun.
- `49c9f39` — fixes from the second round: every offered mode named, one chunk always gets three; a run mode written into a new `plan.md` is not a choice; one commit per phase cycle; the stop's sitting recommends the implementation mode; scenario 4 check 3 and scenario 9 checks 4 and 5 tightened. Validates on scenarios 2, 4 and 9 (skill arm), then 1 and 6 at the next demo run.
- `6abb917` — a slice never changes an approved decision (not to match the code, not as a change for the re-approval to cover); the branch's first commit holds the approved design documents; under a waiver a blocking item passes the gate with the approved text in force. Validates on scenario 6 at the next demo run.

## Latest results

### Models at `509fbe0`

Scenarios 7, 8, 9 and rendering 3, three runs each per model, headless with the plugin loaded; graded by an
independent judge on Opus 5.5 (Fable 5.2's runs by a judge on Fable 5.2).

| Model | 7 | 8 | 9 | Rendering 3 |
|---|---|---|---|---|
| Fable 5.2 | 20/21 | 21/21 | 24/24 | 18/18 |
| Opus 5 | 19/21 | 19/21 | 21/24 | 18/18 |
| Opus 4.8 | 21/21 | 18/21 | 21/24 | 16/18 |
| Opus 4.6 | 18/21 | 21/21 | 19/24 | 16/18 |
| Sonnet 4.6 | 17/21 (13 at `de54434`) | 19/21 (20) | 15/24 (7) | 15/18 (17) |

What the round showed, fixed in `a7926d9`: chunk order against the input's cross-references missed by four models;
in four of six Opus runs, scenario 9's unbuildable R4 was silently redesigned as a wallet refund, and every reviewer
missed it; Opus 5 and Fable runs waited on reviewers with background timers, so their final reply was not the gate;
a Sonnet 4.6 run wrote a reviewer verdict the reviewer never returned; the start sitting's shape had no open-items
line; orchestrators told the reviewer to run `git diff` though it had no shell. Caveats: two skill examples held
eval data (`documents.md`'s `Builds on:` example was scenario 8's seed, the rendering skill's changes line was
scenario 3's answer) and runs copied them; in about ten runs the reviewer read the rules from the live repository
rather than the frozen copy (the run folder's path named it); the first batch's result files were rebuilt from
their transcripts.

### Per scenario

Each scenario's latest run, Sonnet, graded by an independent judge on Opus. `Skill@` is the commit whose skill content
was evaluated.

| Scenario | Skill@ | Arm | Result | Notes |
|---|---|---|---|---|
| 1 | fcc1288 | skill (plugin) | 10/10 (1 run) | the author's own pass found seeds A and B; every blocking fix re-verified until SUFFICIENT (two rounds); reviewer given absolute paths; the brief listed findings only, not every pass item |
| 2 | d106e0c | skill (plugin, Sonnet 5.5) | 26/27 (3 runs; 26/27 at a7926d9, 25/27 at 88f14b2) | the absent context named once 3/3 (the a7926d9 miss); one run asked for "estate standards" in a greenfield project; unscored: that run waited on its reviewers with polling loops, the gates do not list the consistency pass item by item |
| 3 | 3d078c5 | skill | 15/16 (2 runs) | read plan first, full import under the threshold; comment intent beside a data-design row once |
| 3 | — | control | 12/24 (3 runs) | caught the defect without fixing it, but no header, no `file:line`, questions scattered, DDL reconstructed |
| 4 | a7926d9 | skill (plugin, Sonnet 5.5) | 18/18 (3 runs; 17/18 at 88f14b2) | Status kept, R4 awaiting approval, the out-of-scope line contested, run mode asked 3/3; unscored: one commit before re-verification (amended), edits after a SUFFICIENT ruling not sent back, stale change files |
| 5 | e8db71d | skill (plugin) | 10/10 (2 runs) | plan row stays first; every blocking fix re-verified until SUFFICIENT; no decision row on README/config alone in one run, one borderline row in the other; residual: plan written after reading, an edit after a SUFFICIENT ruling not sent back, the author's pass under-reported the README item (the reviewer caught it) |
| 6 | 9bdae75 | skill (plugin) | 6/6 (1 run, checks 1–6; 7 and 8 added after it) | 291 tests re-run green from a fresh clone; every blocking fix re-verified until SUFFICIENT; review result in each slice commit; render offered; missed: approved decisions (W1, an API error code, SD10) rewritten in place during slices and re-approved under the waiver instead of an open item, requirements.md left uncommitted on the branch |
| 2 | 88f14b2 | skill (plugin, Sonnet 4.6) | 23/27 (3 runs) | one chunk and three modes 3/3; the stack constraint answered "none" (2/3); review findings queued in the gate instead of open items (2/3) |

| 7 | d106e0c | skill (plugin, Sonnet 5.5) | 21/21 (3 runs; 21/21 at a7926d9) | start sitting, chunk order, prefixed ids, fresh foreground re-verification, no timers, the gate as the final reply 3/3; unscored: suffixed ids (`CORE-R7a`) in one run, non-blocking items listed by id only |
| 8 | a7926d9 | skill (plugin, Sonnet 5.5) | 21/21 (3 runs; 21/21 at 88f14b2, with the leaked example) | review of the change set, `check_docs.py`, consequences raised 3/3; the reviewer read the diff itself 3/3; unscored: a sequence diagram left disagreeing with the redrawn component diagram (3/3) |
| 9 | d106e0c | skill (plugin, Sonnet 5.5) | 23/24 (3 runs; 22/24 at a7926d9, 21/24 at 88f14b2) | R4 raised and contested, REVIEWED commits, fresh foreground re-verification, no timers, the stop's sitting as the final reply 3/3; one run asked whether to publish events, as `backend-architecture` then told it to (since ruled an `agent` decision) |
| 7 | — | control | 0/21 (3 runs) | a discovery note, no plan, no requirements document, no modes |
| 8 | — | control | 5/21 (3 runs) | rulings left beside "RESOLVED" rows, citations kept, re-approval asked; check 6 passed by every control |
| 9 | — | control | 6/24 (3 runs) | one combined design, no stack selection, no per-phase review, commits on main; checks 4 (as first worded) and 6 passed by every control |
