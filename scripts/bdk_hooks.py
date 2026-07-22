#!/usr/bin/env python3
"""bdk_hooks.py — single hook dispatcher for the BDK plugin.

Called as: python3 bdk_hooks.py <event>   with the hook JSON on stdin.
Events: pretooluse, posttooluse, stop, sessionstart, subagentstop, userpromptsubmit

Contract: if .bdk/state.json is absent or enabled=false, every event exits 0
instantly — the kit is inert outside BDK-managed features. Unexpected errors
also exit 0: a broken hook must never break the user's session.

Decision logic lives in pure functions (decide_*) so the kit can test its own
behavior at this facade.
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bdk_common as C  # noqa: E402

EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
READ_TOOLS = ("Read", "Grep", "Glob")
DOC_DIRS = ("docs", "doc", ".bdk", ".claude", "specs")
DOC_BASENAMES = ("README", "LICENSE", "CHANGELOG", "CONTRIBUTING", "CLAUDE")
DOC_EXTS = (".md", ".rst", ".txt")


# ------------------------------------------------------------ pure decisions

def is_doc_path(rel: str) -> bool:
    if rel in (None, "."):
        return False
    first = rel.replace(os.sep, "/").split("/")[0]
    if first in DOC_DIRS:
        return True
    base = os.path.basename(rel)
    if any(base.upper().startswith(p) for p in DOC_BASENAMES):
        return True
    return os.path.splitext(base)[1].lower() in DOC_EXTS


def target_path_of(tool_name: str, tool_input: dict):
    if tool_name in ("Read", *EDIT_TOOLS):
        return tool_input.get("file_path") or tool_input.get("notebook_path")
    if tool_name in ("Grep", "Glob"):
        return tool_input.get("path") or "."
    return None


def decide_pretooluse(state: dict, config: dict, inp: dict, project: str):
    """Returns (deny_reason | None, state_changed: bool)."""
    phase = state.get("phase", "IDLE")
    tool = inp.get("tool_name", "")
    tool_input = inp.get("tool_input") or {}
    changed = False

    # Track the sanctioned recon window so its own reads aren't blocked.
    if tool == "Task" and "bdk-recon" in str(tool_input.get("subagent_type", "")):
        state["recon_active"] = True
        changed = True
        return None, changed

    if phase == "BRAINSTORM":
        if tool in READ_TOOLS:
            if state.get("recon_active") or "bdk-recon" in str(inp.get("agent_type", "")):
                return None, changed
            rel = C.rel_to_project(target_path_of(tool, tool_input), project)
            if rel is None:  # outside the project (plugin refs, scratchpad) — fine
                return None, changed
            if rel in state.get("peek_allow", []) or is_doc_path(rel):
                return None, changed
            return (
                "[bdk] BRAINSTORM discusses behavior, not implementation — source reading "
                "is blocked. Dispatch the bdk-recon agent for behavior-level repo context, "
                "or ask the user to run /bdk:peek <file> for a logged exception.",
                changed,
            )
        if tool in EDIT_TOOLS:
            rel = C.rel_to_project(target_path_of(tool, tool_input), project)
            if rel is None or rel.replace(os.sep, "/").startswith(".bdk/"):
                return None, changed
            return (
                "[bdk] BRAINSTORM produces exactly one artifact: the behavior spec under "
                ".bdk/specs/. No other edits until the spec is approved (then /bdk:red).",
                changed,
            )
        return None, changed

    if phase == "GREEN" and tool in EDIT_TOOLS:
        rel = C.rel_to_project(target_path_of(tool, tool_input), project)
        if rel and C.is_test_path(rel, config):
            return (
                "[bdk] GREEN phase: tests are frozen — they are the contract you're "
                "implementing against. If a test is genuinely wrong or behavior changed, "
                "run /bdk:back-to-red <reason> (logged) to unlock them.",
                changed,
            )
        return None, changed

    if phase == "REFACTOR" and tool in ("Edit", "Write"):
        rel = C.rel_to_project(target_path_of(tool, tool_input), project)
        if rel and C.is_test_path(rel, config):
            if tool == "Write":
                new_defs = C.count_test_defs(tool_input.get("content", ""), config)
                old_defs = 0
                existing = os.path.join(project, rel)
                if os.path.isfile(existing):
                    with open(existing, encoding="utf-8", errors="replace") as f:
                        old_defs = C.count_test_defs(f.read(), config)
            else:
                new_defs = C.count_test_defs(tool_input.get("new_string", ""), config)
                old_defs = C.count_test_defs(tool_input.get("old_string", ""), config)
            if new_defs > old_defs:
                return (
                    "[bdk] REFACTOR is behavior-preserving: zero new tests (Cooper). "
                    "The urge to add a test here means new behavior is sneaking in — if a "
                    "genuine new public contract emerged, run /bdk:contract-grew to open a "
                    "new RED for it.",
                    changed,
                )
        return None, changed

    return None, changed


def phase_obligation(phase: str) -> str:
    return {
        "BRAINSTORM": (
            "discuss desired behavior only (G/W/T, contract, properties); source reads are "
            "blocked — repo context comes from the bdk-recon agent; sole output is the spec"
        ),
        "RED": (
            "write behavior tests from the approved spec (signature-only stubs in src); "
            "run /bdk:green when they fail for the right reason"
        ),
        "GREEN": (
            "make the tests pass with the simplest code that works — speed trumps design; "
            "tests are frozen; then /bdk:refactor"
        ),
        "REFACTOR": (
            "improve structure only; stay green; zero new tests; then /bdk:done"
        ),
    }.get(phase, "")


def banner(state: dict) -> str:
    return (
        f"[bdk] feature={state.get('feature')} phase={state.get('phase')} "
        f"gear={state.get('gear')} — {phase_obligation(state.get('phase', ''))}"
    )


def is_fresh_green(state: dict) -> bool:
    run = state.get("last_test_run")
    return bool(
        run
        and run.get("exit") == 0
        and run.get("at", 0) >= state.get("last_mutation_at", 0)
    )


# ------------------------------------------------------------ event handlers

def emit(obj: dict) -> None:
    print(json.dumps(obj))


def deny(reason: str) -> None:
    emit({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    })


def handle_pretooluse(state, config, inp, project):
    reason, changed = decide_pretooluse(state, config, inp, project)
    if changed:
        C.save_state(project, state)
    if reason:
        deny(reason)


def handle_posttooluse(state, config, inp, project):
    if state.get("phase") not in ("RED", "GREEN", "REFACTOR"):
        return
    tool = inp.get("tool_name", "")
    tool_input = inp.get("tool_input") or {}
    if tool in EDIT_TOOLS:
        rel = C.rel_to_project(target_path_of(tool, tool_input), project)
        if rel is not None:
            state["last_mutation_at"] = time.time()
            state["stop_block_count"] = 0
            C.save_state(project, state)
    elif tool == "Bash":
        pattern = config.get("test_cmd_pattern")
        command = str(tool_input.get("command", ""))
        if pattern and re.search(pattern, command):
            output = json.dumps(inp.get("tool_response", ""), default=str)
            result = C.infer_run_result(output, config)
            if result is not None:
                C.record_test_run(project, state, result, via="observed")


def handle_stop(state, config, inp, project):
    if state.get("phase") not in ("GREEN", "REFACTOR"):
        return
    if not state.get("test_files"):
        return
    if state.get("stop_block_count", 0) >= 2:
        emit({"systemMessage": "[bdk] tests still red, but giving up blocking (2 attempts). Run /bdk:status."})
        return
    if is_fresh_green(state):
        return
    exit_code, output = C.run_tests(project, config, state["test_files"])
    C.record_test_run(project, state, exit_code, via="stop-hook")
    if exit_code == 0:
        return
    state = C.load_state(project)  # record_test_run saved; reload before mutating
    state["stop_block_count"] = state.get("stop_block_count", 0) + 1
    C.save_state(project, state)
    tail = "\n".join(output.strip().splitlines()[-15:])
    emit({
        "decision": "block",
        "reason": (
            f"[bdk] Cannot finish: the feature's tests are red or stale "
            f"(phase {state['phase']}). Scoped run just failed:\n{tail}\n"
            "Fix the implementation (not the tests) and re-run. Escape: /bdk:off."
        ),
    })


def handle_sessionstart(state, config, inp, project):
    context = (
        f"BDK active — {banner(state)}. Spec: {state.get('spec')}. "
        "Phase transitions go through /bdk:red, /bdk:green, /bdk:refactor, /bdk:done; "
        "escapes: /bdk:back-to-red, /bdk:contract-grew, /bdk:gear, /bdk:off. "
        "Run /bdk:status for full state."
    )
    emit({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    })


def handle_userpromptsubmit(state, config, inp, project):
    emit({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": banner(state),
        }
    })


def handle_subagentstop(state, config, inp, project):
    if state.get("recon_active"):
        state["recon_active"] = False
        C.save_state(project, state)


HANDLERS = {
    "pretooluse": handle_pretooluse,
    "posttooluse": handle_posttooluse,
    "stop": handle_stop,
    "sessionstart": handle_sessionstart,
    "subagentstop": handle_subagentstop,
    "userpromptsubmit": handle_userpromptsubmit,
}


def main() -> int:
    try:
        event = sys.argv[1].lower()
        inp = json.load(sys.stdin)
        project = os.environ.get("CLAUDE_PROJECT_DIR") or inp.get("cwd") or os.getcwd()
        state = C.load_state(project)
        if not state or not state.get("enabled") or state.get("phase") == "IDLE":
            return 0
        config = C.load_config(project) or {}
        handler = HANDLERS.get(event)
        if handler:
            handler(state, config, inp, project)
    except Exception:
        # A broken hook must never break the session.
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
