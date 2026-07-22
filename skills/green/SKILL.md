---
name: green
description: The RED→GREEN gate — verify genuine red, run the test-quality reviewer, send in the EDFH adversary, then unlock implementation.
---

# /bdk:green — the gate

Scripts: `${CLAUDE_SKILL_DIR}/../../scripts`

Run the four stages in order. Do not skip a failed stage — each failure message says
exactly what to fix, and fixing tests is legal (you're still in RED).

## Stage 1 — genuine red

```
python3 <scripts>/bdk_gate.py verify-red
```
Fails if: tests pass already (implementation leaked into RED — revert to stubs, or the
tests can't fail and prove nothing), or failures are import/collection errors (add
signature-only stubs). Fix and re-run until it passes.

## Stage 2 — test-quality review  *(skipped at gear 5)*

Spawn the `bdk-test-reviewer` agent. Give it: the spec path, the registered test files
(`python3 <scripts>/bdk_state.py get test_files`), and the reviewer regex lists from
`.bdk/config.json`. If it returns FAIL: fix each finding, then re-run **Stage 1** (tests
changed) and this stage. When it returns PASS:
```
python3 <scripts>/bdk_gate.py record reviewer PASS
```

## Stage 3 — the EDFH adversary  *(skipped at gear 5)*

1. `bash <scripts>/bdk_worktree.sh create` → prints an isolated worktree dir.
2. Spawn the `bdk-edfh` agent with: the worktree dir (it must work ONLY there), the test
   files, and the exact test command from `.bdk/config.json`.
3. `bash <scripts>/bdk_worktree.sh remove <dir>` when it's done.
4. If **CHEATED**: it returns the degenerate implementation that passed. Record it:
   `python3 <scripts>/bdk_gate.py record edfh CHEATED`. Then run a mini property-hunt —
   which catalog pattern kills this cheat? (invariant? bound? round-trip? oracle?) Add the
   property to the spec (new P-ID) and its test, then restart from **Stage 1**.
   After 3 CHEATED rounds, present the residual cheat to the user and ask whether to
   accept it (recorded in the spec's EDFH section as an accepted gap) or keep going.
5. If **SURVIVED**: `python3 <scripts>/bdk_gate.py record edfh SURVIVED` and note the
   verdict in the spec's EDFH section.

## Stage 4 — unlock

```
python3 <scripts>/bdk_gate.py to-green
```

## GREEN rules (after the gate)

- Write the **simplest, most direct code that makes the tests pass** — transaction script
  is fine, duplication is fine, patterns are banned for now. "For this brief moment, speed
  trumps design" (Beck). Ugliness is corrected in REFACTOR with the tests as a net.
- Implement **nothing beyond the spec**: the Non-goals section is binding.
- Tests are frozen (hook-enforced). Wrong test? `/bdk:back-to-red <reason>`.
- All green → `/bdk:refactor`.
