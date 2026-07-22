# The EDFH drill (Enterprise Developer From Hell)

Any finite set of example tests can be satisfied by a degenerate implementation: `return 4`
passes `1+3` and `2+2`; a lookup table passes every example you'll ever write; an "evil
sort" returning `[]` passes a sortedness check. Evil, stupid, and lazy developers all
produce the same outcome — and the most common "stupid developer" is **you, six months ago,
before you understood the requirements**. Tests must catch the outcome regardless of intent.

## The drill (run during brainstorm, step 7)

1. Look only at the example tests planned so far (B1…Bn).
2. Write down — honestly, adversarially — the *laziest, most literal, technically-compliant*
   implementation that passes all of them. Favorites:
   - hard-code the expected constant,
   - lookup table keyed on the exact test inputs, default to anything,
   - return the input unchanged / empty / zero,
   - special-case whatever pattern the examples share.
3. If such an implementation exists (it almost always does), the test plan is insufficient:
   pick the catalog property that kills it, add it as P*, and repeat until the paper-EDFH
   is dead.
4. Record the analysis in the spec's EDFH section: the cheat you found, the property that
   kills it, residual gaps you accept.

This paper drill primes the real `bdk-edfh` agent, which later attempts the same cheats
mechanically in an isolated worktree before GREEN unlocks. If the agent finds a cheat the
drill missed, the property-hunt reopens — that's the loop working, not failing.
