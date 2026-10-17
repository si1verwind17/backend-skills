# Scenario 2: cancel-order feature, Scala 3

Purpose: verify the skill's concepts transfer across languages (it is
language-neutral by design; Scenario 1 is Python).

**Prompt**: identical task and constraints to [Scenario 1](1-cancel-order-python.md), with the stack
paragraph replaced by:

> Use Scala 3 (ZIO optional — plain Scala is fine; stub the web framework,
> DB driver, and broker client with simple traits/classes — no real server).
> The `scala` runner (Scala CLI) and sbt are available; a single-module
> Scala CLI project with `//> using` directives and munit (or plain
> asserts) is the simplest setup. The deliverable is the source tree +
> tests. Run the tests and make them pass.

**Checks**: the same 7 as Scenario 1, interpreted in Scala terms — e.g.
"inline now()" includes `Instant.now()`/`System.currentTimeMillis()` in
constructors or default parameter values; visibility hints via
`private`/`private[pkg]`; wire DTO = the JSON/request case class.
