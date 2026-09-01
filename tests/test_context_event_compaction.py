from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.agent.context import BuiltContext
from patchloop.agent.context_event_compaction import (
    CompactedEventContext,
    LeanContextEventCompactionEvidence,
    LeanContextEventCompactionEvidenceV2,
    project_lean_context_event_descriptors,
    project_lean_context_event_descriptors_v2,
    restore_lean_context_event_descriptors,
    validate_lean_context_event_compaction,
)
from patchloop.contracts import Artifact
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

REPOSITORY = Path(__file__).resolve().parents[1]


def _render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def _artifact(identity: str, content: bytes) -> Artifact:
    return Artifact(
        artifact_id=f"art_{identity}",
        content_hash=sha256_bytes(content),
        media_type="application/json; charset=utf-8",
        size_bytes=len(content),
        path=f"objects/{identity}.json",
        created_at=datetime(2026, 8, 16, tzinfo=UTC),
    )


def _built_context(*, memory: str | None = None) -> BuiltContext:
    input_artifact = _artifact("input", b'{"path":"parser.py"}')
    result_artifact = _artifact(
        "result",
        b'{"path":"parser.py","content":"public source"}',
    )
    payload = {
        "public_task": {
            "task_id": "public-event-compaction",
            "issue": {"description": "Fix the public parser contract."},
        },
        "phase": "REPRODUCE",
        "checkpoint": None,
        "phase_contract": {
            "current_phase": "REPRODUCE",
            "allowed_next_actions": ["read_file"],
        },
        "recent_events": [
            {
                "sequence": 1,
                "type": "ToolCalled",
                "actor": "agent",
                "payload": {
                    "tool": "read_file",
                    "input_hash": sha256_text("read-input"),
                    "artifact_id": input_artifact.artifact_id,
                    "artifact_path": input_artifact.path,
                    "input_artifact": input_artifact.model_dump(mode="json"),
                },
            },
            {
                "sequence": 2,
                "type": "ToolSucceeded",
                "actor": "tool-gateway",
                "payload": {
                    "tool": "read_file",
                    "status": "succeeded",
                    "artifact_id": result_artifact.artifact_id,
                    "artifact_path": result_artifact.path,
                    "result_artifact": result_artifact.model_dump(mode="json"),
                    "tool_result": {
                        "path": "parser.py",
                        "content": "public source",
                        "worktree_diff_hash": sha256_text(""),
                    },
                },
            },
        ],
        "execution_signals": {"repeated_calls": []},
        "selected_memory": memory,
        "rules": {
            "private_evaluator_data_unavailable": True,
            "registered_checks_only": True,
        },
        "investigation_ledger": {"authoritative": False, "entries": []},
    }
    rendered = _render(payload)
    return BuiltContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence={
            "schema_version": "context-build-evidence-v11",
            "rendered_characters": len(rendered),
            "rendered_bytes": len(rendered.encode("utf-8")),
        },
    )


def _production_composite_context() -> BuiltContext:
    edit_input = _artifact("structured-input", b'{"tool":"apply_structured_edit"}')
    generated_patch = _artifact("generated-patch", b"diff --git a/a.py b/a.py\n")
    blocked_input = _artifact("blocked-input", b'{"tool":"run_check"}')
    blocked_result = _artifact("blocked-result", b'{"status":"rejected"}')
    source = _built_context()
    payload = json.loads(source.rendered)
    payload["recent_events"] = [
        {
            "sequence": 227,
            "type": "ToolCalled",
            "actor": "agent",
            "payload": {
                "tool": "apply_structured_edit",
                "input_hash": sha256_text("structured-input"),
                "input_artifact": edit_input.model_dump(mode="json"),
                "patch_artifact": generated_patch.model_dump(mode="json"),
                "artifact_id": generated_patch.artifact_id,
                "artifact_path": generated_patch.path,
            },
        },
        {
            "sequence": 229,
            "type": "ToolSucceeded",
            "actor": "tool-gateway",
            "payload": {
                "tool": "apply_structured_edit",
                "status": "succeeded",
                "result_artifact": None,
                "artifact_id": "art_mutation-result",
                "artifact_path": "objects/mutation-result.json",
            },
        },
        {
            "sequence": 231,
            "type": "ToolAdmissionBlocked",
            "actor": "tool-admission-policy",
            "payload": {
                "tool": "run_check",
                "status": "rejected",
                "input_artifact": blocked_input.model_dump(mode="json"),
                "result_artifact": blocked_result.model_dump(mode="json"),
                "artifact_id": blocked_result.artifact_id,
                "artifact_path": blocked_result.path,
            },
        },
    ]
    return _rebuild(source, payload)


