# Scenario 1: render the locker-rental doc set

Fixture: committed at `eval/fixtures/rendering-design-docs/docs/backend-design/`
(copy into `<workdir>/docs/backend-design/` before a run): four step
documents in the shared format, `open-items.md` and `context.md`. Ground
truth:

- statuses **3× APPROVED** (requirements, data design, architecture) and
  **1× DRAFT** (stack selection) → the stack tab is the gate tab and opens
  by default;
- **6 open items**: OI-5 and OI-6 block phase 3 (shown on the stack tab,
  and in the banner); OI-1 to OI-4 are due at phase 4 (no tab — shown in the
  stack tab's "later steps" list);
- **3 Mermaid blocks** (ER diagram, component flowchart, sequence diagram);
- stable ids UC1–UC2, R1–R3, NF1–NF2, OI-1–OI-6;
- `context.md` present → a Context tab, visibly not a step.

**Prompt** (verbatim, after the arm's preamble from [`eval/README.md`](../../README.md)):

> The design documents for the locker-rental service are under
> `docs/backend-design/` in <workdir>. Produce an HTML page a human
> reviewer can open to review this design set before implementation
> starts. When done, reply with ONLY: the file(s) you created and a
> one-line summary.

**Checks** (PASS/FAIL per run):

1. **Single standalone page**: one HTML file; inline CSS and script; no
   external dependencies beyond at most one diagram-rendering script (or
   pre-rendered inline SVG) — with the CDN fallback, the **visible footer**
   says diagrams need network access.
2. **Step tabs**: exactly four step tabs in chain order (Requirements, Data
   design, Architecture, Stack selection), each with its status badge (3
   APPROVED, 1 DRAFT) matching the document's `Status:` line; no
   implementation tab; without scripting, all content still readable.
3. **Gate tab opens**: the stack tab is open on load; each tab has a hash
   that opens it.
4. **Decisions where they belong**: OI-5 and OI-6 at the top of the stack
   tab; OI-1–OI-4 in its "later steps" list; each with owner,
   recommendation, assumption; a banner listing OI-5 and OI-6 that opens
   the stack tab.
5. **Context tab**: present, last, set apart, unnumbered, no status badge,
   opening with the "Background the steps read … not approved here." line.
6. **All diagrams and faithful content**: all 3 Mermaid blocks rendered;
   every table and section present; spot-checks unchanged (Node 24.9.0
   LTS, p99 < 800ms, R2 round-up rule, partial-unique-index idempotency).
7. **Ids link across tabs**: every stable id is an anchor; a mention in one
   tab (e.g. R1 in the data design) opens the defining tab at the id.
8. **Source-of-truth hygiene**: source files byte-untouched; the HTML
   carries a generated-from-sources / for-humans / do-not-edit notice.
9. **On the shipped theme**: `theme/review-page.css` and `review-page.js`
   inlined verbatim; the tab bar sits between header and main, each step
   tab's name in a `tl` span; panels carry
   no id; diagrams rendered with `theme/mermaid.json` (no default lavender);
   blocking shown by a `Blocking` chip, not colour alone; the later-steps
   list is one line per item, grouped under a heading per phase.
