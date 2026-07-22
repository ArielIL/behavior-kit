---
name: off
description: Kill switch — disable all BDK enforcement in this repo (logged). Re-enable with "/bdk:off on".
argument-hint: [on]
disable-model-invocation: true
---

# /bdk:off — disable/enable BDK enforcement

Scripts: `${CLAUDE_SKILL_DIR}/../../scripts`
Argument: `$ARGUMENTS`

- If the argument is `on`: `python3 <scripts>/bdk_state.py on` — enforcement resumes at the
  recorded phase.
- Otherwise: `python3 <scripts>/bdk_state.py off` — all hooks go inert for this repo. The
  feature state is preserved, just not enforced.

Confirm to the user what state enforcement is now in.
