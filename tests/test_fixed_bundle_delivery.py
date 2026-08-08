from __future__ import annotations

import copy
import json
import shutil
import socket
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from patchloop.agent.context import build_context_with_evidence
from patchloop.agent.model import ModelTurn, OpenAIResponsesAdapter, RequestedTool
from patchloop.agent.runner import AgentRunner
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    Budget,
    EventType,
    MemoryCondition,
    ModelConfig,
    RunEvent,
    RunOutcomeKind,
)
from patchloop.errors import ContractError
from patchloop.memory import fixed_bundle
from patchloop.runtime import build_manifest
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_text, utc_now

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TASK_PATH = Path("tasks/smoke/csv-quoted-newline/public.yaml")

EXPECTED_BUNDLE_SHA256 = "sha256:572667d431aa75e4fe74bfc030a99f64245b77d9afa1c88e5d531129f708accf"
EXPECTED_INDEX_CONTENT_HASH = (
    "sha256:3a99e6c190672d1676bc4d13604de989899de9ddac85d282cc90c4d56f426c56"
)
EXPECTED_ENTRIES = [
    {
        "order": 1,
        "memory_id": "memgrp_649483b80292fea26e4009ebdb72df31",
        "semantic_group_id": "platform-emulation-matrix-gap",
        "render_file_sha256": (
            "sha256:f1cd44ed10d527ff7f5c44dd0be4e6957810530cd055d3329da0d7962d3cec7c"
        ),
    },
    {
        "order": 2,
        "memory_id": "memgrp_b421547d481faabf9be3511217258de5",
        "semantic_group_id": "request-context-propagation-gap",
        "render_file_sha256": (
            "sha256:ab0273b575f76efd4ca9facda9540d87f2ea85e69a333cf87e4d7ac781287c2a"
        ),
    },
    {
        "order": 3,
        "memory_id": "memgrp_5a23f463cba43bf3ba395f67cf976047",
        "semantic_group_id": "exception-origin-state-conflation",
        "render_file_sha256": (
            "sha256:00ceca8ed912a48f36ab26fb50b1d7eb428fe261a83b2bd84e231f0c6e786bf7"
        ),
    },
]
BOUND_ASSET_PATHS = (
    fixed_bundle.D105_GATE_PATH,
    fixed_bundle.D110_INDEX_PATH,
    fixed_bundle.D110_MARKER_PATH,
    fixed_bundle.D110_GATE_PATH,
    *(entry.render_path for entry in fixed_bundle.EXPECTED_ENTRIES),
)


