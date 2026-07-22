---
name: status
description: Show the current BDK feature, phase, gear, evidence freshness, and outstanding obligations.
---

# /bdk:status

Current state:

```
!`python3 "${CLAUDE_SKILL_DIR}/../../scripts/bdk_state.py" show`
```

Summarize for the user: feature, phase (and what that phase obliges), gear, spec path,
registered test files, red/green evidence freshness (`last_test_run` vs
`last_mutation_at`), reviewer + EDFH verdicts, throwaway tests pending deletion, and the
last few log lines. Then state the single next action (e.g., "fix reviewer findings, then
re-run /bdk:green stage 2").
