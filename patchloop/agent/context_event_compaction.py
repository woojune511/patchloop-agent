"""Reversible offline compaction of redundant recent-event descriptors.

Production context hydration keeps a model-visible ``tool_result`` together
with its ``artifact_id`` and ``artifact_path``.  The nested ``input_artifact``
or ``result_artifact`` descriptor repeats that provenance in every request.
This module moves only that nested descriptor into non-model evidence while
leaving the task, memory, phase policy, event semantics, artifact identity and
tool-result body direct.

The projection is runtime-closed.  It is not imported by the runner or request
shadow and grants no provider, persistence or integration authority.
"""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.context import BuiltContext
from patchloop.util import canonical_json, sha256_json, sha256_text

COMPACTION_SCHEMA = "lean-harness-context-event-compaction-v1"
EVIDENCE_SCHEMA = "lean-harness-context-event-compaction-evidence-v1"
COMPACTION_SCHEMA_V2 = "lean-harness-context-event-compaction-v2"
EVIDENCE_SCHEMA_V2 = "lean-harness-context-event-compaction-evidence-v2"
DESCRIPTOR_FIELDS = (
    "artifact_id",
    "content_hash",
    "media_type",
    "size_bytes",
    "path",
    "created_at",
)
COMPACTED_PAYLOAD_FIELDS = ("input_artifact", "result_artifact")


class CompactedArtifactDescriptor(BaseModel):
    """Frozen exact JSON projection of one artifact descriptor."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    artifact_id: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    media_type: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    path: str = Field(min_length=1)
    created_at: str = Field(min_length=1)


class CompactedEventDescriptorEvidence(BaseModel):
    """Restoration coordinates and identity for one removed descriptor."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    event_sequence: int = Field(ge=1)
    event_index: int = Field(ge=0)
    payload_field: Literal["input_artifact", "result_artifact"]
    payload_key_index: int = Field(ge=0)
    descriptor: CompactedArtifactDescriptor
    descriptor_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_event_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_descriptor(self) -> Self:
        if self.descriptor_hash != sha256_json(self.descriptor.model_dump(mode="json")):
            raise ValueError("event descriptor hash differs")
        return self


class PreservedDistinctEventDescriptorEvidence(BaseModel):
    """Typed evidence for a legitimate non-redundant nested descriptor."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    event_sequence: int = Field(ge=1)
    event_index: int = Field(ge=0)
    event_type: Literal["ToolCalled", "ToolAdmissionBlocked"]
    tool: str = Field(min_length=1)
    payload_field: Literal["input_artifact"]
    binding_field: Literal["patch_artifact", "result_artifact"]
    descriptor_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    binding_descriptor_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    top_level_artifact_id: str = Field(min_length=1)
    top_level_artifact_path: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_role(self) -> Self:
        expected = (
            ("apply_structured_edit", "patch_artifact")
            if self.event_type == "ToolCalled"
            else (self.tool, "result_artifact")
        )
        if (self.tool, self.binding_field) != expected:
            raise ValueError("preserved event descriptor role differs")
        return self


class LeanContextEventCompactionEvidence(BaseModel):
    """Closed evidence for a single-request descriptor projection."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-context-event-compaction-evidence-v1"]
    status: Literal["offline-reversible-runtime-closed"]
    source_context_schema_version: str = Field(pattern=r"^context-build-evidence-v[0-9]+$")
    scope: Literal["single-stateless-request"]
    compaction_schema_version: Literal["lean-harness-context-event-compaction-v1"]
    compacted_payload_fields: tuple[str, ...]
    source_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_context_characters: int = Field(ge=1)
    source_context_bytes: int = Field(ge=1)
    source_request_content_bytes: int = Field(ge=1)
    projected_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_context_characters: int = Field(ge=1)
    projected_context_bytes: int = Field(ge=1)
    projected_request_content_bytes: int = Field(ge=1)
    context_bytes_saved: int = Field(ge=0)
    request_content_bytes_saved: int = Field(ge=0)
    removed_descriptor_count: int = Field(ge=0)
    removed_descriptor_canonical_bytes: int = Field(ge=0)
    descriptors: tuple[CompactedEventDescriptorEvidence, ...]
    source_recent_events_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_recent_events_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    direct_component_hashes: dict[str, str]
    direct_components_preserved: Literal[True]
    tool_result_bodies_preserved: Literal[True]
    artifact_id_and_path_preserved: Literal[True]
    exact_source_roundtrip: Literal[True]
    cross_request_elision_authorized: Literal[False]
    selected_memory_compaction_authorized: Literal[False]
    runner_activation_authorized: Literal[False]
    request_integration_authorized: Literal[False]
    provider_calls_authorized: Literal[False]
    provider_transport_calls: Literal[0]
    state_mutation_authorized: Literal[False]
    request_persistence_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        if self.compacted_payload_fields != COMPACTED_PAYLOAD_FIELDS:
            raise ValueError("event compaction payload fields differ")
        if self.context_bytes_saved != (self.source_context_bytes - self.projected_context_bytes):
            raise ValueError("event compaction context savings differ")
        if self.request_content_bytes_saved != (
            self.source_request_content_bytes - self.projected_request_content_bytes
        ):
            raise ValueError("event compaction request savings differ")
        if self.removed_descriptor_count != len(self.descriptors):
            raise ValueError("event compaction descriptor count differs")
        identities = {
            (item.event_sequence, item.event_index, item.payload_field) for item in self.descriptors
        }
        if len(identities) != len(self.descriptors):
            raise ValueError("event compaction descriptor identities repeat")
        expected_descriptor_bytes = sum(
            len(canonical_json(item.descriptor.model_dump(mode="json")).encode("utf-8"))
            for item in self.descriptors
        )
        if self.removed_descriptor_canonical_bytes != expected_descriptor_bytes:
            raise ValueError("event compaction descriptor bytes differ")
        if self.descriptors:
            if self.context_bytes_saved <= 0 or self.request_content_bytes_saved <= 0:
                raise ValueError("event descriptors must reduce exact request bytes")
        elif (
            self.context_bytes_saved != 0
            or self.request_content_bytes_saved != 0
            or self.source_context_hash != self.projected_context_hash
            or self.source_recent_events_hash != self.projected_recent_events_hash
        ):
            raise ValueError("empty event compaction must preserve the source")
        if not self.direct_component_hashes or any(
            not key.startswith("/")
            or not isinstance(value, str)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None
            for key, value in self.direct_component_hashes.items()
        ):
            raise ValueError("event compaction direct-component hashes differ")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("event compaction evidence hash differs")
        return self