def _copy_bound_assets(destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    for relative in BOUND_ASSET_PATHS:
        source = REPOSITORY_ROOT.joinpath(*Path(relative).parts)
        target = destination.joinpath(*Path(relative).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return destination


def _entry_projection(delivery: fixed_bundle.FixedMemoryDelivery) -> list[dict[str, object]]:
    return [
        {
            "order": entry.order,
            "memory_id": entry.memory_id,
            "semantic_group_id": entry.semantic_group_id,
            "render_file_sha256": entry.render_file_sha256,
        }
        for entry in delivery.evidence.ordered_entries
    ]


def _leaf_differences(left: object, right: object, pointer: str = "") -> set[str]:
    if type(left) is not type(right):
        return {pointer}
    if isinstance(left, dict):
        differences: set[str] = set()
        for key in left.keys() | right.keys():
            child = f"{pointer}/{key}"
            if key not in left or key not in right:
                differences.add(child)
            else:
                differences.update(_leaf_differences(left[key], right[key], child))
        return differences
    if isinstance(left, list):
        if len(left) != len(right):
            return {pointer}
        differences = set()
        for index, (left_item, right_item) in enumerate(zip(left, right, strict=True)):
            differences.update(_leaf_differences(left_item, right_item, f"{pointer}/{index}"))
        return differences
    return set() if left == right else {pointer}


def _forbidden(label: str):
    def fail(*_args, **_kwargs):
        raise AssertionError(f"{label} must not be used by fixed-bundle delivery")

    return fail


def test_a_is_exact_null_delivery_and_performs_zero_asset_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fixed_bundle, "_stable_read", _forbidden("asset read"))

    delivery = fixed_bundle.build_fixed_memory_delivery(
        condition=MemoryCondition.NO_MEMORY,
        repository=tmp_path / "repository-does-not-exist",
    )

    assert delivery.text == ""
    assert delivery.evidence.model_dump(mode="json") == {
        "schema_version": "fixed-memory-delivery-evidence-v1",
        "policy_version": "fixed-d110-bundle-v1",
        "condition": "no_memory",
        "mode": "none",
        "selected_memory_present": False,
        "entry_count": 0,
        "ordered_entries": [],
        "bundle_separator": None,
        "bundle_bytes": 0,
        "bundle_sha256": None,
        "token_budget": 2_000,
        "d105_gate_id": None,
        "d105_gate_file_sha256": None,
        "d105_render_set_sha256": None,
        "index_version": None,
        "index_content_hash": None,
        "index_file_sha256": None,
        "marker_file_sha256": None,
        "d110_gate_id": None,
        "d110_gate_file_sha256": None,
        "query_dependent": False,
        "embedding_or_similarity_used": False,
        "ranking_or_threshold_used": False,
        "truncation_applied": False,
        "legacy_retrieval_called": False,
    }


def test_c_is_the_exact_ordered_three_entry_bundle(tmp_path: Path) -> None:
    repository = _copy_bound_assets(tmp_path / "repository")

    delivery = fixed_bundle.build_fixed_memory_delivery(
        condition=MemoryCondition.STRUCTURED,
        repository=repository,
    )

    expected_text = (
        fixed_bundle.FIXED_BUNDLE_SEPARATOR.join(
            (
                REPOSITORY_ROOT.joinpath(*Path(entry.render_path).parts)
                .read_text(encoding="ascii")
                .removesuffix("\n")
            )
            for entry in fixed_bundle.EXPECTED_ENTRIES
        )
        + "\n"
    )
    assert delivery.text == expected_text
    assert len(delivery.text.encode("ascii")) == 3_528
    assert sha256_bytes(delivery.text.encode("ascii")) == EXPECTED_BUNDLE_SHA256
    assert _entry_projection(delivery) == EXPECTED_ENTRIES

    evidence = delivery.evidence
    assert evidence.condition == "structured"
    assert evidence.mode == "fixed-approved-three-entry-bundle"
    assert evidence.selected_memory_present is True
    assert evidence.entry_count == 3
    assert evidence.bundle_separator == "\n\n---\n\n"
    assert evidence.bundle_bytes == 3_528
    assert evidence.bundle_sha256 == EXPECTED_BUNDLE_SHA256
    assert evidence.token_budget == 2_000
    assert evidence.d105_gate_id == fixed_bundle.D105_GATE_ID
    assert evidence.d105_gate_file_sha256 == fixed_bundle.D105_GATE_FILE_SHA256
    assert evidence.d105_render_set_sha256 == fixed_bundle.D105_RENDER_SET_SHA256
    assert evidence.index_version == fixed_bundle.D110_INDEX_VERSION
    assert evidence.index_content_hash == EXPECTED_INDEX_CONTENT_HASH
    assert evidence.index_file_sha256 == fixed_bundle.D110_INDEX_FILE_SHA256
    assert evidence.marker_file_sha256 == fixed_bundle.D110_MARKER_FILE_SHA256
    assert evidence.d110_gate_id == fixed_bundle.D110_GATE_ID
    assert evidence.d110_gate_file_sha256 == fixed_bundle.D110_GATE_FILE_SHA256
    assert evidence.query_dependent is False
    assert evidence.embedding_or_similarity_used is False
    assert evidence.ranking_or_threshold_used is False
    assert evidence.truncation_applied is False
    assert evidence.legacy_retrieval_called is False


def test_delivery_evidence_schema_rejects_nonexact_a_and_c_claims() -> None:
    no_memory = fixed_bundle.build_fixed_memory_delivery(
        condition=MemoryCondition.NO_MEMORY
    ).evidence.model_dump(mode="json")
    no_memory["bundle_sha256"] = EXPECTED_BUNDLE_SHA256
    with pytest.raises(ValidationError, match="no-memory delivery evidence is not exact"):
        fixed_bundle.FixedMemoryDeliveryEvidence.model_validate(no_memory)

    structured = fixed_bundle.build_fixed_memory_delivery(
        condition=MemoryCondition.STRUCTURED
    ).evidence.model_dump(mode="json")
    structured["ordered_entries"] = list(reversed(structured["ordered_entries"]))
    with pytest.raises(
        ValidationError,
        match="structured fixed-bundle delivery evidence is not exact",
    ):
        fixed_bundle.FixedMemoryDeliveryEvidence.model_validate(structured)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("selected_memory_present", 0),
        ("entry_count", False),
        ("bundle_bytes", False),
        ("query_dependent", 0),
        ("legacy_retrieval_called", 0),
    ],
)
def test_delivery_evidence_rejects_boolean_integer_type_aliases(
    field: str,
    value: object,
) -> None:
    payload = fixed_bundle.build_fixed_memory_delivery(
        condition=MemoryCondition.NO_MEMORY
    ).evidence.model_dump(mode="json")
    payload[field] = value

    with pytest.raises(ValidationError, match="must be an exact"):
        fixed_bundle.FixedMemoryDeliveryEvidence.model_validate(payload)


