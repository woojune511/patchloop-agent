"""Public-only source qualification for AnyIO ordinary-failure preservation.

The consumed AnyIO-v4 task and R14 artifacts are immutable.  This module does
not activate a task, run Docker, inspect private task material, or execute a
registered check.  It defines and source-qualifies one append-only public check
that covers the exact public contract intersection missing from the targeted
v4 check: a normal pytest failure while an async-generator fixture remains
leased across more than one test.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from patchloop.util import sha256_bytes, sha256_json

SCHEMA_VERSION = "anyio-ordinary-failure-public-check-source-qualification-v1"
POLICY_VERSION = "public-ordinary-failure-preservation-v1"
CHECK_ID = "public-ordinary-failure-preservation"
SOURCE_TASK_PATH = Path("fixtures/task-packages/anyio-interrupt-runner-cleanup-v4/public.yaml")
R14_DIAGNOSIS_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-causal-plan-projection-ab-20260826-r14-"
    "workflow-diagnosis-v1.json"
)
QUALIFICATION_PATH = Path(
    "experiments/anyio-ordinary-failure-public-check-source-qualification-20260827-v1.json"
)
SOURCE_FILES = (
    "patchloop/evals/anyio_ordinary_failure_public_check.py",
    "scripts/build_anyio_ordinary_failure_public_check_qualification.py",
    "tests/test_anyio_ordinary_failure_public_check.py",
)


CHECK_SCRIPT = r'''import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path


with tempfile.TemporaryDirectory(prefix="patchloop-anyio-ordinary-failure-") as selected:
    root = Path(selected)
    event_log = root / "events.log"
    test_path = root / "test_ordinary_failure.py"
    test_path.write_text(
        textwrap.dedent(
            f"""
            import pytest
            from pathlib import Path

            EVENT_LOG = Path({str(event_log)!r})

            def record(value):
                with EVENT_LOG.open("a", encoding="utf-8") as stream:
                    stream.write(value + "\\n")

            @pytest.fixture(scope="module")
            def anyio_backend():
                return "asyncio"

            @pytest.fixture(scope="module")
            async def shared(anyio_backend):
                record("shared-start")
                try:
                    yield
                finally:
                    record("shared-cleanup")

            @pytest.mark.anyio
            async def test_ordinary_failure(shared):
                record("ordinary-failure")
                assert False, "expected public ordinary failure"

            @pytest.mark.anyio
            async def test_after_failure(shared):
                record("after-failure")
            """
        ),
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--disable-warnings",
            "-p",
            "anyio",
            "-p",
            "no:asyncio",
            "-p",
            "no:trio",
            str(test_path),
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
    )
    events = (
        event_log.read_text(encoding="utf-8").splitlines()
        if event_log.is_file()
        else []
    )
    expected_events = [
        "shared-start",
        "ordinary-failure",
        "after-failure",
        "shared-cleanup",
    ]
    if completed.returncode != 1:
        raise AssertionError("PUBLIC_CASE:anyio:ordinary-failure-status")
    if events != expected_events:
        raise AssertionError("PUBLIC_CASE:anyio:ordinary-failure-events")
    output = completed.stdout + "\n" + completed.stderr
    if "1 failed" not in output or "1 passed" not in output:
        raise AssertionError("PUBLIC_CASE:anyio:ordinary-failure-summary")
'''


def proposed_check() -> dict[str, Any]:
    """Return the deterministic public check definition; do not execute it."""

    return {
        "id": CHECK_ID,
        "command": ["/opt/conda/envs/testbed/bin/python", "-c", CHECK_SCRIPT],
        "timeout_seconds": 30,
        "environment": {
            "PYTHONPATH": "/workspace/src",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        "working_directory": ".",
        "output_limit_bytes": 20_000,
        "expected_base_observation": "pass",
        "expected_reference_observation": "pass",
    }


def _binding(root: Path, relative: Path | str) -> dict[str, Any]:
    path = (root / relative).resolve()
    path.relative_to(root)
    raw = path.read_bytes()
    result: dict[str, Any] = {
        "path": path.relative_to(root).as_posix(),
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }
    if path.suffix == ".json":
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and isinstance(parsed.get("content_hash"), str):
            result["content_hash"] = parsed["content_hash"]
    return result


def _public_source_gap(root: Path) -> dict[str, Any]:
    raw = (root / SOURCE_TASK_PATH).read_bytes()
    source = yaml.safe_load(raw)
    if not isinstance(source, dict):
        raise ValueError("AnyIO public task source is invalid")
    issue = source.get("issue")
    checks = source.get("visible_checks")
    if (
        source.get("task_id") != "anyio-interrupt-runner-cleanup"
        or source.get("task_version") != 4
        or not isinstance(issue, dict)
        or not isinstance(checks, list)
        or len(checks) != 2
    ):
        raise ValueError("AnyIO-v4 public identity differs")
    description = str(issue.get("description", ""))
    required_fragments = (
        "normal pytest",
        "failure",
        "fixtures whose",
        "lifetime spans more than one test",
    )
    if any(fragment not in description for fragment in required_fragments):
        raise ValueError("AnyIO-v4 public ordinary-failure clause differs")
    targeted = checks[0]
    upstream = checks[1]
    if (
        targeted.get("id") != "public-interrupt-runner-lifecycle"
        or upstream.get("id") != "upstream-pytest-plugin-regression"
    ):
        raise ValueError("AnyIO-v4 visible-check order differs")
    command = targeted.get("command")
    if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
        raise ValueError("AnyIO-v4 targeted command differs")
    script = "\n".join(command)
    for required in ("test_skip", "test_xfail", "test_pass", "shared-cleanup"):
        if required not in script:
            raise ValueError("AnyIO-v4 outcome scenario differs")
    if "test_ordinary_failure" in script or "ordinary-failure" in script:
        raise ValueError("AnyIO-v4 already contains the proposed public scenario")
    return {
        "public_task_file_sha256": sha256_bytes(raw),
        "public_task_content_hash": sha256_json(source),
        "task_id": source["task_id"],
        "task_version": source["task_version"],
        "visible_check_ids": [item["id"] for item in checks],
        "public_clause_present": True,
        "targeted_shared_fixture_present": True,
        "targeted_skip_xfail_pass_present": True,
        "targeted_ordinary_failure_present": False,
        "missing_intersection": (
            "ordinary pytest failure under one async-generator fixture spanning "
            "a later test, with one final cleanup"
        ),
    }


def _r14_public_result(root: Path) -> dict[str, Any]:
    raw = (root / R14_DIAGNOSIS_PATH).read_bytes()
    diagnosis = json.loads(raw)
    boundary = diagnosis.get("evidence_boundary")
    rows = diagnosis.get("rows")
    if not isinstance(boundary, dict) or not isinstance(rows, list):
        raise ValueError("R14 public diagnosis differs")
    if any(
        boundary.get(key) is not expected
        for key, expected in (
            ("hidden_evaluator_content_read", False),
            ("private_task_spec_read", False),
            ("reference_patch_read", False),
            ("reasoning_text_read", False),
        )
    ):
        raise ValueError("R14 diagnosis crossed the public evidence boundary")
    submitted = [row for row in rows if row.get("submission_completed") is True]
    if len(submitted) != 2 or any(row.get("success_at_budget") is not False for row in submitted):
        raise ValueError("R14 submitted public row tuple differs")
    if any(row.get("visible_checks", {}).get("passes") != 2 for row in submitted):
        raise ValueError("R14 submitted visible-check tuple differs")
    return {
        "diagnosis_file_sha256": sha256_bytes(raw),
        "diagnosis_content_hash": diagnosis["content_hash"],
        "submitted_run_ids": [row["run_id"] for row in submitted],
        "submitted_visible_checks_passed": [2, 2],
        "submitted_successes": [False, False],
        "hidden_failure_cause_attributed": False,
    }


def build_qualification(repository: str | Path = ".") -> dict[str, Any]:
    """Build a deterministic, zero-call source qualification."""

    root = Path(repository).resolve()
    check = proposed_check()
    compile(CHECK_SCRIPT, f"<{CHECK_ID}>", "exec")
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "status": "offline-source-qualified",
        "activation_authorized": False,
        "task_version_created": False,
        "paid_execution_authorized": False,
        "public_source_gap": _public_source_gap(root),
        "r14_public_result": _r14_public_result(root),
        "proposed_check": check,
        "proposed_check_hash": sha256_json(check),
        "qualification_assertions": {
            "module_scoped_async_generator_fixture": True,
            "ordinary_assertion_failure": True,
            "later_test_must_execute": True,
            "pytest_exit_code_must_be_one": True,
            "one_failed_one_passed_summary": True,
            "shared_cleanup_exactly_once_and_last": True,
            "base_and_reference_are_both_expected_to_pass": True,
            "does_not_claim_hidden_failure_attribution": True,
        },
        "evidence_boundary": {
            "public_only": True,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "reasoning_text_read": False,
            "docker_calls": 0,
            "provider_calls": 0,
            "evaluator_calls": 0,
            "registered_check_calls": 0,
            "network_calls": 0,
            "added_cost_usd": 0,
        },
        "source_bindings": [_binding(root, item) for item in SOURCE_FILES],
        "input_bindings": [
            _binding(root, SOURCE_TASK_PATH),
            _binding(root, R14_DIAGNOSIS_PATH),
        ],
    }
    body["content_hash"] = sha256_json(body)
    return body


def qualification_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
