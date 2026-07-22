---
name: gear
description: Shift TDD gears for the active feature — 4 (default full cycle), 5 (skip-ahead for obvious implementations), or low (exploratory throwaway tests).
argument-hint: 4 | 5 | low
disable-model-invocation: true
---

# /bdk:gear — Cooper's gears

Scripts: `${CLAUDE_SKILL_DIR}/../../scripts`
Requested gear: `$ARGUMENTS`

- **4** (default): full cycle — brainstorm, genuine red, reviewer, EDFH, dumbest-green,
  refactor. `python3 <scripts>/bdk_state.py set gear 4`
- **5** (skip-ahead): the implementation is genuinely obvious. Reviewer and EDFH are
  skipped at the /bdk:green gate; red verification still runs. Self-police with coverage —
  the moment coverage slips you're writing speculative untested code: drop back to 4.
  `python3 <scripts>/bdk_state.py set gear 5`
- **low** (exploratory): you don't know the solution shape yet. Fine-grained scaffolding
  tests are allowed as a thinking aid, but each must be registered
  (`bdk_state.py append throwaway_tests <path>`) and **deleted before /bdk:done** — they
  couple future maintainers to implementation details.
  `python3 <scripts>/bdk_state.py set gear 3`

After setting, log it: `python3 <scripts>/bdk_state.py log "gear -> $ARGUMENTS (user)"`
