---
name: writing-business-requirements
description: >-
  Use when turning a business ask into structured requirements before any
  design starts — interviewing a stakeholder from a fuzzy idea, digesting an
  existing PRD or business document into agent-workable form, or checking
  whether requirements are complete enough to begin data/architecture design.
  General-purpose: feeds building-backend-services phase 0 and any future
  build flow.
---

# Writing business requirements

Turn a business perspective into requirements an agent can build from. Two
entry modes, one output: **interview** (the ask is fuzzy — elicit) and
**digest** (a PRD or business doc exists — translate it into the uniform
format, preserving its intent and citing it). The deliverable is the input
contract for the design phases that follow.

## The deliverable

`docs/backend-design/requirements.md` unless the user specifies otherwise,
opening with the shared document header (`Status`, `Form`, `Builds on`)
defined in `documents.md` in the `building-backend-services` skill folder,
beside this skill's folder
([../building-backend-services/documents.md](../building-backend-services/documents.md) — to find it, take the folder this SKILL.md is in, go up one level, then into `building-backend-services/`, not relative to your working directory). Every locked
decision, use case, rule, and non-functional carries a **stable id** (LD1,
UC1, R1, NF1) so downstream documents can trace to it ("write path
implements R3"). Ids are never renumbered or reused: a withdrawn item keeps
its id, marked withdrawn, and a new one takes the next free number.
The header and the open-items format, in short (full rules in
documents.md):

```markdown
# <Document>: <service>
Status: DRAFT · <date>            (REVIEWED · <date> / APPROVED · <date> · approved by <name>)
Form: design
Builds on: <upstream documents and ids>
```

`open-items.md` columns, exactly: `| Id | Question | Raised in | Blocks |
Decide by | Owner | Recommendation | Assumption in force |` — `Blocks` and
`Decide by` hold phases (`phase 0` … `phase 4`) or `no`.

Exactly these ten sections, numbered as below — the lifecycle lives inside
§4, never as a section of its own:

1. **Summary & business goal** — what this is and why the business wants
   it, in a few sentences. Context, not marketing.
2. **Locked decisions** — `LD<n>`: choices already made that agents must
   not re-litigate (these become the "approved" baseline the build flow's
   backtracking rule protects), each with its source.
3. **Actors & roles** — who interacts and what they're trying to do; a
   roles-and-permissions table when the system has operator/back-office
   users.
4. **Use cases** — `UC<n>`: actor, goal, main flow, and **acceptance
   criteria** (verifiable statements; these seed the implementation
   phase's tests). Lifecycle states and their transitions are spelled out
   here — downstream data design models them directly.
5. **Business rules** — `R<n>`: one testable statement each, with its
   source: the stakeholder, a PRD section, a law or policy, a locked
   decision quoted in the source (`LD4: "some items sell out during the
   day"`) — so a rule its words do not contain is visibly wrong — or an
   open item (`OI-4`) when it is your own assumption or inference. A use case, another rule or a section of this document is
   never a source — they are your own writing, so a rule traced only to
   them is an assumption and needs its open item. One statement per rule:
   a rule never joins two obligations with ";", "and" or a parenthesis —
   split "one price, one currency" into two rules, "a guest order requires a
   name and a contact address" into two, "the line is omitted and the
   customer is told" into two. Before delivering, read every rule for
   " and ". Hard guardrails are rules
   ("no purchase path anywhere", "a spot is never double-booked");
   **non-goals are not** — they live only in §9, so a rule never carries a
   "no X" tail and nothing appears in both places.
6. **Integrations** — external systems touched, direction, and what each
   consumes or provides.
7. **Non-functionals** — `NF<n>`: criticality (mission-critical?
   user-facing?), expected sizing and growth, SLA/latency expectations,
   compliance and data sensitivity (PII, consent, retention).
8. **Environment context** — cloud, **deployment target** (long-running
   service, serverless / scale-to-zero, or unknown), existing estate,
   team — pass-through for the design phases; data design needs the
   deployment target to choose an engine family. Record what is known;
   anything unknown is an open item, never invented.
9. **Out of scope** — explicit exclusions, one per line, so agents don't
   helpfully build them. An exclusion the stakeholder did not state is an
   assumption: it cites an open item asking them to confirm the list.
10. **Open items** — a one-line pointer to `open-items.md`, where every
    pending decision and open question lives as a row (format in
    [documents.md](../building-backend-services/documents.md)): `Owner` is
    the decider (Business / Tech / Legal / Data / a named person), with
    your recommendation and the assumption in force. A vague point is
    never "TBD": it is either resolved, or a row with an owner and your
    stated interim assumption.

## Translation rules (business language → agent-workable)

- Every vague phrase becomes exactly one of: a testable rule (R), a locked
  decision, or a pending decision with a decider. Nothing survives as
  ambient prose an agent must interpret.
- Marketing language is context for §1 only — it never enters use cases or
  rules. Neither do generic quality words in acceptance criteria — "clear",
  "friendly", "quick", "easy", "intuitive": name the observable outcome
  instead ("rejected with error `SLOT_TAKEN`", "shown the next free
  slot").
- Numbers a stakeholder can't give yet are an open-item row with the
  decider as owner, and the document shows the interim value with the
  row's id ("attribution window: 30 days (proposed — OI-3)"), never a bare
  invented figure or a bare "to confirm".
- When digesting an existing PRD: preserve its decided/undecided split
  faithfully, cite the source section per item, and do not silently
  upgrade its wishes ("might want analytics later") into requirements —
  those land as anticipated-future notes on the relevant use case or
  integration.

## Elicitation order (interview mode)

Ask in this order and stop when the stop rule below is met — don't
interrogate exhaustively. Sort the recorded list — `open-items.md` rows —
by `Blocks` (phase 0 first, then phase 1, …, then `no`), then by `Decide by`;
a question whose answer changes nothing in the design is not asked. An
unknown deployment target blocks phase 1 (data design needs it).

1. Actors and their goals — who touches this and why.
2. The happy path of each core use case, then its failure/edge cases.
3. Lifecycle: what states does the core thing move through, and which
   transitions are forbidden?
4. Business rules and hard guardrails — what must always/never happen?
5. Integrations — what existing systems react to or feed this?
6. Criticality, sizing, growth expectations (this drives how much
   structure every downstream phase applies).
7. Environment: which cloud, and will it run as a long-running service or
   serverless / scale-to-zero? (Ask early — the data design's engine choice
   leans on it.)
8. Compliance and data sensitivity.
9. What is explicitly out of scope?

## The stop rule — "enough to start design"

Requirements are ready for the design phases when:

- Data design can name the **entities, their lifecycle states, and the
  write paths** from the use cases alone.
- Architecture can read the **integrations, reaction/event needs, and
  criticality** without asking again.
- Data design and stack selection can read the **environment context**,
  including the deployment target (or see it as an open item).
- Everything still unknown is a row in `open-items.md` **with an owner** —
  not floating.

Anything beyond that level of detail belongs to the design phases, not
here.

## Before delivering — verify

- [ ] Every use case has acceptance criteria; every rule is a single
      testable statement with a source.
- [ ] Every id (LD/UC/R/NF) is unique and referenced consistently; none
      renumbered or reused.
- [ ] The header is present and exact; §10 points to `open-items.md` and
      holds no questions itself.
- [ ] Every provisional value ("proposed", "to confirm", "assumed", a
      placeholder figure) and every rule sourced to an assumption carries
      its open item's id — search the document for "assum", "propos",
      "confirm", "TBD", then read every number and every rule source: a
      figure the stakeholder did not give — including one you chose to make
      a vague word testable ("easily" → "three actions") — or a rule
      sourced to a use case, needs an open item too. For every rule citing
      a locked decision, quote the decision's words to yourself: if they do
      not contain the rule, cite the open item instead.
- [ ] Exactly ten sections, numbered §1–§10 as listed; `open-items.md` rows
      sorted by `Blocks`, then `Decide by`.
- [ ] Lifecycle states and forbidden transitions are explicit.
- [ ] No vague phrase remains outside §1 — each became a rule, a locked
      decision, or a pending decision with a decider.
- [ ] Sizing/growth, criticality, and the deployment target are stated or
      open items.
- [ ] Size: a soft budget of about 2,500 words; past it, cut restatement
      before cutting rules.
- [ ] Out-of-scope section exists and is non-empty (an empty one usually
      means it wasn't asked).

## Changes to existing requirements

When a change to an existing service starts here (it touches behavior,
rules, or use cases), edit `requirements.md` in place: changed items keep
their ids, new items take the next free ids, withdrawn items stay marked
withdrawn. List the ids the change adds, changes, and withdraws in the
change's file under `docs/backend-design/changes/`, so the later phases see
exactly what moved. The document still describes the current state — no
changelog inside it.

## Common mistakes

- Interrogating past the stop rule — requirements that pre-decide the
  design.
- "TBD" without a decider; wishes silently promoted to requirements.
- Acceptance criteria that restate the flow instead of being verifiable.
- Missing forbidden transitions (only the happy lifecycle captured).
- Marketing adjectives inside rules ("fast", "seamless") instead of
  measurable non-functionals.
- Out-of-scope never asked, discovered at implementation time.
