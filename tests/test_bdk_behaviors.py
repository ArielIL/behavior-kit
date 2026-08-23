"""BDK's own tests, written BDK-style.

System under test = the kit's public facades: the hook decision functions, the
classifier/matcher helpers in bdk_common, the spec schema check, and the actual
CLI processes (bdk_hooks.py / bdk_gate.py) driven end-to-end in sandbox projects.
No internal collaborators are tested; no mocks — real files, real subprocesses
(classicist style: the only shared fixture hazard, the filesystem, is isolated
per-test via tmp_path).

B* = example behaviors, P* = properties (hand-rolled seeded generators — a
property check is just a function; no library dependency for the kit itself).
"""
import json
import os
import random
import re
import subprocess
import sys

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(KIT, "scripts")
sys.path.insert(0, SCRIPTS)

import bdk_common as C  # noqa: E402
import bdk_hooks as H  # noqa: E402
import bdk_state as S  # noqa: E402
from bdk_gate import check_spec_text  # noqa: E402

with open(os.path.join(KIT, "adapters", "python.json")) as f:
    PY = json.load(f)

with open(os.path.join(KIT, "adapters", "typescript.json")) as f:
    TS = json.load(f)

VALID_SPEC = """# Behavior Spec: Demo
- Slug: demo-feature - Status: APPROVED - Gear: 4

## 1. Requirement
Users can add two numbers and get their sum.

## 2. Behaviors
- **B1** Given two integers 2 and 2, When added, Then the result is 4. [example]

## 3. Non-goals
- No floats.

## 4. Contract surface
Port: `calc`
add(x: int, y: int) -> int

## 5. Property candidates
- **P1** [identity] add(x, 0) == x for all x.

## 6. EDFH analysis
Laziest impl passing the examples alone: return 4 hard-coded. Killed by: P1 over
generated inputs. Residual gaps accepted: none.

## 7. Test plan
| ID | Type | Level | SUT |
| B1 | example | port | calc |

## 8. Mock policy
| Dependency | Double | Justification |
| (none) | - | - |
"""


# --------------------------------------------------------------- test harness

def make_project(tmp_path, phase, **state_overrides):
    """A sandbox project with real .bdk/config.json + state.json."""
    (tmp_path / ".bdk" / "specs").mkdir(parents=True)
    cfg = dict(PY)
    cfg["test_cmd"] = f'"{sys.executable}" -m pytest -q --color=no -p no:cacheprovider'
    (tmp_path / ".bdk" / "config.json").write_text(json.dumps(cfg))
    state = S.default_state("demo-feature")
    state["phase"] = phase
    state.update(state_overrides)
    (tmp_path / ".bdk" / "state.json").write_text(json.dumps(state))
    return str(tmp_path), state, cfg


def pt(tool, **tool_input):
    return {"tool_name": tool, "tool_input": tool_input}


def decide(state, cfg, inp, proj):
    reason, _ = H.decide_pretooluse(state, cfg, inp, proj)
    return reason


def run_cli(script, args, proj, stdin=None):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": proj}
    return subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, script)] + args,
        input=stdin, capture_output=True, text=True, env=env, cwd=proj,
    )


def write_feature(tmp_path, impl_body, test_body=None):
    """A real mini feature: src/calc.py + tests/test_calc.py + committed spec."""
    proj, state, cfg = make_project(
        tmp_path, "RED", test_files=["tests/test_calc.py"]
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "calc.py").write_text(f"def add(x, y):\n    {impl_body}\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_calc.py").write_text(test_body or (
        "import os, sys\n"
        "sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))\n"
        "from calc import add\n\n"
        "def test_B1_adding_two_numbers_gives_their_sum():\n"
        "    assert add(2, 2) == 4\n"
    ))
    (tmp_path / ".bdk" / "specs" / "demo-feature.spec.md").write_text(VALID_SPEC)
    return proj


# ------------------------------------------- B1/B2: BRAINSTORM context wall

