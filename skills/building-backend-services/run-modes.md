# Size, chunks and run modes

Part of `building-backend-services` (see [SKILL.md](SKILL.md)): read it during phase 0, before the start
sitting, and at every stop of an auto mode. Document formats: [documents.md](documents.md).

## Size the project

During phase 0, one test for every project: do the requirements for what is
built now fit one requirements document's budget (about 2,500 words, set by
`writing-business-requirements`)?

| Size | Shape |
|---|---|
| Small — a POC, one capability, a handful of entities | one chunk; the three design deliverables may collapse into one shorter document (keeping every section: entities/DDL, decisions, event catalog, stack pins), and the gates may batch into one |
| Fits the budget | one chunk, the four documents |
| Does not fit | split by feature, below |

A small project compresses phases, never skips their *content*.

**Splitting by feature.** Read the whole input once, only to write the
feature map into `plan.md`: every feature the input names, scheduled now or
later, and the order between them — a feature that creates, reads or
registers another feature's entity depends on it, so read `Depends on`
from the input's cross-references and list each chunk after the chunks
it depends on. What every feature needs — the input's cross-cutting
features, whole (accounts, organizations and roles, notifications), plus
identity, access, audit and a shared write pattern where the input
implies them — is the **foundation** chunk: phase 0 writes the
foundation's requirements and the map, and the foundation leads every
phase, stack selection included — no feature designs or builds ahead of it. The foundation's requirements meet
the same budget; one that doesn't fit is too broad. Then each other
scheduled feature the input names is its own chunk — never merged with
another — in the map's order: phase 0 for its area (the input's sections for
that feature), then phases 1, 2 and 4 — phase 3 only when it needs a
library or runtime the stack lacks. A feature scheduled for later is
listed in the map and designed when its turn comes, never modelled ahead.
Every entity has one owning area; other areas reference it. The documents
split the same way (documents.md, Size check), so a change loads only the
areas it touches, and a question that blocks one feature parks that chunk,
not the run.

## The start sitting

The gate of the run's first phase 0, after its review, is one message:

- the size and, when split, the chunk plan, for the user to approve;
- the hard-to-reverse unknowns that neither the requirements nor
  `context.md` settle (a convention it records settles one: follow it) —
  the deployment target, a constraint on the stack,
  the datastore family, paid external services — each with your
  recommendation, never "decide later" or "none": an auto run never decides
  these alone, because overruling one after the run is a rewrite. For the
  stack, recommend the constraint — one language or platform, never a
  choice between two, from the team and the estate; phase 3 still selects
  the full stack within it;
- the run modes that differ for this project — all four when split by
  feature; otherwise always these three: gated, auto until design done,
  auto until done (for one chunk, auto until feature done is auto until
  done) — each named with where it stops, one recommended with one
  line of why, and one short line of when an auto run would still stop
  ("may stop early if a requirement can't be built as written, a blocking
  question parks every remaining chunk, or a step needs money, an external
  account, a push or a deploy");
- the open items awaiting the user, blocking first;
- the render question, last.

Use this shape, so no part is dropped:

```markdown
**Size:** split by feature — <why: the requirements for what is built now vs the budget>
| Chunk | Covers | Depends on | State |          ← when split
**Unknowns to settle before any auto run** (not settled by the requirements or context.md):
| Unknown | Recommendation | Why |
**Open items** — blocking first, one line each (Item · Question · Recommendation)
**Run mode** — gated until you choose:
| Mode | Stops | |
| Gated | at every phase gate | |
| Auto until design done | before any code | recommended: <why> |
| Auto until feature done | after each chunk is built | ← only when split |
| Auto until done | after the last chunk | |
An auto run may still stop early if <the stop line>.
next: step 2/<total> — <skill> (<chunk>)
Render the review page and open it?
```

Then stop. Record the size, the chunks and the chosen mode in `plan.md`;
the user may change the mode at any later stop. When the user chose a mode
before the start sitting ("skip the reviews, proceed to the end"), the run
does not stop here: each hard-to-reverse unknown becomes an open item with
your recommendation as the assumption in force, listed first at the mode's
stop.

## Run modes

| Mode | Stops | Recommend when |
|---|---|---|
| Gated | at every phase gate of every chunk — the default until the user chooses | high stakes (money, compliance), or the user wants to shape the design |
| Auto until design done | after the last design phase of every scheduled chunk, before any code; that sitting asks the mode for implementation | the requirements are new or uncertain |
| Auto until feature done | after each chunk's last slice — offered only with two chunks or more | a project split by feature |
| Auto until done | after the last chunk | a small project |

**Between its stops, an auto run:**

- **decides** every choice the requirements leave to design — data,
  architecture, technical choices and technical figures — as a decision
  row marked `agent`, with one line of why; never as an open item;
- **follows the requirements**: where one doesn't make sense, can't be
  built as written, or hits a limitation, it opens an item, marks what
  depends on it `(contested — OI-n)` — the path that builds the assumption
  in force included — without redefining the requirement, and designs the
  rest; it parks the chunk only when the chunk's core
  depends on the item. A reviewer's judgment disagreement is an item too,
  the author's version in force;
- **parks a chunk** on a blocking item and continues with the chunks that
  do not depend on it; with none left, it stops;
- **never** decides a hard-to-reverse unknown, changes an approved
  decision, pushes, merges, deploys, spends money or creates an external
  account;
- **still runs the agent review** at every phase and slice — it stands in
  for the user's gate, so it is never skipped — and **finishes each cycle
  before the next starts**: review re-verified and committed, then the
  next phase. It waits for its own reviewer; ending a turn while the
  reviewer runs ends a non-interactive run, and is not a stop.

## The stop's sitting

First set each stopped chunk's state in `plan.md` to `awaiting approval`
(or `parked (OI-n)`) and commit. Then one message, per chunk. The user approves changes, rules on items, and may
overrule an agent decision; an overrule is a change for the next run,
through triage when code exists. Use this shape:

```markdown
**Stopped: <mode>, <what is done>**
**Blocking** — decide before the next run (and parked chunks with why):
| Item | Question | Recommendation |
**Awaiting your approval** — the agent's decisions first, then the other changes:
| Id | Change | Document |
**Other open items:**
| Item | Question | Recommendation |
**Run mode for implementation** — after auto until design done: the mode table, one recommended
next: step <k>/<total> — <skill> (<chunk>)
Render the review page and open it?
```