def test_request_evidence_schema_rejects_hash_and_a_normalization_drift() -> None:
    no_memory = fixed_bundle.build_fixed_memory_delivery(condition=MemoryCondition.NO_MEMORY)
    exact_hash = "sha256:" + ("a" * 64)
    valid = fixed_bundle.FixedMemoryRequestEvidence(
        delivery=no_memory.evidence,
        delivery_evidence_sha256=no_memory.evidence_sha256,
        request_body_sha256=exact_hash,
        normalized_no_memory_request_body_sha256=exact_hash,
    )
    payload = valid.model_dump(mode="json")

    payload["delivery_evidence_sha256"] = "sha256:" + ("b" * 64)
    with pytest.raises(ValidationError, match="request delivery hash differs"):
        fixed_bundle.FixedMemoryRequestEvidence.model_validate(payload)

    payload = valid.model_dump(mode="json")
    payload["normalized_no_memory_request_body_sha256"] = "sha256:" + ("c" * 64)
    with pytest.raises(ValidationError, match="no-memory request differs"):
        fixed_bundle.FixedMemoryRequestEvidence.model_validate(payload)

    payload = valid.model_dump(mode="json")
    payload["same_state_counterfactual_only"] = 1
    with pytest.raises(ValidationError, match="must be an exact boolean"):
        fixed_bundle.FixedMemoryRequestEvidence.model_validate(payload)

    structured = fixed_bundle.build_fixed_memory_delivery(condition=MemoryCondition.STRUCTURED)
    with pytest.raises(ValidationError, match="identical to its no-memory normalization"):
        fixed_bundle.FixedMemoryRequestEvidence(
            delivery=structured.evidence,
            delivery_evidence_sha256=structured.evidence_sha256,
            request_body_sha256=exact_hash,
            normalized_no_memory_request_body_sha256=exact_hash,
        )

    entry = fixed_bundle.EXPECTED_ENTRIES[0].model_dump(mode="json")
    entry["order"] = True
    with pytest.raises(ValidationError, match="must be an exact integer"):
        fixed_bundle.FixedBundleEntryBinding.model_validate(entry)