def test_B1_brainstorm_denies_reading_source(tmp_path):
    proj, state, cfg = make_project(tmp_path, "BRAINSTORM")
    reason = decide(state, cfg, pt("Read", file_path=f"{proj}/src/app.py"), proj)
    assert reason is not None and "bdk-recon" in reason
    for tool in ("Grep", "Glob"):
        assert decide(state, cfg, pt(tool, pattern="x", path=proj), proj) is not None


def test_B1_brainstorm_allows_docs_specs_and_outside_paths(tmp_path):
    proj, state, cfg = make_project(tmp_path, "BRAINSTORM")
    for path in ("README.md", "docs/arch.md", ".bdk/specs/demo-feature.spec.md",
                 "CLAUDE.md", "notes.txt"):
        assert decide(state, cfg, pt("Read", file_path=f"{proj}/{path}"), proj) is None
    assert decide(state, cfg, pt("Read", file_path="/somewhere/else/lib.py"), proj) is None


def test_B1_recon_window_opens_on_task_spawn_and_permits_reads(tmp_path):
    proj, state, cfg = make_project(tmp_path, "BRAINSTORM")
    reason, changed = H.decide_pretooluse(
        state, cfg, pt("Task", subagent_type="bdk:bdk-recon", prompt="survey"), proj
    )
    assert reason is None and changed and state["recon_active"] is True
    assert decide(state, cfg, pt("Read", file_path=f"{proj}/src/app.py"), proj) is None


def test_B1_peek_grants_one_logged_file(tmp_path):
    proj, state, cfg = make_project(tmp_path, "BRAINSTORM", peek_allow=["src/app.py"])
    assert decide(state, cfg, pt("Read", file_path=f"{proj}/src/app.py"), proj) is None
    assert decide(state, cfg, pt("Read", file_path=f"{proj}/src/other.py"), proj) is not None


def test_B2_brainstorm_edits_only_the_spec(tmp_path):
    proj, state, cfg = make_project(tmp_path, "BRAINSTORM")
    ok = pt("Write", file_path=f"{proj}/.bdk/specs/demo-feature.spec.md", content="x")
    assert decide(state, cfg, ok, proj) is None
    bad = pt("Write", file_path=f"{proj}/src/app.py", content="x")
    assert decide(state, cfg, bad, proj) is not None


# ----------------------------------------------- B3/B4: GREEN/REFACTOR locks

def test_B3_green_freezes_tests_but_not_source(tmp_path):
    proj, state, cfg = make_project(tmp_path, "GREEN")
    frozen = pt("Edit", file_path=f"{proj}/tests/test_calc.py", old_string="a", new_string="b")
    reason = decide(state, cfg, frozen, proj)
    assert reason is not None and "back-to-red" in reason
    free = pt("Edit", file_path=f"{proj}/src/calc.py", old_string="a", new_string="b")
    assert decide(state, cfg, free, proj) is None


def test_B4_refactor_denies_new_test_functions_but_allows_reshaping(tmp_path):
    proj, state, cfg = make_project(tmp_path, "REFACTOR")
    grow = pt("Edit", file_path=f"{proj}/tests/test_calc.py",
              old_string="x = 1", new_string="def test_sneaky():\n    pass")
    reason = decide(state, cfg, grow, proj)
    assert reason is not None and "contract-grew" in reason
    reshape = pt("Edit", file_path=f"{proj}/tests/test_calc.py",
                 old_string="def test_B1_old_name():", new_string="def test_B1_new_name():")
    assert decide(state, cfg, reshape, proj) is None
    new_file = pt("Write", file_path=f"{proj}/tests/test_extra.py",
                  content="def test_more():\n    pass\n")
    assert decide(state, cfg, new_file, proj) is not None


# --------------------------------------------------- B5/B6: classifier facade

