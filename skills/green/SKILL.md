---
name: green
description: The RED→GREEN gate — verify genuine red, run the test-quality reviewer, send in the EDFH adversary, then unlock implementation.
---

# /bdk:green — the gate

Scripts: `${CLAUDE_SKILL_DIR}/../../scripts`

Run the four stages in order. Do not skip a failed stage — each failure message says
exactly what to fix, and fixing tests is legal (you're still in RED).

**Never pass a `model` parameter when spawning agents in this skill.** The bdk agent
definitions pin their own models; for general-purpose helpers (killer tests etc.) pass
`model: sonnet` explicitly. Overriding to opus multiplies the gate's cost for no gain —
harvesting literals from assertions is not opus work.

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
changed) and this stage.

**Scoped re-review:** when this stage runs again after a CHEATED round (Stage 3 added
killer tests to an already-PASSed suite), give the reviewer ONLY the files that changed
since its last PASS, and say so in its prompt. A full re-review of unchanged files buys
nothing and costs a fresh agent context.

When it returns PASS:
```
python3 <scripts>/bdk_gate.py record reviewer PASS
```

## Stage 3 — the EDFH adversary  *(skipped at gear 5)*

1. `bash <scripts>/bdk_worktree.sh create` → prints an isolated worktree dir.
2. Spawn the `bdk-edfh` agent with: the worktree dir (it must work ONLY there), the test
   files, and the exact test command from `.bdk/config.json`.
3. `bash <scripts>/bdk_worktree.sh remove <dir>` when it's done.
4. If **CHEATED**: the verdict lists EVERY seam it found (the agent probes all cheat
   classes, not just the first hit). Record it:
   `python3 <scripts>/bdk_gate.py record edfh CHEATED`. Then run a mini property-hunt for
   **all listed seams in this one round** — which catalog pattern kills each cheat?
   (invariant? bound? round-trip? oracle?) Add every property to the spec (new P-IDs) and
   their tests, then restart from **Stage 1**. Never patch one seam per round: each extra
   round costs a full fresh EDFH context (~200–450k tokens observed in practice).

   **Replay-prove the killers.** The verdict contains each cheat's implementation
   verbatim. The agent adding the killer tests must apply each cheat in the worktree, see
   its new test fail, then revert — a killer that was never seen killing is a guess.

   **Round 2+ is verification, not a second expedition.** Tell the next EDFH spawn, in
   its prompt: which seams are already killed and replay-proven, that repo exploration
   is done (point it at the new tests only), and to spend at most 2 novel attempts before
   returning SURVIVED. A full re-exploration round costs 3–5× a verification round.
   The killer must be a **property test on the PBT library** or a parametrized example test
   over named boundary values — never an example test with a random input. Throwing
   `random.randint()` at a cheat kills it only on the runs where the draw happens to land
   right; it buys a flaky suite and no guarantee.
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
- **Context hygiene:** in a long session, delegate the implementation to ONE
  general-purpose subagent (give it the spec path, the failing tests, and these rules);
  only its summary returns here. The long-lived session orchestrates — it should not
  carry every edit and test run in its context.
- Tests are frozen (hook-enforced). Wrong test? `/bdk:back-to-red <reason>`.
- All green → `/bdk:refactor`.
