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

- `49c9f39` — fixes from the second round. Validated on 1, 2, 4 and 9 (below); scenario 6 at the next demo run.
- `6abb917` — a slice never changes an approved decision (not to match the code, not as a change for the re-approval to cover); the branch's first commit holds the approved design documents; under a waiver a blocking item passes the gate with the approved text in force. Validates on scenario 6 at the next demo run.

## Latest results

### Release regression, Sonnet 5.5 at `7a5898b` / `34a7495`

Every scenario the branch's changes touch (scenario 6 aside, graded on the demo run), three runs each, the plugin
loaded, each run in a sandbox with a private `/tmp`, the live repository hidden and hooks off; graded by an
independent judge on Opus 5.5. Building 4, architecture 1, stack selection 1 and requirements 1 ran at `7a5898b`;
the rest at `34a7495`, after data design 1 showed a regression (an id's scope decided as an `agent` row, 23/27).

| Skill | Scenario | Result | Before |
|---|---|---|---|
| building-backend-services | 1 / 2 / 3 / 4 / 5 | 26/30 · 25/27 · 22/24 · 18/18 · 13/15 | 10/10 · 26/27 · 15/16 · 18/18 · 10/10 |
| building-backend-services | 7 / 8 / 9 | 21/21 · 21/21 · 23/24 | 21/21 · 21/21 · 23/24 |
| backend-design-by-data | 1 | 25/27 (23/27 at 7a5898b) | 18/18 |
| backend-architecture | 1 | 25/27 | 26/27 |
| backend-stack-selection | 1 | 24/24 | 8/8 |
| writing-business-requirements | 1 / 2 | 25/27 · 25/27 | 9/9 · 26/27 |
| rendering-design-docs | 1 / 2 / 3 | 27/27 · 15/15 · 18/18 | 9/9 · 5/5 · 18/18 |

Three misses came from the branch's own changes and are fixed in `e9a135d`: the printed gate parts left out the
consistency-pass list (scenario 1, 3/3) and gave an import's gate a step count (scenario 5, one run); the
stack-constraint wording drew an estate question in a greenfield project (scenario 2, one run). Rerun at `e9a135d`:
1 · 2 · 3 · 5 = 29/30 · 26/27 · 21/24 · 12/15, with the import gate, the consistency-pass list and the greenfield
wording holding; the remaining misses are in text the branch did not change (the light pass, comment intent, the
absent-context line).

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
| 1 | e9a135d | skill (plugin, Sonnet 5.5) | 29/30 (3 runs; 26/30 at 34a7495, 10/10 at fcc1288) | the consistency pass listed in the gate in two of three runs (none at 34a7495); all four seeds fixed and marked 3/3; unscored: one run resumed a reviewer and slept once |
| 2 | e9a135d | skill (plugin, Sonnet 5.5) | 26/27 (3 runs; 25/27 at 34a7495) | no estate question, consistency pass listed 3/3; one run named the absent context twice, as before this branch |
| 3 | e9a135d | skill (plugin, Sonnet 5.5) | 21/24 (3 runs; 22/24 at 34a7495, 15/16 at 3d078c5) | import gate (approve as they stand, "import", no step count), consistency pass listed and `code` deciders 3/3; misses are the old import ones: comment intent outside the open item (one run), read plan written after reading (one run) |
| 3 | — | control | 12/24 (3 runs) | caught the defect without fixing it, but no header, no `file:line`, questions scattered, DDL reconstructed |
| 4 | 7a5898b | skill (plugin, Sonnet 5.5) | 18/18 (3 runs; 18/18 at a7926d9) | fresh foreground reviewers, no timers 3/3; unscored: pre-existing blocking items left out of the gate's list, edits after a SUFFICIENT ruling not sent back |
| 5 | e9a135d | skill (plugin, Sonnet 5.5) | 12/15 (3 runs; 13/15 at 34a7495, 10/10 at e8db71d) | import gate, consistency pass and `code` deciders 3/3; misses in the light-pass rules: one run read a route module, two did not mark each area with a pointer |
| 6 | 9bdae75 | skill (plugin) | 6/6 (1 run, checks 1–6; 7 and 8 added after it) | 291 tests re-run green from a fresh clone; every blocking fix re-verified until SUFFICIENT; review result in each slice commit; render offered; missed: approved decisions (W1, an API error code, SD10) rewritten in place during slices and re-approved under the waiver instead of an open item, requirements.md left uncommitted on the branch |
| 2 | 88f14b2 | skill (plugin, Sonnet 4.6) | 23/27 (3 runs) | one chunk and three modes 3/3; the stack constraint answered "none" (2/3); review findings queued in the gate instead of open items (2/3) |

| 7 | 34a7495 | skill (plugin, Sonnet 5.5) | 21/21 (3 runs; 21/21 at d106e0c) | unscored: the consistency pass missed ownership and order gaps the reviewer then caught (3/3) |
| 8 | 34a7495 | skill (plugin, Sonnet 5.5) | 21/21 (3 runs; 21/21 at a7926d9) | consequences raised 3/3; the mTLS-termination choice first drafted inside an open item (3/3; reviewers moved it in two) |
| 9 | 34a7495 | skill (plugin, Sonnet 5.5) | 23/24 (3 runs; 23/24 at d106e0c) | R4 contested, fresh foreground reviewers, no timers 3/3; publishing events an `agent` row in two runs, tied to the paid-broker question in one; one run filed a minor finding as an open item |
| 7 | — | control | 0/21 (3 runs) | a discovery note, no plan, no requirements document, no modes |
| 8 | — | control | 5/21 (3 runs) | rulings left beside "RESOLVED" rows, citations kept, re-approval asked; check 6 passed by every control |
| 9 | — | control | 6/24 (3 runs) | one combined design, no stack selection, no per-phase review, commits on main; checks 4 (as first worded) and 6 passed by every control |
