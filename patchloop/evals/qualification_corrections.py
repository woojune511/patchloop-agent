"""Append-only postmortem corrections for immutable qualifications."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from patchloop import __version__
from patchloop.errors import ContractError
from patchloop.evals.qualification import (
    calculate_source_evidence_hash,
    load_trace_qualification,
    qualification_path,
    qualify_run,
)
from patchloop.runtime import git_commit, repository_root, runtime_root
from patchloop.util import canonical_json, sha256_text, utc_now

CORRECTION_SCHEMA_VERSION = "trace-qualification-correction-v1"
CORRECTION_SEMANTICS_VERSION = "qualification-recomputation-v1"
_RUN_ID = re.compile(r"^run_[a-zA-Z0-9_-]+$")
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


def _require_hash(value: str, *, field: str) -> None:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ContractError(f"{field} must be a SHA-256 content hash")


def _failed_check_ids(payload: dict[str, Any]) -> list[str]:
    checks = payload.get("checks")
    if not isinstance(checks, list):
        raise ContractError("trace qualification checks are invalid")
    failed: list[str] = []
    seen: set[str] = set()
    for check in checks:
        check_id = check.get("check_id") if isinstance(check, dict) else None
        passed = check.get("passed") if isinstance(check, dict) else None
        if not isinstance(check_id, str) or not check_id or type(passed) is not bool:
            raise ContractError("trace qualification check entry is invalid")
        if check_id in seen:
            raise ContractError("trace qualification contains duplicate check IDs")
        seen.add(check_id)
        if not passed:
            failed.append(check_id)
    return failed


def _checked_recomputed(payload: dict[str, Any], *, run_id: str) -> dict[str, Any]:
    if payload.get("run_id") != run_id:
        raise ContractError("corrected qualification run identity mismatch")
    recorded_hash = payload.get("qualification_hash")
    _require_hash(recorded_hash, field="corrected qualification hash")
    semantics = {
        key: value for key, value in payload.items() if key != "qualification_hash"
    }
    if sha256_text(canonical_json(semantics)) != recorded_hash:
        raise ContractError("corrected qualification content hash mismatch")
    _require_hash(
        payload.get("source_evidence_hash"),
        field="corrected source evidence hash",
    )
    _failed_check_ids(payload)
    return semantics


def _current_harness_identity() -> dict[str, str]:
    commit = git_commit()
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ContractError("correction harness git commit is unavailable")
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=repository_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    if status.returncode != 0 or status.stdout.strip():
        raise ContractError(
            "qualification correction requires a clean harness worktree"
        )
    return {"git_commit": commit, "package_version": __version__}


def correction_path(
    run_id: str,
    correction_id: str,
    *,
    root: str | Path | None = None,
) -> Path:
    if _RUN_ID.fullmatch(run_id) is None:
        raise ContractError("invalid correction run ID")
    if re.fullmatch(r"qcor_[0-9a-f]{64}", correction_id) is None:
        raise ContractError("invalid qualification correction ID")
    base = Path(root) if root is not None else runtime_root()
    return (
        base
        / "qualification-corrections"
        / "v1"
        / run_id
        / f"{correction_id}.json"
    )


def _validate_existing(
    path: Path,
    *,
    correction_id: str,
    semantic_body: dict[str, Any],
) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("qualification correction artifact is invalid") from exc
    if not isinstance(payload, dict):
        raise ContractError("qualification correction artifact is invalid")
    recorded_hash = payload.get("correction_hash")
    expected_body_hash = sha256_text(canonical_json(semantic_body))
    unhashed = {
        key: value for key, value in payload.items() if key != "correction_hash"
    }
    if (
        payload.get("schema_version") != CORRECTION_SCHEMA_VERSION
        or payload.get("correction_id") != correction_id
        or payload.get("semantic_body_hash") != expected_body_hash
        or correction_id
        != f"qcor_{expected_body_hash.removeprefix('sha256:')}"
        or not isinstance(recorded_hash, str)
        or sha256_text(canonical_json(unhashed)) != recorded_hash
    ):
        raise ContractError("qualification correction artifact integrity failed")
    existing_body = {
        key: value
        for key, value in payload.items()
        if key
        not in {
            "correction_id",
            "correction_hash",
            "created_at",
            "semantic_body_hash",
        }
    }
    if existing_body != semantic_body:
        raise ContractError("qualification correction path already has other content")
    return payload


def create_qualification_correction(
    run_id: str,
    *,
    task_dir: str | Path,
    expected_original_qualification_hash: str,
    expected_source_evidence_hash: str,
    reason: str,
    dataset_manifest_path: str | Path | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Recompute qualification semantics and append a bound correction artifact."""

    if _RUN_ID.fullmatch(run_id) is None:
        raise ContractError("invalid correction run ID")
    _require_hash(
        expected_original_qualification_hash,
        field="expected original qualification hash",
    )
    _require_hash(
        expected_source_evidence_hash,
        field="expected source evidence hash",
    )
    normalized_reason = reason.strip() if isinstance(reason, str) else ""
    if not normalized_reason or len(normalized_reason) > 1_000:
        raise ContractError("qualification correction reason must contain 1-1000 characters")

    run_root = Path(root) if root is not None else runtime_root()
    original_path = qualification_path(run_id, root=run_root)
    try:
        original_bytes = original_path.read_bytes()
    except OSError as exc:
        raise ContractError(f"trace qualification is unavailable: {run_id}") from exc
    original = load_trace_qualification(run_id, root=run_root)
    if original.get("qualification_hash") != expected_original_qualification_hash:
        raise ContractError("original qualification hash does not match approval")
    if original.get("source_evidence_hash") != expected_source_evidence_hash:
        raise ContractError("source evidence hash does not match approval")
    current_source_hash = calculate_source_evidence_hash(
        run_id,
        root=run_root,
        require_valid_plan=False,
    )
    if current_source_hash != expected_source_evidence_hash:
        raise ContractError("qualification source evidence changed")

    corrected = qualify_run(
        run_id,
        task_dir=task_dir,
        dataset_manifest_path=dataset_manifest_path,
        root=run_root,
        persist=False,
    )
    corrected_semantics = _checked_recomputed(corrected, run_id=run_id)
    if corrected.get("source_evidence_hash") != expected_source_evidence_hash:
        raise ContractError("corrected qualification source evidence changed")
    if (
        calculate_source_evidence_hash(
            run_id,
            root=run_root,
            require_valid_plan=False,
        )
        != expected_source_evidence_hash
    ):
        raise ContractError("qualification source evidence changed during recomputation")
    try:
        unchanged_original = original_path.read_bytes()
    except OSError as exc:
        raise ContractError("original qualification disappeared during correction") from exc
    if unchanged_original != original_bytes:
        raise ContractError("original qualification changed during correction")
    if corrected.get("qualification_hash") == original.get("qualification_hash"):
        raise ContractError("recomputed qualification has no semantic correction")

    semantic_body: dict[str, Any] = {
        "schema_version": CORRECTION_SCHEMA_VERSION,
        "semantics_version": CORRECTION_SEMANTICS_VERSION,
        "run_id": run_id,
        "reason": normalized_reason,
        "source_evidence_hash": expected_source_evidence_hash,
        "original_qualification_hash": expected_original_qualification_hash,
        "original_qualification_schema_version": original.get("schema_version"),
        "original_failed_check_ids": _failed_check_ids(original),
        "corrected_qualification_hash": corrected["qualification_hash"],
        "corrected_qualification_schema_version": corrected.get("schema_version"),
        "corrected_failed_check_ids": _failed_check_ids(corrected),
        "corrected_qualified": corrected.get("qualified"),
        "corrected_trace_integrity_passed": corrected.get(
            "trace_integrity_passed"
        ),
        "corrected_qualification_semantics": corrected_semantics,
        "source_harness_git_commit": original.get("harness_git_commit"),
        "correction_harness": _current_harness_identity(),
    }
    body_hash = sha256_text(canonical_json(semantic_body))
    correction_id = f"qcor_{body_hash.removeprefix('sha256:')}"
    path = correction_path(run_id, correction_id, root=run_root)
    if path.exists():
        return _validate_existing(
            path,
            correction_id=correction_id,
            semantic_body=semantic_body,
        )

    payload = {
        "correction_id": correction_id,
        "created_at": utc_now().isoformat(),
        "semantic_body_hash": body_hash,
        **semantic_body,
    }
    payload["correction_hash"] = sha256_text(canonical_json(payload))
    encoded = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded)
    except FileExistsError:
        return _validate_existing(
            path,
            correction_id=correction_id,
            semantic_body=semantic_body,
        )
    return payload