def test_fixed_policy_manifest_binds_only_a_or_c_without_asset_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = load_task_package(TASK_PATH.parent)
    monkeypatch.setattr(fixed_bundle, "_stable_read", _forbidden("asset read"))

    no_memory = build_manifest(
        package,
        run_id="run_fixed_bundle_manifest_a",
        memory_condition=MemoryCondition.NO_MEMORY,
        memory_policy_version=fixed_bundle.FIXED_BUNDLE_POLICY_VERSION,
    )
    structured = build_manifest(
        package,
        run_id="run_fixed_bundle_manifest_c",
        memory_condition=MemoryCondition.STRUCTURED,
        memory_policy_version=fixed_bundle.FIXED_BUNDLE_POLICY_VERSION,
    )

    assert no_memory.memory.index_version is None
    assert no_memory.memory.index_hash is None
    assert structured.memory.index_version == fixed_bundle.D110_INDEX_VERSION
    assert structured.memory.index_hash == EXPECTED_INDEX_CONTENT_HASH
    assert no_memory.tool_schema_version == structured.tool_schema_version == "v2"
    assert (
        no_memory.context_policy_version == structured.context_policy_version == "phase-evidence-v5"
    )


@pytest.mark.parametrize("token_budget", [0, 1_999, 2_001, 3_000])
def test_fixed_bundle_rejects_any_nonexact_token_allowance(token_budget: int) -> None:
    with pytest.raises(
        ContractError,
        match="exact 2,000-token allowance",
    ):
        fixed_bundle.build_fixed_memory_delivery(
            condition=MemoryCondition.NO_MEMORY,
            token_budget=token_budget,
        )


@pytest.mark.parametrize(
    "condition",
    [MemoryCondition.RAW_TRACE, MemoryCondition.SELECTIVE_STRUCTURED],
)
def test_fixed_bundle_rejects_non_a_c_conditions(condition: MemoryCondition) -> None:
    with pytest.raises(ContractError, match="supports only no_memory and structured"):
        fixed_bundle.build_fixed_memory_delivery(condition=condition)
    with pytest.raises(ContractError, match="supports only no_memory and structured"):
        fixed_bundle.fixed_bundle_manifest_binding(condition)


@pytest.mark.parametrize("missing_relative", BOUND_ASSET_PATHS)
def test_c_fails_closed_when_any_bound_asset_is_missing(
    tmp_path: Path,
    missing_relative: str,
) -> None:
    repository = _copy_bound_assets(tmp_path / "repository")
    repository.joinpath(*Path(missing_relative).parts).unlink()

    with pytest.raises(ContractError, match="input is missing"):
        fixed_bundle.build_fixed_memory_delivery(
            condition=MemoryCondition.STRUCTURED,
            repository=repository,
        )


@pytest.mark.parametrize("tampered_relative", BOUND_ASSET_PATHS)
def test_c_fails_closed_when_any_bound_asset_is_tampered(
    tmp_path: Path,
    tampered_relative: str,
) -> None:
    repository = _copy_bound_assets(tmp_path / "repository")
    target = repository.joinpath(*Path(tampered_relative).parts)
    target.write_bytes(target.read_bytes() + b"tamper")

    with pytest.raises(ContractError, match="input identity differs"):
        fixed_bundle.build_fixed_memory_delivery(
            condition=MemoryCondition.STRUCTURED,
            repository=repository,
        )


def test_c_fails_closed_on_a_linked_bound_asset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _copy_bound_assets(tmp_path / "repository")
    relative = fixed_bundle.EXPECTED_ENTRIES[0].render_path
    target = repository.joinpath(*Path(relative).parts)
    outside = tmp_path / "outside-render.txt"
    shutil.copy2(target, outside)
    target.unlink()
    try:
        target.symlink_to(outside.resolve())
    except OSError:
        # Windows may deny symlink creation without Developer Mode. Restore the
        # temp-copy bytes and exercise the same fail-closed reparse/linklike
        # branch explicitly so this platform does not silently lose coverage.
        shutil.copy2(outside, target)
        real_is_linklike = fixed_bundle._is_linklike
        monkeypatch.setattr(
            fixed_bundle,
            "_is_linklike",
            lambda path: path == target or real_is_linklike(path),
        )

    with pytest.raises(ContractError, match="traverses a link"):
        fixed_bundle.build_fixed_memory_delivery(
            condition=MemoryCondition.STRUCTURED,
            repository=repository,
        )


