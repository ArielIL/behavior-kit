# Behavior-first development (BDK doctrine)

This project develops with behavior-first TDD (Ian Cooper) + property-based testing
(Scott Wlaschin), enforced by the bdk plugin. Non-negotiables:

- **The trigger for a test is a requirement** ("the system should X"), never "I'm adding a
  method/class." Tests read as Given/When/Then behavior narratives.
- **The system under test is a module's public facade/port**, not a class. Internals stay
  private; never widen visibility (export, `_` import, `InternalsVisibleTo`) for a test.
- **Mocks are exceptional**: only for genuinely expensive resources or shared-fixture
  hazards, and each one must be justified in the feature spec's Mock Policy. Default is the
  real dependency or an in-memory fake. Never assert call counts/order as surveillance.
- **A "unit" test's isolation is from other tests** (no shared state, no order dependence),
  not from the code's real dependencies. A test hitting a real DB is fine if isolated.
- **Every feature ships at least one property test** (or a signed justification): invariants,
  round-trips, idempotence, oracles — see the bdk property catalog. Ask: "what degenerate
  implementation would pass my example tests?" and add the property that kills it.
- **Red before green**: a test must genuinely fail (assertion failure, not import error)
  before implementation. **Green is the dumbest code that passes** — speed trumps design.
  **Refactor is behavior-preserving with zero new tests.**
- Feature work runs through `/bdk:brainstorm → /bdk:red → /bdk:green → /bdk:refactor →
  /bdk:done`. The committed spec in `.bdk/specs/` is the behavior source of truth.
