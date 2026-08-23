# Adapter schema

An adapter is one JSON file that teaches the language-agnostic BDK core about a stack.
`/bdk:init` copies the chosen adapter into the project as `.bdk/config.json`, where you can
tune any field per-repo (e.g., swap `test_cmd` from vitest to jest). Adding a new stack is
filling in this schema — nothing in `scripts/` or `skills/` needs to change.

| Field | Type | Used by | Meaning |
|---|---|---|---|
| `adapter` | string | init | Stack name. |
| `test_cmd` | string | gates, Stop hook | Command that runs tests; scoped test file paths are appended. Must exit nonzero on failure. |
| `test_cmd_pattern` | regex | PostToolUse hook | Recognizes Bash commands that ran tests, so observed runs update freshness evidence. |
| `test_globs` | globs (`**` ok) | hooks | What counts as a test file — drives the GREEN freeze and REFACTOR no-new-tests rules. |
| `test_def_regex` | regex | hooks, gates | Counts test definitions; an increase during REFACTOR is denied. |
| `right_reason_regexes` | regex[] | red gate | Failing output that means assertions failed — a *genuine* red. |
| `wrong_reason_regexes` | regex[] | red gate | Failing output that means the suite never ran (import/collection/syntax) — red for the wrong reason; the gate demands signature-only stubs instead. |
| `pass_regexes` / `fail_regexes` | regex[] | PostToolUse hook | Infer pass/fail from observed test output (best-effort; gates always run tests themselves). |
| `mock_import_regexes` | regex[] | reviewer | Mocking constructs; anything matching must be justified in the spec's Mock Policy. |
| `surveillance_regexes` | regex[] | reviewer | Call-count/order assertions (Cooper's "mock as surveillance") — flagged. |
| `private_symbol_regexes` | regex[] | reviewer | Tests importing private/internal symbols — flagged. |
| `nondeterminism_regexes` | regex[] | reviewer | Unseeded randomness / wall-clock / random IDs in tests — flagged (blocking). Candidate-finders: the reviewer clears a match only if it is the PBT library's generator or an explicitly seeded one. |
| `pbt.library` / `pbt.install` / `pbt.idiom` | strings | brainstorm, red | The stack's QuickCheck descendant and a canonical property-test snippet. |
| `pbt.budget` / `pbt.replay` | strings | brainstorm, red, reviewer | How this library caps examples per test, and how a found counterexample is reproduced and pinned as a regression example test. |
| `coverage_cmd` | string | gear-5 watch (v2) | Coverage run for Cooper's 5th-gear self-policing signal. |
| `env_symlinks` | string[] | bdk_worktree.sh | Dirs symlinked into the EDFH worktree instead of copied (.venv, node_modules). |

Conventions:
- Regexes are Python `re` syntax (the core is stdlib Python 3).
- `test_globs` match project-relative paths with `/` separators; `**` crosses directories.
- Keep `wrong_reason_regexes` ahead of everything in strictness: if both wrong- and
  right-reason patterns match, the run is classified wrong-reason.
