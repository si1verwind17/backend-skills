# Scenario 3: clinic again, no engine and no deployment given

**Prompt**: the [Scenario 1](1-clinic-postgres.md) prompt with the sentence "Use PostgreSQL." removed.

**Checks** (PASS/FAIL per run):

1. **Family recommended with its assumption**: a family is recommended as a
   `DD` row and the assumption it rests on (the deployment target) is named.
2. **Open item for architecture**: that assumption is a row in
   `open-items.md` with `Decide by: phase 2` (or the architecture phase),
   and the row names the dialect the physical model and DDL are written in
   (e.g. "Postgres dialect").
3. **Product left to stack selection**: no product version is pinned in the
   data design unless researched; a product named is marked as pinned later.
4. **Logical model unaffected**: the logical model and access-pattern table
   are complete and engine-neutral (S1 check 1's profile-numbering question
   still raised).
