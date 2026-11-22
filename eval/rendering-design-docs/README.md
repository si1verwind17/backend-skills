# Evaluations: rendering-design-docs

The review page: one tab per step document, decisions owed per tab, the blocking banner, the Change, Plan and Context tabs, changes since approval, links between ids, faithful content.

## Scenarios

| Scenario | What it tests |
|---|---|
| [1](scenarios/1-locker-rental-tabs.md) | four step documents, open items and context: tabs, gate tab, banner |
| [2](scenarios/2-active-change.md) | an active change with two step documents: the Change tab and touched markers |
| [3](scenarios/3-changes-since-approval.md) | approved documents with a change since approval, and a plan: the changes list, its marker, the gate tab, the Plan tab |

## Pending validation

- `49c9f39` (with `e27550a`) — changes since approval, Plan tab, per-chunk pages: validated on scenarios 1, 2 and 3 (below); the control arm of scenario 3 not run.

## Latest results

Each scenario's latest run, Sonnet, graded by an independent judge on Opus. `Skill@` is the commit whose skill content
was evaluated.

| Scenario | Skill@ | Arm | Result | Notes |
|---|---|---|---|---|
| 1 | 34a7495 | skill (plugin, Sonnet 5.5) | 27/27 (3 runs; 9/9 at 8772816, 1 run) | standalone, tabs, gate tab, decisions owed, ids and theme all verified in a browser; unscored: the full-size viewer never opened, partial text comparison in two runs |
| 2 | 34a7495 | skill (plugin, Sonnet 5.5) | 15/15 (3 runs; 5/5 at 0d17ef9, 1 run) | Change tab first, touched markers, cross-tab links; unscored: one run skipped the text comparison, one added a heading |
| 3 | 34a7495 | skill (plugin, Sonnet 5.5) | 18/18 (3 runs; 18/18 at a7926d9) | commit date and full subject 3/3 |
| 3 | 509fbe0 | skill (plugin, five models) | Fable 5.2 18/18, Opus 5 18/18, Opus 4.8 16/18, Opus 4.6 16/18, Sonnet 4.6 15/18 | the misses copied the skill's example line, which held this scenario's data (shortened subject, ruling date for commit date); fixed in a7926d9 |
| 3 | de54434 | skill (plugin, Sonnet 4.6) | 17/18 (3 runs) | one run listed each commit without the ids it touched; the runs shared `/tmp` and the second reused the first's generator, so the reps are not independent (headless runs now get a private `/tmp`) |
| 3 | 88f14b2 | skill (plugin) | 18/18 (3 runs) | marker, changes list and gate tab on the changed document only; no grouping on the page; one run put diagrams under the wrong headings (outside the checks); plan header lines merged in two runs |
| 1 | — | control | 29/40 (5 runs, the earlier single-page checks) | no gate summary first, no id anchors |
