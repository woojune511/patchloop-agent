from __future__ import annotations

import copy
from pathlib import Path

import pytest

from patchloop.memory import d111_retrieval_readiness_authorization as d111
from patchloop.util import canonical_json, sha256_text

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def exact_context() -> dict:
    return d111._load_exact_inputs(ROOT.resolve())


def _preflight(exact_context: dict) -> dict:
    return d111.build_d111_preflight(repository=ROOT, _context=exact_context)


def test_d111_preflight_binds_exact_frozen_index_and_three_public_probes(
    exact_context: dict,
) -> None:
    preflight = _preflight(exact_context)
    body = preflight["semantic_body"]

    assert body["d110_completion_gate"]["gate_id"] == d111.EXPECTED_D110_GATE_ID
    assert body["portable_frozen_index"]["file_sha256"] == d111.EXPECTED_FROZEN_INDEX_FILE_SHA
    assert body["portable_frozen_index"]["frozen"] is True
    assert [row["probe_id"] for row in body["public_probe_plan"]] == [
        row["probe_id"] for row in d111.PROBE_SPECS
    ]
    assert all(row["public_spec_only_read"] for row in body["public_probe_plan"])
    assert not any(
        row["private_hidden_reference_or_bad_patch_read"] for row in body["public_probe_plan"]
    )


def test_d111_preflight_records_real_readiness_blockers(exact_context: dict) -> None:
    audit = _preflight(exact_context)["semantic_body"]["legacy_retriever_audit"]

    assert audit["current_inline_retrieval_authority"] is False
    assert audit["guard_fails_before_query_embedding"] is True
    assert audit["locked_local_snapshot_enforced_by_query_encoder"] is False
    assert audit["d105_exact_model_facing_text_used_by_structured_renderer"] is False
    assert audit["raw_trace_portable_contract_ready"] is False
    assert audit["perfect_semantic_implement_python_upper_bound"] == 0.65
    assert audit["selective_threshold"] == 0.72
    assert audit["natural_public_query_can_reach_selective_threshold"] is False
    assert all(row["byte_identical"] is False for row in audit["legacy_and_d105_render_comparison"])


def test_d111_candidate_is_one_use_diagnostic_not_retrieval_approval(
    exact_context: dict,
) -> None:
    preflight = _preflight(exact_context)
    candidate = d111.build_d111_authorization_candidate(preflight, repository=ROOT)
    body = candidate["semantic_body"]
    action = body["proposed_one_use_action"]
    authority = body["authority"]

    assert action["maximum_executions"] == 1
    assert action["legacy_retrieve_memory_call_allowed"] is False
    assert action["runtime_memory_injection_allowed"] is False
    assert action["provider_call_allowed"] is False
    assert action["evaluator_call_allowed"] is False
    assert action["score_policy_correction_allowed"] is False
    assert action["threshold_change_allowed"] is False
    assert action["raw_trace_in_scope"] is False
    assert action["local_embedding_model_load_count"] == 1
    assert action["local_batch_encode_call_count"] == 1
    assert action["local_batch_query_row_count"] == 3
    assert action["expected_query_vector_shape"] == [3, 384]
    scoring = action["diagnostic_scoring_contract"]
    assert scoring["score_weights"] == d111.SCORE_WEIGHTS
    assert scoring["selective_threshold"] == 0.72
    assert scoring["selective_comparator"] == "greater-than-or-equal"
    assert authority["retrieval_readiness_candidate_ready"] is True
    assert authority["exact_candidate_user_approval_received"] is False
    assert authority["retrieval_probe_authorized"] is False
    assert authority["retrieval_ready"] is False
    assert authority["core_campaign_unlocked"] is False
    assert body["approval_contract"]["generic_continue_message_is_approval"] is False


def test_d111_rehashed_candidate_scope_widening_fails_closed(exact_context: dict) -> None:
    preflight = _preflight(exact_context)
    candidate = d111.build_d111_authorization_candidate(preflight, repository=ROOT)
    tampered = copy.deepcopy(candidate)
    tampered["semantic_body"]["proposed_one_use_action"]["runtime_memory_injection_allowed"] = True
    body_hash = sha256_text(canonical_json(tampered["semantic_body"]))
    tampered["semantic_body_hash"] = body_hash
    tampered["candidate_id"] = f"d111retrievalcandidate_{body_hash.removeprefix('sha256:')}"

    with pytest.raises(d111.D111ReadinessError, match="candidate semantic content"):
        d111.build_d111_source_gate(preflight, tampered, repository=ROOT)


def test_d111_builder_never_crosses_retrieval_or_external_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    exact_context: dict,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("D-111 crossed an unapproved boundary")

    monkeypatch.setattr("patchloop.memory.retrieval.retrieve_memory", forbidden)
    monkeypatch.setattr("patchloop.memory.retrieval._query_embedding", forbidden)
    monkeypatch.setattr("patchloop.memory.retrieval._render_raw_trace", forbidden)
    preflight = _preflight(exact_context)
    candidate = d111.build_d111_authorization_candidate(preflight, repository=ROOT)
    gate = d111.build_d111_source_gate(preflight, candidate, repository=ROOT)

    boundary = preflight["semantic_body"]["evidence_boundary"]
    assert boundary["retrieval_function_called"] is False
    assert boundary["query_embedding_encoded"] is False
    assert boundary["runtime_memory_injected"] is False
    assert boundary["provider_calls_made"] == 0
    assert boundary["evaluator_calls_made"] == 0
    assert gate["semantic_body"]["authority"]["retrieval_probe_authorized"] is False


def test_d111_rehashed_preflight_frozen_index_tamper_fails_closed(
    exact_context: dict,
) -> None:
    preflight = _preflight(exact_context)
    tampered = copy.deepcopy(preflight)
    tampered["semantic_body"]["portable_frozen_index"]["file_sha256"] = "sha256:" + "0" * 64
    body_hash = sha256_text(canonical_json(tampered["semantic_body"]))
    tampered["semantic_body_hash"] = body_hash
    tampered["preflight_id"] = f"d111preflight_{body_hash.removeprefix('sha256:')}"

    with pytest.raises(d111.D111ReadinessError, match="frozen-index binding"):
        d111.build_d111_authorization_candidate(tampered, repository=ROOT)


def test_d111_checked_in_source_gate_rebuilds_portably() -> None:
    result = d111.validate_d111_source_gate(repository=ROOT)

    assert result["ok"] is True
    assert result["live_runtime_verified"] is False
    assert result["retrieval_readiness_candidate_ready"] is True
    assert result["exact_candidate_user_approval_received"] is False
    assert result["retrieval_probe_authorized"] is False
    assert result["retrieval_probe_executed"] is False
    assert result["runtime_memory_injection_count"] == 0
    assert result["provider_calls_made"] == 0
    assert result["evaluator_calls_made"] == 0
    assert result["core_campaign_unlocked"] is False


def test_d111_checked_in_source_gate_can_verify_live_and_current_bytes() -> None:
    result = d111.validate_d111_source_gate(
        repository=ROOT,
        verify_live_runtime=True,
        verify_current_implementation=True,
    )

    assert result["ok"] is True
    assert result["live_runtime_verified"] is True
    assert result["current_implementation_verified"] is True