def _rehash_evidence(body: dict[str, Any]) -> LeanContextEventCompactionEvidence:
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return LeanContextEventCompactionEvidence.model_validate(body)


def test_projection_removes_only_nested_descriptors_and_restores_exactly() -> None:
    source = _built_context()
    projected = project_lean_context_event_descriptors(source)
    payload = json.loads(projected.rendered)

    assert projected.evidence.removed_descriptor_count == 2
    assert projected.evidence.context_bytes_saved > 0
    assert projected.evidence.request_content_bytes_saved > 0
    assert "input_artifact" not in payload["recent_events"][0]["payload"]
    assert "result_artifact" not in payload["recent_events"][1]["payload"]
    assert payload["recent_events"][0]["payload"]["artifact_id"] == "art_input"
    assert payload["recent_events"][0]["payload"]["artifact_path"] == ("objects/input.json")
    assert payload["recent_events"][1]["payload"]["tool_result"] == {
        "path": "parser.py",
        "content": "public source",
        "worktree_diff_hash": sha256_text(""),
    }
    assert restore_lean_context_event_descriptors(projected) == source.rendered
    validate_lean_context_event_compaction(projected)


def test_projection_is_condition_neutral_and_memory_stays_direct() -> None:
    no_memory = project_lean_context_event_descriptors(_built_context())
    memory = "public generalized memory " + ("m" * 500)
    structured = project_lean_context_event_descriptors(_built_context(memory=memory))
    no_payload = json.loads(no_memory.rendered)
    structured_payload = json.loads(structured.rendered)

    assert no_memory.evidence.request_content_bytes_saved == (
        structured.evidence.request_content_bytes_saved
    )
    assert structured_payload["selected_memory"] == memory
    no_payload["selected_memory"] = None
    structured_payload["selected_memory"] = None
    assert no_payload == structured_payload
    assert structured.evidence.selected_memory_compaction_authorized is False


def test_no_descriptor_projection_is_an_exact_noop() -> None:
    source = _built_context()
    payload = json.loads(source.rendered)
    payload["recent_events"] = []
    rendered = _render(payload)
    no_events = BuiltContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence={
            **source.evidence,
            "rendered_characters": len(rendered),
            "rendered_bytes": len(rendered.encode("utf-8")),
        },
    )

    projected = project_lean_context_event_descriptors(no_events)

    assert projected.rendered == rendered
    assert projected.evidence.descriptors == ()
    assert projected.evidence.context_bytes_saved == 0
    assert projected.evidence.request_content_bytes_saved == 0


def test_source_descriptor_shape_and_artifact_binding_fail_closed() -> None:
    source = _built_context()
    payload = json.loads(source.rendered)
    descriptor = payload["recent_events"][0]["payload"]["input_artifact"]
    payload["recent_events"][0]["payload"]["input_artifact"] = {
        **descriptor,
        "unexpected": True,
    }
    with pytest.raises(ValueError, match="descriptor shape differs"):
        project_lean_context_event_descriptors(_rebuild(source, payload))

    payload = json.loads(source.rendered)
    payload["recent_events"][0]["payload"]["artifact_path"] = "other.json"
    with pytest.raises(ValueError, match="artifact binding differs"):
        project_lean_context_event_descriptors(_rebuild(source, payload))


def test_v2_preserves_production_role_distinct_inputs_and_compacts_result() -> None:
    source = _production_composite_context()

    with pytest.raises(ValueError, match="artifact binding differs"):
        project_lean_context_event_descriptors(source)

    projected = project_lean_context_event_descriptors_v2(source)
    payload = json.loads(projected.rendered)

    assert isinstance(projected.evidence, LeanContextEventCompactionEvidenceV2)
    assert projected.evidence.preserved_distinct_descriptor_count == 2
    assert [
        (item.event_type, item.tool, item.binding_field)
        for item in projected.evidence.preserved_distinct_descriptors
    ] == [
        ("ToolCalled", "apply_structured_edit", "patch_artifact"),
        ("ToolAdmissionBlocked", "run_check", "result_artifact"),
    ]
    assert projected.evidence.removed_descriptor_count == 1
    assert "input_artifact" in payload["recent_events"][0]["payload"]
    assert "input_artifact" in payload["recent_events"][2]["payload"]
    assert "result_artifact" not in payload["recent_events"][2]["payload"]
    assert restore_lean_context_event_descriptors(projected) == source.rendered
    validate_lean_context_event_compaction(projected)


