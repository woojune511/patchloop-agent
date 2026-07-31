"""Load and validate public, hash-bound structured-review checklists."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from patchloop.contracts import PublicReviewContract, PublicTask
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_json, sha256_text

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
    return contract


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
