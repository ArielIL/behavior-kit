#!/usr/bin/env bash
# bdk_worktree.sh — isolated snapshot of the working tree for the EDFH adversary.
#
#   bdk_worktree.sh create        -> prints the worktree dir
#   bdk_worktree.sh remove <dir>  -> tears it down
#
# The snapshot includes tracked modifications AND untracked non-ignored files,
# without ever touching the user's index. Env dirs (.venv/node_modules) are
# symlinked per .bdk/config.json env_symlinks.
set -euo pipefail

PROJECT="${CLAUDE_PROJECT_DIR:-$PWD}"
cd "$PROJECT"

case "${1:-}" in
  create)
    DIR=".bdk/tmp/edfh-$(date +%s)"
    mkdir -p .bdk/tmp
    git worktree add --detach "$DIR" HEAD >/dev/null 2>&1

    # tracked modifications (never touches the index)
    git diff HEAD --binary | git -C "$DIR" apply --allow-empty 2>/dev/null || true

    # untracked, non-ignored files (skip .bdk itself)
    git ls-files --others --exclude-standard -z | while IFS= read -r -d '' f; do
      case "$f" in .bdk/*) continue ;; esac
      mkdir -p "$DIR/$(dirname "$f")"
      cp "$f" "$DIR/$f"
    done

    # symlink heavyweight env dirs
    if [ -f .bdk/config.json ]; then
      python3 - "$DIR" <<'PYEOF'
import json, os, sys
d = sys.argv[1]
cfg = json.load(open(".bdk/config.json"))
for name in cfg.get("env_symlinks", []):
    src, dst = os.path.abspath(name), os.path.join(d, name)
    if os.path.isdir(src) and not os.path.lexists(dst):
        os.symlink(src, dst)
PYEOF
    fi
    echo "$DIR"
    ;;
  remove)
    DIR="${2:?usage: bdk_worktree.sh remove <dir>}"
    find "$DIR" -maxdepth 1 -type l -delete 2>/dev/null || true
    git worktree remove --force "$DIR" 2>/dev/null || rm -rf "$DIR"
    git worktree prune 2>/dev/null || true
    ;;
  *)
    echo "usage: bdk_worktree.sh create | remove <dir>" >&2
    exit 1
    ;;
esac
