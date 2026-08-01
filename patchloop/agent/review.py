"""Load and validate public, hash-bound structured-review checklists."""

from __future__ import annotations

import fnmatch
import re
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from pydantic import ValidationError

from patchloop.contracts import (
    PublicReviewContract,
    PublicReviewCoverageTarget,
    PublicTask,
)
from patchloop.errors import ContractError
from patchloop.util import (
    canonical_json,
    safe_relative_path,
    sha256_bytes,
    sha256_json,
    sha256_text,
)

PUBLIC_REVIEW_BASE_PROVENANCE_SCHEMA = (
    "public-review-base-provenance-v1"
)

_PROHIBITED_PUBLIC_REVIEW_PATTERNS = (
    re.compile(r"(?i)\breference\.patch\b"),
    re.compile(r"(?i)\bprivate\.ya?ml\b"),
    re.compile(r"(?i)\bprivate_spec_hash\b"),
    re.compile(r"(?i)\breference_patch\b"),
    re.compile(r"(?i)\bhidden_checks?\b"),
    re.compile(r"(?i)\.patchloop-hidden(?:[/\\]|$)"),
    re.compile(r"(?i)\bhidden(?:[/\\]|_tests?(?:[/\\]|\.))"),
    re.compile(r"(?i)\bOPENAI_API_KEY\s*[:=]"),
    re.compile(r"(?i)\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"(?i)\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"(?i)\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(
        r"(?i)\bAWS_SECRET_ACCESS_KEY\s*[:=]\s*[\"']?"
        r"[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])"
    ),
    re.compile(
        r"(?i)\bAWS_(?:SESSION|SECURITY)_TOKEN\s*[:=]\s*[\"']?"
        r"[A-Za-z0-9/+=]{80,}(?![A-Za-z0-9/+=])"
    ),
)


def normalize_public_issue_text(value: str) -> str:
    """Normalize only whitespace; preserve the public issue's exact wording."""

    return re.sub(r"\s+", " ", value).strip()


def public_review_requirement_id(source_excerpt: str) -> str:
    """Derive a stable checklist ID from one normalized public excerpt."""

    normalized = normalize_public_issue_text(source_excerpt)
    digest = sha256_text(normalized).removeprefix("sha256:")
    return f"req-{digest[:12]}"


def public_review_coverage_target_id(
    requirement_id: str,
    *,
    description: str,
    evidence_kind: str,
    path: str | None = None,
    anchor: str | None = None,
    check_ids: list[str] | tuple[str, ...] | None = None,
) -> str:
    """Derive a requirement-bound ID from one normalized public target."""

    normalized_description = normalize_public_issue_text(description)
    normalized_path = (
        safe_relative_path(
            path,
            field_name="public review coverage target path",
        )
        if path is not None
        else None
    )
    normalized_anchor = anchor.strip() if anchor is not None else None
    normalized_check_ids = sorted(check_ids or [])
    digest = sha256_json(
        {
            "requirement_id": requirement_id,
            "description": normalized_description,
            "evidence_kind": evidence_kind,
            "path": normalized_path,
            "anchor": normalized_anchor,
            "check_ids": normalized_check_ids,
        }
    ).removeprefix("sha256:")
    return f"cov-{digest[:12]}"


def public_review_contract_content_hash(payload: dict[str, Any]) -> str:
    """Hash a sidecar payload without its self-authenticating hash field."""

    unhashed = dict(payload)
    unhashed.pop("content_hash", None)
    return sha256_json(unhashed)


def _load_yaml_object(path: Path) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ContractError(
            "unable to load public review contract"
        ) from exc
    if not isinstance(raw, dict):
        raise ContractError("public review contract must be a YAML mapping")
    return raw