@pytest.mark.parametrize(
    ("event_index", "binding_field"),
    ((0, "patch_artifact"), (2, "result_artifact")),
)
def test_v2_role_distinct_input_requires_exact_alternate_binding(
    event_index: int,
    binding_field: str,
) -> None:
    source = _production_composite_context()
    payload = json.loads(source.rendered)
    payload["recent_events"][event_index]["payload"][binding_field]["path"] = (
        "objects/forged.json"
    )

    with pytest.raises(ValueError, match="alternate artifact binding differs"):
        project_lean_context_event_descriptors_v2(_rebuild(source, payload))


@pytest.mark.parametrize("event_index", (0, 2))
def test_v2_role_distinct_input_cannot_alias_its_output_role(event_index: int) -> None:
    source = _production_composite_context()
    payload = json.loads(source.rendered)
    event_payload = payload["recent_events"][event_index]["payload"]
    binding_field = "patch_artifact" if event_index == 0 else "result_artifact"
    event_payload["input_artifact"] = event_payload[binding_field]

    with pytest.raises(ValueError, match="not role-distinct"):
        project_lean_context_event_descriptors_v2(_rebuild(source, payload))


def _rebuild(source: BuiltContext, payload: dict[str, Any]) -> BuiltContext:
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


def test_projected_tool_result_or_descriptor_evidence_tamper_is_rejected() -> None:
    projected = project_lean_context_event_descriptors(_built_context())
    payload = json.loads(projected.rendered)
    payload["recent_events"][1]["payload"]["tool_result"]["content"] = "forged"
    rendered = _render(payload)
    forged_context = CompactedEventContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence=projected.evidence,
    )
    with pytest.raises(ValueError, match="projected metrics differ"):
        validate_lean_context_event_compaction(forged_context)

    payload = json.loads(projected.rendered)
    payload["recent_events"][1]["payload"]["tool_result"]["content"] = "forged source"
    rendered = _render(payload)
    evidence_body = projected.evidence.model_dump(mode="python")
    evidence_body["projected_context_hash"] = sha256_text(rendered)
    evidence_body["projected_recent_events_hash"] = sha256_json(payload["recent_events"])
    same_length_forgery = CompactedEventContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence=_rehash_evidence(evidence_body),
    )
    with pytest.raises(ValueError, match="projected event differs"):
        validate_lean_context_event_compaction(same_length_forgery)

    body = projected.evidence.model_dump(mode="python")
    body["descriptors"][0]["descriptor"]["path"] = "forged.json"
    body["descriptors"][0]["descriptor_hash"] = sha256_json(body["descriptors"][0]["descriptor"])
    with pytest.raises(ValidationError, match="differ"):
        LeanContextEventCompactionEvidence.model_validate(body)

    forged_body = projected.evidence.model_dump(mode="python")
    forged_body["descriptors"][0]["descriptor"]["path"] = "forged.json"
    forged_body["descriptors"][0]["descriptor_hash"] = sha256_json(
        forged_body["descriptors"][0]["descriptor"]
    )
    forged_body["removed_descriptor_canonical_bytes"] = sum(
        len(canonical_json(item["descriptor"]).encode("utf-8"))
        for item in forged_body["descriptors"]
    )
    forged_evidence = _rehash_evidence(forged_body)
    with pytest.raises(ValueError, match="does not restore"):
        restore_lean_context_event_descriptors(
            CompactedEventContext(
                rendered=projected.rendered,
                content_hash=projected.content_hash,
                evidence=forged_evidence,
            )
        )


def test_authority_is_closed_and_runner_does_not_import_projection() -> None:
    evidence = project_lean_context_event_descriptors(_built_context()).evidence

    assert evidence.runner_activation_authorized is False
    assert evidence.request_integration_authorized is False
    assert evidence.provider_calls_authorized is False
    assert evidence.provider_transport_calls == 0
    assert evidence.state_mutation_authorized is False
    assert evidence.request_persistence_authorized is False
    runner = (REPOSITORY / "patchloop/agent/runner.py").read_text(encoding="utf-8")
    shadow = (REPOSITORY / "patchloop/agent/shadow_runtime.py").read_text(encoding="utf-8")
    assert "context_event_compaction" not in runner
    assert "project_lean_context_event_descriptors" not in runner
    assert "context_event_compaction" not in shadow
    assert "project_lean_context_event_descriptors" not in shadow
