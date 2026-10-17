# Changes and imports

Part of `building-backend-services` (see [SKILL.md](SKILL.md)): how a service already built, or one that exists
without this process, goes through the chain. Document formats: [documents.md](documents.md).

## Changes after the first build

A service built (or imported) this way is changed through the same chain —
but only the phases a change touches run. **Triage first**, by what the
change touches:

| The change touches | Enters at |
|---|---|
| behavior, rules, a new use case | phase 0 — new or changed ids in `requirements.md` |
| schema only | phase 1 |
| interactions, events, a new service | phase 2 |
| a new library, a runtime change | phase 3 |
| none of these (a bug fix, a refactor) | phase 4 directly; the slice's review checks that no contract changed |

From its entry phase, a change runs every downstream phase it actually
touches and skips the rest; each phase it runs goes through the full cycle
and gate. **A change adds only what the request states.** The rules and use
cases it adds are the ones the requester asked for; everything you infer
around them — edge cases, mechanisms, defaults — is an open item with an
assumption in force, never a new rule. The request is the source; your
recommendation is not. Name the ids it touches: a change that would alter an APPROVED
decision row asks the user before amending it, as in SKILL.md's Backtracking.

**Describe the change in progress** in
`docs/backend-design/changes/<date>-<slug>.md`: what it is and why, the ids
it touches, the phases it runs, and their state. It is local only (see
Local-only files): it never reaches another clone or worktree, so pass its
content to workers explicitly, and tell the user that an unfinished
change's record lives on this machine. When the change's last slice is
approved, delete the file: the documents show the result and git keeps the
narrative.

## Bringing an existing repository in

An existing service enters the chain by writing its documents **from the
code, in `Form: built`**; the user approves them as they stand; from then
on every change goes through Changes above. Importing designs nothing and
changes no code.

- **Your first output is the read plan** — before reading anything beyond
  the build files and a file listing: the files you will read, their total
  line count, and the scope options (whole repository / one path / one
  service). In a non-interactive run, write it as the first row of
  `open-items.md` (the scope question and the scope you assumed) before any
  other document; it stays the first row — sorting the table does not move
  it — until the user rules on the scope.
- **Small repository: import all of it at once.** When the source in scope
  is small (roughly 5,000 lines or fewer, tests excluded), the plan is a full
  import: read it all and write complete documents. Later deep imports would
  cost more than reading it now.
- **Larger repository: light pass, then depth on touch.** The light pass
  reads only a fixed set, whatever else looks interesting: existing docs
  first (cheaper than code), build files, entry points and the config they
  load, deploy and CI files, the migrations (their schema statements), the
  one place routes and consumers are registered (a router file, an app
  factory). Everything else is outside it — route modules and their
  decorators, dependency and auth modules, helpers, publishers, tests — and
  so is its content found by a search: a grep across the code that returns
  lines is reading them; a file listing is not. A README or a config default
  says how the service is set up, not what it does: record it as
  configuration in `context.md`, never as a rule or a decision. It yields the
  module map, the stack pins, the top-level architecture and `context.md`;
  in `requirements.md` and `data-design.md` every area is listed as `not yet
  imported` with a pointer, carrying only what the light-pass set shows
  (routes become use-case names, the migrations' tables become entities).
  Reading any other source file is a deep import, and the deep import of an
  area (its rules, decisions, write paths) happens the first time a change
  touches it. The user may skip the light pass entirely: then the first
  change deep-imports only its own area.
- **Record what the code does, never decide what was meant.** Behavior
  that looks wrong becomes an open item — intended, accepted hazard, or
  bug — never a requirement and never a fix on import. Until the user
  rules, the documents state the **code's behavior as the rule in force**;
  intent found in a comment, a test or a stale document appears only in the
  open item — every rule, decision and write-path row, in every document,
  says what the code does and points to the item (`R3: cancel allowed from
  reserved and checked_in — see OI-2`), nothing more. A bug becomes a change of its own.
- **Read is not run.** A test you read but did not run is evidence of what
  someone intended, not of what the code does: cite it as `per test
  <name>`, never as "verified by test".
- **Provenance on every fact:** code (`file:line`), an existing document, or
  the user (with date). Ask the user in batches built from the evidence —
  what you found, what you think it means, the question — not one question
  at a time.
- **The import's review** runs like any phase's: your consistency pass
  over the documents you wrote comes first, and its list goes to the
  reviewer with the documents.
- **The import's gate** asks the user to approve the documents **as they
  stand** (all four, with the open items), names it "import", not a step
  count, and says that changes enter through triage afterwards.
- **No refactor on import.** The repository's conventions and warts go into
  `context.md`. New code follows the skill rules except at a boundary with
  existing code; cleaning up existing code is a change of its own.
- **Facts kept elsewhere** (a schema another team owns, deployment in an
  ops repository): unknown stays unknown, with a pointer — record it as a
  constraint in `context.md`, record what the code implies as "inferred
  from code" in the design document (no `data-dictionary.yaml` or DDL is
  written for a schema the repository does not hold), and open an item asking the user to point to the source,
  paste it, or accept it as external. Later changes that touch it are
  flagged at triage.

