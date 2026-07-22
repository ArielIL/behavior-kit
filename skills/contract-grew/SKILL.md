---
name: contract-grew
description: Escape hatch — refactoring exposed genuinely new public contract; open a new RED for that surface instead of silently testing internals.
argument-hint: <what new public surface emerged>
---

# /bdk:contract-grew — new public surface deserves its own behaviors

Scripts: `${CLAUDE_SKILL_DIR}/../../scripts`
New surface: `$ARGUMENTS`

Cooper's caveat to "zero new tests during refactor": when refactoring exposes surface that
is *genuinely part of the module's contract* (not an internal that a test wants to peek
at), that surface gets its own behavior tests — through a proper RED, not ad-hoc.

1. Ask the distinguishing question honestly and record the answer: *"Is this genuinely part
   of the module's contract, or just an implementation detail?"* If detail → stop, leave it
   untested, return to REFACTOR.
2. If contract: append to the spec — new **B** entries (G/W/T) for the new surface, extend
   the Contract surface section, revisit Properties for it, append Changelog line
   `contract-grew <date>: <surface>`.
3. Run:
   ```
   python3 <scripts>/bdk_state.py phase RED "contract grew: <surface>"
   python3 <scripts>/bdk_state.py set red_evidence null
   python3 <scripts>/bdk_state.py set reviewer.verdict null
   python3 <scripts>/bdk_state.py set edfh.verdict null
   ```
4. Write the new tests (RED rules apply), then `/bdk:green` again.
