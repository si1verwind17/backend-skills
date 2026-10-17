---
name: rendering-design-docs
description: >-
  Use when turning a set of design/requirements documents (requirements.md,
  data-design.md, architecture-design.md, stack-selection.md, or any domain's
  equivalent doc set) into a single HTML review page for a human reader —
  typically to present a review gate. The page is for people only; agents
  keep consuming the markdown.
---

# Rendering design docs

Produce one polished HTML page a human can open and act on at a review
gate — one tab per design step, so the reviewer reads the step they are
deciding, not one long scroll through everything. The markdown documents remain the **only source of
truth**: the page is generated from them, regenerated on any change, never
hand-edited, and never read by agents.

## The deliverable

`design-review.html`, written beside the doc set it renders (the same
`docs/backend-design/` — or the repo-root docs dir when rendering a
multi-service system view). It is generated on demand and never committed:
add it to `.git/info/exclude` the first time (see `documents.md` in the
`building-backend-services` skill folder). One file:

- **Self-contained, on the shipped theme**: inline
  [`theme/review-page.css`](theme/review-page.css) in a `<style>` and
  [`theme/review-page.js`](theme/review-page.js) in a `<script>` at the
  end of `<body>`, both **verbatim** — never write your own styling or tab
  logic; the page looks the same on every run, light or dark with the
  reader's system. Your job is the markup below. Without scripting the page
  still works: every tab's content is shown, one after another.
- **Diagrams in the theme's colours**: render every Mermaid block with
  [`theme/mermaid.json`](theme/mermaid.json) as its config and a
  transparent background — pre-rendered to inline SVG when a renderer is
  available locally (`mmdc -c theme/mermaid.json -b transparent`), so the
  page works fully offline; make each SVG's internal ids unique per diagram.
  Inlining the diagram library itself (initialised with the same config)
  also works offline, at the cost of a large file. A Mermaid CDN include is
  the acceptable fallback; it is the one permitted external dependency, and
  it means diagrams need network — say so in the page's footer note.
- Opens with an HTML comment and a visible footer note: *generated from
  the markdown sources on <date> — do not edit; regenerate instead; agents
  must consume the markdown, not this page.*

## Markup the theme styles

```html
<body data-gate="data">                       <!-- the gate tab's key -->
<div class="wrap">
<header class="top">
  <h1>parking-reservation <span class="what">· design review</span></h1>
  <p class="gen">Generated … from docs/backend-design/</p>
  <p class="sources">Not present: data-dictionary.yaml, context.md</p>   <!-- only when something is missing -->
  <div class="banner"><span class="chip blocking">Blocking</span><div class="rows">   <!-- only when an item blocks -->
    <p><span class="when">Data design · this step</span><span class="ids"><a class="idref" href="#OI-2">OI-2</a>, …</span></p>
    <p><span class="when">Architecture</span><span class="ids">…</span></p>   <!-- one row per step, in chain order -->
  </div></div>
</header>
<nav class="tabs">                                 <!-- between header and main, never inside the header; the theme draws it as the step rail -->
  <a class="tab change" data-tab="change" href="#change">Change</a>             <!-- only with a changes/ file -->
  <a class="tab" data-tab="requirements" href="#requirements"><span class="tn">0</span><span class="tl">Requirements</span> <span class="badge APPROVED">APPROVED</span></a>
  <a class="tab gate" data-tab="data" href="#data"><span class="tn">1</span><span class="tl">Data design</span> <span class="badge REVIEWED">REVIEWED</span> <span class="chip gate">Gate</span></a>
  <!-- a step tab the change touches adds, after its badge: <span class="touched"></span><span class="vh">touched by the change</span> -->
  <span class="spacer"></span>
  <a class="tab context" data-tab="context" href="#context">Context</a>        <!-- only with context.md -->
</nav>
<main>
  <section class="panel" data-tab="data">        <!-- no id: the tab key is not an element id -->
    <div class="panel-head"><span>Phase 1</span><span class="pn">Data design</span><span class="badge REVIEWED">REVIEWED</span></div>
    <section class="owed"><h2>Decisions owed at this step</h2>
      <div class="oi" id="OI-2"><p class="oi-title"><span class="chip blocking">Blocking</span><span class="oi-id">OI-2</span> <span class="oi-q">…question…</span></p>
        <dl><dt>Owner</dt><dd>…</dd><dt>Recommendation</dt><dd>…</dd><dt>Assumption in force</dt><dd>…</dd></dl></div>
      <div class="later"><h3>Due at later steps</h3>                            <!-- gate tab only -->
        <h4>Phase 2 · Architecture</h4><ul>                                       <!-- one group per later phase -->
          <li><span class="chip blocking">Blocking</span> <a class="idref oi-id" href="#OI-1">OI-1</a> …question…</li></ul>
        <h4>Phase 4 · Implementation · no tab</h4><ul>                           <!-- items with no tab are defined here -->
          <li><details id="OI-4"><summary><span class="oi-id">OI-4</span> …question…</summary><dl>…owner, recommendation, assumption…</dl></details></li></ul>
      </div>
    </section>
    <div class="doc">
      <h1>…</h1><p class="header-lines">Status: …
Form: …
Builds on: …</p>
      …the document, with <figure class="diagram"><svg>…</svg></figure> for each diagram…
    </div>
  </section>
  …one panel per tab…
</main>
<footer>…the generated-from-sources notice…</footer>
</div>
<script>/* theme/review-page.js, verbatim */</script>
</body>
```

Every defined id is an element whose `id` is the id as written, inside its
panel; every mention is `<a class="idref" href="#R3">R3</a>`. Blocking is
always the word in a `chip blocking`, never colour alone. The context
panel opens with `<p class="context-note">Background the steps read: …</p>`.

