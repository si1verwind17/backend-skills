# The design documents

Shared by every phase of `building-backend-services` (see [SKILL.md](SKILL.md)). Each phase skill defines its own
document's content; this file defines what every document has in common.

## Header

Every document under `docs/backend-design/` opens with:

```markdown
# <Document>: <service>
Status: DRAFT | REVIEWED | APPROVED · <date> · approved by <name>
Form: design | built
Builds on: <upstream documents and the ids this one serves>

<one-paragraph summary>
```

The `Status` line holds exactly one value and its stamp, nothing else:
`Status: DRAFT · <date>`, `Status: REVIEWED · <date>` (the agent review's
findings are dispositioned), `Status: APPROVED · <date> · approved by
<name>`. What changed and why goes in the gate presentation and the commit
message, never in the header — "DRAFT (was APPROVED …; edited …)" or
"APPROVED … · R7 amended …" is changelog text in the header.

`Builds on:` names the upstream documents and the ids this one serves —
never a status, a date or an open-item id, so an approval or a ruling
upstream never edits this header: `requirements.md (UC3, R4–R6)`, not
`requirements.md (APPROVED 2026-03-02) — UC3, R4–R6, OI-2`.

A document without a header (written before this convention) is treated
as the user describes it; give it the full header — all three lines — the
first time you edit it.

## Changes since an approval

DRAFT and REVIEWED belong to a document never approved. Once approved, a
document keeps `APPROVED` and the stamp of its last approval: an edit does
not flip it back. Every edit since that approval is a **change**, committed
on the run's branch — the changes are the diff since the approval's commit
— and each is in one of three groups:

| Change | Approval |
|---|---|
| Adds or changes what the document states: a rule, a decision, an entity, a contract, a figure | awaits the user's approval, at the next gate or stop |
| Writes down a ruling as the user gave it; fixes a gap (says what approved artifacts already say); re-points citations; adds a missing id or a `(contested — OI-n)` marker | needs none — the ruling, or the approved artifacts, already decided it; listed for information |
| Would change what an approved decision says | never made: an open item, the approved text in force (SKILL.md, Backtracking) |

Group each change on its own, never by the document or section it sits
in: a table made only to hold a ruling's row belongs to the write-down; a
citation re-pointed to a row awaiting approval awaits with it; an edit that
does both is split, each part in its group; any marker but `(contested —
OI-n)` added to an approved decision awaits approval. An open item you
raise is in neither group: it is listed with the open items.

Approving the changes moves the document's stamp to the approval's date.
The agent review checks every change set — the group that needs no
approval included, since the review is what checks the grouping — its
result in the commit message.

`open-items.md`, `plan.md` and `context.md` are not approved documents:
they carry a title and no `Status`, `Form` or `Builds on` lines.
Data files (`data-dictionary.yaml`, DDL, OpenAPI) carry no header: they
belong to the document that cites them and share its status.

## Ids

