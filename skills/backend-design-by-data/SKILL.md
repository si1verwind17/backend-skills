---
name: backend-design-by-data
description: >-
  Use when designing the data layer of a backend service — modeling entities
  from requirements, choosing between relational, document and key-value
  stores, writing DDL or document/key schemas, designing idempotent or atomic
  write paths, minimizing round-trips, deciding constraints, keys and
  indexes, planning schema evolution, or deciding whether multi-system
  updates need a message queue.
---

# Backend data design

Design starts from the data: translate the requirement into entities, their
invariants and the ways they are read and written, then let the logic
revolve around it. The work runs in three layers, in order: a **logical
model** that holds for any database, the **engine family** chosen from it,
and the **physical model** for that family. SQL examples assume Postgres
(the recommended RDBMS); the other families have their own sections below.

## The deliverable

Delivered under **`docs/backend-design/`** in the target repository unless
the user specifies a different location, so the user can review the
reasoning and the next agent can implement without re-deriving anything.
Every document opens with the shared header and uses the shared ids
(`documents.md` in the `building-backend-services` skill folder, beside
this skill's folder: [../building-backend-services/documents.md](../building-backend-services/documents.md) — to find it, take the folder this SKILL.md is in, go up one level, then into `building-backend-services/`, not relative to your working directory); every open
question and assumption is a row in `open-items.md`, never a section here.

The header and the open-items format, in short:

```markdown
# <Document>: <service>
Status: DRAFT · <date>            (REVIEWED · <date> / APPROVED · <date> · approved by <name>)
Form: design
Builds on: <upstream documents and ids>
```

`open-items.md` columns, exactly: `| Id | Question | Raised in | Blocks |
Decide by | Owner | Recommendation | Assumption in force |` — `Blocks` and
`Decide by` hold phases (`phase 0` … `phase 4`) or `no`.

1. **`data-design.md`**, `Form: design`, containing, in order:
   - **Logical model** — entities (`E1`, `E2`, …) as a Mermaid ER diagram
     with **engine-neutral types** (`id`, `text`, `integer`, `decimal`,
     `boolean`, `date`, `instant`, `enum`, `json`) — never `timestamptz`,
     `jsonb`, `uuid` or a DynamoDB attribute type — and every business
     entity and field, plus per-entity rationale: what each field and key means, **each id's
     semantics** (global or per-parent numbering), invariants, and the
     lifecycle the requirements give it (cite `UC`/`R` ids). Keep the
     diagram source portable: one attribute per line inside entity blocks,
     never `;` separators (several Mermaid builds reject them and fail the
     whole diagram).
   - **Access patterns** — one row per read and write the requirements
     imply: what it looks up by, roughly how often, and the ids it serves.
     This table drives the engine family, the keys and the indexes.
   - **Engine family** — relational, document, key-value or wide-column, as
     a decision row (`DD`) with its reasons (below).
   - **Physical model** for that family — it names everything the logical
     model doesn't: lookup tables, outbox and inbox tables, technical
     columns. Relational: per-table notes (the DDL itself lives in
     `ddl/`); document: collections, document shapes,
     embed-versus-reference choices; key-value / wide-column: tables,
     partition and sort keys, secondary indexes, each beside the access
     patterns it serves.
   - **Write-path table** — `W1`, `W2`, …: one row per operation with its
     idempotency mechanism, its atomicity mechanism, and its queue
     decision. This is the section an implementing agent consumes directly.
   - **Index / key plan** — each index beside the access pattern it serves.
   - **Decisions** — `DD` rows: the decision, why (one line), the
     alternative it beat (one line), the ids it serves.
   - **Schema evolution** notes.
2. **`data-dictionary.yaml`** — the authored source of field definitions
   (`entities: <name>: {description, fields: <field>: {type,
   description}}`), one entry per entity and field stating its purpose, so a
   later analytics agent can know what every field means without a database
   connection.
3. **The physical artifacts for the family**: relational — a `ddl/`
   directory of numbered, per-concern, runnable `.sql` files
   (`01-create-tables.sql`, `02-create-indexes.sql`, `03-functions.sql`, seed
   data) matching the design exactly, including `COMMENT ON TABLE/COLUMN`
   statements mirroring the dictionary (queryable via `pg_description`);
   document — a `schema/` directory with one validation schema per
   collection (JSON Schema, with descriptions) and the index definitions;
   key-value / wide-column — a `schema/` directory with the table and index
   definitions in the engine's own format.

**After the build** (`Form: built`, see documents.md): the logical model,
access patterns, write paths and decisions stay; the physical model, the
dictionary and `ddl/` / `schema/` are replaced by a pointer to the
migrations or schema files in the code, which carry the descriptions
(`COMMENT ON`, schema `description`). Keep the dictionary only while no
schema file carries them.

Nothing above the engine-family row names an engine or product — not the
summary, not the logical model.

**Size:** a soft budget of about 3,000 words for `data-design.md` in design
form; rationale is one line per decision, not an essay.

## From requirement to schema

Start with the core entity the requirement implies (an order system → an
`order` table) and expand by interrogating the domain: which ids, which
status, which dates (`paid_at`?), which links to other systems (`payment_id`)?
When the chain provides `docs/backend-design/context.md`, read it first:
existing DB conventions and shared data contracts inform the design
(conform at constraint boundaries; never mirror a listed wart; record
divergences per the orchestrator's rule).

Discover cardinality as you go — one order, many items → a child `order_item`
table **keyed by the parent's primary key**, never by a duplicated natural
string. Challenge every additional table (tag? item?) against the actual
requirement. If the requirement is too vague to decide, ask the user; if it's
clear, write the model down.

**Pin down each id's semantics explicitly** — is `profile_id` a global
sequence, or does numbering restart per account? Getting this wrong is a
requirements misread that surfaces months later; when the scope of an id is
ambiguous, ask. References to external systems are stored as plain id columns
(no FK across service boundaries). Avoid reserved words as table names
(`order` needs quoting forever).

## Engine family

Choose the family from the logical model, never from habit or from what the
team used last:

- **Relational** — entities relate to each other, invariants span rows
  (uniqueness, foreign keys, exclusion), reads are varied or ad hoc,
  writes touch several entities together. The default when in doubt.
- **Document** — each read fetches one aggregate whole, the aggregate is
  bounded in size, and invariants live inside it.
- **Key-value / wide-column** — every access pattern is known up front and
  is a key lookup or a range within one key; scale or a serverless,
  scale-to-zero deployment makes connection-based databases awkward.

Three inputs decide it: the data's shape (above), the **existing
environment** (an estate that already runs one database is a constraint —
from `context.md` or the requirements' environment section), and the
**deployment target** from the requirements. When the deployment target is
still unknown — architecture comes after this phase — recommend a family
anyway, name the assumption it rests on ("relational, assuming a
long-running service"), and record it as an open item with `Decide by:
phase 2`; if architecture overturns it, that is ordinary backtracking.
When no product is fixed either, the physical model still has to be
written in some dialect: name it in the same open item ("relational,
Postgres dialect, assuming a long-running service") — features such as
exclusion constraints or partial indexes exist only in some products, so
the later phases must see what they inherit. The
**product and version** (Postgres 17, DynamoDB, Firestore) are pinned in
stack selection unless the environment already fixes them — do not pick a
product from memory: research the current options at decision time.

## Relational: DDL defaults

- Every table — **including lookup, helper, and log tables** — gets
  `created_at` with `DEFAULT now()`, named exactly `created_at` (not
  per-table variants like `changed_at` or `received_at`); updatable tables
  also get `updated_at`, supplied on update by the backend from its injected
  clock — outbox and inbox tables count as updatable (a relay marks them
  published or processed). Insert-only tables drop `updated_at`, never `created_at`.
- An indexable primary key — **`bigint` identity by default**. Random
  UUIDs (v4) as keys cost real insert throughput and index health: every
  insert lands on a random B-tree leaf (cold pages, splits, bloat, WAL
  amplification) and the 16-byte width repeats in every referencing FK
  index. Use a UUID key only when ids are generated outside the database
  (client-side, multi-writer) or exposed publicly where enumerable ids
  leak — and then **time-ordered UUIDv7, not v4**, to restore insert
  locality. A hybrid is fine: bigint PK internally, a separate unique UUID
  column as the public identifier. When the public identifier must be short
  or human-friendly (read over the phone, typed from an email) and a UUID
  doesn't fit, the reference must still be **non-enumerable**: padding,
  prefixes, checksums, or a standard base-N encoding of a sequential value
  are order-preserving — anyone holding one reference can compute its
  neighbors (and ticket/order volume between two references). Derive it
  through a bijective scramble (e.g. multiply by an odd constant mod 2^k
  before encoding) or generate a random code behind a unique constraint
  with insert-retry. The test to apply: given one valid reference, can a
  stranger produce another valid one, or read how many exist? If yes, it's
  the sequential id in costume. Be honest about what a scramble buys: it
  defeats casual enumeration, not an adversary — the constant is
  recoverable from a handful of known id/reference pairs. When guessing a
  reference must be genuinely infeasible (it acts as a bearer credential),
  use random codes or UUIDs, never a derived value.
- One timestamp type (`timestamptz`) across the whole schema — never epoch
  `BIGINT` in one log table and `timestamptz` in its sibling.
- Statuses: FK to a lookup table or a DB enum — never free-text `VARCHAR`
  statuses or magic-number `CHECK (status_id IN (1,2,3))` duplicated across
  tables.
- Real columns for core entities. A JSONB column that holds the whole
  business object forces `->>'field'::type` casts into every query and view
  and forfeits constraints — reserve JSONB for genuinely unstructured
  payloads.
- Split append-only tables (status logs, failure details, dead letters) from
  updatable entities; logs are insert-only by design.

**Columns holding encoded values state their exact format.** A column
carrying a path, URL, code, or any encoded reference gets its precise
stored format in the data dictionary and the `COMMENT ON` ("full request
path incl. leading slash, e.g. `/articles/foo`" — not just "the
redirect source"). Producer and consumer both cite the column's stated
format; a format left implicit is a seam where two modules each guess
differently, both pass their own tests, and every real request misses.

## Relational: constraints — gauge, don't default

Add FK/unique/check constraints where the requirement genuinely demands
integrity; skip them where it doesn't. When unclear, ask the user and give a
recommendation. Both failure directions are real: shipping a core table with
its FKs commented out ("todo, confirm") leaves the central data unenforced,
while reflexive constraints on everything makes operations fight the schema.
Friction inserting test data by hand is a signal to write seed scripts — not
to weaken production constraints. For soft-state uniqueness, use a partial
unique index (`UNIQUE ... WHERE status <> 'cancelled'`) so terminal rows
don't block new active ones.

## Document stores

Shape documents by how they are read: **embed** what is read together and
stays bounded (an order's lines); **reference** what is shared, unbounded,
or updated on its own (the customer an order belongs to). One document is
the unit of atomicity: design write paths to touch a single document —
multi-document writes should not exist by design, and a multi-document
transaction is a sign the aggregate boundary is wrong. Give each collection
a validation schema and a `version` field for optimistic concurrency, and
an index per query, as in the relational case.

## Key-value and wide-column stores

**List every access pattern before designing a key.** The partition key
spreads load and is what every query must name; the sort key gives order
and ranges within a partition; each further access pattern costs a
secondary index or a copy of the data — and a pattern discovered later may
cost a migration, so ask about future reads now. Never put a scan on a
request path. Keep items well under the engine's size limit; keep unbounded
lists out of a single item. Put several entity types in one table only when
their access patterns are known and stable; otherwise, one table per
entity is easier to change.

Traps that bite: a table's key attributes are **copied into every
secondary index**, so a secret in a key (a pickup code, a token) leaks to
every view built on an index — keep credentials out of keys. A sparse index
with one constant partition value puts all its items on one hot partition;
fine at low volume only if you say so, otherwise shard it. A short,
guessable code needs a **durable attempt counter** (an item with a TTL, per
target, checked in the increment's own condition — `ADD attempts :one IF
attempts < :limit`). Reserve the attempt **before** the code is tried: the
conditional increment comes first and the code is checked only if it
succeeded — a read of the counter followed by a later increment lets
concurrent guesses all pass the read. Decide whether a successful pickup
gives its attempt back or counts against the budget, and size the limit so
real recipients at peak are not locked out. One generic failure response
for wrong, used and expired codes alike — rate limiting at the edge alone
is not enough. Work out what the
limit allows: live codes per target ÷ code space × guesses allowed per day
is the expected successful guesses per target per day; state it and record
it as an open item for the owner to accept. Prefer a digest of the code
(a keyed hash) as the lookup key over the plaintext code.

## Idempotency lives in the query

For every write path ask: should this create a new record or reuse one?
Inserts are keyed by a caller-provided unique key (`ON CONFLICT DO NOTHING` /
upsert). State transitions are guarded updates:

```sql
UPDATE "order" SET status = 'paid', updated_at = $now
WHERE order_id = $id AND status = 'unpaid';
```

so a redelivered message can't re-apply paid→paid. Zero rows matched is
ambiguous by itself — it covers "already applied" (fine for a retrying
consumer), "row doesn't exist", and "illegal state". Treat it as
already-applied only on paths where redelivery is the expected cause;
where the distinction matters, re-read the row and classify instead of
assuming success.

For state-machine transitions, **classify a suspected duplicate by the
row's current state, never by matching action history**: a retry is
recognized because the current state is one this exact call could have
left the row in (the call's target plus its own cascade); any other
state is a real illegal-transition error. Audit-log/EXISTS guards
("this action was already recorded") look equivalent but false-match
every legitimately repeating action — annual re-review cycles,
per-revision resubmit loops, any workflow that revisits a state by
design — and each patch (scoping by revision, discriminating creation
rows) just moves the false match somewhere else. State is the truth;
history is commentary. Guard inside
procedures too: `WHERE status NOT IN (<terminal states>)` prevents overwriting
final states.

**The same rules in document and key-value stores**: a create keyed by a
caller-provided key is a conditional put (`attribute_not_exists(pk)`, or
insert-if-absent on the unique key); a transition is a conditional update
on the current state (`status = :from`) or on the `version` you read. A
failed condition is the zero-rows case — classify it from the item's
current state the same way.

## Atomicity and round-trips

Two or more writes that belong together execute in **one network trip**: a
stored procedure/function, or a data-modifying CTE
(`WITH upd AS (UPDATE ...) INSERT ...`) — whichever the client stack supports. In a document or key-value store, writes that belong together
belong in **one item or document**; the engine's transactional write
exists, but has item limits and costs more — reaching for it on a hot path
means the model should change.

## Multi-system updates go through a queue

A "double update" is multiple systems each updating **their own** data from
the same source event (order completed → delivery and payment each react).
The source publishes the event once its required business logic has
succeeded; each consumer updates its own DB via the queue, so a failed
consumer retries independently. Never write another service's database
directly. And if the project is too small for microservices, don't imitate
the pattern — one database, one atomic update. Why it matters: partial
fan-out failures show users a paid-but-undelivered (or delivered-but-unpaid)
state with no retry path; queue consumers converge.

## Indexes follow access patterns

Create indexes from the queries the requirement implies — composite indexes
mirroring real `WHERE` clauses — plus the ops/debug paths ("sometimes we only
have the `account_id`"). Not blanket, not skipped.

## Schema evolution

Design expecting change: numbered migration folders with per-concern files
(tables / indexes / functions / seed data), additive changes first, and test
migration guards — an `information_schema` check that can never match makes
the guarded statement silently never run. In stores without a schema, the
reader tolerates both shapes during a change (a missing field has a
default) and a backfill finishes the move.

**Changes to an existing design** edit `data-design.md` in place: changed
entities, write paths and decisions keep their ids, new ones take the next
free id, nothing is renumbered — the document shows the current state.

## Before delivering — verify

Walk these checks against your actual output files; fix, don't rationalize:

- [ ] The header is present and exact; every open question and assumption
      is a row in `open-items.md`, and every provisional value in the
      document cites its row.
- [ ] The logical model and access-pattern table come first, with neutral
      types, and nothing above the engine-family row names an engine; the
      engine family is a `DD` row with the three inputs.
- [ ] When the deployment target is unknown, the family's assumption is an
      open-item row with `Decide by: phase 2`; a product named in this
      document is marked "pinned in stack selection". When no product is
      fixed, that row also names the dialect the physical model is
      written in.
- [ ] Every id whose scope the requirements leave open (per-parent or
      global numbering) has its own open-item row.
- [ ] Relational: every table — lookup, helper, inbox/dedup, and log tables
      included — has `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, named
      exactly `created_at`; `updated_at` present on updatable tables only.
- [ ] Every logical field appears in the physical artifacts; every
      physical table and column appears in `data-dictionary.yaml` and is
      either in the ER diagram or named in the physical-model section —
      walk each one.
- [ ] Every access pattern is served by a key or an index; every write
      path has a `W` row.
- [ ] Relational: `COMMENT ON` statements cover every table and column in
      the DDL. Other families: every schema field has a description.

## Common mistakes

- Choosing the engine first and fitting the model to it.
- Key-value keys designed before the access patterns are listed.

- Id scope misread (per-parent numbering vs global sequence) — ask early.
- Statuses as strings or magic-number CHECKs; needed FKs left commented out.
- Child tables joined by a duplicated natural key with no FK to the parent.
- One JSONB column as the whole schema of a core entity.
- Mixed timestamp representations across sibling tables.
- Indexes invented without an access pattern, or debug paths left unindexed.
- Constraints dropped for test-data convenience instead of writing seeds.
