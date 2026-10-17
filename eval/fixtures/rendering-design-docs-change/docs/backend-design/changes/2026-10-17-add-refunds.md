# Change: add refunds for early-ended rentals

Why: customers who end a rental straight after opening a locker by mistake are charged today; support refunds them by hand.

Ids: adds R4; touches UC2 (end rental) and W2 (end-rental write path).

Phases: phase 0 (requirements) — reviewed, at the gate; phase 1 (data design) — next, for the refund write path; phases 2–3 — not touched; phase 4 — one slice after phase 1.
