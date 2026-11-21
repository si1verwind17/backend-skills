# Evaluations: rendering-design-docs

The review page: one tab per step document, decisions owed per tab, the blocking banner, the Change, Plan and Context tabs, changes since approval, links between ids, faithful content.

## Scenarios

| Scenario | What it tests |
|---|---|
| [1](scenarios/1-locker-rental-tabs.md) | four step documents, open items and context: tabs, gate tab, banner |
| [2](scenarios/2-active-change.md) | an active change with two step documents: the Change tab and touched markers |
| [3](scenarios/3-changes-since-approval.md) | approved documents with a change since approval, and a plan: the changes list, its marker, the gate tab, the Plan tab |

## Pending validation

- `e27550a` — changes since approval (tab marker and per-commit list), the gate tab counting them, the Plan tab, one page per chunk in a split set. Validates on scenario 3 (skill arm; control too, as its checks are new), then 1 and 2.

## Latest results

Each scenario's latest run, Sonnet, graded by an independent judge on Opus. `Skill@` is the commit whose skill content
was evaluated.

| Scenario | Skill@ | Arm | Result | Notes |
|---|---|---|---|---|
| 1 | 8772816 | skill | 9/9 (1 run) | each diagram under its own heading, checked against its Mermaid source; header lines merged into one line in one document |
| 2 | 0d17ef9 | skill | 5/5 (1 run) | Change tab first, two step tabs, touched markers; theme conformance also checked (all pass) |
| 1 | — | control | 29/40 (5 runs, the earlier single-page checks) | no gate summary first, no id anchors |
