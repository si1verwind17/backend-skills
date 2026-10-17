# Scenario 1: cancel-order feature

**Prompt** (verbatim, after the arm's preamble from [`eval/README.md`](../../README.md)):

> In a new Python project at <workdir>, implement an order-cancellation
> feature for an order service. Keep it quick — it's a small feature:
>
> - An HTTP endpoint `POST /v1/orders/{order_no}/cancel` with a JSON body
>   `{"reason": "...", "requested_by": "..."}`.
> - Cancellation is only allowed if the order's current status is `unpaid`
>   or `paid`; a `completed` or already-`cancelled` order must be rejected.
> - On success: update the order status to `cancelled` in the database,
>   append a status log row, and publish an `order_cancelled` event to a
>   message broker.
> - Include tests.
>
> Use plain Python (stdlib + whatever minimal structure you want; you may
> stub the web framework, DB driver, and broker client with thin placeholder
> classes — no need to install packages or actually run a server). The
> deliverable is the source tree + tests. Run the tests with
> `python -m unittest` (or pytest if available) and make them pass.
>
> Constraints: you are working non-interactively. If you would ask the user
> something before or during the work, write the exact question(s) into a
> file `QUESTIONS.md` in the project root, state your assumption, and
> proceed under that assumption. Write a short `NOTES.md` explaining your
> structural choices in 10 lines or fewer.

**Checks** (PASS/FAIL per run):

1. **Sizing question**: a question about the module's expected size/future
   growth is raised (QUESTIONS.md) before/while structuring, despite the
   "keep it quick" pressure.
2. **Layering**: business rules and orchestration are isolated from
   HTTP/serde/config/broker plumbing (separate modules/layers; persistence
   details hidden behind an interface the business code consumes).
3. **Domain ≠ wire**: the request/response wire shape is a distinct type
   from domain types, mapped at the boundary; business code never imports
   the wire type.
4. **Validation split**: malformed-JSON/shape checks happen at the edge;
   the status-based cancellation rule lives in domain/business code as a
   testable unit.
5. **Error ownership**: expected failures (not found, not cancellable) are
   typed and handled exhaustively in exactly one boundary place; no layer
   logs an error another layer also logs.
6. **Logging discipline**: logs are id-tagged events (order_no etc.), one
   per outcome, no raw payload/secret dumps, structurally parallel branches
   log symmetrically.
7. **Test tiers + injected time**: pure unit tests cover the cancellation
   rule; orchestration is tested with stubs; time comes from an injected
   clock (no inline now() in business logic).
