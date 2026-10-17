# Scenario 5: import a repository over the size threshold (light pass)

Fixture: `eval/fixtures/building-backend-services-import-large/` — the [Scenario 3](3-import-small-repo.md)
service grown past 5,000 lines of source, with migrations, route
registration, deploy and CI files and a README; copy into <workdir>, `git
init` and commit. **Seeds**: Scenario 3's cancel defect, plus a second defect deep
in the pricing module's code (a rounding function that rounds down while its
docstring says up) — in no file a light pass reads.

**Prompt**: the [Scenario 3](3-import-small-repo.md) prompt, verbatim.

**Checks** (PASS/FAIL per run):

1. **Plan first, over the threshold**: the first row of `open-items.md` is
   the read plan with a line count over the threshold, the light pass as
   the plan, and the scope options.
2. **Light-pass set only**: the files read are the build, entry, deploy
   and CI files, the migrations, the route registration, the README —
   no module source file (services, repositories, SQL queries, domain
   code).
3. **Partial documents, marked**: `requirements.md` and `data-design.md`
   list each module area as `not yet imported` with a pointer; entities
   come from the migrations, use-case names from the routes; no rule or
   write path is claimed for an area that was not read.
4. **No deep claims**: nothing in the documents describes pricing rounding
   or cancellation rules (reading them would be a deep import).
5. **Format and hygiene**: `Form: built` headers, `file:line` provenance,
   open items in one place, no code changes, and a gate asking the user to
   approve the documents as they stand.
