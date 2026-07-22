#!/usr/bin/env python3
"""bdk_gate.py — phase-transition gates. All transitions run through here.

Usage:
  bdk_gate.py check-spec [path]        # validate spec schema (default: state's spec)
  bdk_gate.py verify-red               # tests exist, fail, and fail for the RIGHT reason
  bdk_gate.py to-green                 # RED -> GREEN: needs red evidence + reviewer PASS + EDFH SURVIVED
  bdk_gate.py to-refactor              # GREEN -> REFACTOR: fresh green + untouched test manifest
  bdk_gate.py verify-done              # REFACTOR -> IDLE: green, no new tests, no throwaway tests; archives
  bdk_gate.py run-tests                # run the feature's scoped suite, record evidence
  bdk_gate.py record reviewer PASS|FAIL
  bdk_gate.py record edfh SURVIVED|CHEATED

Exit codes: 0 = gate passed; 2 = gate failed (stdout explains what to fix).
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bdk_common as C  # noqa: E402
import bdk_state  # noqa: E402

SPEC_SECTIONS = [
    ("Requirement", r"(?mi)^#+\s*(?:\d+\.\s*)?Requirement"),
    ("Behaviors", r"(?mi)^#+\s*(?:\d+\.\s*)?Behaviors"),
    ("Non-goals", r"(?mi)^#+\s*(?:\d+\.\s*)?Non-goals"),
    ("Contract surface", r"(?mi)^#+\s*(?:\d+\.\s*)?Contract surface"),
    ("Property candidates", r"(?mi)^#+\s*(?:\d+\.\s*)?Propert(?:y|ies)"),
    ("EDFH analysis", r"(?mi)^#+\s*(?:\d+\.\s*)?EDFH"),
    ("Test plan", r"(?mi)^#+\s*(?:\d+\.\s*)?Test plan"),
    ("Mock policy", r"(?mi)^#+\s*(?:\d+\.\s*)?Mock policy"),
]


def fail(message: str) -> int:
    print(f"GATE FAILED\n{message}")
    return 2


def ok(message: str) -> int:
    print(f"GATE PASSED\n{message}")
    return 0


# ------------------------------------------------------------------ check-spec

def check_spec_text(text: str) -> list:
    """Pure spec-schema validation. Returns a list of findings (empty = valid)."""
    findings = []
    for section, pattern in SPEC_SECTIONS:
        if not re.search(pattern, text):
            findings.append(f"missing section: {section}")
    if not re.search(r"\*\*B\d+\*\*", text):
        findings.append("Behaviors: need at least one Given/When/Then entry labeled **B1**")
    has_property = re.search(r"\*\*P\d+\*\*", text)
    has_justification = re.search(r"(?i)no non-trivial property", text)
    if not has_property and not has_justification:
        findings.append(
            "Property candidates: need at least one **P1** from the catalog, or an explicit "
            "'No non-trivial property found — justification: ...' signed by the user "
            "(Wlaschin: if you can't state a property, the requirement isn't understood yet)"
        )
    edfh_match = re.search(r"(?mi)^#+\s*(?:\d+\.\s*)?EDFH[^\n]*\n+(.{20,})", text)
    if not edfh_match:
        findings.append(
            "EDFH analysis: describe the laziest implementation that would pass the example "
            "tests, and which property kills it"
        )
    return findings


def cmd_check_spec(project, state, config, args) -> int:
    spec_rel = args[0] if args else state.get("spec")
    path = os.path.join(project, spec_rel)
    if not os.path.isfile(path):
        return fail(f"spec not found at {spec_rel}")
    with open(path, encoding="utf-8") as f:
        findings = check_spec_text(f.read())
    if findings:
        return fail("spec schema incomplete:\n- " + "\n- ".join(findings))
    return ok(f"spec {spec_rel} is structurally complete")


# ------------------------------------------------------------------ verify-red

def cmd_verify_red(project, state, config, args) -> int:
    if state.get("phase") != "RED":
        return fail(f"verify-red runs in RED (current phase: {state.get('phase')})")
    rc = cmd_check_spec(project, state, config, [])
    if rc != 0:
        return rc
    test_files = [
        f for f in state.get("test_files", []) if os.path.isfile(os.path.join(project, f))
    ]
    if not test_files:
        return fail(
            "no test files recorded — write the spec's tests, then register them:\n"
            "  bdk_state.py append test_files <path>  (one per file)"
        )
    exit_code, output = C.run_tests(project, config, test_files)
    if exit_code == 0:
        return fail(
            "the suite PASSES — red must come first. Either implementation was written "
            "during RED (revert it, keep signature-only stubs) or the tests are incapable "
            "of failing (they prove nothing — Cooper's 'genuine red' rule). If the "
            "implementation is truly obvious and already correct, declare /bdk:gear 5."
        )
    classified = C.classify_test_output(output, config)
    if classified == "wrong-reason":
        tail = "\n".join(output.strip().splitlines()[-15:])
        return fail(
            "tests fail for the WRONG reason (import/collection/syntax errors — the "
            "assertions never ran):\n" + tail + "\n"
            "Create signature-only stubs in src (raise NotImplementedError / throw) so "
            "the failures become assertion failures, then re-run."
        )
    state["red_evidence"] = {
        "cmd": config.get("test_cmd"),
        "exit": exit_code,
        "classified": classified,
        "at": time.time(),
    }
    state["test_manifest"] = C.build_manifest(project, test_files, config)
    C.save_state(project, state)
    total_defs = sum(m["test_defs"] for m in state["test_manifest"].values())
    return ok(
        f"genuine red: {len(test_files)} test file(s), {total_defs} test(s), "
        f"failures classified as {classified}. Manifest recorded.\n"
        "Next: reviewer + EDFH (the /bdk:green skill orchestrates both)."
    )


# -------------------------------------------------------------------- record

def cmd_record(project, state, config, args) -> int:
    if len(args) != 2 or args[0] not in ("reviewer", "edfh"):
        return fail("usage: bdk_gate.py record <reviewer|edfh> <verdict>")
    kind, verdict = args[0], args[1].upper()
    valid = {"reviewer": ("PASS", "FAIL"), "edfh": ("SURVIVED", "CHEATED")}[kind]
    if verdict not in valid:
        return fail(f"{kind} verdict must be one of {valid}")
    if kind == "reviewer":
        state["reviewer"] = {"verdict": verdict, "at": time.time()}
    else:
        state["edfh"] = {
            "verdict": verdict,
            "attempts": state.get("edfh", {}).get("attempts", 0) + 1,
        }
    C.save_state(project, state)
    return ok(f"{kind} verdict recorded: {verdict}")


# ------------------------------------------------------------------- to-green

def cmd_to_green(project, state, config, args) -> int:
    if state.get("phase") != "RED":
        return fail(f"to-green runs from RED (current phase: {state.get('phase')})")
    problems = []
    if not state.get("red_evidence"):
        problems.append("no red evidence — run: bdk_gate.py verify-red")
    else:
        drift = C.manifest_drift(project, state.get("test_manifest", {}), config)
        if drift:
            problems.append(
                f"tests changed since verify-red ({', '.join(drift)}) — re-run verify-red"
            )
    gear = state.get("gear", 4)
    if gear < 5:
        if state.get("reviewer", {}).get("verdict") != "PASS":
            problems.append(
                "test-quality reviewer has not passed — spawn bdk-test-reviewer, fix "
                "findings, then: bdk_gate.py record reviewer PASS"
            )
        if state.get("edfh", {}).get("verdict") != "SURVIVED":
            problems.append(
                "EDFH adversary has not been defeated — spawn bdk-edfh in a worktree, "
                "then: bdk_gate.py record edfh SURVIVED (or add properties if CHEATED)"
            )
    if problems:
        return fail("- " + "\n- ".join(problems))
    bdk_state.add_log(state, f"gate RED->GREEN passed (gear {gear})")
    state["phase"] = "GREEN"
    state["stop_block_count"] = 0
    C.save_state(project, state)
    note = " (gear 5: reviewer/EDFH skipped — self-police with coverage)" if gear >= 5 else ""
    return ok(
        f"GREEN unlocked{note}. Write the simplest code that passes — speed trumps "
        "design; ugliness is corrected in REFACTOR, not now. Tests are frozen."
    )


# ---------------------------------------------------------------- to-refactor

def cmd_to_refactor(project, state, config, args) -> int:
    if state.get("phase") != "GREEN":
        return fail(f"to-refactor runs from GREEN (current phase: {state.get('phase')})")
    drift = C.manifest_drift(project, state.get("test_manifest", {}), config)
    if drift:
        return fail(
            f"test files changed during GREEN ({', '.join(drift)}) — tests are the "
            "contract; route changes through /bdk:back-to-red"
        )
    exit_code, output = C.run_tests(project, config, state.get("test_files", []))
    C.record_test_run(project, state, exit_code, via="gate")
    if exit_code != 0:
        tail = "\n".join(output.strip().splitlines()[-15:])
        return fail("suite is red — GREEN isn't done:\n" + tail)
    state = C.load_state(project)
    bdk_state.add_log(state, "gate GREEN->REFACTOR passed")
    state["phase"] = "REFACTOR"
    C.save_state(project, state)
    return ok(
        "REFACTOR unlocked. Behavior-preserving structural changes only: extract, rename, "
        "dedupe, introduce patterns now that the shape is known. Zero new tests. Keep "
        "internals private — never widen visibility for a test."
    )


# ---------------------------------------------------------------- verify-done

def cmd_verify_done(project, state, config, args) -> int:
    if state.get("phase") not in ("GREEN", "REFACTOR"):
        return fail(f"verify-done runs from GREEN/REFACTOR (current: {state.get('phase')})")
    problems = []
    drift = C.manifest_drift(project, state.get("test_manifest", {}), config)
    added = {rel: d for rel, d in drift.items() if d.get("defs_added", 0) > 0}
    if added:
        problems.append(
            f"new test functions appeared since RED ({', '.join(added)}) — new tests mean "
            "new behavior: route through /bdk:contract-grew or /bdk:back-to-red"
        )
    if state.get("throwaway_tests"):
        problems.append(
            f"throwaway exploratory tests still present: {state['throwaway_tests']} — "
            "Cooper's low-gear rule: scaffolding tests are a thinking aid, delete them "
            "(then bdk_state.py clear throwaway_tests)"
        )
    exit_code, output = C.run_tests(project, config, state.get("test_files", []))
    C.record_test_run(project, state, exit_code, via="gate")
    if exit_code != 0:
        tail = "\n".join(output.strip().splitlines()[-15:])
        problems.append("suite is red:\n" + tail)
    if problems:
        return fail("- " + "\n- ".join(problems))
    state = C.load_state(project)
    feature, spec = state.get("feature"), state.get("spec")
    bdk_state.add_log(state, "gate verify-done passed")
    C.save_state(project, state)
    return ok(
        f"feature '{feature}' complete and green. Finalize:\n"
        f"1. Update {spec}: set Status: IMPLEMENTED, tick the test plan.\n"
        f"2. Archive: bdk_state.py archive\n"
        f"3. Commit the spec with the code."
    )


# ------------------------------------------------------------------ run-tests

def cmd_run_tests(project, state, config, args) -> int:
    exit_code, output = C.run_tests(project, config, state.get("test_files", []))
    C.record_test_run(project, state, exit_code, via="gate")
    tail = "\n".join(output.strip().splitlines()[-20:])
    print(tail)
    return 0 if exit_code == 0 else 2


COMMANDS = {
    "check-spec": cmd_check_spec,
    "verify-red": cmd_verify_red,
    "to-green": cmd_to_green,
    "to-refactor": cmd_to_refactor,
    "verify-done": cmd_verify_done,
    "run-tests": cmd_run_tests,
    "record": cmd_record,
}


def main(argv: list) -> int:
    if len(argv) < 2 or argv[1] not in COMMANDS:
        print(__doc__)
        return 1
    project = C.project_dir()
    state = C.load_state(project)
    if state is None:
        print("GATE FAILED\nno .bdk/state.json — run /bdk:brainstorm <feature> first")
        return 2
    config = C.load_config(project)
    if config is None:
        print("GATE FAILED\nno .bdk/config.json — run /bdk:init first")
        return 2
    return COMMANDS[argv[1]](project, state, config, argv[2:])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
