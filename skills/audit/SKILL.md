---
name: audit
description: Retro-review an existing feature against the behavior-first standard (Cooper + Wlaschin) without entering the phased workflow. Use whenever the user asks whether already-written code and its tests meet the standard, are over-mocked, or would survive a degenerate implementation.
argument-hint: <path | module | feature description>
---

# /bdk:audit — passive standards review

Audits code that was NOT built through the BDK phases. This arms nothing: no state
changes, no phase, no enforcement — safe to run anytime, including mid-feature elsewhere.

Scripts: `${CLAUDE_SKILL_DIR}/../../scripts`
Target: `$ARGUMENTS`

Config: use `.bdk/config.json` if present; otherwise detect the stack and read the
matching adapter from `${CLAUDE_SKILL_DIR}/../../adapters/` for the regex lists and test
command.

## Protocol

1. **Scope.** From the argument, identify: the module's public port(s) (exported surface),
   the implementation files behind them, and the test files exercising them. If there are
   no tests at all, stop — that is the audit result; offer `/bdk:brainstorm` to retrofit
   behaviors properly instead of bolting tests onto existing code.

2. **Behavior inventory.** Extract from the TESTS (not the implementation) what behaviors
   they actually pin down, as Given/When/Then sentences with B-IDs. Tests that can't be
   restated as a behavior get flagged now — they're testing mechanics, not requirements.

3. **Cooper review.** Spawn `bdk-test-reviewer` with the test files, the port names, the
   adapter regex lists, and the words **"AUDIT MODE — no spec exists"**. It returns
   file:line findings for: unjustifiable mocks (only expensive-resource / shared-fixture
   reasons count), call-count/order surveillance, private-symbol reach-ins, structure
   mirroring and method-named tests, shared-fixture hazards, pyramid misplacement,
   non-determinism (unseeded randomness, wall-clock, random IDs).

4. **Wlaschin review — property gap.** Read
   `${CLAUDE_SKILL_DIR}/../brainstorm/references/property-catalog.md` and walk the eight
   questions against the port's contract. List each pattern that applies but has no
   property test. Flag if the stack's PBT library (config `pbt`) isn't installed at all.

   Then read `${CLAUDE_SKILL_DIR}/../brainstorm/references/determinism.md` and classify
   every non-determinism finding from step 3 by cause: undefined edge cases (→ parametrized
   test over concrete boundary values), a real for-all-inputs claim (→ property test on the
   PBT library), or crash-hunting (→ fuzz target outside the per-commit suite). A randomized
   example test is a double finding: it is flaky *and* it marks an edge case the team never
   decided.

5. **EDFH verdict — the decisive check.** In a git repo:
   `bash <scripts>/bdk_worktree.sh create`, spawn `bdk-edfh` with the worktree dir, the
   test files, and the test command; it replaces the existing implementation with
   degenerate cheats (hard-code, lookup table, evil-sort) and reports whether the current
   tests catch them. `bash <scripts>/bdk_worktree.sh remove <dir>` after. This answers the
   real question: do these tests pin the behavior down, or do they merely pass?

6. **Report, then offer (don't do unasked).** Order findings by severity:
   (a) EDFH CHEATED — show the cheat and name the killer property from the catalog;
   (b) flaky-by-construction tests (non-determinism findings) with their cause and fix;
   (c) coupling smells (reviewer findings, file:line);
   (d) missing properties;
   (e) structural notes (naming, pyramid).
   Then offer two follow-ups: write a **retro-fit spec** at `.bdk/specs/<slug>.spec.md`
   from step 2's inventory (Status: IMPLEMENTED — future changes to this feature then
   enter the phased flow with documented behavior, and recon can read it), and/or **fix
   the findings** (test edits are unrestricted — no phase is armed).
