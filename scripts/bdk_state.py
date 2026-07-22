#!/usr/bin/env python3
"""bdk_state.py — the only sanctioned writer of .bdk/state.json.

Usage:
  bdk_state.py init <feature-slug>          # fresh state for a feature (phase BRAINSTORM)
  bdk_state.py show                         # pretty-print full state
  bdk_state.py get <key>                    # print one value (dot paths ok: edfh.verdict)
  bdk_state.py set <key> <value>            # value parsed as JSON when possible
  bdk_state.py append <key> <value>         # append to a list key
  bdk_state.py clear <key>                  # reset a list key to []
  bdk_state.py phase <PHASE> [reason]       # transition phase + log it
  bdk_state.py log <message>
  bdk_state.py archive                      # move state to .bdk/history/, back to IDLE
  bdk_state.py off / on                     # per-repo kill switch

State lives at <project>/.bdk/state.json (project = $CLAUDE_PROJECT_DIR or cwd).
"""
from __future__ import annotations

import json
import os
import sys
import time

PHASES = ["IDLE", "BRAINSTORM", "RED", "GREEN", "REFACTOR"]


def project_dir() -> str:
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def state_path() -> str:
    return os.path.join(project_dir(), ".bdk", "state.json")


def now() -> float:
    return time.time()


def default_state(feature: str = "") -> dict:
    return {
        "enabled": True,
        "feature": feature,
        "phase": "BRAINSTORM" if feature else "IDLE",
        "gear": 4,
        "spec": f".bdk/specs/{feature}.spec.md" if feature else "",
        "test_files": [],
        "test_manifest": {},
        "red_evidence": None,
        "last_test_run": None,
        "last_mutation_at": 0,
        "edfh": {"verdict": None, "attempts": 0},
        "reviewer": {"verdict": None, "at": 0},
        "throwaway_tests": [],
        "recon_active": False,
        "peek_allow": [],
        "warned": [],
        "stop_block_count": 0,
        "log": [],
    }


def load() -> dict | None:
    try:
        with open(state_path()) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def save(state: dict) -> None:
    path = state_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, path)


def dig(state: dict, key: str):
    cur = state
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def put(state: dict, key: str, value) -> None:
    parts = key.split(".")
    cur = state
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


def parse_value(raw: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def add_log(state: dict, message: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    state["log"].append(f"[{stamp}] {message}")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd, args = argv[1], argv[2:]

    if cmd == "init":
        if not args:
            print("usage: bdk_state.py init <feature-slug>", file=sys.stderr)
            return 1
        existing = load()
        if existing and existing.get("phase") not in (None, "IDLE"):
            print(
                f"error: feature '{existing.get('feature')}' is active in phase "
                f"{existing.get('phase')} — finish it (/bdk:done) or /bdk:off first.",
                file=sys.stderr,
            )
            return 2
        state = default_state(args[0])
        add_log(state, f"init feature={args[0]}")
        save(state)
        print(json.dumps({"feature": args[0], "phase": state["phase"], "spec": state["spec"]}))
        return 0

    state = load()
    if state is None:
        if cmd in ("show", "get"):
            print("null")
            return 0
        print("error: no .bdk/state.json — run /bdk:brainstorm <feature> first.", file=sys.stderr)
        return 2

    if cmd == "show":
        print(json.dumps(state, indent=2))
    elif cmd == "get":
        print(json.dumps(dig(state, args[0])))
    elif cmd == "set":
        put(state, args[0], parse_value(args[1]))
        save(state)
    elif cmd == "append":
        target = dig(state, args[0])
        if not isinstance(target, list):
            put(state, args[0], [])
            target = dig(state, args[0])
        target.append(parse_value(args[1]))
        save(state)
    elif cmd == "clear":
        put(state, args[0], [])
        save(state)
    elif cmd == "phase":
        new = args[0].upper()
        if new not in PHASES:
            print(f"error: unknown phase {new} (valid: {PHASES})", file=sys.stderr)
            return 1
        reason = " ".join(args[1:]) or "(no reason given)"
        add_log(state, f"phase {state['phase']} -> {new}: {reason}")
        state["phase"] = new
        state["stop_block_count"] = 0
        save(state)
        print(json.dumps({"phase": new}))
    elif cmd == "log":
        add_log(state, " ".join(args))
        save(state)
    elif cmd == "archive":
        hist_dir = os.path.join(project_dir(), ".bdk", "history")
        os.makedirs(hist_dir, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        dest = os.path.join(hist_dir, f"{state.get('feature', 'unknown')}-{stamp}.json")
        with open(dest, "w") as f:
            json.dump(state, f, indent=2)
        fresh = default_state()
        fresh["log"] = [f"archived {state.get('feature')} to {os.path.basename(dest)}"]
        save(fresh)
        print(json.dumps({"archived": dest, "phase": "IDLE"}))
    elif cmd == "off":
        state["enabled"] = False
        add_log(state, "kit disabled via /bdk:off")
        save(state)
        print(json.dumps({"enabled": False}))
    elif cmd == "on":
        state["enabled"] = True
        add_log(state, "kit re-enabled")
        save(state)
        print(json.dumps({"enabled": True}))
    else:
        print(f"error: unknown command {cmd}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
