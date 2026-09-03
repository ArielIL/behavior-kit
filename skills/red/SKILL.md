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
- **Property tests** use the library and idiom in `.bdk/config.json` (`pbt` field), with an
  explicit example budget (`max_examples` / `numRuns`).
- **No unseeded randomness anywhere in a test** — not `random.*`, `Math.random()`, `uuid4()`,
  `Date.now()`/`datetime.now()`, nor an unseeded faker, in the test or its fixtures. A
  varying input belongs in exactly one of three places: the spec's enumerated boundary values
  (write them as a parametrized/table-driven test, one named row each), a property test whose
  generator is the PBT library, or a fuzz target outside this suite. Inject the clock and ID
  generator through the port instead of reading the real ones. If you catch yourself
  reaching for a random value, read
  `${CLAUDE_SKILL_DIR}/../brainstorm/references/determinism.md` before writing the test.
- **Oracle strength for transforming surfaces.** When the port renders, serializes,
  converts, or formats content (markdown→PDF, model→CSV, template→HTML…), "the output
  contains the input's words" is the weakest oracle and will not survive EDFH. Write,
  already in RED: (a) a structural oracle — the format's metacharacters are absent or
  transformed in the output, checked over a checklist of the format's constructs, never
  one sample input; (b) generator alphabets that INCLUDE the format's metacharacters
  (an alphabet that can't emit `[`/`(`/`<` never exercises a markdown link); (c) an
  encoding round-trip (non-ASCII input survives to the output); (d) a size/pagination
  bound. Each of these, missing, has cost a full EDFH round in practice.
- **In source files: signature-only stubs.** The contract surface's signatures may be
  created so tests import cleanly, with bodies `raise NotImplementedError` / `throw new
  Error('not implemented')`. No logic — logic in RED defeats the gate.
- **Register every test file** as you create it:
  `python3 <scripts>/bdk_state.py append test_files "<relative/path>"`
- Low gear only: exploratory scaffolding tests are allowed but must be registered with
  `bdk_state.py append throwaway_tests "<path>"` — /bdk:done blocks until they're deleted.

## Context hygiene

The spec is self-contained by design — exploit that. If this conversation already carries
earlier phases or another feature, delegate the bulk authoring to ONE general-purpose
subagent instead of writing tests inline: give it the spec path, `.bdk/config.json`, and
the rules above verbatim, and spawn it with `model: sonnet` — test authoring from an
approved spec is not opus work. It writes the test files and stubs, registers each test file
(`bdk_state.py append test_files`), and returns a one-paragraph summary. Phase hooks apply
inside subagents too, so RED rules stay enforced. Only the summary lands in this session —
not every draft and test run.

## Exit

Run the suite yourself first; expect failures that are **assertion failures**, not
import/collection errors (fix those with stubs). Then run `/bdk:green`, which verifies
genuine red, reviews test quality, and sends in the EDFH adversary.