def _contains_private_marker(value: Any) -> bool:
    try:
        rendered = canonical_json(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(
            "public review contract must contain only JSON-compatible values"
        ) from exc
    return any(
        pattern.search(rendered) is not None
        for pattern in _PROHIBITED_PUBLIC_REVIEW_PATTERNS
    )


def _matches_public_path(path: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(path, pattern) or PurePosixPath(path).match(
        pattern
    )


def _validate_public_coverage_target(
    target: PublicReviewCoverageTarget,
    *,
    requirement_id: str,
    task: PublicTask,
) -> None:
    expected_target_id = public_review_coverage_target_id(
        requirement_id,
        description=target.description,
        evidence_kind=target.evidence_kind,
        path=target.path,
        anchor=target.anchor,
        check_ids=target.check_ids,
    )
    if target.coverage_target_id != expected_target_id:
        raise ContractError(
            "public review coverage target ID does not match its canonical fields"
        )
    if target.evidence_kind == "current_diff_inspection":
        assert target.path is not None
        allowed = any(
            _matches_public_path(target.path, pattern)
            for pattern in task.constraints.allowed_paths
        )
        forbidden = any(
            _matches_public_path(target.path, pattern)
            for pattern in task.constraints.forbidden_paths
        )
        if not allowed or forbidden:
            raise ContractError(
                "public review coverage target path is not public and allowed"
            )
    else:
        visible_check_ids = {check.id for check in task.visible_checks}
        if any(check_id not in visible_check_ids for check_id in target.check_ids):
            raise ContractError(
                "public review coverage target references an unknown visible check"
            )


def validate_public_review_contract(
    contract: PublicReviewContract,
    *,
    task: PublicTask,
    public_spec_hash: str,
) -> PublicReviewContract:
    """Bind a sidecar to one public task without consulting private data."""

    actual_public_hash = sha256_json(task.model_dump(mode="json"))
    if actual_public_hash != public_spec_hash:
        raise ContractError("provided public task hash is inconsistent")
    if (contract.task_id, contract.task_version) != (
        task.task_id,
        task.task_version,
    ):
        raise ContractError("public review contract task identity mismatch")
    if contract.public_spec_hash != public_spec_hash:
        raise ContractError("public review contract public spec hash mismatch")
    if _contains_private_marker(contract.model_dump(mode="json")):
        raise ContractError("public review contract leak scan failed")

    normalized_description = normalize_public_issue_text(
        task.issue.description
    )
    for requirement in contract.requirements:
        excerpt = requirement.source_excerpt
        normalized_excerpt = normalize_public_issue_text(excerpt)
        if excerpt != normalized_excerpt:
            raise ContractError(
                "public review source excerpts must use normalized whitespace"
            )
        if normalized_excerpt not in normalized_description:
            raise ContractError(
                "public review source excerpt is not in the public issue description"
            )
        if requirement.requirement_id != public_review_requirement_id(
            normalized_excerpt
        ):
            raise ContractError(
                "public review requirement ID does not match its source excerpt"
            )
        for target in requirement.coverage_targets:
            _validate_public_coverage_target(
                target,
                requirement_id=requirement.requirement_id,
                task=task,
            )
    return contract


def build_public_review_base_provenance(
    contract: PublicReviewContract,
    *,
    repository_url: str,
    base_commit: str,
    read_base_file: Callable[[str], bytes],
) -> dict[str, Any]:
    """Prove every inspection anchor existed in the immutable public base.

    The callback must read from the repository base revision (for the Git
    workspaces used by PatchLoop, ``git show HEAD:<path>``), not from the
    mutable worktree. Only hashes and the already-public target declarations
    are retained in the returned provenance document.
    """

    if contract.schema_version != "public-review-contract-v2":
        raise ContractError(
            "public review base provenance requires contract v2"
        )
    cached_files: dict[str, bytes] = {}
    rows: list[dict[str, Any]] = []
    missing_target_ids: list[str] = []
    for requirement in contract.requirements:
        for target in requirement.coverage_targets:
            if target.evidence_kind != "current_diff_inspection":
                continue
            assert target.path is not None
            assert target.anchor is not None
            if target.path not in cached_files:
                content = read_base_file(target.path)
                if not isinstance(content, bytes):
                    raise ContractError(
                        "public review base reader must return exact bytes"
                    )
                cached_files[target.path] = content
            content = cached_files[target.path]
            found = target.anchor.encode("utf-8") in content
            rows.append(
                {
                    "coverage_target_id": target.coverage_target_id,
                    "path": target.path,
                    "anchor": target.anchor,
                    "base_file_content_hash": sha256_bytes(content),
                    "found": found,
                }
            )
            if not found:
                missing_target_ids.append(target.coverage_target_id)
    if missing_target_ids:
        raise ContractError(
            "public review inspection anchor is absent from the public base "
            "revision: "
            + ", ".join(missing_target_ids)
        )
    document = {
        "schema_version": PUBLIC_REVIEW_BASE_PROVENANCE_SCHEMA,
        "task_id": contract.task_id,
        "task_version": contract.task_version,
        "public_spec_hash": contract.public_spec_hash,
        "public_review_contract_content_hash": contract.content_hash,
        "repository_url": repository_url,
        "base_commit": base_commit,
        "inspection_targets": rows,
    }
    return validate_public_review_base_provenance_document(
        document,
        contract=contract,
        repository_url=repository_url,
        base_commit=base_commit,
    )


def validate_public_review_base_provenance_document(
    document: Any,
    *,
    contract: PublicReviewContract,
    repository_url: str,
    base_commit: str,
) -> dict[str, Any]:
    """Validate the portable CAS form of base-anchor provenance."""

    if not isinstance(document, dict):
        raise ContractError(
            "public review base provenance must be a JSON object"
        )
    expected_top_level = {
        "schema_version",
        "task_id",
        "task_version",
        "public_spec_hash",
        "public_review_contract_content_hash",
        "repository_url",
        "base_commit",
        "inspection_targets",
    }
    if set(document) != expected_top_level:
        raise ContractError(
            "public review base provenance has an invalid shape"
        )
    if (
        document.get("schema_version")
        != PUBLIC_REVIEW_BASE_PROVENANCE_SCHEMA
        or document.get("task_id") != contract.task_id
        or document.get("task_version") != contract.task_version
        or document.get("public_spec_hash") != contract.public_spec_hash
        or document.get("public_review_contract_content_hash")
        != contract.content_hash
        or document.get("repository_url") != repository_url
        or document.get("base_commit") != base_commit
    ):
        raise ContractError(
            "public review base provenance identity mismatch"
        )
    rows = document.get("inspection_targets")
    if not isinstance(rows, list):
        raise ContractError(
            "public review base provenance targets must be a list"
        )
    expected_targets = [
        target
        for requirement in contract.requirements
        for target in requirement.coverage_targets
        if target.evidence_kind == "current_diff_inspection"
    ]
    if len(rows) != len(expected_targets):
        raise ContractError(
            "public review base provenance target count mismatch"
        )
    path_hashes: dict[str, str] = {}
    for row, target in zip(rows, expected_targets, strict=True):
        if not isinstance(row, dict) or set(row) != {
            "coverage_target_id",
            "path",
            "anchor",
            "base_file_content_hash",
            "found",
        }:
            raise ContractError(
                "public review base provenance target has an invalid shape"
            )
        base_file_hash = row.get("base_file_content_hash")
        if (
            row.get("coverage_target_id") != target.coverage_target_id
            or row.get("path") != target.path
            or row.get("anchor") != target.anchor
            or row.get("found") is not True
            or not isinstance(base_file_hash, str)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", base_file_hash) is None
        ):
            raise ContractError(
                "public review base provenance target mismatch"
            )
        assert target.path is not None
        prior_hash = path_hashes.setdefault(target.path, base_file_hash)
        if prior_hash != base_file_hash:
            raise ContractError(
                "public review base provenance file hash is inconsistent"
            )
    return document


def load_public_review_contract(
    path: str | Path,
    *,
    task: PublicTask,
    public_spec_hash: str,
) -> PublicReviewContract:
    """Load one public sidecar and verify identity, content, and provenance."""

    raw = _load_yaml_object(Path(path))
    if _contains_private_marker(raw):
        raise ContractError("public review contract leak scan failed")
    try:
        contract = PublicReviewContract.model_validate(raw)
    except ValidationError as exc:
        raise ContractError(
            "public review contract validation failed"
        ) from exc
    return validate_public_review_contract(
        contract,
        task=task,
        public_spec_hash=public_spec_hash,
    )
