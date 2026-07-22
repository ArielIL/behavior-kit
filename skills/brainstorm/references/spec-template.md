# Behavior Spec: <feature title>

- **Slug:** `<slug>`  ·  **Status:** DRAFT  ·  **Gear:** 4
- **Approved:** —
- **Changelog:** (back-to-red / contract-grew entries append here)

## 1. Requirement

One paragraph in user language. This requirement — nothing narrower — is the trigger for
every test below.

## 2. Behaviors

<!-- Given/When/Then, happy paths then edge cases. IDs are load-bearing: tests reference
     them by name (test_B1_...) and the reviewer checks traceability both ways. -->
- **B1** Given <initial state>, When <action>, Then <observable outcome>. `[example]`
- **B2** Given <edge state — empty/huge/duplicate/unauthorized/already-done>, When <action>,
  Then <observable outcome>. `[example]`

## 3. Non-goals

<!-- The anti-gold-plating contract. GREEN implements nothing on this list. -->
- Not handling <adjacent concern> (future feature).

## 4. Contract surface (the SUT)

Port/facade: `<PortName>` (existing | new)

```
<method>(<inputs with types>) -> <output type>
```

- Errors: `<ErrorA>`, `<ErrorB>`
- Observable side effects/events: `<event on outbound port>`

<!-- Signatures, error modes, observable events ONLY. Internal collaborators, data
     structures, and algorithms are banned here — they belong to GREEN/REFACTOR. -->

## 5. Property candidates

<!-- From the catalog: paths / round-trip / invariant / idempotence / induction /
     easy-verify / oracle / model-metamorphic. Tag each. -->
- **P1** `[invariant]` <what stays the same, for ALL inputs>
- **P2** `[idempotence]` <doing it twice == once>

<!-- If truly none: "No non-trivial property found — justification: <why> — signed by user
     <date>." This is an alarm, not a formality: try the catalog twice before signing. -->

## 6. EDFH analysis

Laziest implementation passing the examples alone: <describe the cheat>.
Killed by: <P-IDs>. Residual gaps accepted: <none | describe>.
EDFH agent verdict: — (filled by /bdk:green)

## 7. Test plan

| ID | Type | Level | SUT | Notes |
|----|----------|-------|------|-------|
| B1 | example  | port  | `<PortName>` | happy path, doc value |
| P1 | property | port  | `<PortName>` | generator: <what varies> |

Integration: <n> test(s) — adapter wiring only. E2E: <covered by … | 1 thin path>.

## 8. Mock policy

<!-- Default is REAL. Only two justifications exist: expensive resource, shared-fixture
     hazard. Anything else: use the real thing or an in-memory fake. -->
| Dependency | Double | Justification |
|------------|--------|---------------|
| `<dep>` | real | — |
| `<dep>` | in-memory fake | shared-fixture hazard: <what> |
| `<dep>` | mock | expensive resource: <what> |