def test_c_build_uses_no_legacy_retrieval_embedding_or_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from patchloop.memory import retrieval, store

    repository = _copy_bound_assets(tmp_path / "repository")
    monkeypatch.setattr(retrieval, "retrieve_memory", _forbidden("legacy retrieval"))
    monkeypatch.setattr(retrieval, "_query_embedding", _forbidden("query embedding"))
    monkeypatch.setattr(store, "_build_embeddings", _forbidden("embedding builder"))
    monkeypatch.setattr(socket, "socket", _forbidden("network socket"))
    monkeypatch.setattr(socket, "create_connection", _forbidden("network connection"))

    delivery = fixed_bundle.build_fixed_memory_delivery(
        condition=MemoryCondition.STRUCTURED,
        repository=repository,
    )

    assert delivery.evidence.entry_count == 3
    assert delivery.evidence.bundle_sha256 == EXPECTED_BUNDLE_SHA256


def test_same_durable_prefix_context_diff_is_only_selected_memory(tmp_path: Path) -> None:
    package = load_task_package(TASK_PATH.parent)
    store = ArtifactStore(tmp_path / "artifacts")
    same_prefix = [
        RunEvent(
            event_id="evt_fixed_bundle_same_prefix",
            run_id="run_fixed_bundle_same_prefix",
            sequence=1,
            type=EventType.RUN_STARTED,
            timestamp=utc_now(),
            actor="runner",
            payload={"task_id": package.public.task_id},
        )
    ]
    common = {
        "policy_version": "phase-evidence-v5",
        "artifact_store": store,
        "budget": Budget(),
        "max_output_tokens": 4_096,
        "model_provider": "mock",
    }
    structured = fixed_bundle.build_fixed_memory_delivery(condition=MemoryCondition.STRUCTURED)

    no_memory_context = build_context_with_evidence(
        package.public,
        same_prefix,
        None,
        "",
        **common,
    )
    structured_context = build_context_with_evidence(
        package.public,
        same_prefix,
        None,
        structured.text,
        **common,
    )
    no_memory_payload = json.loads(no_memory_context.rendered)
    structured_payload = json.loads(structured_context.rendered)

    assert _leaf_differences(no_memory_payload, structured_payload) == {"/selected_memory"}
    assert no_memory_payload["selected_memory"] is None
    assert structured_payload["selected_memory"] == structured.text
    normalized = copy.deepcopy(structured_payload)
    normalized["selected_memory"] = None
    assert canonical_json(normalized) == canonical_json(no_memory_payload)


