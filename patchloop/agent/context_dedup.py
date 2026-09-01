"""Offline, reversible context-reference projection for Lean Harness V1.

The production agent is stateless across provider turns, so this module never
elides a value merely because it appeared in an earlier request.  It only
replaces repeated long strings inside one rendered context, leaves the public
task, phase contract, selected memory, recent events, and model-visible tool
result bodies direct, and proves byte-exact restoration of the source context.

This module is intentionally not imported by the runner.  The reference syntax
still needs public-development qualification before it may enter a request.
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

CONTEXT_REFERENCE_SCHEMA = "lean-harness-context-references-v1"
CONTEXT_DEDUP_EVIDENCE_SCHEMA = "lean-harness-context-dedup-evidence-v1"
REFERENCE_SYNTAX = "@context-ref:<id>"
REFERENCE_PREFIX = "@context-ref:"
MIN_REPEATED_VALUE_BYTES = 64

_REFERENCE_ID = re.compile(r"^r[0-9]{4}$")
_REFERENCE_VALUE = re.compile(r"^@context-ref:(r[0-9]{4})$")
_PROTECTED_TOP_LEVEL_COMPONENTS = (
    "public_task",
    "public_review_contract",
    "phase_contract",
    "recent_events",
    "selected_memory",
    "rules",
    "rejected_mutation_retry",
    "coverage_rejection_feedback",
    "probe_ledger",
)


class ContextReferenceEvidence(BaseModel):
    """Auditable identity for one exact-string reference group."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    reference_id: str = Field(pattern=r"^r[0-9]{4}$")
    anchor_pointer: str = Field(pattern=r"^/(?:[^/~]|~[01])(?:.*)$")
    value_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    value_utf8_bytes: int = Field(ge=MIN_REPEATED_VALUE_BYTES)
    occurrence_count: int = Field(ge=2)
    replacement_count: int = Field(ge=1)
    replacement_pointers: tuple[str, ...]
    anchor_protected: bool

    @model_validator(mode="after")
    def validate_reference(self) -> Self:
        if self.replacement_count != len(self.replacement_pointers):
            raise ValueError("context reference replacement count differs")
        if len(set(self.replacement_pointers)) != len(self.replacement_pointers):
            raise ValueError("context reference replacement pointers repeat")
        if self.anchor_pointer in self.replacement_pointers:
            raise ValueError("context reference replaces its own anchor")
        if self.occurrence_count < self.replacement_count + 1:
            raise ValueError("context reference lacks a retained occurrence")
        return self