def test_B5_classifier_separates_wrong_reason_from_genuine_red():
    wrong = ("==== ERRORS ====\nImportError while importing test module 'tests/test_x.py'\n"
             "ModuleNotFoundError: No module named 'calc'")
    right = ("E       assert 4 == 5\nFAILED tests/test_calc.py::test_B1 - AssertionError")
    assert C.classify_test_output(wrong, PY) == "wrong-reason"
    assert C.classify_test_output(right, PY) == "right-reason"
    both = wrong + "\n" + right
    assert C.classify_test_output(both, PY) == "wrong-reason"  # wrong-reason wins


def test_B6_observed_run_inference():
    assert C.infer_run_result("22 passed in 0.31s", PY) == 0
    assert C.infer_run_result("1 failed, 21 passed in 0.40s", PY) == 1
    assert C.infer_run_result("garbage with no verdict", PY) is None


# --------------------------------------------------------- B7: spec schema

def test_B7_complete_spec_passes():
    assert check_spec_text(VALID_SPEC) == []


def test_B7_property_section_requires_property_or_signed_justification():
    no_prop = VALID_SPEC.replace("- **P1** [identity] add(x, 0) == x for all x.", "TBD")
    findings = check_spec_text(no_prop)
    assert any("P1" in f or "Property" in f for f in findings)
    justified = VALID_SPEC.replace(
        "- **P1** [identity] add(x, 0) == x for all x.",
        "No non-trivial property found — justification: pure UI copy change — signed by user 2026-07-22.",
    )
    assert check_spec_text(justified) == []


def test_B7_missing_sections_are_each_reported():
    findings = check_spec_text("# Behavior Spec: Empty\n")
    assert len(findings) >= 8


# ----------------------------------------- B8: the hook process, end to end

def test_B8_hook_process_denies_via_stdout_json(tmp_path):
    proj, _, _ = make_project(tmp_path, "BRAINSTORM")
    inp = json.dumps({**pt("Read", file_path=f"{proj}/src/app.py"), "cwd": proj})
    proc = run_cli("bdk_hooks.py", ["pretooluse"], proj, stdin=inp)
    assert proc.returncode == 0
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_B8_hook_process_is_inert_without_state_and_when_disabled(tmp_path):
    empty = tmp_path / "no-bdk"
    empty.mkdir()
    inp = json.dumps({**pt("Read", file_path=str(empty / "src.py")), "cwd": str(empty)})
    proc = run_cli("bdk_hooks.py", ["pretooluse"], str(empty), stdin=inp)
    assert proc.returncode == 0 and proc.stdout.strip() == ""

    proj, _, _ = make_project(tmp_path / "disabled", "BRAINSTORM", enabled=False)
    inp = json.dumps({**pt("Read", file_path=f"{proj}/src/app.py"), "cwd": proj})
    proc = run_cli("bdk_hooks.py", ["pretooluse"], proj, stdin=inp)
    assert proc.returncode == 0 and proc.stdout.strip() == ""


def test_B8_banner_injected_on_prompt_submit(tmp_path):
    proj, _, _ = make_project(tmp_path, "GREEN")
    proc = run_cli("bdk_hooks.py", ["userpromptsubmit"], proj, stdin=json.dumps({"cwd": proj}))
    out = json.loads(proc.stdout)
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "phase=GREEN" in ctx and "simplest code" in ctx


# ------------------------------------- B9-B11: the gate pipeline, end to end

def test_B9_full_gate_pipeline_red_green_refactor_done(tmp_path):
    proj = write_feature(tmp_path, "raise NotImplementedError")

    red = run_cli("bdk_gate.py", ["verify-red"], proj)
    assert red.returncode == 0, red.stdout + red.stderr
    assert "genuine red" in red.stdout

    early = run_cli("bdk_gate.py", ["to-green"], proj)
    assert early.returncode == 2 and "reviewer" in early.stdout and "EDFH" in early.stdout

    assert run_cli("bdk_gate.py", ["record", "reviewer", "PASS"], proj).returncode == 0
    assert run_cli("bdk_gate.py", ["record", "edfh", "SURVIVED"], proj).returncode == 0
    green = run_cli("bdk_gate.py", ["to-green"], proj)
    assert green.returncode == 0, green.stdout
    assert json.loads(run_cli("bdk_state.py", ["get", "phase"], proj).stdout) == "GREEN"

    still_red = run_cli("bdk_gate.py", ["to-refactor"], proj)
    assert still_red.returncode == 2

    (tmp_path / "src" / "calc.py").write_text("def add(x, y):\n    return x + y\n")
    refactor = run_cli("bdk_gate.py", ["to-refactor"], proj)
    assert refactor.returncode == 0, refactor.stdout
    assert json.loads(run_cli("bdk_state.py", ["get", "phase"], proj).stdout) == "REFACTOR"

    done = run_cli("bdk_gate.py", ["verify-done"], proj)
    assert done.returncode == 0, done.stdout
    assert "bdk_state.py archive" in done.stdout


