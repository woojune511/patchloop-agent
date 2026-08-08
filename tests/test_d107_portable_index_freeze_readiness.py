from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from patchloop.errors import ContractError
from patchloop.memory import d107_portable_index_freeze_readiness as d107
from patchloop.util import canonical_json, sha256_text

ROOT = Path(__file__).resolve().parents[1]


def _future_receipt(
    plan: dict,
    baseline: int,
    with_memory: int,
) -> dict:
    pair = plan["semantic_body"]["count_request_pair"]
    plan_binding = {
        "plan_id": plan["plan_id"],
        "semantic_body_hash": plan["semantic_body_hash"],
        "file_sha256": d107.sha256_bytes(d107._pretty_json(plan)),
    }
    body = {
        "plan": plan_binding,
        "calls": [
            {
                "order": 1,
                "label": "baseline",
                "request_file_sha256": pair["baseline_artifact"]["file_sha256"],
                "request_semantic_hash": pair["baseline_semantic_hash"],
                "response": {
                    "object": "response.input_tokens",
                    "input_tokens": baseline,
                },
            },
            {
                "order": 2,
                "label": "with_memory",
                "request_file_sha256": pair["with_memory_artifact"]["file_sha256"],
                "request_semantic_hash": pair["with_memory_semantic_hash"],
                "response": {
                    "object": "response.input_tokens",
                    "input_tokens": with_memory,
                },
            },
        ],
        "baseline_input_tokens": baseline,
        "with_memory_input_tokens": with_memory,
        "memory_delta_tokens": with_memory - baseline,
        "provider_input_token_count_calls_made": 2,
        "provider_generation_calls_made": 0,
        "sdk_transport_max_retries": 0,
        "automatic_retry_used": False,
        "api_key_persisted_in_artifact": False,
        "provider_exact_budget_validated": True,
        "index_freeze_authorized": False,
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": d107.TOKEN_RECEIPT_SCHEMA_VERSION,
        "receipt_id": f"d107countreceipt_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def test_d107_token_plan_uses_exact_runtime_pair_without_calls() -> None:
    plan, artifacts = d107.build_d107_token_count_plan(repository=ROOT)
    body = plan["semantic_body"]

    assert len(artifacts) == 6
    assert body["context_pair"]["observed_deep_diff_json_pointers"] == ["/selected_memory"]
    assert body["context_pair"]["byte_identical_after_slot_normalization"] is True
    assert body["memory_bundle"]["file_bytes"] == 3_528
    assert body["memory_bundle"]["file_sha256"] == d107.EXPECTED_MEMORY_BUNDLE_SHA
    assert body["runtime_tuple"] == {
        **body["runtime_tuple"],
        "model": "gpt-5.4-mini-2026-03-17",
        "reasoning_effort": "medium",
        "reasoning_mode": "standard",
        "service_tier": "default",
        "transport_max_retries": 0,
        "system_prompt_version": "SYSTEM_PROMPT_V3",
        "tool_schema_version": "v2",
        "tool_schema_count": 6,
        "context_policy_version": "phase-evidence-v5",
        "max_output_tokens": 25_000,
        "openai_sdk_version": "2.47.0",
        "store": False,
        "previous_response_id": None,
        "truncation": "disabled",
    }
    assert body["count_request_pair"]["exact_payload_fields"] == [
        "model",
        "input",
        "tools",
        "reasoning",
        "truncation",
    ]
    assert body["count_request_pair"]["endpoint"] == ("POST /v1/responses/input_tokens")
    assert body["unobserved_counts"]["baseline_input_tokens"] is None
    assert body["unobserved_counts"]["with_memory_input_tokens"] is None
    assert body["unobserved_counts"]["memory_delta_tokens"] is None
    assert body["authority"]["provider_input_token_count_calls_made"] == 0
    assert body["authority"]["provider_generation_calls_made"] == 0
    assert body["authority"]["index_freeze_authorized"] is False


def test_d107_request_artifacts_only_change_selected_memory() -> None:
    _, artifacts = d107.build_d107_token_count_plan(repository=ROOT)
    root = d107.DEFAULT_ARTIFACT_DIRECTORY
    baseline_context = json.loads(artifacts[root / d107.ARTIFACT_NAMES["baseline_context"]])
    with_memory_context = json.loads(artifacts[root / d107.ARTIFACT_NAMES["with_memory_context"]])
    assert d107._deep_diff_pointers(baseline_context, with_memory_context) == ["/selected_memory"]
    assert baseline_context["selected_memory"] is None
    assert with_memory_context["selected_memory"].encode("ascii").endswith(b"\n")

    baseline_full = json.loads(artifacts[root / d107.ARTIFACT_NAMES["baseline_full_request"]])
    memory_full = json.loads(artifacts[root / d107.ARTIFACT_NAMES["with_memory_full_request"]])
    assert baseline_full["store"] is False
    assert baseline_full["truncation"] == "disabled"
    assert baseline_full["reasoning"] == {"effort": "medium"}
    assert "previous_response_id" not in baseline_full
    normalized = d107._normalize_request_context(
        memory_full,
        baseline_context=baseline_full["input"][1]["content"],
    )
    assert normalized == json.loads(canonical_json(baseline_full))


def test_d107_no_call_builder_does_not_touch_external_paths(monkeypatch) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("unapproved external or runtime path was called")

    monkeypatch.setattr("patchloop.agent.model.OpenAI", forbidden)
    monkeypatch.setattr(d107.d106, "download_d106_snapshot", forbidden)
    monkeypatch.setattr(d107.d106, "run_d106_embedding_preflight", forbidden)
    monkeypatch.setattr("patchloop.memory.retrieval.retrieve_memory", forbidden)
    monkeypatch.setattr("patchloop.memory.store.freeze_index", forbidden)

    plan, artifacts = d107.build_d107_token_count_plan(repository=ROOT)

    authority = plan["semantic_body"]["authority"]
    assert authority["provider_input_token_count_calls_made"] == 0
    assert authority["provider_generation_calls_made"] == 0
    assert len(artifacts) == 6


def test_d107_token_plan_tamper_fails_closed() -> None:
    plan, _ = d107.build_d107_token_count_plan(repository=ROOT)
    tampered = copy.deepcopy(plan)
    tampered["semantic_body"]["runtime_tuple"]["max_output_tokens"] = 24_999
    body_hash = sha256_text(canonical_json(tampered["semantic_body"]))
    tampered["semantic_body_hash"] = body_hash
    tampered["plan_id"] = f"d107plan_{body_hash.removeprefix('sha256:')}"

    with pytest.raises(d107.D107ReadinessError, match="semantic content"):
        d107.validate_d107_token_count_plan_payload(tampered, repository=ROOT)


def test_d107_future_receipt_accepts_exact_2000_boundary() -> None:
    plan, _ = d107.build_d107_token_count_plan(repository=ROOT)
    receipt = _future_receipt(plan, 100_000, 102_000)

    validated = d107.validate_d107_future_provider_receipt(receipt, plan)

    assert validated["memory_delta_tokens"] == 2_000
    assert validated["provider_exact_budget_validated"] is True
    assert validated["index_freeze_authorized"] is False


@pytest.mark.parametrize(
    ("baseline", "with_memory"),
    [
        (True, 100),
        (-1, 100),
        (101, 100),
        (100, 2_101),
    ],
)
def test_d107_future_receipt_rejects_invalid_counts(
    baseline: int,
    with_memory: int,
) -> None:
    plan, _ = d107.build_d107_token_count_plan(repository=ROOT)
    receipt = _future_receipt(plan, baseline, with_memory)

    with pytest.raises(ContractError):
        d107.validate_d107_future_provider_receipt(receipt, plan)


def test_d107_future_receipt_rejects_request_substitution() -> None:
    plan, _ = d107.build_d107_token_count_plan(repository=ROOT)
    receipt = _future_receipt(plan, 100_000, 101_000)
    receipt["semantic_body"]["calls"][1]["request_file_sha256"] = "sha256:" + "0" * 64
    body_hash = sha256_text(canonical_json(receipt["semantic_body"]))
    receipt["semantic_body_hash"] = body_hash
    receipt["receipt_id"] = f"d107countreceipt_{body_hash.removeprefix('sha256:')}"

    with pytest.raises(d107.D107ReadinessError, match="call identity"):
        d107.validate_d107_future_provider_receipt(receipt, plan)


def test_d107_pinned_d106_gate_rejects_one_byte_tamper() -> None:
    content = (ROOT / d107.DEFAULT_D106_GATE_PATH).read_bytes()
    tampered = content.replace(b'"milestone": "D-106"', b'"milestone": "D-10X"')

    with pytest.raises(d107.D107ReadinessError, match="file hash"):
        d107._validate_pinned_d106_gate_content(tampered, repository=ROOT)


def test_d107_portable_vectors_are_exact_three_normalized_rows() -> None:
    payload = json.loads((ROOT / d107.DEFAULT_D106_INDEX_PATH).read_text(encoding="utf-8"))

    norms = d107.portable_vector_norms(payload)

    assert list(norms) == list(d107.EXPECTED_MEMORY_IDS)
    assert all(abs(norm - 1.0) <= 1e-5 for norm in norms.values())


def test_d107_checked_in_source_gate_deeply_rebuilds_without_runtime_read(
    monkeypatch,
) -> None:
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(path: Path) -> bytes:
        if ".patchloop" in path.parts:
            raise AssertionError("D-107 portable validation read runtime state")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    result = d107.validate_d107_source_gate(repository=ROOT)

    assert result["ok"] is True
    assert result["request_artifact_count"] == 6
    assert result["provider_calls_made"] == 0
    assert result["provider_exact_budget_validated"] is False
    assert result["index_freeze_authorized"] is False
    assert result["memory_index_frozen"] is False
    assert result["retrieval_ready"] is False
    assert result["core_campaign_unlocked"] is False