class LeanContextEventCompactionEvidenceV2(LeanContextEventCompactionEvidence):
    """Successor evidence preserving typed, non-redundant input descriptors."""

    schema_version: Literal["lean-harness-context-event-compaction-evidence-v2"]
    compaction_schema_version: Literal["lean-harness-context-event-compaction-v2"]
    preserved_distinct_descriptor_count: int = Field(ge=0)
    preserved_distinct_descriptors: tuple[
        PreservedDistinctEventDescriptorEvidence, ...
    ]

    @model_validator(mode="after")
    def validate_preserved_descriptors(self) -> Self:
        if self.preserved_distinct_descriptor_count != len(
            self.preserved_distinct_descriptors
        ):
            raise ValueError("preserved event descriptor count differs")
        identities = {
            (item.event_sequence, item.event_index, item.payload_field)
            for item in self.preserved_distinct_descriptors
        }
        if len(identities) != len(self.preserved_distinct_descriptors):
            raise ValueError("preserved event descriptor identities repeat")
        return self


@dataclass(frozen=True)
class CompactedEventContext:
    """Projected context plus its non-authorizing restoration evidence."""

    rendered: str
    content_hash: str
    evidence: LeanContextEventCompactionEvidence | LeanContextEventCompactionEvidenceV2


def _render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def _request_content_bytes(rendered: str) -> int:
    return len(canonical_json(rendered).encode("utf-8"))


def _direct_component_hashes(payload: dict[str, Any]) -> dict[str, str]:
    return {
        f"/{key}": sha256_json(value) for key, value in payload.items() if key != "recent_events"
    }


def _descriptor(raw: Any) -> CompactedArtifactDescriptor:
    if (
        type(raw) is not dict
        or len(raw) != len(DESCRIPTOR_FIELDS)
        or set(raw) != set(DESCRIPTOR_FIELDS)
    ):
        raise ValueError("recent-event artifact descriptor shape differs")
    return CompactedArtifactDescriptor.model_validate(raw)


