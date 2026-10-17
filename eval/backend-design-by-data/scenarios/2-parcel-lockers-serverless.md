# Scenario 2: serverless, key-value-shaped data

**Prompt** (verbatim, after the arm's preamble from [`eval/README.md`](../../README.md)):

> Design the data layer for a parcel-locker service, in <workdir>.
> Requirements:
>
> - It runs on AWS Lambda behind API Gateway and must scale to zero at
>   night; the team wants no database servers to manage.
> - A courier drops a parcel into a locker: the service records the drop
>   and generates a 6-digit pickup code, valid 72 hours.
> - The recipient opens the locker with the code; each code works once.
> - The courier app lists today's drops for one courier; the support tool
>   looks up a parcel by its tracking number; a nightly job finds drops
>   older than 72 hours that were never picked up.
> - The courier app retries a drop request when the network is flaky.
> - About 40,000 drops a day across 900 lockers, peaks at 7–9 am.
>
> Produce whatever design artifacts you think an engineer should review and
> a next agent could implement from. You are working non-interactively: if
> you would ask the user something, record the exact question(s)
> prominently in your output, state your assumption, and proceed.

**Checks** (PASS/FAIL per run):

1. **Logical first**: entities, ids and invariants (one-use code, 72-hour
   validity) and an access-pattern table come before any engine, and name
   no engine.
2. **Family from the inputs**: the engine family is a `DD` row whose reasons
   cite the access patterns and the serverless, scale-to-zero deployment;
   key-value (or document) chosen — or relational with an explicit, reasoned
   answer to the connection problem under Lambda.
3. **Keys from access patterns**: partition and sort keys (and secondary
   indexes) designed so every listed access pattern is a key lookup or a
   range query; the nightly job uses an index or a time-keyed design, not a
   table scan on a request path (a scan in the batch job must be called out
   and justified).
4. **Idempotency by condition**: the retried drop is a conditional put on a
   caller-provided key; the one-use code is a conditional update on the
   current state (never a read-then-write); a failed condition is classified
   from the current item.
5. **Right artifacts**: a `schema/` (or equivalent) with the table and index
   definitions in the engine's format and field descriptions — no `ddl/` of
   SQL; the dictionary and the design agree.
6. **Code security**: a 6-digit code is treated as guessable — attempt
   limiting or lockout, with the attempt reserved by a conditional
   increment **before** the code is tried (a read of the counter as the
   gate fails), and codes unique among active drops per locker (or the
   collision handled).
7. **Product pinned later**: the design names the family; if it names a
   product, it says the version is pinned in stack selection (or researched,
   not from memory).
