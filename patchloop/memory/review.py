"""Read-only validation for leak-safe, deduplicated memory review proposals."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from patchloop.contracts import (
    DatasetRole,
    FailureRecord,
    MemoryReviewProposal,
)
from patchloop.dataset import require_frozen_dataset
from patchloop.errors import ContractError, RecoveryError
from patchloop.memory.store import _require_memory_source
from patchloop.runtime import repository_root, runtime_root
from patchloop.state import StateStore
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_text

_PROHIBITED_REVIEW_PATTERNS = (
    re.compile(r"(?i)diff --git\s"),
    re.compile(r"@@(?:\s|$)"),
    re.compile(r"(?i)(?:\+\+\+|---)\s+[ab]/"),
    re.compile(r"```"),
    re.compile(r"(?i)\breference\.patch\b"),
    re.compile(r"(?i)\bprivate\.ya?ml\b"),
    re.compile(r"(?i)\.patchloop-hidden(?:[/\\]|$)"),
    re.compile(r"(?i)(?:^|[/\\])hidden(?:[/\\]|_tests?(?:[/\\]|\.))"),
    re.compile(r"(?i)\bOPENAI_API_KEY\s*[:=]"),
    re.compile(r"(?i)\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"(?m)^\s*(?:async\s+)?def\s+[A-Za-z_]\w*\s*\("),
    re.compile(r"(?m)^\s*class\s+[A-Za-z_]\w*(?:\([^)]*\))?\s*:"),
)


def _mapping(value: Any, *, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{name} must be a JSON object")
    return value


def _string_list(value: Any, *, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ContractError(f"{name} must be a list of strings")
    return value


def _load_json_object(path: Path, *, name: str) -> dict[str, Any]:
    try:
        return _mapping(json.loads(path.read_text(encoding="utf-8")), name=name)
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"unable to load {name}") from exc


def _review_text(proposal: MemoryReviewProposal) -> str:
    parts = [proposal.proposal_id]
    for source in proposal.sources:
        parts.extend((source.semantic_group_id, source.assessment))
    for group in proposal.groups:
        rule = group.rule
        parts.extend(
            (
                group.semantic_group_id,
                group.merge_rationale,
                rule.failure_pattern.failure_class,
                rule.failure_pattern.phase.value,
                rule.failure_pattern.description,
                *rule.preconditions,
                *rule.diagnostic_evidence,
                *rule.recommended_actions,
                *rule.do_not_apply_when,
            )
        )
    parts.extend(item.reason for item in proposal.excluded_runs)
    return "\n".join(parts)


def _require_leak_safe_text(proposal: MemoryReviewProposal) -> None:
    text = _review_text(proposal)
    if any(pattern.search(text) for pattern in _PROHIBITED_REVIEW_PATTERNS):
        # Never return the matched marker or matched text. The artifact is safe to
        # inspect only after its author removes the leak/code-shaped content.
        raise ContractError("memory review proposal leak scan failed")


def _campaign_rows(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = report.get("runs")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ContractError("campaign report runs must be a list of objects")
    by_run: dict[str, dict[str, Any]] = {}
    for row in rows:
        run_id = row.get("run_id")
        if not isinstance(run_id, str) or run_id in by_run:
            raise ContractError("campaign report run identities are invalid")
        by_run[run_id] = row
    return by_run


def _portable_artifacts(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = report.get("portable_artifacts")
    if not isinstance(artifacts, list) or not all(
        isinstance(artifact, dict) for artifact in artifacts
    ):
        raise ContractError("campaign portable_artifacts must be a list of objects")
    by_run: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        if artifact.get("role") != "submitted-task-failure-diff":
            continue
        run_id = artifact.get("run_id")
        if not isinstance(run_id, str) or run_id in by_run:
            raise ContractError("campaign submitted patch identities are invalid")
        by_run[run_id] = artifact
    return by_run


def _validate_group_deduplication(proposal: MemoryReviewProposal) -> None:
    sources_by_group: dict[str, list] = {}
    for source in proposal.sources:
        sources_by_group.setdefault(source.semantic_group_id, []).append(source)

    groups = {group.semantic_group_id: group for group in proposal.groups}
    if set(groups) != set(sources_by_group):
        raise ContractError("semantic groups must exactly cover proposal sources")

    seen_failures: set[str] = set()
    seen_runs: set[str] = set()
    for group_id, sources in sources_by_group.items():
        group = groups[group_id]
        failure_ids = {source.failure_id for source in sources}
        run_ids = {source.run_id for source in sources}
        if set(group.member_failure_ids) != failure_ids:
            raise ContractError("semantic group failure membership mismatch")
        if set(group.member_run_ids) != run_ids:
            raise ContractError("semantic group run membership mismatch")
        if any(source.disposition != group.disposition for source in sources):
            raise ContractError("semantic group disposition mismatch")
        if seen_failures & failure_ids or seen_runs & run_ids:
            raise ContractError("a review source may belong to only one semantic group")
        seen_failures.update(failure_ids)
        seen_runs.update(run_ids)


def validate_review_proposal(
    proposal_path: str | Path,
    *,
    dataset_manifest_path: str | Path | None = None,
    root: str | Path | None = None,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Validate a proposal without approving failures or constructing an index."""

    source_root = Path(root) if root is not None else runtime_root()
    repo_root = Path(repository) if repository is not None else repository_root()
    selected_path = Path(proposal_path).resolve()
    try:
        proposal = MemoryReviewProposal.model_validate_json(
            selected_path.read_text(encoding="utf-8")
        )
    except (OSError, ValidationError) as exc:
        raise ContractError("memory review proposal validation failed") from exc

    canonical_payload = proposal.model_dump(mode="json")
    recorded_content_hash = canonical_payload.pop("content_hash")
    if sha256_text(canonical_json(canonical_payload)) != recorded_content_hash:
        raise ContractError("memory review proposal content hash mismatch")
    if not proposal.evidence_boundary.generic_outcome_only:
        raise ContractError("review proposal must use generic outcome evidence only")
    _require_leak_safe_text(proposal)
    _validate_group_deduplication(proposal)

    campaign_path = ensure_within(repo_root, proposal.campaign.report_path)
    if not campaign_path.is_file():
        raise ContractError("memory review campaign report is unavailable")
    if sha256_bytes(campaign_path.read_bytes()) != proposal.campaign.report_sha256:
        raise ContractError("memory review campaign report hash mismatch")
    report = _load_json_object(campaign_path, name="campaign report")
    campaign = _mapping(report.get("campaign"), name="campaign report campaign")
    if (
        report.get("experiment_id") != proposal.campaign.experiment_id
        or report.get("execution_hash") != proposal.campaign.execution_hash
        or campaign.get("suite_hash") != proposal.campaign.suite_hash
    ):
        raise ContractError("memory review campaign identity mismatch")

    _, dataset_hash, _ = require_frozen_dataset(dataset_manifest_path)
    if dataset_hash != proposal.campaign.dataset_manifest_hash:
        raise ContractError("memory review dataset manifest hash mismatch")

    review_admission = _mapping(
        report.get("review_admission"), name="campaign review_admission"
    )
    expected_candidates = set(
        _string_list(
            review_admission.get("task_failure_candidates"),
            name="campaign task_failure_candidates",
        )
    )
    expected_exclusions = set(
        _string_list(
            review_admission.get("budget_confounded_candidates"),
            name="campaign budget_confounded_candidates",
        )
    )
    proposed_candidates = {source.run_id for source in proposal.sources}
    proposed_exclusions = {item.run_id for item in proposal.excluded_runs}
    if proposed_candidates != expected_candidates:
        raise ContractError("review sources must exactly cover task failure candidates")
    if proposed_exclusions != expected_exclusions:
        raise ContractError("excluded runs must exactly cover budget-confounded candidates")

    rows = _campaign_rows(report)
    artifacts = _portable_artifacts(report)
    state = StateStore(source_root / "state.sqlite3")
    for source in proposal.sources:
        failure_path = (
            source_root / "failures" / "dev-train" / f"{source.failure_id}.json"
        )
        if not failure_path.is_file():
            raise ContractError("memory review failure record is unavailable")
        try:
            record = FailureRecord.model_validate_json(
                failure_path.read_text(encoding="utf-8")
            )
        except (OSError, ValidationError) as exc:
            raise ContractError("memory review failure record is invalid") from exc
        if record.run_id != source.run_id:
            raise ContractError("memory review failure/run binding mismatch")
        try:
            manifest = state.get_manifest(source.run_id)
        except RecoveryError as exc:
            raise ContractError("memory review source manifest is unavailable") from exc
        if (
            manifest.task_id != source.task_id
            or manifest.public_spec_hash != source.public_spec_hash
        ):
            raise ContractError("memory review public task binding mismatch")

        (
            dataset_role,
            source_dataset_hash,
            qualification_hash,
            source_evidence_hash,
        ) = _require_memory_source(
            record,
            dataset_manifest_path=dataset_manifest_path,
            root=source_root,
        )
        if dataset_role != DatasetRole.MEMORY_DEVELOPMENT.value:
            raise ContractError("memory review source has an ineligible dataset role")
        if (
            source_dataset_hash != proposal.campaign.dataset_manifest_hash
            or qualification_hash != source.qualification_hash
            or source_evidence_hash != source.source_evidence_hash
        ):
            raise ContractError("memory review source provenance mismatch")

        row = rows.get(source.run_id)
        if (
            row is None
            or row.get("task_id") != source.task_id
            or row.get("outcome_kind") != "task_failure"
            or row.get("evaluation_reached") is not True
            or row.get("qualified") is not True
            or row.get("qualification_hash") != source.qualification_hash
            or row.get("source_evidence_hash") != source.source_evidence_hash
        ):
            raise ContractError("memory review campaign source row mismatch")

        artifact = artifacts.get(source.run_id)
        if (
            artifact is None
            or artifact.get("path") != source.submitted_patch_path
            or artifact.get("sha256") != source.submitted_patch_sha256
        ):
            raise ContractError("memory review portable patch binding mismatch")
        patch_path = ensure_within(repo_root, source.submitted_patch_path)
        if (
            not patch_path.is_file()
            or sha256_bytes(patch_path.read_bytes()) != source.submitted_patch_sha256
        ):
            raise ContractError("memory review portable patch hash mismatch")

        available_sequences = {
            event.sequence for event in state.list_events(source.run_id)
        }
        if not set(source.evidence_event_sequences) <= available_sequences:
            raise ContractError("memory review evidence sequence is unavailable")

    for excluded in proposal.excluded_runs:
        row = rows.get(excluded.run_id)
        if (
            row is None
            or row.get("outcome_kind") != "agent_failure"
            or row.get("evaluation_reached") is not False
            or row.get("terminal_reason") != excluded.reason
        ):
            raise ContractError("memory review excluded run provenance mismatch")

    return {
        "schema_version": proposal.schema_version,
        "proposal_id": proposal.proposal_id,
        "content_hash": proposal.content_hash,
        "producer_kind": proposal.producer.kind,
        "producer_method": proposal.producer.method,
        "experiment_id": proposal.campaign.experiment_id,
        "execution_hash": proposal.campaign.execution_hash,
        "dataset_manifest_hash": proposal.campaign.dataset_manifest_hash,
        "source_count": len(proposal.sources),
        "semantic_group_count": len(proposal.groups),
        "candidate_group_count": sum(
            group.disposition == "candidate" for group in proposal.groups
        ),
        "hold_group_count": sum(group.disposition == "hold" for group in proposal.groups),
        "excluded_run_count": len(proposal.excluded_runs),
        "leak_scan": "pass",
        "human_review_status": proposal.human_review_status,
        "review_history_written": False,
        "memory_index_built": False,
    }