def _validate_source(built_context: BuiltContext) -> tuple[dict[str, Any], str]:
    if type(built_context) is not BuiltContext:
        raise TypeError("event compaction requires an exact BuiltContext")
    if sha256_text(built_context.rendered) != built_context.content_hash:
        raise ValueError("event compaction source hash differs")
    schema = built_context.evidence.get("schema_version")
    if type(schema) is not str or not schema.startswith("context-build-evidence-v"):
        raise ValueError("event compaction requires production context evidence")
    if built_context.evidence.get("rendered_characters") != len(
        built_context.rendered
    ) or built_context.evidence.get("rendered_bytes") != len(
        built_context.rendered.encode("utf-8")
    ):
        raise ValueError("event compaction source metrics differ")
    try:
        source = json.loads(built_context.rendered)
    except json.JSONDecodeError as exc:
        raise ValueError("event compaction source is not JSON") from exc
    if type(source) is not dict or _render(source) != built_context.rendered:
        raise ValueError("event compaction source is not production-rendered")
    recent = source.get("recent_events")
    if type(recent) is not list:
        raise ValueError("event compaction requires recent_events")
    return source, schema


def _preserved_input_role(
    *,
    event: dict[str, Any],
    event_index: int,
    sequence: int,
    descriptor: CompactedArtifactDescriptor,
) -> PreservedDistinctEventDescriptorEvidence:
    event_type = event.get("type")
    payload = event["payload"]
    tool = payload.get("tool")
    if type(tool) is not str or not tool:
        raise ValueError("preserved input descriptor tool differs")
    if event_type == "ToolCalled" and tool == "apply_structured_edit":
        binding_field = "patch_artifact"
    elif event_type == "ToolAdmissionBlocked":
        binding_field = "result_artifact"
    else:
        raise ValueError("input descriptor belongs to an unsupported event role")
    binding = _descriptor(payload.get(binding_field))
    if (
        payload.get("artifact_id") != binding.artifact_id
        or payload.get("artifact_path") != binding.path
    ):
        raise ValueError("recent-event alternate artifact binding differs")
    if (
        descriptor.artifact_id == binding.artifact_id
        or descriptor.path == binding.path
    ):
        raise ValueError("preserved input descriptor is not role-distinct")
    return PreservedDistinctEventDescriptorEvidence(
        event_sequence=sequence,
        event_index=event_index,
        event_type=event_type,
        tool=tool,
        payload_field="input_artifact",
        binding_field=binding_field,
        descriptor_hash=sha256_json(descriptor.model_dump(mode="json")),
        binding_descriptor_hash=sha256_json(binding.model_dump(mode="json")),
        top_level_artifact_id=binding.artifact_id,
        top_level_artifact_path=binding.path,
    )


