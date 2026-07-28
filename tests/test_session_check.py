"""Behavior tests for bdk_session_check.py — the audit-of-the-audit.

Facade under test: parse_events + evaluate (pure) and the CLI process.
Transcripts are synthesized in the real JSONL shape observed from Claude Code
(message.content lists with tool_use / tool_result / text blocks).
"""
import json
import os
import random
import subprocess
import sys

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(KIT, "scripts")
sys.path.insert(0, SCRIPTS)

from bdk_session_check import evaluate, parse_events  # noqa: E402


def tool_use(name, **input_obj):
    return json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": name, "input": input_obj}]}})


def tool_result(text):
    return json.dumps({"type": "user", "message": {"content": [
        {"type": "tool_result", "content": [{"type": "text", "text": text}]}]}})


def text(body, etype="assistant"):
    return json.dumps({"type": etype, "message": {"content": [
        {"type": "text", "text": body}]}})


GOOD_SESSION = [
    text("<command-name>/bdk:audit</command-name> src/calc", etype="user"),
    tool_use("Skill", skill="bdk:audit", args="src/calc"),
    tool_use("Task", subagent_type="bdk:bdk-test-reviewer",
             prompt="Review these tests. AUDIT MODE — no spec exists. Files: ..."),
    tool_result("VERDICT: PASS\nFINDINGS:\n(none)"),
    tool_use("Bash", command="bash /plug/scripts/bdk_worktree.sh create"),
    tool_result(".bdk/tmp/edfh-123"),
    tool_use("Task", subagent_type="bdk:bdk-edfh",
             prompt="Cheat the tests. Worktree: .bdk/tmp/edfh-123 ..."),
    tool_result("VERDICT: SURVIVED\nATTEMPTS: 3\nDETAILS: hard-code caught by P1"),
    tool_use("Bash", command="bash /plug/scripts/bdk_worktree.sh remove .bdk/tmp/edfh-123"),
    text("Audit report — findings: none blocking. EDFH verdict SURVIVED; property coverage OK."),
]


def statuses(lines):
    return {name: status for name, status, _ in evaluate(parse_events(lines))}


def test_B14_proper_session_passes_every_checkpoint():
    result = statuses(GOOD_SESSION)
    assert all(s == "PASS" for s in result.values()), result


def test_B15_session_that_skipped_the_adversary_and_armed_phases_fails():
    lines = [
        tool_use("Skill", skill="bdk:audit"),
        tool_use("Task", subagent_type="bdk:bdk-test-reviewer", prompt="AUDIT MODE ..."),
        tool_result("VERDICT: PASS"),
        tool_use("Bash", command="python3 /plug/scripts/bdk_state.py phase RED oops"),
        text("Looks good to me overall! Findings: none."),
    ]
    result = statuses(lines)
    assert result["edfh-run"] == "FAIL"
    assert result["edfh-verdict"] == "FAIL"
    assert result["no-phase-armed"] == "FAIL"
    assert result["audit-invoked"] == "PASS"


def test_B16_adversary_without_prior_worktree_is_flagged():
    lines = list(GOOD_SESSION)
    lines.remove(tool_use("Bash", command="bash /plug/scripts/bdk_worktree.sh create"))
    result = statuses(lines)
    assert result["edfh-in-worktree"] == "FAIL"


def test_B17_reviewer_without_audit_mode_warns():
    lines = [line.replace("AUDIT MODE", "audit requested") for line in GOOD_SESSION]
    result = statuses(lines)
    assert result["reviewer-audit-mode"] == "WARN"


def test_B18_cli_locates_by_session_id_and_exit_codes(tmp_path):
    projects = tmp_path / "projects" / "-Users-me-repos-app"
    projects.mkdir(parents=True)
    (projects / "sess-good.jsonl").write_text("\n".join(GOOD_SESSION))
    (projects / "sess-bad.jsonl").write_text("\n".join([
        text("is my feature ok?", etype="user"),
        text("Yes, looks fine to me!"),
    ]))

    def run(ref):
        return subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "bdk_session_check.py"),
             ref, "--projects-dir", str(tmp_path / "projects")],
            capture_output=True, text=True,
        )

    good = run("sess-good")
    assert good.returncode == 0 and "PROPER (0 FAIL" in good.stdout

    bad = run("sess-bad")
    assert bad.returncode == 2 and "IMPROPER" in bad.stdout
    assert "no bdk:audit invocation" in bad.stdout

    missing = run("no-such-session")
    assert missing.returncode == 1 and "no transcript" in missing.stderr


def test_P4_verdict_is_invariant_under_unrelated_session_noise():
    """[invariant] Interleaving arbitrary unrelated tool activity anywhere before
    the final report never changes any checkpoint's status. (Noise AFTER the final
    report rightly demotes report-delivered — the last message is what the user
    sees — so insertion points exclude the tail.)"""
    rng = random.Random(42)
    noise = [
        tool_use("Read", file_path="/repo/docs/arch.md"),
        tool_use("Bash", command="ls -la"),
        tool_result("total 42"),
        text("Let me look at the structure."),
        tool_use("Grep", pattern="add", path="/repo"),
    ]
    baseline = statuses(GOOD_SESSION)
    for _ in range(50):
        lines = list(GOOD_SESSION)
        for _ in range(rng.randint(1, 8)):
            lines.insert(rng.randint(0, len(lines) - 1), rng.choice(noise))
        assert statuses(lines) == baseline