def test_B10_verify_red_rejects_a_passing_suite(tmp_path):
    proj = write_feature(tmp_path, "return x + y")
    red = run_cli("bdk_gate.py", ["verify-red"], proj)
    assert red.returncode == 2 and "PASSES" in red.stdout


def test_B11_verify_red_rejects_import_errors_with_stub_guidance(tmp_path):
    proj = write_feature(
        tmp_path, "raise NotImplementedError",
        test_body=("from calc_that_does_not_exist import add\n\n"
                   "def test_B1_adds():\n    assert add(2, 2) == 4\n"),
    )
    red = run_cli("bdk_gate.py", ["verify-red"], proj)
    assert red.returncode == 2 and "WRONG reason" in red.stdout and "stub" in red.stdout


def test_B12_done_blocks_while_throwaway_scaffolding_exists(tmp_path):
    proj = write_feature(tmp_path, "return x + y")
    for args in (["set", "phase", '"GREEN"'], ["set", "red_evidence", "{}"],
                 ["append", "throwaway_tests", "tests/test_scratch.py"]):
        assert run_cli("bdk_state.py", args, proj).returncode == 0
    done = run_cli("bdk_gate.py", ["verify-done"], proj)
    assert done.returncode == 2 and "throwaway" in done.stdout


# ------------------------------------------------- B13: the Stop-hook net

def test_B13_stop_blocks_red_then_allows_after_fix(tmp_path):
    proj = write_feature(tmp_path, "raise NotImplementedError")
    run_cli("bdk_state.py", ["set", "phase", '"GREEN"'], proj)

    proc = run_cli("bdk_hooks.py", ["stop"], proj, stdin=json.dumps({"cwd": proj}))
    out = json.loads(proc.stdout)
    assert out["decision"] == "block" and "red or stale" in out["reason"]

    (tmp_path / "src" / "calc.py").write_text("def add(x, y):\n    return x + y\n")
    proc = run_cli("bdk_hooks.py", ["stop"], proj, stdin=json.dumps({"cwd": proj}))
    assert proc.stdout.strip() == ""  # fresh green recorded, no block


def test_B13_stop_gives_up_after_two_blocks(tmp_path):
    proj = write_feature(tmp_path, "raise NotImplementedError")
    run_cli("bdk_state.py", ["set", "phase", '"GREEN"'], proj)
    run_cli("bdk_state.py", ["set", "stop_block_count", "2"], proj)
    proc = run_cli("bdk_hooks.py", ["stop"], proj, stdin=json.dumps({"cwd": proj}))
    out = json.loads(proc.stdout)
    assert "decision" not in out and "giving up" in out["systemMessage"]


# ------------------------------- B14: the reviewer's non-determinism finder

def flagged(snippet, patterns):
    return any(re.search(p, snippet) for p in patterns)


