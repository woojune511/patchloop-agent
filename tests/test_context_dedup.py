from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.agent.context import BuiltContext
from patchloop.agent.context_dedup import (
    DeduplicatedContext,
    LeanContextDedupEvidence,
    project_lean_context_dedup,
    restore_lean_context_references,
    validate_lean_context_dedup_projection,
)
from patchloop.util import sha256_json, sha256_text

REPOSITORY = Path(__file__).resolve().parents[1]
DIFF_HASH = "sha256:" + ("a" * 64)


def _render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def _built_context(*, memory: str | None = None) -> BuiltContext:
    payload = {
        "public_task": {
            "task_id": "public-development-context-dedup",
            "issue": {"description": "Preserve the exact public behavior while fixing the parser."},
        },
        "public_review_contract": {
            "requirements": [
                {
                    "source": "issue.description",
                    "source_excerpt": (
                        "Preserve the exact public behavior while fixing the parser."
                    ),
                }
            ]
        },
        "phase": "REVIEW",
        "checkpoint": {"worktree_diff_hash": DIFF_HASH},
        "phase_contract": {
            "current_phase": "REVIEW",
            "current_diff_hash": DIFF_HASH,
            "allowed_next_actions": ["review_task"],
        },
        "review_evidence": {
            "worktree_diff_hash": DIFF_HASH,
            "pinned_results": [
                {
                    "sequence": 7,
                    "payload": {
                        "worktree_diff_hash": DIFF_HASH,
                        "artifact_id": "art_" + ("b" * 64),
                        "result_artifact": {
                            "content_hash": DIFF_HASH,
                        },
                        "tool_result": {
                            "check_id": "public-check",
                            "passed": True,
                            "worktree_diff_hash": DIFF_HASH,
                        },
                    },
                },
                {
                    "sequence": 8,
                    "payload": {
                        "worktree_diff_hash": DIFF_HASH,
                        "result_artifact": {
                            "content_hash": DIFF_HASH,
                        },
                        "tool_result": {
                            "patch": "diff --git a/parser.py b/parser.py\n",
                            "worktree_diff_hash": DIFF_HASH,
                        },
                    },
                },
            ],
        },
        "recent_events": [
            {
                "sequence": 6,
                "type": "PatchApplied",
                "payload": {"worktree_diff_hash": DIFF_HASH},
            }
        ],
        "execution_signals": {"repeated_calls": []},
        "selected_memory": memory,
        "rules": {
            "private_evaluator_data_unavailable": True,
            "registered_checks_only": True,
        },
        "investigation_ledger": {
            "worktree_diff_hash": DIFF_HASH,
            "tail_policy": {"worktree_diff_hash": DIFF_HASH},
        },
        "probe_ledger": {"authoritative": False, "entries": []},
        "rejected_mutation_retry": None,
    }
    rendered = _render(payload)
    return BuiltContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence={
            "schema_version": "context-build-evidence-v10",
            "rendered_characters": len(rendered),
            "rendered_bytes": len(rendered.encode("utf-8")),
        },
    )


def _rehash_evidence(body: dict[str, Any]) -> LeanContextDedupEvidence:
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return LeanContextDedupEvidence.model_validate(body)


def test_single_request_projection_is_smaller_reversible_and_runtime_closed() -> None:
    source = _built_context()
    projected = project_lean_context_dedup(source)
    payload = json.loads(projected.rendered)

    assert projected.evidence.scope == "single-stateless-request"
    assert projected.evidence.references
    assert projected.evidence.bytes_saved > 0
    assert projected.evidence.request_content_bytes_saved > 0
    assert projected.evidence.projected_context_bytes < (projected.evidence.source_context_bytes)
    assert projected.evidence.projected_request_content_bytes < (
        projected.evidence.source_request_content_bytes
    )
    assert payload["_context_refs"]["schema_version"] == ("lean-harness-context-references-v1")
    assert restore_lean_context_references(projected.rendered) == source.rendered
    assert payload["phase_contract"]["current_diff_hash"] == DIFF_HASH
    assert payload["recent_events"][0]["payload"]["worktree_diff_hash"] == (DIFF_HASH)
    assert (
        payload["review_evidence"]["pinned_results"][0]["payload"]["tool_result"][
            "worktree_diff_hash"
        ]
        == DIFF_HASH
    )
    assert projected.evidence.direct_components_preserved is True
    assert projected.evidence.exact_source_roundtrip is True
    assert projected.evidence.cross_request_elision_authorized is False
    assert projected.evidence.memory_deduplication_authorized is False
    assert projected.evidence.provider_calls_authorized is False
    assert projected.evidence.provider_transport_calls == 0
    assert projected.evidence.runner_activation_authorized is False
    assert projected.evidence.state_mutation_authorized is False
    assert projected.evidence.request_persistence_authorized is False
    validate_lean_context_dedup_projection(projected)


