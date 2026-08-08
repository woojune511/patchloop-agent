"""D-100 append-only semantic-group decisions and non-indexing entry previews.

The production D-099 proposal is immutable.  This module records explicit human
decisions in a separate hash-chained JSONL journal and can project approved
groups into MemoryEntry-shaped templates.  It deliberately does not import or
call the legacy per-failure review, embedding, index-build, or freeze paths.
"""

from __future__ import annotations

import json
import os
import re
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from patchloop.contracts import (
    D099ReviewProposal,
    D099SemanticGroup,
    D100DecisionJournalDescriptor,
    D100EntryPreview,
    D100EntryPreviewBody,
    D100GroupDecisionRecord,
    D100MemoryEntryTemplate,
    D100PreviewAuthority,
    D100PreviewProvenance,
    D100ProjectedEntry,
    D100SourceAuthority,
    D100SourceGate,
    D100SourceGateBody,
    D100SourceGroupBinding,
    D100SourceMechanism,
    FailurePattern,
)
from patchloop.errors import ContractError
from patchloop.memory.d099_review import (
    DEFAULT_PROPOSAL_PATH,
    EXPECTED_PROPOSAL_BYTES,
    EXPECTED_PROPOSAL_FILE_SHA,
    EXPECTED_SEMANTIC_BODY_HASH,
    validate_d099_review_proposal,
)
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_text, utc_now

DECISION_SCHEMA_VERSION = "memory-group-review-decision-d100-v1"
JOURNAL_SCHEMA_VERSION = "memory-group-review-journal-d100-v1"
PREVIEW_SCHEMA_VERSION = "memory-entry-preview-d100-v1"
SOURCE_GATE_SCHEMA_VERSION = "memory-group-review-projector-source-gate-d100-v1"
MECHANISM_STATUS_SCHEMA_VERSION = "memory-group-review-mechanism-status-d100-v1"
SOURCE_GATE_VALIDATION_RESULT_SCHEMA_VERSION = (
    "memory-group-review-source-gate-validation-result-d100-v1"
)
SOURCE_GATE_RECORDED_AT = "2026-08-05T13:05:00Z"
DEFAULT_SOURCE_GATE_PATH = Path(
    "reports/memory-development/d100-group-review-projector-source-gate.json"
)
SOURCE_IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d100_group_admission.py"),
    Path("patchloop/contracts.py"),
    Path("patchloop/cli.py"),
    Path("tests/test_d100_group_admission.py"),
)

