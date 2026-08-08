from __future__ import annotations

import copy
from pathlib import Path

import pytest

from patchloop.memory import d109_index_freeze_authorization as d109
from patchloop.util import canonical_json, sha256_text

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def exact_predecessors() -> tuple[tuple[dict, bytes, dict], dict]:
    return (
        d109._load_exact_portable_inputs(ROOT.resolve()),
        d109.d108.validate_d108_completion_gate(repository=ROOT),
    )


@pytest.fixture(autouse=True)
def reuse_exact_predecessors(
    monkeypatch: pytest.MonkeyPatch,
    exact_predecessors: tuple[tuple[dict, bytes, dict], dict],
) -> None:
    portable_inputs, d108_result = exact_predecessors
    monkeypatch.setattr(d109, "_load_exact_portable_inputs", lambda _repository: portable_inputs)
    monkeypatch.setattr(
        d109.d108,
        "validate_d108_completion_gate",
        lambda **_kwargs: d108_result,
    )


def _preflight() -> dict:
    return d109.observe_d109_runtime_preflight(repository=ROOT)


def test_d109_runtime_preflight_binds_exact_unfrozen_runtime_copy() -> None:
    preflight = _preflight()
    body = preflight["semantic_body"]

    assert body["runtime_target"] == {
        **body["runtime_target"],
        "target_path": d109.DEFAULT_RUNTIME_INDEX_PATH.as_posix(),
        "directory_file_names": ["index.json"],
        "file_bytes": 55_644,
        "file_sha256": d109.EXPECTED_INDEX_FILE_SHA,
        "content_hash": d109.EXPECTED_INDEX_CONTENT_HASH,
        "index_id": d109.EXPECTED_INDEX_ID,
        "frozen": False,
        "frozen_marker_present": False,
        "index_freeze_authorized": False,
        "memory_index_frozen": False,
        "retrieval_ready": False,
        "runtime_memory_injection_count": 0,
        "byte_identical_to_portable_index": True,
    }
    assert body["semantic_contents"]["memory_ids"] == list(d109.EXPECTED_MEMORY_IDS)
    assert body["semantic_contents"]["semantic_group_ids"] == list(d109.EXPECTED_GROUP_IDS)
    assert body["semantic_contents"]["held_group_ids"] == list(
        d109.EXPECTED_HELD_GROUP_IDS
    )
    assert body["evidence_boundary"]["runtime_index_written"] is False
    assert body["evidence_boundary"]["freeze_called"] is False


def test_d109_candidate_allows_only_freeze_mutations_and_keeps_later_gates_closed() -> None:
    preflight = _preflight()
    candidate = d109.build_d109_freeze_authorization_candidate(
        preflight,
        repository=ROOT,
    )
    body = candidate["semantic_body"]

    assert body["d108_completion_gate"]["memory_delta_tokens"] == 702
    assert body["d108_completion_gate"]["maximum_memory_delta_tokens"] == 2_000
    assert body["authorized_action_template"]["allowed_existing_json_mutations"] == list(
        d109.ALLOWED_EXISTING_JSON_MUTATIONS
    )
    assert body["authorized_action_template"]["approval_receipt_required"] is True
    assert body["authorized_action_template"]["one_use_execution_required"] is True
    assert body["authorized_action_template"]["automatic_retry_allowed"] is False
    assert body["authorized_action_template"]["retrieval_authorized"] is False
    assert body["authorized_action_template"]["core_campaign_authorized"] is False
    assert body["current_authority"] == {
        **body["current_authority"],
        "freeze_authorization_candidate_ready": True,
        "explicit_user_approval_received": False,
        "index_freeze_authorized": False,
        "memory_index_frozen": False,
        "frozen_marker_present": False,
        "retrieval_ready": False,
        "core_campaign_unlocked": False,
        "provider_calls_made_by_d109": 0,
        "evaluator_calls_made_by_d109": 0,
    }


