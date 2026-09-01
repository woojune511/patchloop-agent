"""Append-only AnyIO-v5 public task successor and zero-call qualification.

The new public check was derived from the AnyIO-v4 public issue and separately
qualified on immutable base/reference trees.  This module creates no Rapid
candidate and never calls Docker, an evaluator, a provider, or a registered
check.  Private evaluator material is copied as opaque bytes; only the private
task-version metadata line changes.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

from patchloop.evals.anyio_ordinary_failure_public_check import proposed_check
from patchloop.task_loader import load_task_package
from patchloop.util import ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "anyio-ordinary-failure-public-task-successor-source-qualification-v1"
POLICY_VERSION = "public-ordinary-failure-task-successor-v1"
PREDECESSOR_PATH = Path("fixtures/task-packages/anyio-interrupt-runner-cleanup-v4")
SUCCESSOR_PATH = Path("fixtures/task-packages/anyio-interrupt-runner-cleanup-v5")
QUALIFICATION_PATH = Path(
    "experiments/anyio-ordinary-failure-public-task-successor-source-qualification-20260827-v1.json"
)

CHECK_QUALIFICATION_CANDIDATE_PATH = Path(
    "reports/rapid-development/artifacts/"
    "anyio-ordinary-failure-public-check-qualification-candidate-v1.json"
)
CHECK_QUALIFICATION_APPROVAL_PATH = Path(
    "reports/rapid-development/artifacts/"
    "anyio-ordinary-failure-public-check-qualification-approval-v1.json"
)
CHECK_QUALIFICATION_ATTEMPT_PATH = Path(
    "reports/rapid-development/artifacts/"
    "anyio-ordinary-failure-public-check-qualification-attempt-v1.json"
)
CHECK_QUALIFICATION_RESULT_PATH = Path(
    "reports/rapid-development/artifacts/"
    "anyio-ordinary-failure-public-check-qualification-result-v1.json"
)
CHECK_EXECUTION_HASH = "sha256:4269db56125f87e84e22a26299c9e2c58c55832e696f344068f6f09063544600"
CHECK_CANDIDATE_FILE_SHA256 = (
    "sha256:3b3341d1dc5802fad004973ef4b92d31ba8233f9a95dcd9153ed66e9e6c9fa0b"
)
CHECK_APPROVAL_FILE_SHA256 = (
    "sha256:4480985785f5143cc431f6108c20babbefc410d8fe17f54a769fb317b05cf5a0"
)
CHECK_ATTEMPT_FILE_SHA256 = (
    "sha256:947157dbee188f4f5c55b1cddcc16c5f61ad722bc5f8217b5386441cee5203ad"
)
CHECK_RESULT_FILE_SHA256 = "sha256:ff70ac1a63a78d5cbb05b1a50510ce270c294252192aed196804848e3f81f760"
CHECK_RESULT_CONTENT_HASH = (
    "sha256:0e5d5e48dc15b0fa01bb1d83ff8068cdf28d6ebe6affed7c407e6eb1cdef465a"
)

TARGETED_CHECK_ID = "public-interrupt-runner-lifecycle"
PRESERVATION_CHECK_ID = "public-ordinary-failure-preservation"
UPSTREAM_CHECK_ID = "upstream-pytest-plugin-regression"
OPAQUE_PATHS = (
    "environment.yaml",
    "reference.patch",
    "hidden/test_interrupt_runner_cleanup.py",
)
SOURCE_PATHS = (
    "patchloop/evals/anyio_ordinary_failure_task_successor.py",
    "patchloop/evals/anyio_ordinary_failure_public_check.py",
    "scripts/build_anyio_ordinary_failure_public_task_successor.py",
    "tests/test_anyio_ordinary_failure_task_successor.py",
)

AUDIT_TEXT = """# AnyIO public ordinary-failure preservation successor v5

This append-only successor preserves the AnyIO-v4 repository, issue, constraints, environment,
reference patch and hidden evaluator bytes. Public metadata advances to version 5 and adds the
independently qualified `public-ordinary-failure-preservation` check between the interrupt-specific
check and upstream regression. Private metadata changes only its task version.

The new check comes only from the public requirement to preserve normal pytest failures under a
shared async-generator fixture. Execution
`sha256:4269db56125f87e84e22a26299c9e2c58c55832e696f344068f6f09063544600` matched the local AnyIO
image and passed immutable base/reference trees. Base also passes, so this is a non-discriminating
regression guard, not evidence about the R14 hidden failure or a reference-derived solution.

