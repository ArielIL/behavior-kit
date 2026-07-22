---
name: peek
description: Escape hatch — allow Claude to read one specific source file during BRAINSTORM, logged. Use sparingly; the recon agent is the intended path.
argument-hint: <project-relative file path>
disable-model-invocation: true
---

# /bdk:peek — logged one-file exception to the brainstorm read-block

Scripts: `${CLAUDE_SKILL_DIR}/../../scripts`
File: `$ARGUMENTS`

```
python3 <scripts>/bdk_state.py append peek_allow "$ARGUMENTS"
python3 <scripts>/bdk_state.py log "peek granted: $ARGUMENTS (user)"
```

Then read the file. Remember the thin line: use what you learn to describe *behavior and
contract* in the spec — do not let internal structure leak into the behaviors, and do not
propose implementation approaches during BRAINSTORM.