def test_d109_runtime_inspection_rejects_extra_marker(tmp_path: Path) -> None:
    target_dir = tmp_path / ".patchloop" / "memory" / "indexes" / d109.EXPECTED_INDEX_ID
    target_dir.mkdir(parents=True)
    portable = (ROOT / d109.DEFAULT_PORTABLE_INDEX_PATH).read_bytes()
    (target_dir / "index.json").write_bytes(portable)
    (target_dir / "FROZEN").write_text("unexpected\n", encoding="utf-8")

    with pytest.raises(d109.D109AuthorizationError, match="only index.json|already frozen"):
        d109._inspect_runtime_target_bytes(
            target_dir / "index.json",
            portable,
            repository=tmp_path.resolve(),
        )


def test_d109_runtime_inspection_rejects_one_byte_drift(tmp_path: Path) -> None:
    target_dir = tmp_path / ".patchloop" / "memory" / "indexes" / d109.EXPECTED_INDEX_ID
    target_dir.mkdir(parents=True)
    portable = (ROOT / d109.DEFAULT_PORTABLE_INDEX_PATH).read_bytes()
    tampered = portable.replace(b'"frozen": false', b'"frozen": true ', 1)
    (target_dir / "index.json").write_bytes(tampered)

    with pytest.raises(d109.D109AuthorizationError, match="differs from the portable"):
        d109._inspect_runtime_target_bytes(
            target_dir / "index.json",
            portable,
            repository=tmp_path.resolve(),
        )


def test_d109_rehashed_candidate_authority_tamper_fails_closed() -> None:
    preflight = _preflight()
    candidate = d109.build_d109_freeze_authorization_candidate(
        preflight,
        repository=ROOT,
    )
    tampered = copy.deepcopy(candidate)
    tampered["semantic_body"]["current_authority"]["index_freeze_authorized"] = True
    body_hash = sha256_text(canonical_json(tampered["semantic_body"]))
    tampered["semantic_body_hash"] = body_hash
    tampered["candidate_id"] = (
        f"d109freezecandidate_{body_hash.removeprefix('sha256:')}"
    )

    with pytest.raises(d109.D109AuthorizationError, match="semantic content"):
        d109.validate_d109_candidate_payload(tampered, preflight, repository=ROOT)


def test_d109_builder_never_calls_freeze_retrieval_or_external_boundaries(monkeypatch) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("D-109 crossed an unapproved boundary")

    monkeypatch.setattr("patchloop.memory.store.freeze_index", forbidden)
    monkeypatch.setattr("patchloop.memory.retrieval.retrieve_memory", forbidden)
    monkeypatch.setattr(d109.d108, "execute_d108_provider_token_counts", forbidden)

    preflight = _preflight()
    candidate = d109.build_d109_freeze_authorization_candidate(
        preflight,
        repository=ROOT,
    )
    gate = d109.build_d109_source_gate(preflight, candidate, repository=ROOT)

    boundary = gate["semantic_body"]["evidence_boundary"]
    assert boundary["runtime_index_written"] is False
    assert boundary["frozen_marker_created"] is False
    assert boundary["freeze_function_called"] is False
    assert boundary["retrieval_called"] is False
    assert boundary["provider_calls_made"] == 0
    assert boundary["evaluator_calls_made"] == 0


def test_d109_checked_in_source_gate_rebuilds_portably() -> None:
    result = d109.validate_d109_source_gate(repository=ROOT)

    assert result["ok"] is True
    assert result["live_runtime_verified"] is False
    assert result["index_freeze_authorized"] is False
    assert result["memory_index_frozen"] is False
    assert result["retrieval_ready"] is False
    assert result["core_campaign_unlocked"] is False
    assert result["provider_calls_made"] == 0
    assert result["evaluator_calls_made"] == 0


def test_d109_checked_in_source_gate_can_recheck_live_runtime_precondition() -> None:
    result = d109.validate_d109_source_gate(
        repository=ROOT,
        verify_live_runtime=True,
    )

    assert result["ok"] is True
    assert result["live_runtime_verified"] is True
    assert result["memory_index_frozen"] is False
