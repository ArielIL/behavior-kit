---
name: red
description: Enter or resume the RED phase — write failing behavior tests from the approved spec, with signature-only stubs in source.
---

# /bdk:red — write the spec's tests (and nothing else)

Scripts: `${CLAUDE_SKILL_DIR}/../../scripts`

Preflight: `python3 <scripts>/bdk_state.py get phase` must be `RED`. If it's `BRAINSTORM`,
the spec isn't approved yet — go back to the brainstorm session. Read the spec at the path
from `python3 <scripts>/bdk_state.py get spec`.

## Rules for RED

- **Tests come from the spec's test plan, nothing else.** Name them after the IDs so
  traceability is mechanical: `test_B1_<behavior_slug>`, `test_P2_<property_slug>`
  (TS: `it('B1: …')`). Every B*/P* in the plan gets a test; no orphan tests.
- **Test the port** named in the spec's contract surface — never internal classes. Use
  Given/When/Then structure in the test body (arrange/act/assert on observable outcomes).
- **Doubles only per the spec's Mock Policy.** Real dependencies by default; the fixture
  and fakes conventions recon found are listed in the spec — reuse them.
- **Property tests** use the library and idiom in `.bdk/config.json` (`pbt` field).
- **In source files: signature-only stubs.** The contract surface's signatures may be
  created so tests import cleanly, with bodies `raise NotImplementedError` / `throw new
  Error('not implemented')`. No logic — logic in RED defeats the gate.
- **Register every test file** as you create it:
  `python3 <scripts>/bdk_state.py append test_files "<relative/path>"`
- Low gear only: exploratory scaffolding tests are allowed but must be registered with
  `bdk_state.py append throwaway_tests "<path>"` — /bdk:done blocks until they're deleted.

## Exit

Run the suite yourself first; expect failures that are **assertion failures**, not
import/collection errors (fix those with stubs). Then run `/bdk:green`, which verifies
genuine red, reviews test quality, and sends in the EDFH adversary.
