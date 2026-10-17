# Scenario 1: interview mode — fuzzy bakery ask

**Prompt** (verbatim, after the arm's preamble from [`eval/README.md`](../../README.md)):

> A business stakeholder gives you this ask, verbatim: "We run a small
> bakery chain — five shops. We want customers to pre-order baked goods
> online and pick them up in shop. Some items sell out during the day;
> also our regulars should be able to repeat their usual order easily.
> That's the idea — you figure out what you need to know."
>
> Produce the requirements deliverable that an engineer should review and a
> next agent could start designing from, in <workdir>. You are working
> non-interactively: record the exact questions you would ask the
> stakeholder, state your assumption for each, and proceed.

**Checks** (PASS/FAIL per run, both scenarios; "S1:" / "S2:" mark what a check expects in each):

1. **Uniform deliverable**: a requirements doc opening with the document
   header (`Status:` DRAFT or REVIEWED with a date, never APPROVED; `Form:
   design`; `Builds on:`), the full section set (summary, locked decisions,
   actors, use cases, rules, integrations, non-functionals, environment,
   out of scope, a §10 that points to `open-items.md`) and stable ids
   (LD/UC/R/NF) used consistently.
2. **Locked decisions separated**: stakeholder-fixed choices captured as
   locked (S2: Zoom-not-building-video, Stripe, manual vetting) and not
   re-litigated or redesigned.
3. **Lifecycle explicit**: states AND forbidden transitions spelled out
   (S2: booked→completed→paid-out, refund window, no refund inside 24h;
   S1: order/pickup lifecycle incl. sold-out handling), with verifiable
   acceptance criteria on use cases.
4. **Rules testable with sources**: each business rule a single testable
   statement citing its source; guardrails present (S2: no double-booking,
   one review per completed lesson, 48h edit window); non-goals only in §9,
   one per line, never as a rule's tail.
5. **No vague survivors**: marketing adjectives do not appear inside rules
   or acceptance criteria — translated into measurable non-functionals or
   pending decisions.
6. **Wishes and TBDs handled**: speculative wishes recorded as
   anticipated-future notes, not requirements (S2: warehouse "someday");
   every TBD is a row in `open-items.md` — and nowhere else — with an owner
   (S2: no-show → Ops; commission → assigned, e.g. Business) and a stated
   interim assumption.
7. **Non-functionals & environment captured**: criticality, sizing +
   growth, compliance (S2: GDPR) recorded; environment context (S2:
   AWS/TypeScript) passed through; the deployment target (long-running vs
   serverless) stated or an open item; S1 unknowns appear as open items,
   not inventions.
8. **Stop-rule discipline**: no design leakage — no schemas, table
   definitions, endpoint specs, or tech-stack choices in the requirements
   doc; the elicitation-question list is bounded and prioritized, not an
   exhaustive interrogation.
9. **Provisional values carry their id**: every interim figure or
   "proposed / to confirm" value in the document cites its open-item row
   (e.g. "48 h (proposed — OI-3)").
