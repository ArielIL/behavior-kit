---
name: check-session
description: Verify that a past Claude Code session properly ran the /bdk:audit protocol — locates the session transcript by ID and grades each audit checkpoint.
argument-hint: <session-id | transcript path>
---

# /bdk:check-session — audit the audit

Scripts: `${CLAUDE_SKILL_DIR}/../../scripts`
Session: `$ARGUMENTS`

Run:
```
python3 <scripts>/bdk_session_check.py "$ARGUMENTS"
```

It searches `~/.claude/projects/*/<id>.jsonl` (a path works too) and grades: audit skill
actually invoked · reviewer spawned in AUDIT MODE · reviewer verdict returned · EDFH
adversary ran · inside a worktree created beforehand · worktree cleaned up · EDFH verdict
returned · no phase state touched · a findings report delivered last.

Relay the checkpoint table to the user verbatim, then interpret: FAILs mean the session
answered from opinion rather than running the machinery (or ran it unsafely); WARNs are
hygiene issues. If the transcript isn't found, the session likely ran on another machine
or under a different projects dir — ask the user where it ran.