def test_memory_is_direct_and_reference_policy_is_condition_neutral() -> None:
    no_memory = project_lean_context_dedup(_built_context())
    memory_text = "public generalized memory " + ("m" * 200)
    structured = project_lean_context_dedup(_built_context(memory=memory_text))
    no_memory_payload = json.loads(no_memory.rendered)
    structured_payload = json.loads(structured.rendered)

    assert no_memory_payload["_context_refs"] == (structured_payload["_context_refs"])
    assert structured_payload["selected_memory"] == memory_text
    assert "@context-ref:" not in structured_payload["selected_memory"]
    no_memory_payload["selected_memory"] = None
    structured_payload["selected_memory"] = None
    assert no_memory_payload == structured_payload
    assert "condition" not in inspect.signature(project_lean_context_dedup).parameters


def test_projection_is_a_noop_when_no_exact_group_saves_bytes() -> None:
    payload = {
        "public_task": {"description": "x" * 80},
        "phase_contract": {"allowed_next_actions": ["read_file"]},
        "recent_events": [],
        "selected_memory": None,
        "rules": {"registered_checks_only": True},
    }
    rendered = _render(payload)
    source = BuiltContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence={
            "schema_version": "context-build-evidence-v11",
            "rendered_characters": len(rendered),
            "rendered_bytes": len(rendered.encode("utf-8")),
        },
    )

    projected = project_lean_context_dedup(source)

    assert projected.rendered == source.rendered
    assert projected.content_hash == source.content_hash
    assert projected.evidence.references == ()
    assert projected.evidence.bytes_saved == 0
    assert projected.evidence.candidate_group_count == 0


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda source: BuiltContext(
                rendered=source.rendered + " ",
                content_hash=source.content_hash,
                evidence=source.evidence,
            ),
            "hash differs",
        ),
        (
            lambda source: BuiltContext(
                rendered=source.rendered,
                content_hash=source.content_hash,
                evidence={**source.evidence, "rendered_bytes": 1},
            ),
            "metrics differ",
        ),
        (
            lambda source: _source_with_reserved_key(source),
            "reserved reference key",
        ),
        (
            lambda source: _source_with_reserved_value(source),
            "reserved reference syntax",
        ),
    ],
)
def test_source_identity_metrics_and_reserved_syntax_fail_closed(
    mutator,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        project_lean_context_dedup(mutator(_built_context()))


def _source_with_reserved_key(source: BuiltContext) -> BuiltContext:
    payload = json.loads(source.rendered)
    payload["_context_refs"] = {"schema_version": "forged"}
    return _rebuilt(source, payload)


def _source_with_reserved_value(source: BuiltContext) -> BuiltContext:
    payload = json.loads(source.rendered)
    payload["checkpoint"]["forged"] = "@context-ref:r0001"
    return _rebuilt(source, payload)


def _rebuilt(source: BuiltContext, payload: dict[str, Any]) -> BuiltContext:
    rendered = _render(payload)
    return BuiltContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence={
            **source.evidence,
            "rendered_characters": len(rendered),
            "rendered_bytes": len(rendered.encode("utf-8")),
        },
    )


def test_rehashed_anchor_drift_cannot_validate_against_source_identity() -> None:
    projected = project_lean_context_dedup(_built_context())
    payload = json.loads(projected.rendered)
    payload["phase_contract"]["current_diff_hash"] = "sha256:" + ("f" * 64)
    rendered = _render(payload)
    evidence_body = projected.evidence.model_dump(mode="python")
    evidence_body["projected_context_hash"] = sha256_text(rendered)
    evidence_body["projected_context_characters"] = len(rendered)
    evidence_body["projected_context_bytes"] = len(rendered.encode("utf-8"))
    evidence_body["bytes_saved"] = (
        evidence_body["source_context_bytes"] - evidence_body["projected_context_bytes"]
    )
    forged = DeduplicatedContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence=_rehash_evidence(evidence_body),
    )

    with pytest.raises(ValueError, match="restore its source"):
        validate_lean_context_dedup_projection(forged)


def test_rehashed_authority_or_reference_count_drift_is_rejected() -> None:
    projected = project_lean_context_dedup(_built_context())
    authority = projected.evidence.model_dump(mode="python")
    authority["provider_calls_authorized"] = True
    authority["content_hash"] = sha256_json(
        {key: value for key, value in authority.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError):
        LeanContextDedupEvidence.model_validate(authority)

    reference = projected.evidence.model_dump(mode="python")
    reference["references"][0]["replacement_count"] += 1
    reference["content_hash"] = sha256_json(
        {key: value for key, value in reference.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError, match="replacement count differs"):
        LeanContextDedupEvidence.model_validate(reference)


def test_projection_is_not_imported_by_runner_or_request_shadow() -> None:
    runner = (REPOSITORY / "patchloop/agent/runner.py").read_text(encoding="utf-8")
    shadow = (REPOSITORY / "patchloop/agent/shadow_runtime.py").read_text(encoding="utf-8")

    assert "patchloop.agent.context_dedup" not in runner
    assert "project_lean_context_dedup" not in runner
    assert "patchloop.agent.context_dedup" not in shadow
    assert "project_lean_context_dedup" not in shadow