def _project_with_policy(
    built_context: BuiltContext,
    *,
    preserve_distinct_inputs: bool,
) -> CompactedEventContext:
    source, schema = _validate_source(built_context)
    projected = copy.deepcopy(source)
    records: list[CompactedEventDescriptorEvidence] = []
    preserved: list[PreservedDistinctEventDescriptorEvidence] = []
    source_recent = source["recent_events"]
    projected_recent = projected["recent_events"]
    seen_sequences: set[int] = set()
    for event_index, event in enumerate(projected_recent):
        if type(event) is not dict or type(event.get("payload")) is not dict:
            raise ValueError("recent-event projection shape differs")
        sequence = event.get("sequence")
        if type(sequence) is not int or sequence < 1 or sequence in seen_sequences:
            raise ValueError("recent-event sequence identity differs")
        seen_sequences.add(sequence)
        payload = event["payload"]
        pending: list[tuple[str, int, CompactedArtifactDescriptor]] = []
        for payload_field in COMPACTED_PAYLOAD_FIELDS:
            if payload_field not in payload:
                continue
            if payload_field == "input_artifact" and event.get("type") not in (
                {"ToolCalled", "ToolAdmissionBlocked"}
                if preserve_distinct_inputs
                else {"ToolCalled"}
            ):
                raise ValueError("input descriptor belongs to a non-call event")
            result_event_types = {
                "ToolSucceeded",
                "ToolFailed",
                "ToolReplayed",
            }
            if preserve_distinct_inputs:
                result_event_types.add("ToolAdmissionBlocked")
            if (
                payload_field == "result_artifact"
                and event.get("type") not in result_event_types
            ):
                raise ValueError("result descriptor belongs to a non-result event")
            # Mutation results deliberately keep a null result-artifact marker;
            # only a real repeated descriptor is eligible for compaction.
            if payload[payload_field] is None:
                continue
            payload_key_index = list(payload).index(payload_field)
            descriptor = _descriptor(payload[payload_field])
            role_distinct_input = bool(
                preserve_distinct_inputs
                and payload_field == "input_artifact"
                and (
                    event.get("type") == "ToolAdmissionBlocked"
                    or (
                        event.get("type") == "ToolCalled"
                        and payload.get("tool") == "apply_structured_edit"
                        and "patch_artifact" in payload
                    )
                )
            )
            if role_distinct_input:
                preserved.append(
                    _preserved_input_role(
                        event=event,
                        event_index=event_index,
                        sequence=sequence,
                        descriptor=descriptor,
                    )
                )
                continue
            if (
                payload.get("artifact_id") != descriptor.artifact_id
                or payload.get("artifact_path") != descriptor.path
            ):
                if preserve_distinct_inputs and payload_field == "input_artifact":
                    preserved.append(
                        _preserved_input_role(
                            event=event,
                            event_index=event_index,
                            sequence=sequence,
                            descriptor=descriptor,
                        )
                    )
                    continue
                raise ValueError("recent-event artifact binding differs")
            pending.append((payload_field, payload_key_index, descriptor))
        for payload_field, _, _ in pending:
            payload.pop(payload_field)
        projected_event_hash = sha256_json(event)
        for payload_field, payload_key_index, descriptor in pending:
            records.append(
                CompactedEventDescriptorEvidence(
                    event_sequence=sequence,
                    event_index=event_index,
                    payload_field=payload_field,
                    payload_key_index=payload_key_index,
                    descriptor=descriptor,
                    descriptor_hash=sha256_json(descriptor.model_dump(mode="json")),
                    projected_event_hash=projected_event_hash,
                )
            )
    rendered = _render(projected)
    body: dict[str, Any] = {
        "schema_version": EVIDENCE_SCHEMA_V2 if preserve_distinct_inputs else EVIDENCE_SCHEMA,
        "status": "offline-reversible-runtime-closed",
        "source_context_schema_version": schema,
        "scope": "single-stateless-request",
        "compaction_schema_version": (
            COMPACTION_SCHEMA_V2 if preserve_distinct_inputs else COMPACTION_SCHEMA
        ),
        "compacted_payload_fields": COMPACTED_PAYLOAD_FIELDS,
        "source_context_hash": built_context.content_hash,
        "source_context_characters": len(built_context.rendered),
        "source_context_bytes": len(built_context.rendered.encode("utf-8")),
        "source_request_content_bytes": _request_content_bytes(built_context.rendered),
        "projected_context_hash": sha256_text(rendered),
        "projected_context_characters": len(rendered),
        "projected_context_bytes": len(rendered.encode("utf-8")),
        "projected_request_content_bytes": _request_content_bytes(rendered),
        "context_bytes_saved": len(built_context.rendered.encode("utf-8"))
        - len(rendered.encode("utf-8")),
        "request_content_bytes_saved": _request_content_bytes(built_context.rendered)
        - _request_content_bytes(rendered),
        "removed_descriptor_count": len(records),
        "removed_descriptor_canonical_bytes": sum(
            len(canonical_json(item.descriptor.model_dump(mode="json")).encode("utf-8"))
            for item in records
        ),
        "descriptors": tuple(item.model_dump(mode="python") for item in records),
        "source_recent_events_hash": sha256_json(source_recent),
        "projected_recent_events_hash": sha256_json(projected_recent),
        "direct_component_hashes": _direct_component_hashes(source),
        "direct_components_preserved": True,
        "tool_result_bodies_preserved": True,
        "artifact_id_and_path_preserved": True,
        "exact_source_roundtrip": True,
        "cross_request_elision_authorized": False,
        "selected_memory_compaction_authorized": False,
        "runner_activation_authorized": False,
        "request_integration_authorized": False,
        "provider_calls_authorized": False,
        "provider_transport_calls": 0,
        "state_mutation_authorized": False,
        "request_persistence_authorized": False,
    }
    evidence_model: type[
        LeanContextEventCompactionEvidence | LeanContextEventCompactionEvidenceV2
    ] = LeanContextEventCompactionEvidence
    if preserve_distinct_inputs:
        body.update(
            {
                "preserved_distinct_descriptor_count": len(preserved),
                "preserved_distinct_descriptors": tuple(
                    item.model_dump(mode="python") for item in preserved
                ),
            }
        )
        evidence_model = LeanContextEventCompactionEvidenceV2
    evidence = evidence_model.model_validate(
        {**body, "content_hash": sha256_json(body)}
    )
    return CompactedEventContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence=evidence,
    )


def _project_unvalidated(built_context: BuiltContext) -> CompactedEventContext:
    return _project_with_policy(built_context, preserve_distinct_inputs=False)


def _project_v2_unvalidated(built_context: BuiltContext) -> CompactedEventContext:
    return _project_with_policy(built_context, preserve_distinct_inputs=True)


