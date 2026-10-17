# Scenario 2: digest mode — founder's meeting notes

A fixture `business-brief.md` (tutor-marketplace founder notes, at
`eval/fixtures/writing-business-requirements/business-brief.md`) sits in the workdir. Planted traps: marketing
adjectives ("effortless", "fast and seamless"), a wish ("marketing might
want lesson data in the warehouse someday"), one TBD with a decider hinted
(tutor no-show policy — ops) and one without (commission percentage),
locked decisions (Zoom link only — no video build; Stripe — no card data;
manual tutor vetting), a lifecycle with a refund-window rule, sizing
numbers with a growth multiplier, GDPR, and environment context (AWS,
TypeScript team).

**Prompt**: "The founder's meeting notes are in `business-brief.md` in
<workdir>. Turn them into the requirements deliverable that an engineer
should review and a next agent could start designing from, in <workdir>.
You are working non-interactively: record the exact questions you would
ask, state your assumption for each, and proceed." (Same arm prefixes.)

**Checks:** the same as [Scenario 1](1-interview-bakery.md).
