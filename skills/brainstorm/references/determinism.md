# Determinism: no unseeded randomness in tests

**Same commit, same verdict, every run — on every machine.** A test whose input varies
run-to-run without a recorded seed is flaky by construction: it goes red at 3am on someone
else's laptop with an input nobody can reproduce, and the team learns to re-run instead of
to read. One such test discredits the whole suite.

Banned inside a test (and inside its fixtures/factories):
`random.*` without a fixed seed, `Math.random()`, `uuid4()`, `os.urandom`, `Date.now()`,
`datetime.now()`, `faker` without `seed_instance`/`seed`, set/dict iteration order, and any
"pick a value so the test isn't hard-coded" trick.

## The urge to randomize means one of three things

**1. The edge cases were never defined** (the usual case — and a spec bug, not a test bug).
Randomizing an input hides that you don't know which inputs matter. Name them instead:
minimum, minimum−1, maximum, maximum+1, zero, empty, one element, two, many, duplicates,
negative, boundary of each validation rule, and the awkward strings (unicode, whitespace,
very long). Write them as a table-driven / parametrized test — one row per interesting
value, each row named. A failure then reports *which* value broke, at no cost in coverage.
Loop back to the spec's Behaviors section and record those values there.

**2. It should be a property test.** The requirement really does hold "for all inputs" —
so state the property and let the stack's PBT library (`.bdk/config.json` → `pbt`) generate.
Framework randomness is legitimate where ad-hoc randomness is not, because the framework
**reports the seed, shrinks the counterexample, and replays it**. Rules that keep it that
way:
- Use the library (`hypothesis` / `fast-check`) — never a hand-rolled loop over `random`.
- Fixed budget per test (`max_examples` / `numRuns`), so the suite's runtime is predictable.
- Keep the failure database (hypothesis `.hypothesis/`, fast-check `seed`+`path` in the
  failure output) and, when a counterexample is found, **pin it as a named example test**.
  That regression is now deterministic forever; the property keeps hunting for the next one.
- No PBT library available? A loop over an explicitly seeded generator
  (`random.Random(1234)`) is acceptable — deterministic, but no shrinking, so prefer the
  library. An unseeded generator is never acceptable.

**3. It should be a fuzz test.** You want to hunt crashes over a large input space with a
time budget and a corpus. That is a separate target (`atheris`, `libFuzzer`, `jazzer`,
vitest fuzz job), run on its own schedule with its own budget — **not part of the per-commit
suite, and never a RED→GREEN gate**. Every crash it finds comes back as a named example
test in the normal suite.

## Related non-determinism, same rule

Time, identity, and ordering are inputs too. Inject the clock and the ID generator through
the port (or use the framework's fake timers) rather than asserting on "now"; sort before
comparing collections whose order is not part of the contract. Freezing them is what makes
"expired code is rejected" testable at all.
