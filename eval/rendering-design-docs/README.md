# Evaluations: rendering-design-docs

The review page: one tab per step document, decisions owed per tab, the blocking banner, the Change, Plan and Context tabs, changes since approval, links between ids, faithful content.

## Scenarios

| Scenario | What it tests |
|---|---|
| [1](scenarios/1-locker-rental-tabs.md) | four step documents, open items and context: tabs, gate tab, banner |
| [2](scenarios/2-active-change.md) | an active change with two step documents: the Change tab and touched markers |
| [3](scenarios/3-changes-since-approval.md) | approved documents with a change since approval, and a plan: the changes list, its marker, the gate tab, the Plan tab |

## Pending validation

- `509fbe0` — how to find the ids a commit adds, changes or removes, and the checklist asks for them: scenario 3 (skill arm).
- `49c9f39` — `plan.md`'s header lines keep their lines; with `e27550a`'s changes since approval, Plan tab and per-chunk pages: control arm of scenario 3, and scenarios 1 and 2 (skill arm), not yet run.

## Latest results

Each scenario's latest run, Sonnet, graded by an independent judge on Opus. `Skill@` is the commit whose skill content
was evaluated.

| Scenario | Skill@ | Arm | Result | Notes |
|---|---|---|---|---|
| 1 | 8772816 | skill | 9/9 (1 run) | each diagram under its own heading, checked against its Mermaid source; header lines merged into one line in one document |
| 2 | 0d17ef9 | skill | 5/5 (1 run) | Change tab first, two step tabs, touched markers; theme conformance also checked (all pass) |
| 3 | de54434 | skill (plugin, Sonnet 4.6) | 17/18 (3 runs) | one run listed each commit without the ids it touched; the runs shared `/tmp` and the second reused the first's generator, so the reps are not independent (headless runs now get a private `/tmp`) |
| 3 | 88f14b2 | skill (plugin) | 18/18 (3 runs) | marker, changes list and gate tab on the changed document only; no grouping on the page; one run put diagrams under the wrong headings (outside the checks); plan header lines merged in two runs |
| 1 | — | control | 29/40 (5 runs, the earlier single-page checks) | no gate summary first, no id anchors |
