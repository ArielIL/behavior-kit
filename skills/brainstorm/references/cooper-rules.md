# Cooper doctrine (condensed from "TDD, Where Did It All Go Wrong")

## The one root rule
Do not test implementation details — test behaviors. The trigger for a new test is
*"I have a requirement"* (add money to an account, upload a file), never *"I'm adding a
method to a class."* A method-shaped test couples you to an unstable implementation choice;
a behavior-shaped test survives every refactor.

## What is the system under test
The **public facade/port of a module** — its exports, not its internal classes. A class may
*happen* to be the facade; it is never the unit of testing just because the language makes
you write classes. Ports-and-adapters gives the boundary a home: technology-free domain
core, adapters for all I/O, developer tests aimed at the port.

## "Unit" reclaimed
The unit of isolation is **the test** (no shared fixtures, no order dependence) — NOT the
class under test. Mock-everything "for isolation" is a misreading and is the direct cause of
refactor-breaking test suites. Classicist testing is legitimate: a test may talk to a real
database/filesystem when there's no shared-fixture hazard and speed is acceptable.

## Mocks: the policy
Legitimate: expensive-to-create resources; genuine shared-fixture hazards.
Illegitimate: isolation-by-default; surveillance (asserting call counts/order/params to
police *how* something was implemented — "it couples your test to your software; it's never
worth it"). Prefer real deps, then in-memory fakes, then mocks — in that order.

## Red — Green — Refactor, properly
- **Red**: the test must be *capable of failing* and must be seen failing for the right
  reason (assertion), not accidentally (import error) or never (a test that always passes
  proves nothing).
- **Green**: "for this brief moment, speed trumps design" (Beck). Write the ugliest,
  fastest thing that passes — transaction script, copy-paste, no patterns. You cannot
  simultaneously discover a solution and engineer it cleanly; don't try.
- **Refactor**: this is where clean code happens — extract, dedupe, resolve smells,
  introduce patterns *now that the shape is known* (Kerievsky). Hard rule: **zero new tests
  during refactor.** A newly extracted internal class gets no test — that keeps it free to
  change. If you feel the pull to add a test, new behavior is sneaking in: take it back to
  Red. Exception: if refactoring exposed *genuinely new public contract*, that surface
  deserves its own behavior tests later — ask "is this really part of my module's contract?"

## Gears
- **4th (default)**: the full cycle above, for discovering unknown solutions.
- **5th (skip-ahead)**: implementation is obvious — write the correct code directly.
  Self-police with coverage: the moment coverage slips, you're writing speculative untested
  code; drop back to 4th.
- **Low (exploratory)**: you don't know how to solve it — write fine-grained throwaway
  tests (or use a REPL) purely to think. **Delete them afterward**; they were scaffolding
  for you, and leaving them couples future maintainers to implementation details.

## Test distribution
Pyramid, not inverted: most coverage from fast port-level behavior tests; integration tests
only verify *your adapter is wired correctly* (never re-test third-party code); a thin E2E
layer. Red flags: IoC registrations inside a test; suites red "because not implemented yet";
a blame process for broken tests (proof nobody values them).
