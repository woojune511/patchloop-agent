"""Source-only proposal for a public AnyIO runner-continuity check.

The proposal is derived only from the AnyIO-v5 public task.  Building this
artifact compiles the proposed Python body, but never executes the check,
Docker, an evaluator, or a provider.  It is not a task successor and grants no
activation authority.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from patchloop.util import sha256_bytes, sha256_json

SCHEMA_VERSION = "anyio-runner-continuity-public-check-source-qualification-v1"
POLICY_VERSION = "public-runner-continuity-composite-outcomes-v1"
CHECK_ID = "public-runner-continuity-composite-outcomes"
SOURCE_TASK_PATH = Path("fixtures/task-packages/anyio-interrupt-runner-cleanup-v5/public.yaml")
QUALIFICATION_PATH = Path(
    "experiments/anyio-runner-continuity-public-check-source-qualification-20260831-v1.json"
)
SOURCE_FILES = (
    "patchloop/evals/anyio_runner_continuity_public_check.py",
    "scripts/build_anyio_runner_continuity_public_check_qualification.py",
    "tests/test_anyio_runner_continuity_public_check.py",
)


CHECK_SCRIPT = r'''import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path


with tempfile.TemporaryDirectory(prefix="patchloop-anyio-runner-continuity-") as selected:
    root = Path(selected)
    event_log = root / "events.log"
    test_path = root / "test_runner_continuity.py"
    test_path.write_text(
        textwrap.dedent(
            f"""
            import asyncio
            from pathlib import Path

            import pytest

            EVENT_LOG = Path({str(event_log)!r})

            def record(label):
                loop_id = id(asyncio.get_running_loop())
                with EVENT_LOG.open("a", encoding="utf-8") as stream:
                    stream.write(f"{{label}}:{{loop_id}}\\n")

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
            async def test_skip(shared):
                record("skip")
                pytest.skip("public skip")

            @pytest.mark.anyio
            async def test_xfail(shared):
                record("xfail")
                pytest.xfail("public xfail")

            @pytest.mark.anyio
            async def test_ordinary_failure(shared):
                record("ordinary-failure")
                assert False, "expected public ordinary failure"

            @pytest.mark.anyio
            async def test_after_outcomes(shared):
                record("after-outcomes")
            """
        ),
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTHONPATH": "/workspace/src",
        }
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--no-header",
            "-q",
            "-p",
            "anyio.pytest_plugin",
            "-p",
            "no:cacheprovider",
            str(test_path),
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    events = event_log.read_text(encoding="utf-8").splitlines() if event_log.is_file() else []
    labels = [event.rsplit(":", 1)[0] for event in events]
    loop_ids = [event.rsplit(":", 1)[1] for event in events if ":" in event]
    expected_labels = [
        "shared-start",
        "skip",
        "xfail",
        "ordinary-failure",
        "after-outcomes",
        "shared-cleanup",
    ]
    if completed.returncode != 1:
        raise AssertionError("PUBLIC_CASE:anyio:runner-continuity-status")
    if labels != expected_labels:
        raise AssertionError("PUBLIC_CASE:anyio:runner-continuity-events")
    if len(loop_ids) != len(expected_labels) or len(set(loop_ids)) != 1:
        raise AssertionError("PUBLIC_CASE:anyio:runner-continuity-loop-identity")
    output = completed.stdout + "\n" + completed.stderr
    for summary in ("1 failed", "1 passed", "1 skipped", "1 xfailed"):
        if summary not in output:
            raise AssertionError("PUBLIC_CASE:anyio:runner-continuity-summary")
'''


def proposed_check() -> dict[str, Any]:
    """Return the deterministic public check definition without executing it."""

    return {
        "id": CHECK_ID,
        "command": ["/opt/conda/envs/testbed/bin/python", "-c", CHECK_SCRIPT],
        "timeout_seconds": 30,
        "environment": {
            "PYTHONPATH": "/workspace/src",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        },
        "working_directory": ".",
        "output_limit_bytes": 20_000,
        "expected_base_observation": "pass_unverified",
        "expected_reference_observation": "pass_unverified",
    }


def _binding(root: Path, relative: Path | str) -> dict[str, Any]:
    path = (root / relative).resolve()
    path.relative_to(root)
    raw = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }


def _public_source_contract(root: Path) -> dict[str, Any]:
    raw = (root / SOURCE_TASK_PATH).read_bytes()
    source = yaml.safe_load(raw)
    if not isinstance(source, dict):
        raise ValueError("AnyIO-v5 public task source is invalid")
    issue = source.get("issue")
    checks = source.get("visible_checks")
    if (
        source.get("task_id") != "anyio-interrupt-runner-cleanup"
        or source.get("task_version") != 5
        or not isinstance(issue, dict)
        or not isinstance(checks, list)
    ):
        raise ValueError("AnyIO-v5 public identity differs")
    check_ids = [check.get("id") for check in checks if isinstance(check, dict)]
    expected_ids = [
        "public-interrupt-runner-lifecycle",
        "public-ordinary-failure-preservation",
        "upstream-pytest-plugin-regression",
    ]
    if check_ids != expected_ids:
        raise ValueError("AnyIO-v5 public visible-check order differs")
    description = str(issue.get("description", ""))
    for fragment in (
        "Preserve normal pytest",
        "pass, failure, skip, and expected-failure outcomes",
        "lifetime spans more than one test",
    ):
        if fragment not in description:
            raise ValueError("AnyIO-v5 public outcome contract differs")
    scripts = ["\n".join(check.get("command", [])) for check in checks[:2]]
    if not all(isinstance(script, str) for script in scripts):
        raise ValueError("AnyIO-v5 public check command differs")
    combined = "\n".join(scripts)
    for marker in ("test_skip", "test_xfail", "test_pass", "test_ordinary_failure"):
        if marker not in combined:
            raise ValueError("AnyIO-v5 public outcome coverage differs")
    composite_markers = ("test_skip", "test_ordinary_failure")
    composite_already_present = any(
        all(marker in script for marker in composite_markers) for script in scripts
    )
    if composite_already_present:
        raise ValueError("AnyIO-v5 already contains the proposed composite scenario")
    return {
        "public_task_file_sha256": sha256_bytes(raw),
        "public_task_content_hash": sha256_json(source),
        "task_id": source["task_id"],
        "task_version": source["task_version"],
        "visible_check_ids": check_ids,
        "public_outcome_clause_present": True,
        "existing_outcomes_split_across_checks": True,
        "composite_runner_continuity_present": False,
        "proposed_intersection": (
            "one module-scoped async fixture and one asyncio loop survive skip, xfail, "
            "ordinary failure, and a later pass before exactly one cleanup"
        ),
    }


def build_qualification(repository: str | Path = ".") -> dict[str, Any]:
    """Build a deterministic zero-call source qualification for the proposal."""

    root = Path(repository).resolve()
    check = proposed_check()
    compile(CHECK_SCRIPT, f"<{CHECK_ID}>", "exec")
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "status": "offline-source-qualified-proposal",
        "activation_authorized": False,
        "task_successor_created": False,
        "behavior_observed": False,
        "paid_execution_authorized": False,
        "public_source_contract": _public_source_contract(root),
        "proposed_check": check,
        "proposed_check_hash": sha256_json(check),
        "qualification_assertions": {
            "single_module_scoped_async_generator_fixture": True,
            "single_runner_identity_expected": True,
            "skip_xfail_failure_then_pass_order": True,
            "shared_cleanup_exactly_once_and_last": True,
            "expected_observations_are_unverified": True,
            "does_not_attribute_hidden_failures": True,
        },
        "evidence_boundary": {
            "public_task_source_only": True,
            "private_task_spec_read_by_builder": False,
            "hidden_evaluator_content_read_by_builder": False,
            "reference_patch_read_by_builder": False,
            "reasoning_text_read_by_builder": False,
            "docker_calls": 0,
            "provider_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "network_calls": 0,
            "added_cost_usd": 0,
        },
        "source_bindings": [_binding(root, item) for item in SOURCE_FILES],
        "input_bindings": [_binding(root, SOURCE_TASK_PATH)],
    }
    body["content_hash"] = sha256_json(body)
    return body


def qualification_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