This task version is not in the frozen dataset and creates no Rapid candidate, provider, evaluator,
paid or Docker authority. Any later runtime use requires its own source qualification and exact
candidate contract.
"""


class AnyIOOrdinaryFailureTaskSuccessorError(ValueError):
    """The predecessor, exact delta, qualification chain, or output differs."""


def _replace_once(value: str, before: str, after: str, *, label: str) -> str:
    if value.count(before) != 1:
        raise AnyIOOrdinaryFailureTaskSuccessorError(f"{label} delta is ambiguous")
    return value.replace(before, after, 1)


def _check_yaml_block() -> str:
    check = proposed_check()
    command = check["command"]
    if command[:2] != ["/opt/conda/envs/testbed/bin/python", "-c"] or len(command) != 3:
        raise AnyIOOrdinaryFailureTaskSuccessorError("qualified check command differs")
    script_lines = command[2].splitlines()
    script = "".join(f"        {line}\n" if line else "        \n" for line in script_lines)
    return (
        f"  - id: {PRESERVATION_CHECK_ID}\n"
        "    command:\n"
        "      - /opt/conda/envs/testbed/bin/python\n"
        "      - -c\n"
        "      - |\n"
        f"{script}"
        "    timeout_seconds: 30\n"
        "    environment:\n"
        "      PYTHONPATH: /workspace/src\n"
        '      PYTHONDONTWRITEBYTECODE: "1"\n'
        "    output_limit_bytes: 20000\n"
    )


def _successor_public_bytes(root: Path) -> bytes:
    source = (root / PREDECESSOR_PATH / "public.yaml").read_text(encoding="utf-8")
    source = _replace_once(source, "task_version: 4", "task_version: 5", label="public version")
    source = _replace_once(
        source,
        "  - id: upstream-pytest-plugin-regression\n",
        _check_yaml_block() + "  - id: upstream-pytest-plugin-regression\n",
        label="public check insertion",
    )
    source = _replace_once(
        source,
        "  - public-behavior-check-v4\n",
        "  - public-behavior-check-v5\n",
        label="public tag",
    )
    return source.encode()


def _successor_private_bytes(root: Path) -> bytes:
    source = (root / PREDECESSOR_PATH / "private.yaml").read_text(encoding="utf-8")
    source = _replace_once(source, "task_version: 4", "task_version: 5", label="private version")
    return source.encode()


def successor_files(repository: str | Path = ".") -> dict[str, bytes]:
    """Return exact successor bytes without mutating the repository."""

    root = Path(repository).resolve()
    predecessor = ensure_within(root, PREDECESSOR_PATH.as_posix())
    if predecessor.is_symlink() or not predecessor.is_dir():
        raise AnyIOOrdinaryFailureTaskSuccessorError("AnyIO-v4 predecessor is unavailable")
    files = {
        "audit.md": AUDIT_TEXT.encode(),
        "public.yaml": _successor_public_bytes(root),
        "private.yaml": _successor_private_bytes(root),
    }
    for relative in OPAQUE_PATHS:
        path = ensure_within(predecessor, relative)
        if path.is_symlink() or not path.is_file():
            raise AnyIOOrdinaryFailureTaskSuccessorError(f"opaque predecessor differs: {relative}")
        files[relative] = path.read_bytes()
    return dict(sorted(files.items()))


def _verify_materialized(root: Path, expected: dict[str, bytes]) -> None:
    destination = ensure_within(root, SUCCESSOR_PATH.as_posix())
    actual = {
        path.relative_to(destination).as_posix(): path.read_bytes()
        for path in sorted(destination.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }
    if actual != expected or any(path.is_symlink() for path in destination.rglob("*")):
        raise AnyIOOrdinaryFailureTaskSuccessorError("materialized AnyIO-v5 bytes differ")


def materialize_successor(repository: str | Path = ".") -> Path:
    """Create AnyIO-v5 once, or verify its exact existing bytes."""

    root = Path(repository).resolve()
    destination = ensure_within(root, SUCCESSOR_PATH.as_posix())
    expected = successor_files(root)
    if destination.exists():
        if destination.is_symlink() or not destination.is_dir():
            raise AnyIOOrdinaryFailureTaskSuccessorError("AnyIO-v5 destination differs")
        _verify_materialized(root, expected)
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".anyio-ordinary-failure-v5-", dir=destination.parent
    ) as selected:
        staging = Path(selected) / "package"
        staging.mkdir()
        for relative, raw in expected.items():
            path = staging / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
        os.replace(staging, destination)
    _verify_materialized(root, expected)
    return destination


def _binding(root: Path, relative: str | Path) -> dict[str, Any]:
    path = ensure_within(root, Path(relative).as_posix())
    if path.is_symlink() or not path.is_file():
        raise AnyIOOrdinaryFailureTaskSuccessorError(f"required file differs: {relative}")
    raw = path.read_bytes()
    result: dict[str, Any] = {
        "path": path.relative_to(root).as_posix(),
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }
    if path.suffix == ".json":
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AnyIOOrdinaryFailureTaskSuccessorError(
                f"required JSON differs: {relative}"
            ) from exc
        if isinstance(value, dict) and isinstance(value.get("content_hash"), str):
            result["content_hash"] = value["content_hash"]
    return result


def _load_chain_artifact(
    root: Path,
    relative: Path,
    expected_file_hash: str,
) -> dict[str, Any]:
    binding = _binding(root, relative)
    if binding["file_sha256"] != expected_file_hash:
        raise AnyIOOrdinaryFailureTaskSuccessorError(f"consumed artifact differs: {relative}")
    value = json.loads((root / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AnyIOOrdinaryFailureTaskSuccessorError(f"consumed artifact differs: {relative}")
    content = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(content):
        raise AnyIOOrdinaryFailureTaskSuccessorError(f"consumed artifact differs: {relative}")
    return value


def _qualified_check_chain(root: Path) -> dict[str, Any]:
    candidate = _load_chain_artifact(
        root, CHECK_QUALIFICATION_CANDIDATE_PATH, CHECK_CANDIDATE_FILE_SHA256
    )
    approval = _load_chain_artifact(
        root, CHECK_QUALIFICATION_APPROVAL_PATH, CHECK_APPROVAL_FILE_SHA256
    )
    attempt = _load_chain_artifact(
        root, CHECK_QUALIFICATION_ATTEMPT_PATH, CHECK_ATTEMPT_FILE_SHA256
    )
    result = _load_chain_artifact(root, CHECK_QUALIFICATION_RESULT_PATH, CHECK_RESULT_FILE_SHA256)
    execution_hashes = {
        item.get("execution_hash") for item in (candidate, approval, attempt, result)
    }
    rows = result.get("row_observations")
    if (
        execution_hashes != {CHECK_EXECUTION_HASH}
        or result.get("content_hash") != CHECK_RESULT_CONTENT_HASH
        or approval.get("status") != "EXACT_DOCKER_QUALIFICATION_APPROVED_ONCE"
        or attempt.get("status") != "DOCKER_QUALIFICATION_ATTEMPT_CLAIMED_BEFORE_CALL"
        or result.get("status") != "PUBLIC_ORDINARY_FAILURE_CHECK_QUALIFIED"
        or result.get("docker_image_inspect_calls") != 1
        or result.get("docker_container_run_attempts") != 2
        or result.get("docker_container_run_completions") != 2
        or result.get("provider_calls") != 0
        or result.get("evaluator_calls") != 0
        or result.get("agent_calls") != 0
        or result.get("network_calls") != 0
        or result.get("added_cost_usd") != 0
        or not isinstance(rows, list)
        or len(rows) != 2
        or [row.get("source_state") for row in rows] != ["base", "reference"]
        or any(row.get("check_id") != PRESERVATION_CHECK_ID for row in rows)
        or any(row.get("expected_observation_matched") is not True for row in rows)
    ):
        raise AnyIOOrdinaryFailureTaskSuccessorError("check qualification chain differs")
    check = candidate.get("proposed_check")
    if not isinstance(check, dict):
        raise AnyIOOrdinaryFailureTaskSuccessorError("qualified check projection differs")
    return {
        "candidate": _binding(root, CHECK_QUALIFICATION_CANDIDATE_PATH),
        "approval": _binding(root, CHECK_QUALIFICATION_APPROVAL_PATH),
        "attempt": _binding(root, CHECK_QUALIFICATION_ATTEMPT_PATH),
        "result": _binding(root, CHECK_QUALIFICATION_RESULT_PATH),
        "execution_hash": CHECK_EXECUTION_HASH,
        "proposed_check": check,
        "row_hashes": [sha256_json(row) for row in rows],
    }


def _inventory(root: Path, package: Path) -> dict[str, Any]:
    selected = ensure_within(root, package.as_posix())
    rows = [
        _binding(root, path.relative_to(root))
        for path in sorted(selected.rglob("*"))
        if path.is_file()
    ]
    return {
        "path": package.as_posix(),
        "file_count": len(rows),
        "inventory_hash": sha256_json(rows),
        "files": rows,
    }


def _validate_successor(root: Path, chain: dict[str, Any]) -> dict[str, Any]:
    _verify_materialized(root, successor_files(root))
    predecessor = load_task_package(root / PREDECESSOR_PATH)
    successor = load_task_package(root / SUCCESSOR_PATH)
    predecessor_checks = predecessor.public.visible_checks
    successor_checks = successor.public.visible_checks
    qualified_check = chain["proposed_check"]
    if (
        predecessor.public.task_version != 4
        or predecessor.private.task_version != 4
        or successor.public.task_version != 5
        or successor.private.task_version != 5
        or successor.public.task_id != predecessor.public.task_id
        or successor.public.issue != predecessor.public.issue
        or successor.public.constraints != predecessor.public.constraints
        or successor.public.repository != predecessor.public.repository
        or successor.environment != predecessor.environment
        or successor.private.reference_patch.sha256 != predecessor.private.reference_patch.sha256
        or [check.id for check in successor_checks]
        != [TARGETED_CHECK_ID, PRESERVATION_CHECK_ID, UPSTREAM_CHECK_ID]
        or successor_checks[0] != predecessor_checks[0]
        or successor_checks[2] != predecessor_checks[1]
        or successor_checks[1].model_dump(mode="json") != qualified_check
    ):
        raise AnyIOOrdinaryFailureTaskSuccessorError("AnyIO-v5 semantic contract differs")
    for relative in OPAQUE_PATHS:
        if (root / SUCCESSOR_PATH / relative).read_bytes() != (
            root / PREDECESSOR_PATH / relative
        ).read_bytes():
            raise AnyIOOrdinaryFailureTaskSuccessorError(f"opaque bytes differ: {relative}")

    dataset = yaml.safe_load((root / "data/dataset-manifest.yaml").read_text(encoding="utf-8"))
    admitted = {
        (item.get("task_id"), item.get("task_version"), item.get("path"))
        for item in dataset.get("tasks", [])
    }
    identity = (
        successor.public.task_id,
        successor.public.task_version,
        SUCCESSOR_PATH.as_posix(),
    )
    if identity in admitted:
        raise AnyIOOrdinaryFailureTaskSuccessorError("AnyIO-v5 entered the frozen dataset")
    return {
        "task_id": successor.public.task_id,
        "predecessor_version": predecessor.public.task_version,
        "successor_version": successor.public.task_version,
        "visible_check_ids": [check.id for check in successor_checks],
        "new_check_hash": sha256_json(successor_checks[1].model_dump(mode="json")),
        "frozen_dataset_member": False,
        "rapid_candidate_created": False,
    }


def build_qualification(repository: str | Path = ".") -> dict[str, Any]:
    """Build deterministic source evidence after the exact package is materialized."""

    root = Path(repository).resolve()
    chain = _qualified_check_chain(root)
    successor_contract = _validate_successor(root, chain)
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "status": "offline-source-qualified",
        "activation_authorized": False,
        "rapid_candidate_created": False,
        "docker_execution_authorized": False,
        "paid_execution_authorized": False,
        "successor_contract": successor_contract,
        "delta_contract": {
            "public_task_version_4_to_5": True,
            "private_metadata_version_4_to_5_only": True,
            "qualified_preservation_check_inserted_second": True,
            "targeted_check_unchanged_first": True,
            "upstream_check_unchanged_third": True,
            "environment_reference_hidden_bytes_unchanged": True,
            "audit_updated": True,
            "base_and_reference_both_passed": True,
            "check_is_non_discriminating_regression_guard": True,
            "hidden_failure_cause_attributed": False,
        },
        "qualified_check_chain": {
            key: value for key, value in chain.items() if key != "proposed_check"
        },
        "predecessor_inventory": _inventory(root, PREDECESSOR_PATH),
        "successor_inventory": _inventory(root, SUCCESSOR_PATH),
        "source_bindings": [_binding(root, item) for item in SOURCE_PATHS],
        "evidence_boundary": {
            "public_check_derived_from_public_issue_only": True,
            "private_metadata_body_projected": False,
            "hidden_evaluator_content_projected": False,
            "reference_patch_body_interpreted": False,
            "reasoning_text_read": False,
            "docker_calls": 0,
            "provider_calls": 0,
            "evaluator_calls": 0,
            "registered_check_calls": 0,
            "network_calls": 0,
            "added_cost_usd": 0,
        },
        "next_gate": "three-visible-check-runtime-compatibility-source-gate",
    }
    body["content_hash"] = sha256_json(body)
    return body


def qualification_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def materialize_qualification(repository: str | Path = ".") -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_qualification(root)
    raw = qualification_bytes(value)
    output = ensure_within(root, QUALIFICATION_PATH.as_posix())
    if output.exists():
        if output.is_symlink() or output.read_bytes() != raw:
            raise AnyIOOrdinaryFailureTaskSuccessorError("append-only qualification differs")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    return value


__all__ = [
    "AnyIOOrdinaryFailureTaskSuccessorError",
    "PREDECESSOR_PATH",
    "QUALIFICATION_PATH",
    "SUCCESSOR_PATH",
    "build_qualification",
    "materialize_qualification",
    "materialize_successor",
    "qualification_bytes",
    "successor_files",
]