class LeanContextDedupEvidence(BaseModel):
    """Closed evidence for a single-request reversible projection."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-context-dedup-evidence-v1"]
    status: Literal["offline-reversible-runtime-closed"]
    source_context_schema_version: str = Field(pattern=r"^context-build-evidence-v[0-9]+$")
    scope: Literal["single-stateless-request"]
    reference_schema_version: Literal["lean-harness-context-references-v1"]
    reference_syntax: Literal["@context-ref:<id>"]
    minimum_repeated_value_bytes: Literal[64]
    protected_top_level_components: tuple[str, ...]
    source_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_context_characters: int = Field(ge=1)
    source_context_bytes: int = Field(ge=1)
    projected_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_context_characters: int = Field(ge=1)
    projected_context_bytes: int = Field(ge=1)
    bytes_saved: int = Field(ge=0)
    source_request_content_bytes: int = Field(ge=1)
    projected_request_content_bytes: int = Field(ge=1)
    request_content_bytes_saved: int = Field(ge=0)
    candidate_group_count: int = Field(ge=0)
    references: tuple[ContextReferenceEvidence, ...]
    direct_component_hashes: dict[str, str]
    direct_components_preserved: Literal[True]
    exact_source_roundtrip: Literal[True]
    cross_request_elision_authorized: Literal[False]
    memory_deduplication_authorized: Literal[False]
    runner_activation_authorized: Literal[False]
    provider_calls_authorized: Literal[False]
    provider_transport_calls: Literal[0]
    state_mutation_authorized: Literal[False]
    request_persistence_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        if self.protected_top_level_components != (_PROTECTED_TOP_LEVEL_COMPONENTS):
            raise ValueError("context dedup protected components differ")
        if self.bytes_saved != (self.source_context_bytes - self.projected_context_bytes):
            raise ValueError("context dedup byte savings differ")
        if self.request_content_bytes_saved != (
            self.source_request_content_bytes - self.projected_request_content_bytes
        ):
            raise ValueError("context dedup request-content savings differ")
        if len({item.reference_id for item in self.references}) != len(self.references):
            raise ValueError("context dedup reference ids repeat")
        if self.candidate_group_count < len(self.references):
            raise ValueError("context dedup candidate count is too small")
        if self.references:
            if self.bytes_saved <= 0 or self.request_content_bytes_saved <= 0:
                raise ValueError("context references must reduce context and request-content bytes")
        elif (
            self.bytes_saved != 0
            or self.request_content_bytes_saved != 0
            or self.source_context_hash != self.projected_context_hash
            or self.source_context_characters != self.projected_context_characters
        ):
            raise ValueError("empty context projection must preserve source")
        if not self.direct_component_hashes or any(
            not re.fullmatch(r"sha256:[0-9a-f]{64}", digest)
            for digest in self.direct_component_hashes.values()
        ):
            raise ValueError("context direct-component hashes are invalid")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("context dedup evidence content hash differs")
        return self


@dataclass(frozen=True)
class DeduplicatedContext:
    """Projected model context plus non-authorizing offline evidence."""

    rendered: str
    content_hash: str
    evidence: LeanContextDedupEvidence


@dataclass(frozen=True)
class _ReferenceCandidate:
    value: str
    anchor_path: tuple[str, ...]
    replacement_paths: tuple[tuple[str, ...], ...]
    occurrence_count: int
    anchor_protected: bool


def _render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def _request_content_bytes(rendered: str) -> int:
    """Measure the exact JSON-string bytes embedded in a request payload."""

    return len(canonical_json(rendered).encode("utf-8"))


def _escape_pointer_component(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _unescape_pointer_component(value: str) -> str:
    return value.replace("~1", "/").replace("~0", "~")


def _pointer(path: tuple[str, ...]) -> str:
    return "/" + "/".join(_escape_pointer_component(item) for item in path)


def _resolve_pointer(root: Any, pointer: str) -> Any:
    if not pointer.startswith("/"):
        raise ValueError("context reference pointer must be absolute")
    current = root
    for encoded in pointer[1:].split("/"):
        component = _unescape_pointer_component(encoded)
        if isinstance(current, list):
            if not component.isdigit():
                raise ValueError("context reference list pointer is invalid")
            index = int(component)
            if index >= len(current):
                raise ValueError("context reference list pointer is out of range")
            current = current[index]
        elif isinstance(current, dict):
            if component not in current:
                raise ValueError("context reference object pointer is missing")
            current = current[component]
        else:
            raise ValueError("context reference pointer crosses a scalar")
    return current


def _set_path(root: Any, path: tuple[str, ...], value: Any) -> None:
    current = root
    for component in path[:-1]:
        current = current[int(component)] if isinstance(current, list) else current[component]
    final = path[-1]
    if isinstance(current, list):
        current[int(final)] = value
    else:
        current[final] = value


def _is_protected_path(path: tuple[str, ...]) -> bool:
    if not path:
        return True
    if path[0] in _PROTECTED_TOP_LEVEL_COMPONENTS:
        return True
    return bool(
        len(path) >= 5
        and path[0] == "review_evidence"
        and path[1] == "pinned_results"
        and path[2].isdigit()
        and path[3:5] == ("payload", "tool_result")
    )


def _walk_strings(
    value: Any,
    *,
    path: tuple[str, ...] = (),
) -> list[tuple[str, tuple[str, ...]]]:
    found: list[tuple[str, tuple[str, ...]]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            found.extend(_walk_strings(item, path=(*path, str(key))))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_walk_strings(item, path=(*path, str(index))))
    elif isinstance(value, str):
        found.append((value, path))
    return found


def _reference_candidates(
    payload: dict[str, Any],
) -> tuple[_ReferenceCandidate, ...]:
    occurrences: dict[str, list[tuple[str, ...]]] = {}
    for value, path in _walk_strings(payload):
        if _REFERENCE_VALUE.fullmatch(value):
            raise ValueError("source context contains the reserved reference syntax")
        if len(value.encode("utf-8")) >= MIN_REPEATED_VALUE_BYTES:
            occurrences.setdefault(value, []).append(path)

    candidates: list[_ReferenceCandidate] = []
    for value, paths in occurrences.items():
        if len(paths) < 2:
            continue
        protected = [path for path in paths if _is_protected_path(path)]
        anchor = protected[0] if protected else paths[0]
        replacements = tuple(
            path for path in paths if path != anchor and not _is_protected_path(path)
        )
        if replacements:
            candidates.append(
                _ReferenceCandidate(
                    value=value,
                    anchor_path=anchor,
                    replacement_paths=replacements,
                    occurrence_count=len(paths),
                    anchor_protected=bool(protected),
                )
            )
    return tuple(candidates)


def _apply_candidates(
    source: dict[str, Any],
    candidates: tuple[_ReferenceCandidate, ...],
) -> tuple[dict[str, Any], tuple[ContextReferenceEvidence, ...]]:
    projected = copy.deepcopy(source)
    reference_map: dict[str, str] = {}
    evidence: list[ContextReferenceEvidence] = []
    for index, candidate in enumerate(candidates, start=1):
        reference_id = f"r{index:04d}"
        reference_value = f"{REFERENCE_PREFIX}{reference_id}"
        for path in candidate.replacement_paths:
            _set_path(projected, path, reference_value)
        anchor_pointer = _pointer(candidate.anchor_path)
        reference_map[reference_id] = anchor_pointer
        evidence.append(
            ContextReferenceEvidence(
                reference_id=reference_id,
                anchor_pointer=anchor_pointer,
                value_sha256=sha256_text(candidate.value),
                value_utf8_bytes=len(candidate.value.encode("utf-8")),
                occurrence_count=candidate.occurrence_count,
                replacement_count=len(candidate.replacement_paths),
                replacement_pointers=tuple(_pointer(path) for path in candidate.replacement_paths),
                anchor_protected=candidate.anchor_protected,
            )
        )
    contract: dict[str, Any] = {
        "schema_version": CONTEXT_REFERENCE_SCHEMA,
        "syntax": REFERENCE_SYNTAX,
        **reference_map,
    }
    return {"_context_refs": contract, **projected}, tuple(evidence)


def _dedup_payload(
    source: dict[str, Any],
) -> tuple[str, tuple[ContextReferenceEvidence, ...], int]:
    candidates = _reference_candidates(source)
    if not candidates:
        return _render(source), (), 0

    empty_contract = {
        "_context_refs": {
            "schema_version": CONTEXT_REFERENCE_SCHEMA,
            "syntax": REFERENCE_SYNTAX,
        },
        **copy.deepcopy(source),
    }
    empty_bytes = len(_render(empty_contract).encode("utf-8"))
    empty_request_bytes = _request_content_bytes(_render(empty_contract))
    admitted: list[_ReferenceCandidate] = []
    for candidate in candidates:
        single, _ = _apply_candidates(source, (candidate,))
        rendered_single = _render(single)
        if (
            len(rendered_single.encode("utf-8")) < empty_bytes
            and _request_content_bytes(rendered_single) < empty_request_bytes
        ):
            admitted.append(candidate)
    if not admitted:
        return _render(source), (), len(candidates)

    projected, evidence = _apply_candidates(source, tuple(admitted))
    rendered = _render(projected)
    rendered_source = _render(source)
    if len(rendered.encode("utf-8")) >= len(
        rendered_source.encode("utf-8")
    ) or _request_content_bytes(rendered) >= _request_content_bytes(rendered_source):
        return rendered_source, (), len(candidates)
    return rendered, evidence, len(candidates)


def _direct_component_hashes(payload: dict[str, Any]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for key in _PROTECTED_TOP_LEVEL_COMPONENTS:
        if key in payload:
            hashes[_pointer((key,))] = sha256_json(payload[key])
    review = payload.get("review_evidence")
    if isinstance(review, dict):
        pinned = review.get("pinned_results")
        if isinstance(pinned, list):
            for index, item in enumerate(pinned):
                if not isinstance(item, dict):
                    continue
                nested = item.get("payload")
                if isinstance(nested, dict) and "tool_result" in nested:
                    path = (
                        "review_evidence",
                        "pinned_results",
                        str(index),
                        "payload",
                        "tool_result",
                    )
                    hashes[_pointer(path)] = sha256_json(nested["tool_result"])
    return hashes


def restore_lean_context_references(rendered: str) -> str:
    """Expand a projected context back to the production pretty JSON bytes."""

    if type(rendered) is not str:
        raise TypeError("projected context must be an exact string")
    try:
        payload = json.loads(rendered)
    except json.JSONDecodeError as exc:
        raise ValueError("projected context is not valid JSON") from exc
    if type(payload) is not dict:
        raise ValueError("projected context must be a JSON object")
    contract = payload.pop("_context_refs", None)
    if contract is None:
        return _render(payload)
    if type(contract) is not dict:
        raise ValueError("context reference contract must be an object")
    if (
        contract.get("schema_version") != CONTEXT_REFERENCE_SCHEMA
        or contract.get("syntax") != REFERENCE_SYNTAX
    ):
        raise ValueError("context reference contract identity differs")
    references = {
        key: value for key, value in contract.items() if key not in {"schema_version", "syntax"}
    }
    if not references or any(
        not _REFERENCE_ID.fullmatch(key) or type(pointer) is not str
        for key, pointer in references.items()
    ):
        raise ValueError("context reference map is invalid")
    used = {key: 0 for key in references}
    for value, path in _walk_strings(payload):
        match = _REFERENCE_VALUE.fullmatch(value)
        if match is None:
            continue
        reference_id = match.group(1)
        pointer = references.get(reference_id)
        if pointer is None:
            raise ValueError("context reference id is not declared")
        anchor = _resolve_pointer(payload, pointer)
        if type(anchor) is not str or _REFERENCE_VALUE.fullmatch(anchor):
            raise ValueError("context reference anchor is not a direct string")
        _set_path(payload, path, anchor)
        used[reference_id] += 1
    if any(count == 0 for count in used.values()):
        raise ValueError("context reference contract contains an unused entry")
    return _render(payload)


def _hashed_evidence(body: dict[str, Any]) -> LeanContextDedupEvidence:
    return LeanContextDedupEvidence.model_validate({**body, "content_hash": sha256_json(body)})


def validate_lean_context_dedup_projection(
    projected: DeduplicatedContext,
) -> None:
    """Recompute the deterministic projection and all source bindings."""

    if type(projected) is not DeduplicatedContext:
        raise TypeError("context projection must be an exact DeduplicatedContext")
    evidence = projected.evidence
    if type(evidence) is not LeanContextDedupEvidence:
        raise TypeError("context projection evidence type differs")
    if sha256_text(projected.rendered) != projected.content_hash:
        raise ValueError("projected context hash differs")
    if (
        projected.content_hash != evidence.projected_context_hash
        or len(projected.rendered) != evidence.projected_context_characters
        or len(projected.rendered.encode("utf-8")) != evidence.projected_context_bytes
        or _request_content_bytes(projected.rendered) != evidence.projected_request_content_bytes
    ):
        raise ValueError("projected context metrics differ")

    restored = restore_lean_context_references(projected.rendered)
    if (
        sha256_text(restored) != evidence.source_context_hash
        or len(restored) != evidence.source_context_characters
        or len(restored.encode("utf-8")) != evidence.source_context_bytes
        or _request_content_bytes(restored) != evidence.source_request_content_bytes
    ):
        raise ValueError("context projection does not restore its source")
    source_payload = json.loads(restored)
    recomputed, references, candidate_count = _dedup_payload(source_payload)
    if recomputed != projected.rendered:
        raise ValueError("context projection differs from deterministic policy")
    if references != evidence.references:
        raise ValueError("context projection reference evidence differs")
    if candidate_count != evidence.candidate_group_count:
        raise ValueError("context projection candidate count differs")
    if _direct_component_hashes(source_payload) != (evidence.direct_component_hashes):
        raise ValueError("context projection direct-component binding differs")


def project_lean_context_dedup(
    built_context: BuiltContext,
) -> DeduplicatedContext:
    """Build a condition-neutral, no-call, reversible single-request view."""

    if type(built_context) is not BuiltContext:
        raise TypeError("context dedup requires an exact BuiltContext")
    if sha256_text(built_context.rendered) != built_context.content_hash:
        raise ValueError("built context hash differs")
    schema_version = built_context.evidence.get("schema_version")
    if type(schema_version) is not str or not re.fullmatch(
        r"context-build-evidence-v[0-9]+", schema_version
    ):
        raise ValueError("context dedup requires production context evidence")
    if built_context.evidence.get("rendered_characters") != len(
        built_context.rendered
    ) or built_context.evidence.get("rendered_bytes") != len(
        built_context.rendered.encode("utf-8")
    ):
        raise ValueError("built context evidence metrics differ")
    try:
        source = json.loads(built_context.rendered)
    except json.JSONDecodeError as exc:
        raise ValueError("built context is not valid JSON") from exc
    if type(source) is not dict:
        raise ValueError("built context must be a JSON object")
    if "_context_refs" in source:
        raise ValueError("built context already uses the reserved reference key")
    if _render(source) != built_context.rendered:
        raise ValueError("built context bytes differ from the production renderer")

    rendered, references, candidate_count = _dedup_payload(source)
    body: dict[str, Any] = {
        "schema_version": CONTEXT_DEDUP_EVIDENCE_SCHEMA,
        "status": "offline-reversible-runtime-closed",
        "source_context_schema_version": schema_version,
        "scope": "single-stateless-request",
        "reference_schema_version": CONTEXT_REFERENCE_SCHEMA,
        "reference_syntax": REFERENCE_SYNTAX,
        "minimum_repeated_value_bytes": MIN_REPEATED_VALUE_BYTES,
        "protected_top_level_components": (_PROTECTED_TOP_LEVEL_COMPONENTS),
        "source_context_hash": built_context.content_hash,
        "source_context_characters": len(built_context.rendered),
        "source_context_bytes": len(built_context.rendered.encode("utf-8")),
        "projected_context_hash": sha256_text(rendered),
        "projected_context_characters": len(rendered),
        "projected_context_bytes": len(rendered.encode("utf-8")),
        "bytes_saved": len(built_context.rendered.encode("utf-8")) - len(rendered.encode("utf-8")),
        "source_request_content_bytes": _request_content_bytes(built_context.rendered),
        "projected_request_content_bytes": _request_content_bytes(rendered),
        "request_content_bytes_saved": _request_content_bytes(built_context.rendered)
        - _request_content_bytes(rendered),
        "candidate_group_count": candidate_count,
        "references": tuple(item.model_dump(mode="python") for item in references),
        "direct_component_hashes": _direct_component_hashes(source),
        "direct_components_preserved": True,
        "exact_source_roundtrip": True,
        "cross_request_elision_authorized": False,
        "memory_deduplication_authorized": False,
        "runner_activation_authorized": False,
        "provider_calls_authorized": False,
        "provider_transport_calls": 0,
        "state_mutation_authorized": False,
        "request_persistence_authorized": False,
    }
    result = DeduplicatedContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence=_hashed_evidence(body),
    )
    validate_lean_context_dedup_projection(result)
    return result