_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_PROCESS_GUARD = threading.RLock()
_PROCESS_LOCKS: set[Path] = set()
_LEAK_PATTERNS = (
    re.compile(r"(?i)diff --git\s"),
    re.compile(r"@@(?:\s|$)"),
    re.compile(r"(?i)(?:\+\+\+|---)\s+[ab]/"),
    re.compile(r"```"),
    re.compile(r"(?i)\breference\.patch\b"),
    re.compile(r"(?i)\bprivate\.ya?ml\b"),
    re.compile(r"(?i)\.patchloop-hidden(?:[/\\]|$)"),
    re.compile(r"(?i)(?:^|[/\\])hidden(?:[/\\]|_tests?(?:[/\\]|\.))"),
    re.compile(r"(?i)\bOPENAI_API_KEY\s*[:=]"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._-]{12,}\b"),
    re.compile(r"(?i)\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"(?i)\bC:\\Users\\"),
    re.compile(r"(?m)^\s*(?:async\s+)?def\s+[A-Za-z_]\w*\s*\("),
    re.compile(r"(?m)^\s*class\s+[A-Za-z_]\w*(?:\([^)]*\))?\s*:"),
)


class D100GroupAdmissionError(ContractError):
    """Stable fail-closed error for the D-100 mechanism boundary."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D100GroupAdmissionError(message)


def _normalized_text(value: str, *, field: str, maximum: int) -> str:
    normalized = value.strip() if isinstance(value, str) else ""
    _require(0 < len(normalized) <= maximum, f"D-100 {field} is invalid")
    if any(pattern.search(normalized) for pattern in _LEAK_PATTERNS):
        # Never echo text that may contain private evidence or a credential.
        raise D100GroupAdmissionError(f"D-100 {field} leak scan failed")
    return normalized


def _parsed_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise D100GroupAdmissionError("D-100 decision timestamp is invalid") from exc
    _require(parsed.tzinfo is not None, "D-100 decision timestamp must be timezone-aware")
    return parsed


def _proposal_binding(proposal: D099ReviewProposal, content: bytes) -> dict[str, Any]:
    return {
        "schema_version": proposal.schema_version,
        "proposal_id": proposal.proposal_id,
        "semantic_body_hash": proposal.semantic_body_hash,
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _load_exact_proposal(
    proposal_path: str | Path,
    *,
    repository: str | Path | None = None,
) -> tuple[D099ReviewProposal, dict[str, Any]]:
    repo_root = Path(repository) if repository is not None else repository_root()
    selected = Path(proposal_path)
    if not selected.is_absolute():
        selected = repo_root / selected
    try:
        content = selected.read_bytes()
        proposal = D099ReviewProposal.model_validate_json(content)
    except (OSError, ValidationError) as exc:
        raise D100GroupAdmissionError("D-100 source proposal is invalid") from exc
    if EXPECTED_PROPOSAL_BYTES is not None:
        _require(
            len(content) == EXPECTED_PROPOSAL_BYTES,
            "D-100 source proposal byte count drifted",
        )
    if EXPECTED_PROPOSAL_FILE_SHA is not None:
        _require(
            sha256_bytes(content) == EXPECTED_PROPOSAL_FILE_SHA,
            "D-100 source proposal file hash drifted",
        )
    if EXPECTED_SEMANTIC_BODY_HASH is not None:
        _require(
            proposal.semantic_body_hash == EXPECTED_SEMANTIC_BODY_HASH,
            "D-100 source proposal semantic body drifted",
        )
    validate_d099_review_proposal(selected, repository=repo_root)
    try:
        confirmed_content = selected.read_bytes()
    except OSError as exc:
        raise D100GroupAdmissionError("D-100 source proposal became unavailable") from exc
    _require(
        confirmed_content == content,
        "D-100 source proposal changed during validation",
    )
    return proposal, _proposal_binding(proposal, content)


def _groups_by_id(proposal: D099ReviewProposal) -> dict[str, D099SemanticGroup]:
    return {group.semantic_group_id: group for group in proposal.semantic_body.groups}


def _rule_projection(group: D099SemanticGroup) -> dict[str, Any] | None:
    if group.proposed_rule is None:
        return None
    payload = group.proposed_rule.model_dump(mode="json")
    payload.pop("admission_decision", None)
    return payload


def _rule_hash(group: D099SemanticGroup) -> str | None:
    projection = _rule_projection(group)
    return sha256_text(canonical_json(projection)) if projection is not None else None


def _action_input(
    *,
    action_id: str,
    proposal_binding: dict[str, Any],
    group: D099SemanticGroup,
    decision: str,
    expected_tail: str | None,
    reviewer_kind: str,
    reviewer: str,
    rationale: str,
) -> dict[str, Any]:
    return {
        "schema_version": "memory-group-review-action-d100-v1",
        "action_id": action_id,
        "proposal": proposal_binding,
        "semantic_group_id": group.semantic_group_id,
        "semantic_group_fingerprint": group.semantic_fingerprint,
        "group_disposition": group.disposition,
        "decision": decision,
        "expected_tail": expected_tail,
        "reviewer_kind": reviewer_kind,
        "reviewer": reviewer,
        "rationale": rationale,
        "proposed_rule_hash": _rule_hash(group) if decision == "approve" else None,
    }


def _decision_identity(record: dict[str, Any]) -> str:
    identity = {
        "action_input_hash": record["action_input_hash"],
        "sequence": record["sequence"],
        "event_kind": record["event_kind"],
        "previous_decision_hash": record["previous_decision_hash"],
        "supersedes_decision_hash": record["supersedes_decision_hash"],
        "recorded_at": record["recorded_at"],
    }
    return f"d100dec_{sha256_text(canonical_json(identity)).removeprefix('sha256:')}"


def _validate_record_sequence(
    records: list[D100GroupDecisionRecord],
    *,
    proposal: D099ReviewProposal,
    binding: dict[str, Any],
) -> dict[str, D100GroupDecisionRecord]:
    groups = _groups_by_id(proposal)
    previous_hash: str | None = None
    previous_time: datetime | None = None
    effective: dict[str, D100GroupDecisionRecord] = {}
    action_hashes: dict[str, str] = {}

    for sequence, record in enumerate(records, start=1):
        _require(record.sequence == sequence, "D-100 journal sequence is not contiguous")
        _require(
            record.proposal.model_dump(mode="json") == binding,
            "D-100 journal proposal binding drifted",
        )
        group = groups.get(record.semantic_group_id)
        _require(group is not None, "D-100 journal contains an unknown semantic group")
        assert group is not None
        _require(
            record.semantic_group_fingerprint == group.semantic_fingerprint
            and record.group_disposition == group.disposition,
            "D-100 journal group binding drifted",
        )
        expected_rule_hash = _rule_hash(group) if record.decision == "approve" else None
        _require(
            record.proposed_rule_hash == expected_rule_hash,
            "D-100 journal proposed rule binding drifted",
        )
        _require(
            record.previous_decision_hash == previous_hash,
            "D-100 journal hash chain is broken",
        )
        prior_for_group = effective.get(group.semantic_group_id)
        expected_supersedes = prior_for_group.decision_hash if prior_for_group else None
        expected_kind = "DecisionCorrected" if prior_for_group else "DecisionRecorded"
        _require(
            record.supersedes_decision_hash == expected_supersedes
            and record.event_kind == expected_kind,
            "D-100 journal correction binding is invalid",
        )
        recorded_time = _parsed_time(record.recorded_at)
        if previous_time is not None:
            _require(
                recorded_time >= previous_time,
                "D-100 journal timestamps are not monotonic",
            )
        previous_time = recorded_time
        action_input = _action_input(
            action_id=record.action_id,
            proposal_binding=binding,
            group=group,
            decision=record.decision,
            expected_tail=record.previous_decision_hash,
            reviewer_kind=record.reviewer_kind,
            reviewer=record.reviewer,
            rationale=record.rationale,
        )
        expected_action_hash = sha256_text(canonical_json(action_input))
        _require(
            record.action_input_hash == expected_action_hash,
            "D-100 journal action input hash drifted",
        )
        _require(
            record.action_id not in action_hashes,
            "D-100 journal action IDs must be unique",
        )
        action_hashes[record.action_id] = expected_action_hash
        raw = record.model_dump(mode="json")
        recorded_decision_hash = raw.pop("decision_hash")
        _require(
            record.decision_id == _decision_identity(raw),
            "D-100 journal decision identity drifted",
        )
        _require(
            sha256_text(canonical_json(raw)) == recorded_decision_hash,
            "D-100 journal decision hash drifted",
        )
        _normalized_text(record.reviewer, field="reviewer", maximum=200)
        _normalized_text(record.rationale, field="rationale", maximum=2_000)
        effective[group.semantic_group_id] = record
        previous_hash = record.decision_hash

    return effective


def _read_journal(
    journal_path: str | Path,
    *,
    proposal: D099ReviewProposal,
    binding: dict[str, Any],
    allow_missing: bool = False,
) -> tuple[bytes, list[D100GroupDecisionRecord], dict[str, D100GroupDecisionRecord]]:
    path = Path(journal_path)
    if not path.exists():
        if allow_missing:
            return b"", [], {}
        raise D100GroupAdmissionError("D-100 decision journal is unavailable")
    try:
        content = path.read_bytes()
        text = content.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise D100GroupAdmissionError("D-100 decision journal is invalid") from exc
    _require(content, "D-100 decision journal is empty")
    _require(content.endswith(b"\n"), "D-100 decision journal has a truncated tail")
    lines = text.splitlines()
    _require(all(line.strip() for line in lines), "D-100 decision journal has a blank row")
    records: list[D100GroupDecisionRecord] = []
    for line in lines:
        try:
            records.append(D100GroupDecisionRecord.model_validate_json(line))
        except ValidationError as exc:
            raise D100GroupAdmissionError("D-100 decision journal schema is invalid") from exc
    canonical_content = (
        "".join(
            canonical_json(record.model_dump(mode="json")) + "\n" for record in records
        ).encode("utf-8")
    )
    _require(
        content == canonical_content,
        "D-100 decision journal is not canonical JSONL",
    )
    effective = _validate_record_sequence(records, proposal=proposal, binding=binding)
    return content, records, effective


def _journal_descriptor(
    content: bytes,
    records: list[D100GroupDecisionRecord],
    effective: dict[str, D100GroupDecisionRecord],
) -> dict[str, Any]:
    return {
        "schema_version": JOURNAL_SCHEMA_VERSION,
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
        "record_count": len(records),
        "correction_count": sum(record.event_kind == "DecisionCorrected" for record in records),
        "decided_group_count": len(effective),
        "head_decision_hash": records[-1].decision_hash,
    }


def _validate_external_anchor(
    descriptor: D100DecisionJournalDescriptor,
    *,
    expected_head: str | None,
    expected_record_count: int | None,
) -> bool:
    _require(
        (expected_head is None) == (expected_record_count is None),
        "D-100 external journal anchor requires both head and record count",
    )
    if expected_head is None:
        return False
    _require(
        _SHA256.fullmatch(expected_head) is not None,
        "D-100 expected journal head is invalid",
    )
    assert expected_record_count is not None
    _require(expected_record_count >= 1, "D-100 expected journal record count is invalid")
    _require(
        descriptor.head_decision_hash == expected_head
        and descriptor.record_count == expected_record_count,
        "D-100 external journal anchor does not match",
    )
    return True


def _lock_stream(stream: Any) -> None:
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        return
    import fcntl

    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_stream(stream: Any) -> None:
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


@contextmanager
def _journal_lock(journal_path: Path) -> Iterator[None]:
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = journal_path.with_name(f".{journal_path.name}.lock").resolve()
    stream = None
    with _PROCESS_GUARD:
        if lock_path in _PROCESS_LOCKS:
            raise D100GroupAdmissionError("D-100 decision journal already has a writer")
        stream = lock_path.open("a+b", buffering=0)
        try:
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b"\0")
            stream.seek(0)
            _lock_stream(stream)
        except OSError as exc:
            stream.close()
            raise D100GroupAdmissionError("D-100 decision journal already has a writer") from exc
        _PROCESS_LOCKS.add(lock_path)
    try:
        yield
    finally:
        with _PROCESS_GUARD:
            try:
                if stream is not None:
                    stream.seek(0)
                    _unlock_stream(stream)
            finally:
                if stream is not None:
                    stream.close()
                _PROCESS_LOCKS.discard(lock_path)


def validate_d100_decision_journal(
    proposal_path: str | Path,
    journal_path: str | Path,
    *,
    repository: str | Path | None = None,
    expected_head: str | None = None,
    expected_record_count: int | None = None,
) -> dict[str, Any]:
    """Validate the complete append-only chain without writing any state."""

    proposal, binding = _load_exact_proposal(proposal_path, repository=repository)
    journal = Path(journal_path)
    content, records, effective = _read_journal(
        journal,
        proposal=proposal,
        binding=binding,
    )
    descriptor = D100DecisionJournalDescriptor.model_validate(
        _journal_descriptor(content, records, effective)
    )
    external_anchor_validated = _validate_external_anchor(
        descriptor,
        expected_head=expected_head,
        expected_record_count=expected_record_count,
    )
    all_groups = [group.semantic_group_id for group in proposal.semantic_body.groups]
    return {
        "ok": True,
        "schema_version": descriptor.schema_version,
        "proposal_id": proposal.proposal_id,
        "record_count": descriptor.record_count,
        "correction_count": descriptor.correction_count,
        "decided_group_count": descriptor.decided_group_count,
        "complete_group_decisions": set(effective) == set(all_groups),
        "head_decision_hash": descriptor.head_decision_hash,
        "external_head_anchor_validated": external_anchor_validated,
        "effective_decisions": [
            {
                "semantic_group_id": group_id,
                "decision": effective[group_id].decision,
                "decision_hash": effective[group_id].decision_hash,
            }
            for group_id in all_groups
            if group_id in effective
        ],
        "leak_scan": "pass",
        "admission_seal_created": False,
        "memory_index_built": False,
    }


def record_d100_group_decision(
    proposal_path: str | Path,
    journal_path: str | Path,
    *,
    semantic_group_id: str,
    decision: str,
    reviewer_kind: str,
    reviewer: str,
    rationale: str,
    action_id: str,
    expected_tail: str | None,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Append one CAS-bound self-attested decision, or return an idempotent retry."""

    _require(
        decision in {"approve", "reject", "continue_hold"},
        "D-100 decision is invalid",
    )
    _require(
        reviewer_kind in {"human", "maintainer_assisted", "synthetic"},
        "D-100 reviewer kind is invalid",
    )
    normalized_reviewer = _normalized_text(reviewer, field="reviewer", maximum=200)
    normalized_rationale = _normalized_text(rationale, field="rationale", maximum=2_000)
    _require(
        re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", action_id) is not None,
        "D-100 action ID is invalid",
    )
    if expected_tail is not None:
        _require(
            _SHA256.fullmatch(expected_tail) is not None,
            "D-100 expected journal tail is invalid",
        )
    proposal, binding = _load_exact_proposal(proposal_path, repository=repository)
    groups = _groups_by_id(proposal)
    group = groups.get(semantic_group_id)
    _require(group is not None, "D-100 semantic group is unknown")
    assert group is not None
    if decision == "approve":
        _require(
            group.disposition == "candidate" and group.proposed_rule is not None,
            "D-100 hold groups cannot be approved",
        )
    action = _action_input(
        action_id=action_id,
        proposal_binding=binding,
        group=group,
        decision=decision,
        expected_tail=expected_tail,
        reviewer_kind=reviewer_kind,
        reviewer=normalized_reviewer,
        rationale=normalized_rationale,
    )
    action_input_hash = sha256_text(canonical_json(action))
    journal = Path(journal_path).resolve()
    proposal_selected = Path(proposal_path)
    if not proposal_selected.is_absolute():
        repo_root = Path(repository) if repository is not None else repository_root()
        proposal_selected = (repo_root / proposal_selected).resolve()
    _require(journal != proposal_selected, "D-100 journal cannot overwrite the proposal")

    with _journal_lock(journal):
        _, records, effective = _read_journal(
            journal,
            proposal=proposal,
            binding=binding,
            allow_missing=True,
        )
        existing = next((record for record in records if record.action_id == action_id), None)
        if existing is not None:
            _require(
                existing.action_input_hash == action_input_hash,
                "D-100 action ID was reused with different input",
            )
            return {
                **existing.model_dump(mode="json"),
                "appended": False,
                "idempotent_retry": True,
                "journal_record_count": len(records),
            }
        actual_tail = records[-1].decision_hash if records else None
        _require(
            actual_tail == expected_tail,
            "D-100 expected journal tail does not match",
        )
        prior_for_group = effective.get(group.semantic_group_id)
        record: dict[str, Any] = {
            "schema_version": DECISION_SCHEMA_VERSION,
            "decision_id": "",
            "sequence": len(records) + 1,
            "event_kind": "DecisionCorrected" if prior_for_group else "DecisionRecorded",
            "action_id": action_id,
            "action_input_hash": action_input_hash,
            "proposal": binding,
            "semantic_group_id": group.semantic_group_id,
            "semantic_group_fingerprint": group.semantic_fingerprint,
            "group_disposition": group.disposition,
            "decision": decision,
            "reviewer_kind": reviewer_kind,
            "reviewer": normalized_reviewer,
            "rationale": normalized_rationale,
            "proposed_rule_hash": _rule_hash(group) if decision == "approve" else None,
            "previous_decision_hash": actual_tail,
            "supersedes_decision_hash": (
                prior_for_group.decision_hash if prior_for_group is not None else None
            ),
            "recorded_at": utc_now().isoformat(),
        }
        record["decision_id"] = _decision_identity(record)
        record["decision_hash"] = sha256_text(canonical_json(record))
        validated = D100GroupDecisionRecord.model_validate(record)
        _validate_record_sequence(
            [*records, validated],
            proposal=proposal,
            binding=binding,
        )
        encoded = canonical_json(validated.model_dump(mode="json")) + "\n"
        with journal.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        _, confirmed, _ = _read_journal(journal, proposal=proposal, binding=binding)
        _require(
            confirmed[-1].decision_hash == validated.decision_hash,
            "D-100 appended decision was not durably observed",
        )
        return {
            **validated.model_dump(mode="json"),
            "appended": True,
            "idempotent_retry": False,
            "journal_record_count": len(confirmed),
        }


def _memory_template(
    proposal: D099ReviewProposal,
    group: D099SemanticGroup,
    decision: D100GroupDecisionRecord,
) -> D100ProjectedEntry:
    rule = _rule_projection(group)
    _require(rule is not None, "D-100 approved group has no proposed rule")
    assert rule is not None
    rule_hash = sha256_text(canonical_json(rule))
    stable_identity = {
        "proposal_semantic_body_hash": proposal.semantic_body_hash,
        "semantic_group_id": group.semantic_group_id,
        "semantic_group_fingerprint": group.semantic_fingerprint,
        "proposed_rule_hash": rule_hash,
    }
    proposed_memory_id = (
        "memgrp_" + sha256_text(canonical_json(stable_identity)).removeprefix("sha256:")[:32]
    )
    template = D100MemoryEntryTemplate(
        target_schema="memory-entry-v1",
        proposed_memory_id=proposed_memory_id,
        failure_pattern=FailurePattern(
            failure_class=rule["failure_class"],
            phase=rule["phase"],
            description=rule["description"],
        ),
        preconditions=rule["preconditions"],
        diagnostic_evidence=rule["diagnostic_evidence"],
        recommended_actions=rule["recommended_actions"],
        do_not_apply_when=rule["do_not_apply_when"],
        applicable_languages=rule["applicable_languages"],
        source_run_ids=[member.run_id for member in group.members],
        validation_count=0,
        confidence=rule["confidence"],
    )
    provenance = D100PreviewProvenance(
        semantic_group_id=group.semantic_group_id,
        semantic_group_fingerprint=group.semantic_fingerprint,
        decision_hash=decision.decision_hash,
        source_failure_ids=[member.failure_record_id for member in group.members],
        evidence_ref_ids=group.evidence_ref_ids,
        dedup_confidence=group.dedup_confidence,
    )
    template_payload = template.model_dump(mode="json")
    return D100ProjectedEntry(
        template=template,
        provenance=provenance,
        template_hash=sha256_text(canonical_json(template_payload)),
    )


def project_d100_memory_entry_preview(
    proposal_path: str | Path,
    journal_path: str | Path,
    *,
    repository: str | Path | None = None,
    expected_head: str | None = None,
    expected_record_count: int | None = None,
) -> dict[str, Any]:
    """Project complete decisions into templates without building an index."""

    proposal, binding = _load_exact_proposal(proposal_path, repository=repository)
    journal = Path(journal_path)
    content, records, effective = _read_journal(
        journal,
        proposal=proposal,
        binding=binding,
    )
    groups = proposal.semantic_body.groups
    group_ids = [group.semantic_group_id for group in groups]
    _require(
        set(effective) == set(group_ids),
        "D-100 preview requires an effective decision for every semantic group",
    )
    approved = [
        group for group in groups if effective[group.semantic_group_id].decision == "approve"
    ]
    entries = [
        _memory_template(proposal, group, effective[group.semantic_group_id]) for group in approved
    ]
    source_runs = [run_id for entry in entries for run_id in entry.template.source_run_ids]
    source_failures = [
        failure_id for entry in entries for failure_id in entry.provenance.source_failure_ids
    ]
    _require(
        len(source_runs) == len(set(source_runs))
        and len(source_failures) == len(set(source_failures)),
        "D-100 preview contains duplicate source provenance",
    )
    descriptor = D100DecisionJournalDescriptor.model_validate(
        _journal_descriptor(content, records, effective)
    )
    external_anchor_validated = _validate_external_anchor(
        descriptor,
        expected_head=expected_head,
        expected_record_count=expected_record_count,
    )
    approved_ids = [group.semantic_group_id for group in approved]
    rejected_ids = [
        group.semantic_group_id
        for group in groups
        if effective[group.semantic_group_id].decision == "reject"
    ]
    hold_ids = [
        group.semantic_group_id
        for group in groups
        if effective[group.semantic_group_id].decision == "continue_hold"
    ]
    body = D100EntryPreviewBody(
        milestone="D-100",
        evidence_kind="group-aware-memory-entry-preview",
        proposal=binding,
        journal=descriptor,
        final_decision_hashes={
            group_id: effective[group_id].decision_hash for group_id in group_ids
        },
        approved_group_ids=approved_ids,
        rejected_group_ids=rejected_ids,
        continued_hold_group_ids=hold_ids,
        entries=entries,
        leak_scan_passed=True,
        authority=D100PreviewAuthority(
            projection_only=True,
            complete_group_decisions_validated=True,
            external_head_anchor_validated=external_anchor_validated,
            admission_seal_created=False,
            admitted_memory_rule_count=0,
            memory_admission_unlocked=False,
            memory_index_build_authorized=False,
            memory_index_built=False,
            memory_index_frozen=False,
            core_campaign_unlocked=False,
            analysis_ready=False,
            provider_calls_made=0,
            evaluator_calls_made=0,
            added_model_cost_usd=0,
        ),
    )
    body_payload = body.model_dump(mode="json")
    if any(pattern.search(canonical_json(body_payload)) for pattern in _LEAK_PATTERNS):
        raise D100GroupAdmissionError("D-100 preview leak scan failed")
    body_hash = sha256_text(canonical_json(body_payload))
    preview = D100EntryPreview(
        schema_version=PREVIEW_SCHEMA_VERSION,
        preview_id=f"d100preview_{body_hash.removeprefix('sha256:')}",
        semantic_body_hash=body_hash,
        semantic_body=body,
    )
    return preview.model_dump(mode="json")


def d100_mechanism_status(
    proposal_path: str | Path = DEFAULT_PROPOSAL_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Report the implemented mechanism without fabricating production decisions."""

    proposal, binding = _load_exact_proposal(proposal_path, repository=repository)
    groups = proposal.semantic_body.groups
    return {
        "schema_version": MECHANISM_STATUS_SCHEMA_VERSION,
        "milestone": "D-100",
        "proposal": binding,
        "semantic_group_count": len(groups),
        "candidate_group_count": sum(group.disposition == "candidate" for group in groups),
        "hold_group_count": sum(group.disposition == "hold" for group in groups),
        "decision_journal_contract_implemented": True,
        "group_aware_preview_implemented": True,
        "production_human_decision_records": 0,
        "group_review_completed": False,
        "admitted_memory_rule_count": 0,
        "preview_entry_count": 0,
        "memory_admission_unlocked": False,
        "memory_index_build_authorized": False,
        "memory_index_built": False,
        "memory_index_frozen": False,
        "historical_memory_artifacts_modified": False,
        "core_campaign_unlocked": False,
        "analysis_ready": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "added_model_cost_usd": 0,
        "next_gate": "explicit-human-group-decisions-and-portable-admission-seal",
    }


def _source_descriptor(path: Path, *, repository: Path) -> dict[str, Any]:
    selected = repository / path
    try:
        content = selected.read_bytes()
    except OSError as exc:
        raise D100GroupAdmissionError("D-100 implementation source is unavailable") from exc
    return {
        "path": path.as_posix(),
        "bytes": len(content),
        "sha256": sha256_bytes(content),
    }


def build_d100_source_gate(
    *,
    repository: str | Path | None = None,
    proposal_path: str | Path = DEFAULT_PROPOSAL_PATH,
) -> dict[str, Any]:
    """Build the deterministic mechanism-only source gate."""

    repo_root = Path(repository) if repository is not None else repository_root()
    proposal, binding = _load_exact_proposal(proposal_path, repository=repo_root)
    body = D100SourceGateBody(
        milestone="D-100",
        evidence_kind="group-review-projector-offline-source-gate",
        recorded_at=SOURCE_GATE_RECORDED_AT,
        proposal=binding,
        group_bindings=[
            D100SourceGroupBinding(
                semantic_group_id=group.semantic_group_id,
                semantic_group_fingerprint=group.semantic_fingerprint,
                disposition=group.disposition,
                proposed_rule_hash=_rule_hash(group),
            )
            for group in proposal.semantic_body.groups
        ],
        implementation_files=[
            _source_descriptor(path, repository=repo_root) for path in SOURCE_IMPLEMENTATION_PATHS
        ],
        commands=[
            "patchloop memory d100-status",
            "patchloop memory validate-d100-source-gate",
            "patchloop memory record-d100-decision",
            "patchloop memory validate-d100-decisions",
            "patchloop memory preview-d100-entries",
        ],
        mechanism=D100SourceMechanism(
            decision_schema=DECISION_SCHEMA_VERSION,
            journal_schema=JOURNAL_SCHEMA_VERSION,
            preview_schema=PREVIEW_SCHEMA_VERSION,
            target_entry_schema="memory-entry-v1",
            semantic_group_count=5,
            tail_cas_required=True,
            action_idempotency_required=True,
            correction_binds_effective_group_head=True,
            append_flush_and_fsync=True,
            canonical_rows_required=True,
            snapshot_consistency_required=True,
            malformed_or_hash_inconsistent_chain_fails_closed=True,
            external_head_anchor_supported=True,
            external_head_anchor_required_for_suffix_rewrite_detection=True,
            reviewer_provenance_self_attested=True,
            one_approved_group_per_template=True,
            preview_has_no_index_version_or_embedding=True,
            legacy_failure_builder_connected=False,
        ),
        authority=D100SourceAuthority(
            mechanism_source_gate_only=True,
            production_human_decision_records=0,
            group_review_completed=False,
            admission_seal_created=False,
            admitted_memory_rule_count=0,
            preview_entry_count=0,
            memory_admission_unlocked=False,
            memory_index_build_authorized=False,
            memory_index_built=False,
            memory_index_frozen=False,
            historical_memory_artifacts_modified=False,
            core_campaign_unlocked=False,
            analysis_ready=False,
            provider_calls_made=0,
            evaluator_calls_made=0,
            added_model_cost_usd=0,
        ),
        next_gate="explicit-human-group-decisions-and-portable-admission-seal",
    )
    body_payload = body.model_dump(mode="json")
    body_hash = sha256_text(canonical_json(body_payload))
    gate = D100SourceGate(
        schema_version=SOURCE_GATE_SCHEMA_VERSION,
        gate_id=f"d100_{body_hash.removeprefix('sha256:')}",
        semantic_body_hash=body_hash,
        semantic_body=body,
    )
    return gate.model_dump(mode="json")


def validate_d100_source_gate(
    source_gate_path: str | Path = DEFAULT_SOURCE_GATE_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Validate the portable D-100 source gate against the current implementation."""

    repo_root = Path(repository) if repository is not None else repository_root()
    selected = Path(source_gate_path)
    if not selected.is_absolute():
        selected = repo_root / selected
    try:
        content = selected.read_bytes()
        gate = D100SourceGate.model_validate_json(content)
    except (OSError, ValidationError) as exc:
        raise D100GroupAdmissionError("D-100 source gate is invalid") from exc
    body_payload = gate.semantic_body.model_dump(mode="json")
    body_hash = sha256_text(canonical_json(body_payload))
    _require(body_hash == gate.semantic_body_hash, "D-100 source gate body hash drifted")
    _require(
        gate.gate_id == f"d100_{body_hash.removeprefix('sha256:')}",
        "D-100 source gate identity drifted",
    )
    expected = build_d100_source_gate(repository=repo_root)
    expected_content = encode_d100_source_gate(expected)
    _require(
        content == expected_content,
        "D-100 source gate does not match the implementation",
    )
    return {
        **d100_mechanism_status(repository=repo_root),
        "schema_version": SOURCE_GATE_VALIDATION_RESULT_SCHEMA_VERSION,
        "gate_id": gate.gate_id,
        "semantic_body_hash": gate.semantic_body_hash,
        "source_gate_bytes": len(content),
        "source_gate_file_sha256": sha256_bytes(content),
        "source_gate_validation": "pass",
    }


def encode_d100_source_gate(payload: dict[str, Any]) -> bytes:
    """Encode the source gate in its one accepted checked-in representation."""

    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