def test_request_artifact_replay_binds_actual_bundle_and_normalization(tmp_path: Path) -> None:
    package = load_task_package(TASK_PATH.parent)
    store = ArtifactStore(tmp_path / "artifacts")
    events = [
        RunEvent(
            event_id="evt_fixed_bundle_replay",
            run_id="run_fixed_bundle_replay",
            sequence=1,
            type=EventType.RUN_STARTED,
            timestamp=utc_now(),
            actor="runner",
            payload={"task_id": package.public.task_id},
        )
    ]
    common = {
        "policy_version": "phase-evidence-v5",
        "artifact_store": store,
        "budget": Budget(),
        "max_output_tokens": 4_096,
        "model_provider": "mock",
    }
    delivery = fixed_bundle.build_fixed_memory_delivery(condition=MemoryCondition.STRUCTURED)
    structured = build_context_with_evidence(
        package.public,
        events,
        None,
        delivery.text,
        **common,
    )
    no_memory = build_context_with_evidence(
        package.public,
        events,
        None,
        "",
        **common,
    )
    request_body = {
        "model": "mock-v1",
        "system_prompt": "fixed-system",
        "context": structured.rendered,
        "tools": [],
    }
    normalized_body = {**request_body, "context": no_memory.rendered}
    request_hash = sha256_text(canonical_json(request_body))
    normalized_hash = sha256_text(canonical_json(normalized_body))
    request_evidence = fixed_bundle.FixedMemoryRequestEvidence(
        delivery=delivery.evidence,
        delivery_evidence_sha256=delivery.evidence_sha256,
        request_body_sha256=request_hash,
        normalized_no_memory_request_body_sha256=normalized_hash,
    )
    artifact = {
        "schema_version": "model-request-evidence-v1",
        "provider": "mock",
        "endpoint": None,
        "request_body": request_body,
        "request_body_hash": request_hash,
        "context_build": structured.evidence,
        "fixed_memory_delivery": request_evidence.model_dump(mode="json"),
    }

    assert fixed_bundle.validate_fixed_memory_request_artifact(artifact) == request_evidence

    tampered = copy.deepcopy(artifact)
    tampered_context = json.loads(structured.rendered)
    tampered_context["selected_memory"] = delivery.text[:-2] + "X\n"
    tampered["request_body"]["context"] = json.dumps(
        tampered_context,
        indent=2,
        ensure_ascii=False,
        default=str,
    )
    tampered_hash = sha256_text(canonical_json(tampered["request_body"]))
    tampered["request_body_hash"] = tampered_hash
    tampered["fixed_memory_delivery"]["request_body_sha256"] = tampered_hash
    with pytest.raises(ContractError, match="selected-memory text identity differs"):
        fixed_bundle.validate_fixed_memory_request_artifact(tampered)


def test_request_artifact_replay_supports_the_offline_openai_payload_shape(
    tmp_path: Path,
) -> None:
    package = load_task_package(TASK_PATH.parent)
    store = ArtifactStore(tmp_path / "artifacts")
    events = [
        RunEvent(
            event_id="evt_fixed_bundle_openai_replay",
            run_id="run_fixed_bundle_openai_replay",
            sequence=1,
            type=EventType.RUN_STARTED,
            timestamp=utc_now(),
            actor="runner",
            payload={"task_id": package.public.task_id},
        )
    ]
    common = {
        "policy_version": "phase-evidence-v5",
        "artifact_store": store,
        "budget": Budget(),
        "max_output_tokens": 25_000,
        "model_provider": "openai",
    }
    delivery = fixed_bundle.build_fixed_memory_delivery(condition=MemoryCondition.STRUCTURED)
    structured = build_context_with_evidence(
        package.public,
        events,
        None,
        delivery.text,
        **common,
    )
    no_memory = build_context_with_evidence(
        package.public,
        events,
        None,
        "",
        **common,
    )
    adapter = OpenAIResponsesAdapter(
        ModelConfig(
            provider="openai",
            model_id="gpt-5.4-mini-2026-03-17",
            max_output_tokens=25_000,
            transport_max_retries=0,
        ),
        client=SimpleNamespace(max_retries=0),
    )
    request_body = adapter.request_payload(structured.rendered, [])
    normalized_body = adapter.request_payload(no_memory.rendered, [])
    request_hash = sha256_text(canonical_json(request_body))
    request_evidence = fixed_bundle.FixedMemoryRequestEvidence(
        delivery=delivery.evidence,
        delivery_evidence_sha256=delivery.evidence_sha256,
        request_body_sha256=request_hash,
        normalized_no_memory_request_body_sha256=sha256_text(canonical_json(normalized_body)),
    )
    artifact = {
        "schema_version": "model-request-evidence-v1",
        "provider": "openai",
        "endpoint": "/v1/responses",
        "request_body": request_body,
        "request_body_hash": request_hash,
        "context_build": structured.evidence,
        "fixed_memory_delivery": request_evidence.model_dump(mode="json"),
    }

    assert fixed_bundle.validate_fixed_memory_request_artifact(artifact) == request_evidence