def test_B14_nondeterminism_regexes_flag_unseeded_input_and_clear_reproducible_input():
    """Given a test line that draws a fresh value on every run, the adapter's
    nondeterminism candidate-finder marks it; given a seeded generator, a PBT
    generator, or an enumerated boundary list, it stays silent."""
    for adapter in (PY, TS):
        assert adapter["nondeterminism_regexes"], adapter["adapter"]

    for snippet in ("qty = random.randint(1, 100)", "pick = random.choice(words)",
                    "from random import randint", "rng = random.Random()",
                    "uid = uuid.uuid4()", "now = datetime.now()",
                    "stamp = time.time()", "name = Faker().name()",
                    "salt = os.urandom(16)", "tok = secrets.token_hex(8)"):
        assert flagged(snippet, PY["nondeterminism_regexes"]), snippet

    for snippet in ("rng = random.Random(1234)",
                    "@given(st.lists(st.integers()))",
                    "@settings(max_examples=200)",
                    "for qty in (0, 1, MAX, MAX + 1):",
                    "frozen = datetime(2026, 1, 1)"):
        assert not flagged(snippet, PY["nondeterminism_regexes"]), snippet

    for snippet in ("const x = Math.random()", "const id = crypto.randomUUID()",
                    "const t = Date.now()", "const d = new Date()",
                    "const n = faker.person.firstName()"):
        assert flagged(snippet, TS["nondeterminism_regexes"]), snippet

    for snippet in ("fc.assert(fc.property(fc.integer(), f), { numRuns: 200 })",
                    "const d = new Date('2026-01-01T00:00:00Z')",
                    "for (const qty of [0, 1, MAX, MAX + 1])"):
        assert not flagged(snippet, TS["nondeterminism_regexes"]), snippet


# ------------------------------------------------------------- P: properties

def test_P1_test_globs_partition_paths_for_all_generated_names():
    """[invariant] Anything under tests/ or named test_*/*_test is a test path;
    plain src paths never are — for arbitrary generated names."""
    rng = random.Random(1234)
    words = ["alpha", "beta", "gamma", "delta", "omega", "kappa", "zeta"]
    for _ in range(300):
        a, b = rng.choice(words), rng.choice(words)
        assert C.is_test_path(f"tests/{a}/{b}.py", PY)
        assert C.is_test_path(f"pkg/{a}/test_{b}.py", PY)
        assert C.is_test_path(f"pkg/{a}_test.py", PY)
        assert not C.is_test_path(f"src/{a}/{b}.py", PY)
        assert not C.is_test_path(f"{a}/{b}_helper.py", PY)


def test_P2_test_def_count_is_additive_over_concatenation():
    """[different paths, same destination] Counting defs of a concatenation equals
    the sum of the parts — so REFACTOR's increase-detection can't be confused by
    where in the file an edit lands."""
    rng = random.Random(99)
    frags = [
        "def test_a():\n    pass\n",
        "def helper():\n    pass\n",
        "    def test_inner():\n        pass\n",
        "x = 1\n",
        "async def test_b():\n    pass\n",
        "# def test_commented():\n",
    ]
    for _ in range(200):
        a = "".join(rng.choices(frags, k=rng.randint(0, 5)))
        b = "".join(rng.choices(frags, k=rng.randint(0, 5)))
        assert C.count_test_defs(a + b, PY) == C.count_test_defs(a, PY) + C.count_test_defs(b, PY)


def test_P3_manifest_round_trip_detects_exactly_what_changed(tmp_path):
    """[round trip + invariant] Unchanged files -> empty drift; adding one test def
    to one file -> exactly that file reported with defs_added == 1."""
    rng = random.Random(7)
    (tmp_path / "tests").mkdir()
    rels = []
    for i in range(5):
        rel = f"tests/test_gen{i}.py"
        n = rng.randint(0, 4)
        body = "".join(f"def test_case_{i}_{j}():\n    pass\n" for j in range(n))
        (tmp_path / rel).write_text(body or "# empty\n")
        rels.append(rel)
    manifest = C.build_manifest(str(tmp_path), rels, PY)
    assert C.manifest_drift(str(tmp_path), manifest, PY) == {}
    victim = rng.choice(rels)
    with open(tmp_path / victim, "a") as f:
        f.write("def test_added_later():\n    pass\n")
    drift = C.manifest_drift(str(tmp_path), manifest, PY)
    assert set(drift) == {victim}
    assert drift[victim]["defs_added"] == 1 and drift[victim]["sha_changed"]