def restore_lean_context_event_descriptors(
    projected: CompactedEventContext,
) -> str:
    """Restore the production-rendered source context byte-for-byte."""

    if type(projected) is not CompactedEventContext:
        raise TypeError("event compaction restoration requires exact evidence")
    evidence = projected.evidence
    if type(evidence) not in {
        LeanContextEventCompactionEvidence,
        LeanContextEventCompactionEvidenceV2,
    }:
        raise TypeError("event compaction evidence type differs")
    if (
        sha256_text(projected.rendered) != projected.content_hash
        or projected.content_hash != evidence.projected_context_hash
        or len(projected.rendered) != evidence.projected_context_characters
        or len(projected.rendered.encode("utf-8")) != evidence.projected_context_bytes
        or _request_content_bytes(projected.rendered) != evidence.projected_request_content_bytes
    ):
        raise ValueError("event compaction projected metrics differ")
    grouped: dict[int, list[CompactedEventDescriptorEvidence]] = {}
    for record in evidence.descriptors:
        grouped.setdefault(record.event_index, []).append(record)

    # Artifact JSON can originate directly from ``model_dump`` (field order)
    # or from the canonical state store (sorted object keys). JSON object order
    # is not semantic, but the production-rendered context is byte-bound. Try
    # both deterministic encodings and accept only the one that restores every
    # recorded source identity exactly.
    descriptor_orders = (DESCRIPTOR_FIELDS, tuple(sorted(DESCRIPTOR_FIELDS)))
    for descriptor_order in dict.fromkeys(descriptor_orders):
        try:
            payload = json.loads(projected.rendered)
        except json.JSONDecodeError as exc:
            raise ValueError("event compaction projection is not JSON") from exc
        if type(payload) is not dict or type(payload.get("recent_events")) is not list:
            raise ValueError("event compaction projection shape differs")
        recent = payload["recent_events"]
        for event_index, records in grouped.items():
            if event_index >= len(recent) or type(recent[event_index]) is not dict:
                raise ValueError("event compaction restoration index differs")
            event = recent[event_index]
            projected_event_hash = sha256_json(event)
            if type(event.get("payload")) is not dict or any(
                event.get("sequence") != record.event_sequence
                or projected_event_hash != record.projected_event_hash
                for record in records
            ):
                raise ValueError("event compaction projected event differs")
            event_payload = event["payload"]
            for record in sorted(records, key=lambda item: item.payload_key_index):
                if record.payload_field in event_payload:
                    raise ValueError("event compaction field already exists")
                items = list(event_payload.items())
                if record.payload_key_index > len(items):
                    raise ValueError("event compaction payload index differs")
                descriptor = record.descriptor.model_dump(mode="json")
                items.insert(
                    record.payload_key_index,
                    (
                        record.payload_field,
                        {key: descriptor[key] for key in descriptor_order},
                    ),
                )
                event_payload = dict(items)
                event["payload"] = event_payload
        restored = _render(payload)
        if (
            sha256_text(restored) == evidence.source_context_hash
            and len(restored) == evidence.source_context_characters
            and len(restored.encode("utf-8")) == evidence.source_context_bytes
            and _request_content_bytes(restored) == evidence.source_request_content_bytes
            and sha256_json(payload["recent_events"]) == evidence.source_recent_events_hash
            and _direct_component_hashes(payload) == evidence.direct_component_hashes
        ):
            return restored
    raise ValueError("event compaction does not restore its source")


def validate_lean_context_event_compaction(
    projected: CompactedEventContext,
) -> None:
    """Recompute the deterministic projection and all source bindings."""

    restored = restore_lean_context_event_descriptors(projected)
    source = BuiltContext(
        rendered=restored,
        content_hash=projected.evidence.source_context_hash,
        evidence={
            "schema_version": projected.evidence.source_context_schema_version,
            "rendered_characters": len(restored),
            "rendered_bytes": len(restored.encode("utf-8")),
        },
    )
    recomputed = (
        _project_v2_unvalidated(source)
        if type(projected.evidence) is LeanContextEventCompactionEvidenceV2
        else _project_unvalidated(source)
    )
    if recomputed != projected:
        raise ValueError("event compaction differs from deterministic policy")


def project_lean_context_event_descriptors(
    built_context: BuiltContext,
) -> CompactedEventContext:
    """Move redundant nested descriptors out of one model request."""

    result = _project_unvalidated(built_context)
    validate_lean_context_event_compaction(result)
    return result


def project_lean_context_event_descriptors_v2(
    built_context: BuiltContext,
) -> CompactedEventContext:
    """Compact only redundant descriptors and preserve typed role-distinct inputs."""

    result = _project_v2_unvalidated(built_context)
    validate_lean_context_event_compaction(result)
    return result
