# Property catalog (from Wlaschin's "Lazy Programmer's Guide")

Walk these eight questions for every feature. Each pattern kills a class of wrong
implementations; **properties compose — one is almost never enough** (sortedness alone is
satisfied by `return []`; add "output is a permutation of input" to kill it).

1. **Different paths, same destination** — Is there another sequence of operations that must
   land on the same result? (commutativity/associativity: `add(x,y)==add(y,x)`; negate-then-
   sort == sort-then-negate-reversed)
2. **There and back again (round trip)** — Is there an inverse that must return the start?
   (serialize→deserialize, write→read, add→remove, parse→regenerate). Weak alone — combine.
3. **Invariants** — What survives the operation unchanged? (sort/map preserve length; sort
   preserves contents/permutation; a balanced tree stays balanced after insert)
4. **Idempotence** — Does doing it twice equal doing it once? (sort, distinct, filter;
   critical for distributed systems: processing the same event twice == once)
5. **Structural induction** — Can correctness be stated as "solve smaller parts, combine"?
   (any divide-and-conquer algorithm or recursive data structure)
6. **Hard to prove, easy to verify** — Is checking a candidate output cheap even if
   producing it is hard? (a maze path is easy to walk; factors multiply back; split parts
   rejoin to the original; every adjacent pair in sorted output satisfies `a[i] <= a[i+1]`)
7. **Test oracle** — Is there an independent source of truth? (brute-force vs optimized;
   single-threaded vs parallelized; the legacy system being replaced)
8. **Stateful/concurrent → model-based; no ground truth → metamorphic** — For I/O, state,
   or concurrency: generate random operation sequences and diff the real system against a
   trivially simple in-memory model (an int counter found a months-old Erlang concurrency
   bug). No oracle at all? Assert *relations between outputs of related inputs* (rotate the
   photo → face location rotates equally).

Practical notes:
- Zero and identity elements are inputs you know the answer to **without an implementation**
  (`add(x,0)==x` killed the always-return-0 cheat). Hunt them.
- Comparing against a re-implementation of the same logic is an anti-pattern; find a
  genuinely independent property instead.
- Generators surface what humans forget: weird unicode, non-printables, huge/negative
  numbers, empty and single-element collections, duplicates, nulls.
- **A property test is the only licensed use of generated input** — because the library
  reports the seed, shrinks the counterexample, and replays it. That license does not
  extend to sprinkling `random.*` / `Math.random()` / `uuid4()` into an example test, which
  is just a flaky test. When the generator finds a counterexample, pin it as a named example
  test; the property keeps hunting. See `determinism.md` in this directory.
- **If no non-trivial property can be stated, the requirement isn't understood yet** — that
  is a requirements-discovery alarm, not a testing inconvenience. Loop back to behaviors.
- Keep example tests too: `2 + 2 == 4` documents intent at a glance; an abstract
  commutativity property doesn't. Properties for thoroughness, examples for communication.