`requirements.md`: `UC` use cases, `R` rules, `NF` non-functionals,
`LD` locked decisions. `data-design.md`: `E` entities, `W` write paths, `DD`
data decisions. `architecture-design.md`: `I` interactions, `EV` events,
`AD` architecture decisions. `stack-selection.md`: `SD` stack decisions (pins
are listed without ids). `open-items.md`: `OI`. A decision is one row: the
decision, who made it (`user`, with the ruling's date, or `agent`), why
(one line), the alternative it beat (one line), and the ids it serves. A
ruling's row carries the ruling as the user worded it, `user, <name>,
<date>`, and `<name>'s ruling` as its why — never a reason the user did
not give, and never the open item it closed; what the ruling implies
beyond its words takes the open-item test below: a design choice is an
`agent` row of its own, awaiting approval, and an outside fact or a
business call is an open item.
A design phase decides the choices the requirements leave to design itself,
as `agent` rows — it never asks them as open items. Ids are how approved
decisions are protected and how changes are triaged. In a set split by
feature, every id but `OI` takes its area's short code as a prefix
(`STK-R3`, `STK-W2`; the foundation's code is `CORE`), so chunks never
renumber each other; open items stay one table with one numbering.

## `open-items.md`

The only home of an open question, across all phases:

| Id | Question | Raised in | Blocks | Decide by | Owner | Recommendation | Assumption in force |
|---|---|---|---|---|---|---|---|

`Raised in` is the phase that raised the item (`phase 0` … `phase 4`).
`Blocks` is a phase whose gate cannot pass until this is decided, or `no`;
`Decide by` is a phase (for a blocking item, the same phase as `Blocks`),
or — only on a service already built or imported, never during the first
design — `the change touching <area>`;
never a person: the person is `Owner`. Write phases as `phase 0` … `phase 4`,
not document names.

Every question you cannot settle yourself lives here and nowhere else.
**The test: can you settle it from the requirements, `context.md`, the
approved documents and engineering judgment?** Then it is a design choice
— the service split when the criteria agree, events, instance counts,
auth mechanism, cache, figures like timeouts — decided as an `agent`
decision row (see Ids), never a row here. A row is for the rest:

- every assumption about what the business wants, what the environment
  is, or what an outside system does (an integration's contract, which its
  owner answers) — including a phase skill's elicitation or research
  record, and every question a phase skill names as the user's — is a row
  with its assumption in force, never a section of the phase's own
  document; a fact `context.md` already records is not an assumption;
- so is every hard-to-reverse unknown (run-modes.md, the start sitting), every
  requirement that doesn't make sense, can't be built as written, or hits
  a limitation, and every proposal to change an approved decision;
- a review finding that needs the user — a judgment disagreement, a
  change to an approved decision — is a row; a minor finding is fixed, or
  named in the commit message with the phase that will fix it, never a
  row;
- a value written into a document as provisional ("proposed", "to
  confirm", "TBD", "assumed", a placeholder figure) — and any rule whose
  source is your own assumption — carries the id of its
  row, e.g. `p95 < 500 ms (proposed — OI-7)`, `source: OI-4`. The
  self-check searches the documents for "assum", "propos", "confirm",
  "TBD" and adds a row for any that lacks one.

Each cell is one line: the detail lives in the document section the item
concerns, and a row never carries dated updates. `open-items.md` holds its
title and the table, nothing else — no lists of
questions around it; rows are sorted by `Blocks`, then `Decide by` — except
an import's read-plan row, which stays first until the scope is ruled. A
checklist you ran is never written into a document.

When there is no `requirements.md` yet (a phase skill used on its own), give
the brief's statements ids of their own (`B1`, `B2`, …) in the document
that uses them, so decisions still say which ids they serve.

How the run itself works — the run mode, whether a reviewer agent may be
dispatched, whether to render the review page — is asked in the gate
message, never recorded as an open item: open items are decisions about the
service, and the run's settings live in `plan.md`. When the user rules,
delete the row and write the answer as a decision row (`user`, dated), with
an id, in the document it belongs to — git keeps the history.

## `plan.md`

The run's plan, short at every size — one chunk is one row:

```markdown
# Plan: <service>

Size: small | one chunk | split by feature
Run mode: gated | auto until design done | auto until feature done | auto until done
Reviewer: agent dispatch | declared self-review (<reason>)

| Chunk | Code | Covers | Depends on | State |
|---|---|---|---|---|
| foundation | CORE | identity, access, audit | — | built |
| stock | STK | the input's stock sections | foundation | in design |
| trips | TRP | the input's trips sections | foundation | later |
```

`Run mode` reads `gated` until the user chooses, and every gate asks it
until then: a mode you wrote while creating `plan.md` is not a choice. `State` is one of
`later` (a feature the input schedules for a later release only), `to do`
(scheduled, not started), `in design`, `awaiting approval` (an auto mode stopped
with its changes unapproved), `design approved`, `building`, `built`,
`parked (OI-n)`. Update a chunk's state in the commit that changes it.

## Two forms

Documents describe the **current state**, not history:
superseded text is rewritten in place, never struck through or appended as
a changelog. `Form: design` is the full document the phases produce.
`Form: built` keeps only what code cannot say — rules, decisions and why,
accepted trade-offs, contracts with outside systems — and points to the
code for the rest: the physical data model becomes a pointer to the
migrations or schema files, the API inventory a pointer to the routes or
OpenAPI, the stack's research shrinks to the pins and their sources. A
document switches to `built` once, when the first implementation slice that
makes its physical part real is approved. Keeping a second copy of what the
code says is forked truth.

## Size check

Part of every self-check: each document stays within a
soft word budget the phase skill sets; flag resolved items still listed,
superseded text still present, and physical-model copies left after
migrations exist. There is no separate compaction step.

**Past the budget once restatement is cut, split per area.** A project
split by feature (SKILL.md) is split from the start: the foundation keeps
the root names (`docs/backend-design/requirements.md`, `data-design.md`,
`architecture-design.md`, `stack-selection.md`), and each feature area gets
`docs/backend-design/<area>/` with the same names for the phases it runs;
`open-items.md` and `plan.md` stay one each, at the root. Each budget then
applies per file, so a change loads, and its approval shows, only the areas
it touches.

## Local-only files

`docs/backend-design/changes/` (see [changes-and-import.md](changes-and-import.md)) and the
rendered `design-review.html` are never committed: the first time you
create either, add its path to `.git/info/exclude` — never to the repo's
`.gitignore`, which would itself be a committed change.

