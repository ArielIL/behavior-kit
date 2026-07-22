---
name: back-to-red
description: Escape hatch — a test is wrong or the desired behavior changed; reopen RED with a logged reason so tests can be edited again.
argument-hint: <reason>
---

# /bdk:back-to-red — reopen RED (logged)

Scripts: `${CLAUDE_SKILL_DIR}/../../scripts`
Reason given: `$ARGUMENTS`

This unfreezes the tests. It is legitimate when a test asserted the wrong behavior or the
user changed what they want. It is NOT for "the test is inconvenient for my
implementation" — if that's the situation, say so to the user plainly instead of using this.

1. If you (Claude) are invoking this rather than the user, first confirm with the user via
   AskUserQuestion: state which test is wrong and why, and get their go-ahead.
2. Append to the spec's Changelog line: `back-to-red <date>: <reason>`.
3. Run:
   ```
   python3 <scripts>/bdk_state.py phase RED "<reason>"
   python3 <scripts>/bdk_state.py set red_evidence null
   python3 <scripts>/bdk_state.py set reviewer.verdict null
   python3 <scripts>/bdk_state.py set edfh.verdict null
   ```
   (Verdicts are stale once tests change — /bdk:green re-earns them.)
4. Update the spec's Behaviors/Properties if the behavior itself changed, then edit the
   tests, then go through `/bdk:green` again.
