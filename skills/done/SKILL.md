---
name: done
description: Close out the active BDK feature — final green verification, no new tests since RED, throwaway scaffolding deleted, spec finalized and archived.
---

# /bdk:done — close the loop

Scripts: `${CLAUDE_SKILL_DIR}/../../scripts`

```
python3 <scripts>/bdk_gate.py verify-done
```

If it fails, the message lists exactly what's outstanding (red suite, new test functions
that need `/bdk:contract-grew`, throwaway exploratory tests still present). Fix and re-run.

When it passes, finish in order:
1. Update the spec: `Status: IMPLEMENTED`, tick off the test plan rows, fill the EDFH
   verdict line if not already done.
2. `python3 <scripts>/bdk_state.py archive`
3. Offer the user a commit that includes the spec alongside the code (don't commit
   without asking).
