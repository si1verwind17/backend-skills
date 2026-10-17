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
<name>`. What changed and why goes in the gate presentation, never in the
header — "DRAFT (was APPROVED …; edited …)" is changelog text in the header.

Any edit to an APPROVED document returns it to `DRAFT` until the user
approves it again, keeping the approval it had:
`Status: DRAFT · <date> · last approved <date> by <name>` — and the same
tail on `REVIEWED`, until the user approves it again — so a reader (and a
reviewer) can see it was approved and what changed since. A document without a header (written before this
convention) is treated as the user describes it; give it the full header —
all three lines — the first time you edit it.

`open-items.md` and `context.md` are not approved documents: they carry a
title and no `Status`, `Form` or `Builds on` lines.
Data files (`data-dictionary.yaml`, DDL, OpenAPI) carry no header: they
belong to the document that cites them and share its status.

## Ids

`requirements.md`: `UC` use cases, `R` rules, `NF` non-functionals,
`LD` locked decisions. `data-design.md`: `E` entities, `W` write paths, `DD`
data decisions. `architecture-design.md`: `I` interactions, `EV` events,
`AD` architecture decisions. `stack-selection.md`: `SD` stack decisions (pins
are listed without ids). `open-items.md`: `OI`. A decision is one row: the
decision, why (one line), the alternative it beat (one line), and the ids
it serves. Ids are how approved decisions are protected and how changes are
triaged.

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

Everything awaiting the user lives here and nowhere else:

- every assumption a phase makes — including a phase skill's elicitation
  or research record — is a row with its assumption in force, never a
  section of the phase's own document;
- every agent-review finding queued for the user (not fixed before the
  gate) is a row;
- a value written into a document as provisional ("proposed", "to
  confirm", "TBD", "assumed", a placeholder figure) — and any rule or
  decision whose source is your own assumption — carries the id of its
  row, e.g. `p95 < 500 ms (proposed — OI-7)`, `source: OI-4`. The
  self-check searches the documents for "assum", "propos", "confirm",
  "TBD" and adds a row for any that lacks one.

`open-items.md` holds its title and the table, nothing else — no lists of
questions around it; rows are sorted by `Blocks`, then `Decide by` — except
an import's read-plan row, which stays first until the scope is ruled. A
checklist you ran is never written into a document.

When there is no `requirements.md` yet (a phase skill used on its own), give
the brief's statements ids of their own (`B1`, `B2`, …) in the document
that uses them, so decisions still say which ids they serve.

How the run itself works — whether a reviewer agent may be dispatched,
whether to render the review page — is asked in the gate message, never
recorded as an open item: open items are decisions about the service. When the user rules, delete the row and write
the answer as a decision row, with an id, in the document it belongs to —
git keeps the history.

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
migrations exist. Large services split documents per area, so a change
loads only the areas it touches. There is no separate compaction step.

## Local-only files

`docs/backend-design/changes/` (see [changes-and-import.md](changes-and-import.md)) and the
rendered `design-review.html` are never committed: the first time you
create either, add its path to `.git/info/exclude` — never to the repo's
`.gitignore`, which would itself be a committed change.

