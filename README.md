# bdk — Behavior-first Development Kit for Claude Code

A Claude Code plugin that makes Claude develop the way you do: **behavior-first TDD**
(Ian Cooper, *"TDD, Where Did It All Go Wrong"*) with **property-based testing**
(Scott Wlaschin, *"The Lazy Programmer's Guide to Writing Thousands of Tests"*).

It exists because Claude's default failure modes are exactly what those talks warn
against: tests written last, implementation-driven tests, over-mocking, no edge cases,
and implementation talk before behavior is agreed.

## The workflow

```
/bdk:brainstorm <feature>   BRAINSTORM  behavior-only session → committed spec
        ↓ user approves         RED     failing behavior tests from the spec
/bdk:green (the gate)         GREEN     verify genuine red → reviewer → EDFH adversary
        ↓                                → simplest code that passes (tests frozen)
/bdk:refactor              REFACTOR     structure only, zero new tests, stay green
        ↓
/bdk:done                     IDLE      final checks, spec archived as living doc
```

Escape hatches (all logged): `/bdk:back-to-red <reason>` · `/bdk:contract-grew` ·
`/bdk:gear 4|5|low` · `/bdk:peek <file>` · `/bdk:off` · `/bdk:status`

**Passive mode**: `/bdk:audit <path|feature>` retro-reviews code written *outside* the
phased workflow — behavior inventory from the tests, the Cooper reviewer in audit mode,
a property-gap walk of the catalog, and the EDFH adversary against the existing tests in
a worktree. No phases armed, nothing enforced; produces a findings report and offers a
retro-fit spec. Because skills are auto-invocable, a plain question like "does this
feature meet my testing standard?" triggers it too.

**Audit the audit**: `/bdk:check-session <session-id>` (or
`scripts/bdk_session_check.py <id>`) replays a past session's transcript from
`~/.claude/projects/` and grades whether the audit protocol actually ran: skill invoked,
reviewer in AUDIT MODE with a verdict, EDFH adversary inside a pre-created worktree with a
verdict, worktree cleaned up, no phase state touched, findings report delivered. Exit 0 =
proper, 2 = protocol violations.

## What's enforced, and how

- **BRAINSTORM**: hooks block Claude from reading source and from editing anything but the
  spec. Repo context flows only through the `bdk-recon` agent, which reports behavior
  (Given/When/Then, ports, invariants, hazards) and is forbidden from reporting internals —
  the "informed but not implementation-driven" thin line, enforced by context separation.
- **RED→GREEN gate**: tests must *genuinely fail for the right reason* (assertion failures,
  not import errors); the `bdk-test-reviewer` agent rejects implementation-coupled tests
  (unjustified mocks, call-count surveillance, private reach-ins, missing traceability);
  the `bdk-edfh` agent tries hard-coding, lookup tables, and evil-sort cheats against your
  tests in an isolated git worktree — GREEN unlocks only when the tests defeat it.
- **GREEN**: test files are frozen by hook. The spec's Non-goals bound the implementation.
- **REFACTOR**: adding a test function is denied by hook (Cooper: zero new tests during
  refactor; `/bdk:contract-grew` handles the legitimate exception).
- **Always**: Claude cannot end its turn while the feature's tests are red or stale — the
  Stop hook runs the scoped suite and blocks.

The kit is **inert** anywhere `.bdk/state.json` doesn't exist or is disabled — hooks exit
in ~10ms without it. Enforcement is defense against drift, not against an adversary.

## Install

```bash
# try it locally
claude --plugin-dir /path/to/behavior-kit

# or add as a marketplace and install
/plugin marketplace add /path/to/behavior-kit
/plugin install bdk@bdk-marketplace
```

Then per project: `/bdk:init` (detects Python/pytest+hypothesis or TS/vitest+fast-check,
writes `.bdk/config.json`, installs the doctrine rules file, sets gitignore entries).

## Layout

```
skills/      slash commands: brainstorm, red, green, refactor, done, + escapes
agents/      bdk-recon, bdk-test-reviewer, bdk-edfh
hooks/       hooks.json → scripts/bdk_hooks.py (single dispatcher)
scripts/     bdk_hooks.py, bdk_gate.py, bdk_state.py, bdk_common.py, bdk_worktree.sh
adapters/    python.json, typescript.json, _adapter-schema.md (add your stack here)
rules/       behavior-first.md — the ~20-line always-on doctrine
tests/       the kit's own tests (written BDK-style: behavior + property tests)
```

Per project: `.bdk/config.json` (committed), `.bdk/specs/*.spec.md` (committed — living
behavioral documentation), `.bdk/state.json` + `history/` + `tmp/` (gitignored).

## Philosophy in one paragraph

Test behaviors through a module's public port, never implementation details; mocks only for
expensive resources or shared-fixture hazards. Red must genuinely fail; green is the
dumbest code that passes ("speed trumps design" — Beck); refactor is behavior-preserving
with zero new tests. Any finite set of examples can be gamed by a degenerate implementation
— so every feature also states properties (invariants, round-trips, idempotence, oracles)
that hold for *all* inputs, and an adversary verifies the tests can't be cheated before
implementation begins. If you can't state a property, you don't understand the requirement
yet — that's the alarm, not the inconvenience.