class _StopAfterSecondRequest(Exception):
    pass


class _TwoRequestMockAdapter:
    def __init__(self) -> None:
        self.contexts: list[str] = []

    def next_turn(self, context: str, _tools: list[dict[str, object]]) -> ModelTurn:
        self.contexts.append(context)
        if len(self.contexts) == 1:
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "search_files",
                        "fixed-bundle-first-turn-search",
                        {"query": "parse", "path_glob": "**/*.py"},
                    )
                ]
            )
        raise _StopAfterSecondRequest("two request prefixes captured before evaluation")


def test_mock_runner_records_exact_fixed_delivery_on_every_request_without_retrieval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = load_task_package(TASK_PATH.parent)
    manifest = build_manifest(
        package,
        run_id="run_fixed_bundle_two_request_evidence",
        provider="mock",
        model_id="mock-v1",
        memory_condition=MemoryCondition.STRUCTURED,
        memory_policy_version=fixed_bundle.FIXED_BUNDLE_POLICY_VERSION,
        sandbox_backend="local",
    )
    adapter = _TwoRequestMockAdapter()
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    monkeypatch.setattr(
        "patchloop.agent.runner.retrieve_memory",
        _forbidden("legacy retrieval"),
    )
    monkeypatch.setattr(
        "patchloop.memory.retrieval._query_embedding",
        _forbidden("query embedding"),
    )
    monkeypatch.setattr(socket, "socket", _forbidden("network socket"))
    monkeypatch.setattr(socket, "create_connection", _forbidden("network connection"))
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)
    monkeypatch.setattr(runner, "_evaluate", _forbidden("evaluator"))

    result = runner.start(TASK_PATH, model="mock", manifest=manifest)

    assert result["outcome_kind"] == RunOutcomeKind.INFRASTRUCTURE_ERROR.value
    assert len(adapter.contexts) == 2
    events = runner.state.list_events(manifest.run_id)
    assert not any(event.type == EventType.MEMORY_RETRIEVED for event in events)
    context_events = [event for event in events if event.type == EventType.CONTEXT_BUILT]
    assert len(context_events) == 2
    assert context_events[0].sequence < context_events[1].sequence
    between_contexts = [
        event
        for event in events
        if context_events[0].sequence < event.sequence < context_events[1].sequence
    ]
    assert any(event.type == EventType.MODEL_CALLED for event in between_contexts)
    assert any(
        event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "search_files"
        for event in between_contexts
    )
    assert any(event.type == EventType.CHECKPOINT_SAVED for event in between_contexts)

    request_hashes = []
    normalized_hashes = []
    delivery_hashes = []
    for index, event in enumerate(context_events):
        assert event.payload["memory_delivery_policy_version"] == "fixed-d110-bundle-v1"
        assert event.payload["memory_delivery_entry_count"] == 3
        assert event.payload["memory_delivery_bundle_sha256"] == EXPECTED_BUNDLE_SHA256
        artifact = json.loads(Path(event.payload["artifact_path"]).read_text(encoding="utf-8"))
        fixed_evidence = artifact["fixed_memory_delivery"]
        delivery = fixed_evidence["delivery"]
        request_body = artifact["request_body"]
        request_context = json.loads(request_body["context"])

        replayed = fixed_bundle.validate_fixed_memory_request_artifact(
            artifact,
            context_event_payload=event.payload,
        )
        assert replayed.delivery.entry_count == 3
        if index == 0:
            tampered_event = dict(event.payload)
            tampered_event["memory_delivery_entry_count"] = 0
            with pytest.raises(ContractError, match="ContextBuilt fixed-memory binding differs"):
                fixed_bundle.validate_fixed_memory_request_artifact(
                    artifact,
                    context_event_payload=tampered_event,
                )

        assert artifact["schema_version"] == "model-request-evidence-v1"
        assert artifact["provider"] == "mock"
        assert artifact["endpoint"] is None
        assert request_body["context"] == adapter.contexts[index]
        assert request_context["selected_memory"] is not None
        assert delivery["condition"] == "structured"
        assert delivery["entry_count"] == 3
        assert [
            {
                key: entry[key]
                for key in (
                    "order",
                    "memory_id",
                    "semantic_group_id",
                    "render_file_sha256",
                )
            }
            for entry in delivery["ordered_entries"]
        ] == EXPECTED_ENTRIES
        assert delivery["bundle_sha256"] == EXPECTED_BUNDLE_SHA256
        assert delivery["legacy_retrieval_called"] is False
        assert delivery["embedding_or_similarity_used"] is False
        assert delivery["ranking_or_threshold_used"] is False
        assert fixed_evidence["request_body_sha256"] == artifact["request_body_hash"]
        assert event.payload["request_body_hash"] == artifact["request_body_hash"]
        assert (
            event.payload["memory_delivery_evidence_sha256"]
            == fixed_evidence["delivery_evidence_sha256"]
        )
        assert (
            event.payload["normalized_no_memory_request_body_sha256"]
            == fixed_evidence["normalized_no_memory_request_body_sha256"]
        )

        normalized_context = copy.deepcopy(request_context)
        normalized_context["selected_memory"] = None
        normalized_request = copy.deepcopy(request_body)
        normalized_request["context"] = json.dumps(
            normalized_context,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
        assert (
            sha256_text(canonical_json(normalized_request))
            == fixed_evidence["normalized_no_memory_request_body_sha256"]
        )
        request_hashes.append(fixed_evidence["request_body_sha256"])
        normalized_hashes.append(fixed_evidence["normalized_no_memory_request_body_sha256"])
        delivery_hashes.append(fixed_evidence["delivery_evidence_sha256"])

    assert len(set(request_hashes)) == 2
    assert len(set(normalized_hashes)) == 2
    assert len(set(delivery_hashes)) == 1


def test_mock_a_and_c_keep_the_same_event_type_topology(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = load_task_package(TASK_PATH.parent)
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    monkeypatch.setattr(
        "patchloop.agent.runner.retrieve_memory",
        _forbidden("legacy retrieval"),
    )
    monkeypatch.setattr(socket, "socket", _forbidden("network socket"))
    monkeypatch.setattr(socket, "create_connection", _forbidden("network connection"))

    event_types: dict[MemoryCondition, list[EventType]] = {}
    for condition in (MemoryCondition.NO_MEMORY, MemoryCondition.STRUCTURED):
        manifest = build_manifest(
            package,
            run_id=f"run_fixed_bundle_topology_{condition.value}",
            provider="mock",
            model_id="mock-v1",
            memory_condition=condition,
            memory_policy_version=fixed_bundle.FIXED_BUNDLE_POLICY_VERSION,
            sandbox_backend="local",
        )
        adapter = _TwoRequestMockAdapter()
        runner = AgentRunner(tmp_path / condition.value)
        monkeypatch.setattr(
            runner,
            "_model_adapter",
            lambda *_args, _adapter=adapter, **_kwargs: _adapter,
        )
        monkeypatch.setattr(runner, "_evaluate", _forbidden("evaluator"))

        result = runner.start(TASK_PATH, model="mock", manifest=manifest)

        assert result["outcome_kind"] == RunOutcomeKind.INFRASTRUCTURE_ERROR.value
        events = runner.state.list_events(manifest.run_id)
        event_types[condition] = [event.type for event in events]
        assert len([event for event in events if event.type == EventType.CONTEXT_BUILT]) == 2
        assert not any(event.type == EventType.MEMORY_RETRIEVED for event in events)

    assert event_types[MemoryCondition.NO_MEMORY] == event_types[MemoryCondition.STRUCTURED]
