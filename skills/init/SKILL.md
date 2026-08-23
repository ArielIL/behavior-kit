---
name: init
description: Set up BDK in the current project — detect the stack, write .bdk/config.json, install the doctrine rules file, and prepare gitignore entries.
disable-model-invocation: true
---

# /bdk:init — set up BDK in this project

Plugin root (adapters, rules, scripts live here): `${CLAUDE_SKILL_DIR}/../..`

Steps:

1. **Detect the stack.** `pyproject.toml`/`setup.cfg`/`requirements*.txt` → python;
   `package.json` → typescript (check whether vitest or jest is a dev dependency).
   If both or neither, ask the user which adapter to use.

2. **Write `.bdk/config.json`.** Copy `<plugin-root>/adapters/<stack>.json` to
   `.bdk/config.json`, then adjust for this repo:
   - `test_cmd`: honor the repo's runner wrapper (`uv run pytest`, `poetry run pytest`,
     `npx jest` instead of vitest, a `make test` target…). It must exit nonzero on failure
     and accept test file paths appended.
   - `test_globs`: reconcile with where tests actually live in this repo.
   - Check the PBT library (`hypothesis` / `fast-check`) is installed; if not, tell the
     user the install command from the adapter's `pbt.install` — don't install unasked.

3. **Create dirs & gitignore.** Create `.bdk/specs/`. Append to `.gitignore` (create if
   missing, skip lines already present):
   ```
   .bdk/state.json
   .bdk/history/
   .bdk/tmp/
   ```
   (`.bdk/config.json` and `.bdk/specs/` are committed. If the team's repo gitignores
   all of `.bdk/`, that's fine too: linked git worktrees bootstrap the static config
   files from the main worktree automatically — init is once per clone, not per branch.)

4. **Install the doctrine.** Copy `<plugin-root>/rules/behavior-first.md` to
   `.claude/rules/bdk-behavior-first.md` in the project (committed — teammates get the
   doctrine even without the plugin installed).

5. **Report.** Show the chosen adapter, final `test_cmd`, test globs, PBT library status,
   and the workflow summary: `/bdk:brainstorm <feature>` → approve spec → `/bdk:red` →
   `/bdk:green` → `/bdk:refactor` → `/bdk:done`. Escapes: `/bdk:back-to-red`,
   `/bdk:contract-grew`, `/bdk:gear`, `/bdk:peek`, `/bdk:off`.
