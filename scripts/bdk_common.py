#!/usr/bin/env python3
"""bdk_common.py — pure helpers shared by bdk_hooks.py and bdk_gate.py.

Everything here is deliberately side-effect-free (except run_tests) so the kit
can test its own behavior at this facade. stdlib only.
"""
import hashlib
import json
import os
import re
import subprocess
import time


# ---------------------------------------------------------------- paths/state

def project_dir() -> str:
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def load_json(path: str):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def load_state(project: str):
    return load_json(os.path.join(project, ".bdk", "state.json"))


def load_config(project: str):
    return load_json(os.path.join(project, ".bdk", "config.json"))


def save_state(project: str, state: dict) -> None:
    path = os.path.join(project, ".bdk", "state.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, path)


def rel_to_project(path: str, project: str):
    """Project-relative path, or None if the path lies outside the project."""
    if not path:
        return None
    absolute = os.path.abspath(os.path.join(project, path)) if not os.path.isabs(path) else os.path.abspath(path)
    proj = os.path.abspath(project)
    if absolute == proj:
        return "."
    if not absolute.startswith(proj + os.sep):
        return None
    return os.path.relpath(absolute, proj)


# ------------------------------------------------------------- glob matching

def glob_to_regex(glob: str) -> str:
    """Convert a **-style glob to a regex over '/'-separated relative paths."""
    out, i = [], 0
    while i < len(glob):
        c = glob[i]
        if c == "*":
            if glob[i : i + 3] == "**/":
                out.append("(?:[^/]+/)*")
                i += 3
                continue
            if glob[i : i + 2] == "**":
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(c))
        i += 1
    return "^" + "".join(out) + "$"


def path_matches(rel_path: str, globs: list) -> bool:
    rel = rel_path.replace(os.sep, "/")
    for g in globs:
        if re.match(glob_to_regex(g), rel):
            return True
        # a glob like "tests/**" should also match the bare "tests" dir itself
        if g.endswith("/**") and re.match(glob_to_regex(g[:-3]), rel):
            return True
    return False


def is_test_path(rel_path: str, config: dict) -> bool:
    return path_matches(rel_path, config.get("test_globs", []))


# --------------------------------------------------------- test-def counting

def count_test_defs(text: str, config: dict) -> int:
    pattern = config.get("test_def_regex")
    if not pattern or not text:
        return 0
    return len(re.findall(pattern, text))


# ------------------------------------------------------ output classification

def classify_test_output(output: str, config: dict) -> str:
    """Classify a failing test run: 'wrong-reason' (collection/import/syntax
    errors — the suite never really ran) beats 'right-reason' (assertions)."""
    for pattern in config.get("wrong_reason_regexes", []):
        if re.search(pattern, output):
            return "wrong-reason"
    for pattern in config.get("right_reason_regexes", []):
        if re.search(pattern, output):
            return "right-reason"
    return "unknown"


def infer_run_result(output: str, config: dict):
    """Best-effort pass/fail inference from observed test output. Returns
    0 (pass), 1 (fail) or None (can't tell)."""
    for pattern in config.get("fail_regexes", []):
        if re.search(pattern, output):
            return 1
    for pattern in config.get("pass_regexes", []):
        if re.search(pattern, output):
            return 0
    return None


# ------------------------------------------------------------------ manifest

def file_sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(project: str, test_files: list, config: dict) -> dict:
    manifest = {}
    for rel in test_files:
        path = os.path.join(project, rel)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
        manifest[rel] = {"sha": file_sha(path), "test_defs": count_test_defs(text, config)}
    return manifest


def manifest_drift(project: str, manifest: dict, config: dict) -> dict:
    """Compare current test files against a recorded manifest.
    Returns {rel: {'sha_changed': bool, 'defs_added': int}} for drifted files."""
    drift = {}
    current = build_manifest(project, list(manifest.keys()), config)
    for rel, recorded in manifest.items():
        cur = current.get(rel)
        if cur is None:
            drift[rel] = {"sha_changed": True, "defs_added": -recorded["test_defs"], "missing": True}
        elif cur["sha"] != recorded["sha"]:
            drift[rel] = {
                "sha_changed": True,
                "defs_added": cur["test_defs"] - recorded["test_defs"],
            }
    return drift


# ----------------------------------------------------------------- run tests

def run_tests(project: str, config: dict, test_files: list, timeout: int = 300):
    """Run the configured test command scoped to test_files.
    Returns (exit_code, combined_output)."""
    cmd = config.get("test_cmd", "")
    existing = [f for f in test_files if os.path.isfile(os.path.join(project, f))]
    full = cmd + (" " + " ".join(existing) if existing else "")
    try:
        proc = subprocess.run(
            full, shell=True, cwd=project, capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"test run timed out after {timeout}s"


def record_test_run(project: str, state: dict, exit_code: int, via: str) -> None:
    state["last_test_run"] = {"exit": exit_code, "at": time.time(), "via": via}
    if exit_code == 0:
        state["stop_block_count"] = 0
    save_state(project, state)
