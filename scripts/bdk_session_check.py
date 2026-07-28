#!/usr/bin/env python3
"""bdk_session_check.py — verify a Claude Code session properly ran /bdk:audit.

Usage:
  bdk_session_check.py <session-id | path-to-transcript.jsonl> [--projects-dir DIR]

Locates the session transcript (default search: ~/.claude/projects/*/<id>.jsonl),
replays its events, and grades the audit protocol checkpoints:

  PASS/FAIL  audit-invoked          the bdk:audit skill was actually entered
  PASS/WARN  reviewer-audit-mode    bdk-test-reviewer spawned, with "AUDIT MODE"
  PASS/FAIL  reviewer-verdict       a VERDICT: PASS|FAIL came back
  PASS/FAIL  edfh-run               bdk-edfh adversary was spawned
  PASS/FAIL  edfh-in-worktree       a worktree was created BEFORE the adversary ran
  PASS/WARN  worktree-cleanup       the worktree was removed afterward
  PASS/FAIL  edfh-verdict           a VERDICT: CHEATED|SURVIVED came back
  PASS/FAIL  no-phase-armed         audit never touched phase state (init/phase)
  PASS/WARN  report-delivered       the session ended with a findings report

Exit 0 = proper (no FAILs). Exit 2 = protocol violations found. Exit 1 = usage/not found.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

AGENT_TOOLS = ("Task", "Agent")
VERDICT_REVIEWER = re.compile(r"VERDICT:\s*(PASS|FAIL)")
VERDICT_EDFH = re.compile(r"VERDICT:\s*(CHEATED|SURVIVED)")


# ------------------------------------------------------------------ locate

def find_transcript(ref: str, projects_dir: str) -> str:
    if os.path.isfile(ref):
        return ref
    session_id = ref[:-6] if ref.endswith(".jsonl") else ref
    hits = glob.glob(os.path.join(projects_dir, "*", session_id + ".jsonl"))
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise FileNotFoundError(
            f"no transcript {session_id}.jsonl under {projects_dir}/*/ "
            "(session from another machine, or a different --projects-dir?)"
        )
    raise FileNotFoundError(f"ambiguous session id, found: {hits}")


# ------------------------------------------------------------------- parse

def _iter_result_text(content):
    if isinstance(content, str):
        yield content
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                yield item.get("text", "")


def parse_events(lines):
    """Flatten a transcript into ordered events:
    {kind: tool_use|tool_result|text|user_text, name, input, text}."""
    events = []
    for line in lines:
        try:
            entry = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        etype = entry.get("type")
        content = (entry.get("message") or {}).get("content")
        if isinstance(content, str):
            if etype == "user":
                events.append({"kind": "user_text", "text": content})
            continue
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == "tool_use":
                events.append({
                    "kind": "tool_use",
                    "name": block.get("name", ""),
                    "input": json.dumps(block.get("input", {}), default=str),
                })
            elif btype == "tool_result":
                text = "\n".join(_iter_result_text(block.get("content")))
                events.append({"kind": "tool_result", "text": text})
            elif btype == "text":
                kind = "user_text" if etype == "user" else "text"
                events.append({"kind": kind, "text": block.get("text", "")})
    return events


# ---------------------------------------------------------------- evaluate

def _first_index(events, predicate):
    for i, event in enumerate(events):
        if predicate(event):
            return i
    return None


def evaluate(events):
    """Grade the audit protocol. Returns list of (checkpoint, status, evidence)."""
    results = []

    def bash_cmd(event, *parts):
        # Exact Bash executions only — a Write whose *content* mentions a command
        # (e.g. authoring a skill file) must not count as running it.
        return (
            event["kind"] == "tool_use"
            and event["name"] == "Bash"
            and all(p in event["input"] for p in parts)
        )

    skill_i = _first_index(events, lambda e: (
        (e["kind"] == "tool_use" and e["name"] == "Skill" and "audit" in e["input"])
        or (e["kind"] == "user_text" and "bdk:audit" in e.get("text", ""))
    ))
    results.append((
        "audit-invoked",
        "PASS" if skill_i is not None else "FAIL",
        "Skill call or /bdk:audit command found" if skill_i is not None
        else "no bdk:audit invocation — the session may have answered from opinion only",
    ))

    reviewer_i = _first_index(events, lambda e: (
        e["kind"] == "tool_use" and e["name"] in AGENT_TOOLS and "bdk-test-reviewer" in e["input"]
    ))
    if reviewer_i is None:
        results.append(("reviewer-audit-mode", "FAIL", "bdk-test-reviewer never spawned"))
    elif "AUDIT MODE" in events[reviewer_i]["input"]:
        results.append(("reviewer-audit-mode", "PASS", "spawned with AUDIT MODE"))
    else:
        results.append((
            "reviewer-audit-mode", "WARN",
            "reviewer spawned WITHOUT 'AUDIT MODE' — spec-traceability checks misapply",
        ))

    reviewer_verdict = None
    if reviewer_i is not None:
        for event in events[reviewer_i:]:
            if event["kind"] in ("tool_result", "text"):
                match = VERDICT_REVIEWER.search(event.get("text", ""))
                if match:
                    reviewer_verdict = match.group(1)
                    break
    results.append((
        "reviewer-verdict",
        "PASS" if reviewer_verdict else "FAIL",
        f"reviewer returned {reviewer_verdict}" if reviewer_verdict
        else "no reviewer VERDICT: PASS|FAIL observed",
    ))

    edfh_i = _first_index(events, lambda e: (
        e["kind"] == "tool_use" and e["name"] in AGENT_TOOLS and "bdk-edfh" in e["input"]
    ))
    results.append((
        "edfh-run",
        "PASS" if edfh_i is not None else "FAIL",
        "adversary spawned" if edfh_i is not None
        else "bdk-edfh never ran — nothing verified the tests can't be cheated",
    ))

    create_i = _first_index(events, lambda e: bash_cmd(e, "bdk_worktree.sh", "create"))
    if edfh_i is None:
        results.append(("edfh-in-worktree", "FAIL", "n/a — adversary never ran"))
    elif create_i is not None and create_i < edfh_i:
        results.append(("edfh-in-worktree", "PASS", "worktree created before the adversary ran"))
    else:
        results.append((
            "edfh-in-worktree", "FAIL",
            "adversary ran without a prior bdk_worktree.sh create — it may have "
            "edited the real working tree",
        ))

    remove_i = _first_index(events, lambda e: bash_cmd(e, "bdk_worktree.sh", "remove"))
    if create_i is None:
        results.append(("worktree-cleanup", "WARN", "n/a — no worktree was created"))
    elif remove_i is not None and remove_i > create_i:
        results.append(("worktree-cleanup", "PASS", "worktree removed"))
    else:
        results.append(("worktree-cleanup", "WARN", "worktree never removed — stale dir under .bdk/tmp/"))

    edfh_verdict = None
    if edfh_i is not None:
        for event in events[edfh_i:]:
            if event["kind"] in ("tool_result", "text"):
                match = VERDICT_EDFH.search(event.get("text", ""))
                if match:
                    edfh_verdict = match.group(1)
                    break
    results.append((
        "edfh-verdict",
        "PASS" if edfh_verdict else "FAIL",
        f"adversary returned {edfh_verdict}" if edfh_verdict
        else "no CHEATED|SURVIVED verdict observed",
    ))

    armed = _first_index(events, lambda e: (
        bash_cmd(e, "bdk_state.py init") or bash_cmd(e, "bdk_state.py phase")
    ))
    results.append((
        "no-phase-armed",
        "PASS" if armed is None else "FAIL",
        "audit stayed passive" if armed is None
        else "audit changed phase state — it must arm nothing",
    ))

    final_text = ""
    for event in reversed(events):
        if event["kind"] == "text" and event.get("text", "").strip():
            final_text = event["text"]
            break
    keywords = ("finding", "verdict", "property", "EDFH", "CHEATED", "SURVIVED")
    delivered = any(k.lower() in final_text.lower() for k in keywords)
    results.append((
        "report-delivered",
        "PASS" if delivered else "WARN",
        "final message reads as a findings report" if delivered
        else "final message doesn't look like a findings report",
    ))
    return results


def render(results):
    width = max(len(name) for name, _, _ in results)
    lines = [f"{status:4}  {name:<{width}}  {evidence}" for name, status, evidence in results]
    fails = sum(1 for _, status, _ in results if status == "FAIL")
    warns = sum(1 for _, status, _ in results if status == "WARN")
    verdict = "PROPER" if fails == 0 else "IMPROPER"
    lines.append(f"\nAUDIT-OF-AUDIT: {verdict} ({fails} FAIL, {warns} WARN)")
    return "\n".join(lines), fails


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 1
    projects_dir = os.path.expanduser("~/.claude/projects")
    if "--projects-dir" in argv:
        projects_dir = argv[argv.index("--projects-dir") + 1]
    try:
        path = find_transcript(args[0], projects_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    with open(path, encoding="utf-8", errors="replace") as f:
        events = parse_events(f)
    print(f"transcript: {path}  ({len(events)} events)\n")
    report, fails = render(evaluate(events))
    print(report)
    return 2 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