## The sources

Read `docs/backend-design/`: the step documents (`requirements.md`,
`data-design.md` + `data-dictionary.yaml` + `ddl/` or `schema/`,
`architecture-design.md`, `stack-selection.md`), `open-items.md`,
`context.md`, and any file under `changes/`. Each step document's status
comes from its own `Status:` line; each open item's step from its `Blocks`
and `Decide by` columns. Phases map to tabs as phase 0 = Requirements,
phase 1 = Data design, phase 2 = Architecture, phase 3 = Stack selection;
phase 4 (implementation) has no tab — its items go to the gate tab's
"later steps" list.

## Page structure

1. **Header** — service name, generation time, and — only when any open
   item is blocking — a **banner** naming the blocking items, one row per
   step they block (the gate step marked "this step"), each a link that
   opens its tab and scrolls to it.
2. **Tabs**, in this order:
   - **Change** — first, only while a file under `changes/` exists: the
     change file rendered, with the ids it touches linked; the step tabs it
     touches carry a marker.
   - **One tab per step that has a document**, in chain order:
     Requirements, Data design, Architecture, Stack selection. A step with
     no document has no tab (rendered after phase 1: two tabs). Each tab
     label shows the **phase number** (0–3, as the open items use it), its
     name and its status badge (DRAFT /
     REVIEWED / APPROVED, from the document's `Status:` line). There is no
     implementation tab.
   - **Context** — last, only when `context.md` exists, set apart from the
     step tabs (a gap or divider, a different style), with no number and
     no status badge. Its content opens with: *"Background the steps read:
     the existing environment, constraints, conventions, warts. Not a
     design step and not approved here."*
3. **Which tab opens.** The step at the gate: the earliest step tab whose
   document is not APPROVED, or the last step tab when all are approved.
   Each tab has its own URL hash (`#requirements`, `#data`,
   `#architecture`, `#stack`, `#change`, `#context`); a link with a hash
   opens that tab; an unknown hash opens the gate tab.
4. **Inside a step tab, in order:**
   - **Decisions owed at this step** — the open items whose `Blocks` or
     `Decide by` is this step, blocking first, each with owner,
     recommendation and assumption in force. On the gate tab, a second
     short list follows: items due at later steps, so nothing is hidden —
     one line each (id and question), grouped under one heading per phase;
     an item whose step has no tab keeps its owner, recommendation and
     assumption folded under that line.
   - **The document**, faithfully: all headings, tables, and lists;
     every Mermaid block as a diagram; SQL, schemas and code in
     syntax-styled code blocks; the data tab includes the dictionary and
     the DDL or schema files.
5. **Ids link everywhere.** Every stable id (`UC1`, `R3`, `E2`, `W1`, `AD4`,
   `EV2`, `SD1`, `OI-7`, …) is an anchor where it is defined — the anchor is
   the id exactly as written (`#OI-7`, `#R3`), so links stay stable across
   regenerations — and every mention elsewhere links to it, across tabs,
   switching to the right tab. An id mentioned but defined nowhere is shown
   unlinked and flagged.
6. **Diagrams in tabs.** A diagram renderer cannot lay out a hidden panel:
   render each tab's diagrams the first time that tab is shown (or before
   the panels are hidden), so every diagram appears whichever tab opens
   first.

## Faithfulness rules

- Render what the documents say — **never add, reword, summarize away, or
  "fix" content**. A rendering decision (grouping, layout) is yours; a
  content decision is not.
- Numbers, versions, and statuses appear exactly as in the sources; each
  document's header keeps its lines (`Status`, `Form`, `Builds on` on lines
  of their own).
- A source doc that is missing or unparseable is shown as such in the
  header — not silently skipped.
- The markdown files are not modified by rendering, ever.

## Before delivering — verify

- [ ] One HTML file, inline CSS and script, opens standalone (fully offline
      with pre-rendered SVG; with the CDN fallback, standalone except
      diagrams — and the footer says so); every Mermaid block from the
      sources appears as a rendered diagram, in the theme's colours
      (rendered with `theme/mermaid.json`, transparent background), and
      in its own place: under each heading, the diagram drawn from that
      heading's block — check one label from each against its source.
- [ ] One tab per step document present, in chain order, each with its
      status badge matching the document's `Status:` line; no tab for a
      missing step; no implementation tab; Change tab first only when a
      `changes/` file exists; Context tab last and visibly not a step.
- [ ] The gate tab opens by default; each tab's hash opens it.
- [ ] Every open item appears on the tab of its `Blocks` / `Decide by`
      step (blocking first) or in the gate tab's "later steps" list; the
      banner appears exactly when a blocking item exists.
- [ ] Every table and section present in the sources is present in the
      page, and the page's text matches the sources: compare the rendered
      text of each document with its markdown, list item by list item and
      row by row — a hand-written markdown converter breaks on wrapped
      lines and nested lists. Say in your reply that you did this, and
      what (if anything) differed.
- [ ] Every stable id resolves as an anchor, and links across tabs work.
- [ ] Source markdown files untouched; generated-for-humans notice present.

Write any generator script or scratch file outside the user's repository
(a temp directory), never beside the documents.

## Common mistakes

- Summarizing or paraphrasing source content instead of rendering it.
- One long page with every document stacked — the reviewer has to scroll
  past what they are not deciding.
- Open items listed only once at the top, away from the step that must
  decide them.
- External CSS/font/JS dependencies beyond the single diagram script.
- Editing the HTML by hand to fix a content issue that belongs in the
  markdown.
- Rendering a stale page at a gate — regenerate after every doc change.
