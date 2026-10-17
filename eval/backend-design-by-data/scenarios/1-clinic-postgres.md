# Scenario 1: clinic appointment service data layer

**Prompt** (verbatim, after the arm's preamble from [`eval/README.md`](../../README.md)):

> Design the data layer for a clinic appointment service, in
> <workdir>. Keep it quick — it's a small service. Requirements:
>
> - Patients book appointments at clinics. A patient account can have
>   several profiles (family members); staff refer to "profile number 2 of
>   this account" when talking to patients.
> - An appointment moves through: booked → confirmed → completed, or is
>   cancelled from booked/confirmed. History of these changes must be
>   auditable.
> - Payment is handled by a separate payment service; when an appointment is
>   completed, the payment service and the notification service both need to
>   act on it.
> - The booking-confirmation message from the payment gateway can be
>   delivered more than once.
> - The clinic front-desk app lists appointments by clinic and date; the
>   patient app lists them by account; support staff often have only an
>   account id when investigating.
>
> Use PostgreSQL. Produce whatever design artifacts you think an engineer
> should review and a next agent could implement from. You are working
> non-interactively: if you would ask the user something, record the exact
> question(s) prominently in your output, state your assumption, and proceed.

**Checks** (PASS/FAIL per run):

1. **Open questions surfaced**: the ambiguous profile-numbering requirement
   ("profile number 2 of this account" — per-account numbering vs global id)
   is raised as a row in `open-items.md` with an assumption in force; other
   assumptions are rows too, not a section of `data-design.md`.
2. **Deliverable contract**: `data-design.md` opens with the document header
   and has, in order, a logical model (Mermaid ER diagram, `E` ids, per-entity
   rationale, id semantics), an access-pattern table, the engine family as a
   `DD` row, per-table physical notes, a write-path table (`W` ids:
   idempotency → atomicity → queue decision), an index plan tied to access
   patterns, decisions, and evolution notes; plus a `data-dictionary.yaml`
   (per entity and field, type + purpose); plus a `ddl/` directory of numbered
   per-concern runnable `.sql` files consistent with the doc, including
   `COMMENT ON TABLE/COLUMN` statements mirroring the dictionary.
3. **DDL defaults**: every table — including lookup, helper, and log
   tables — has `created_at` (`DEFAULT now()`), named exactly `created_at`
   (not `changed_at`/`received_at` variants); `updated_at` where updatable
   (omitted on insert-only log tables); one consistent timestamp type
   (`timestamptz`); indexable PKs; no reserved-word table names.
4. **Status modeling**: appointment status as enum or FK-to-lookup (not free
   VARCHAR, not magic-number CHECKs); an append-only status-log child table
   keyed by the parent's PK with an FK.
5. **Idempotency in the query**: redeliverable confirmation handled via
   guarded update (`WHERE ... status = <previous>`) and/or unique-key insert
   with `ON CONFLICT`; zero-rows treated as already-applied for the retry
   path.
6. **Atomicity**: status change + status-log insert designed as one network
   trip (procedure/function or data-modifying CTE), with terminal-state
   guards.
7. **Ownership & queue decision**: payment service referenced by id only (no
   cross-service FK, no writing other services' data); completion fan-out to
   payment/notification via a published event consumed from a queue, with
   publish-after-required-logic — or an explicitly reasoned monolith
   collapse.
8. **Access-pattern indexes**: composite index for clinic+date, index for
   account-based listing, and the support/debug path (account id only)
   covered; no blanket indexing.

9. **State-classified idempotency** (added 2026-10-03 for `644da1d`):
   whether a redelivered/retried status transition was already applied is
   decided from the entity's CURRENT state (current status within the
   transition's own target/cascade closure → already applied), never by
   matching rows in the audit/status-log history.
