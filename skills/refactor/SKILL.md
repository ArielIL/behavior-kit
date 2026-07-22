---
name: refactor
description: Enter the REFACTOR phase — behavior-preserving structural improvement with zero new tests, protected by the green suite.
---

# /bdk:refactor — now make it clean

Scripts: `${CLAUDE_SKILL_DIR}/../../scripts`

Gate in:
```
python3 <scripts>/bdk_gate.py to-refactor
```
(Requires a fresh green run and an untouched test manifest; failures tell you what to fix.)

## REFACTOR rules

- **Behavior-preserving moves only**: extract function/class, rename, remove duplication,
  resolve code smells, introduce a design pattern *now that the solution's shape is known*
  (Kerievsky) — never speculatively.
- **Zero new tests** (hook-enforced). A newly extracted internal class gets no test — that
  keeps it free to change later. Feeling the pull to test something new means new behavior
  is sneaking in: `/bdk:contract-grew` opens a proper new RED for it if it's genuinely new
  public contract; otherwise it's implementation detail — leave it untested.
- **Keep internals private.** Never widen visibility (`export`, `_`-import,
  `InternalsVisibleTo`) so a test can reach in.
- Run the suite after every move (`python3 <scripts>/bdk_gate.py run-tests`); the Stop
  hook will refuse to end the session red anyway.

Done improving → `/bdk:done`.
