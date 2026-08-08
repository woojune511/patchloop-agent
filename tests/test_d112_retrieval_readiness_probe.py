from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from patchloop.memory import d111_retrieval_readiness_authorization as d111
from patchloop.memory import d112_retrieval_readiness_probe as d112
from patchloop.util import canonical_json, sha256_text

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def exact_input() -> tuple[dict[str, Any], dict[str, Any], Path, dict[str, str]]:
    return d112._input_state(ROOT.resolve())


def _fake_implementation_bindings() -> list[dict[str, Any]]:
    return [
        {
            "path": path.as_posix(),
            "file_bytes": index + 1,
            "file_sha256": f"sha256:{index + 1:064x}",
        }
        for index, path in enumerate(d112.D112_IMPLEMENTATION_PATHS)
    ]


def _install_fake_input(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    exact_input: tuple[dict[str, Any], dict[str, Any], Path, dict[str, str]],
) -> tuple[dict[str, Any], dict[str, Any], Path, dict[str, str]]:
    input_state, context, _snapshot, dependencies = exact_input
    fake_state = copy.deepcopy(input_state)
    implementation = _fake_implementation_bindings()
    fake_state["state"]["implementation_files"] = implementation
    fake_state["fingerprint"] = sha256_text(canonical_json(fake_state["state"]))
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()

    def fake_input_state(_repository: Path):
        return copy.deepcopy(fake_state), context, snapshot, dict(dependencies)

    monkeypatch.setattr(d112, "_input_state", fake_input_state)
    monkeypatch.setattr(
        d112,
        "_implementation_bindings",
        lambda _repository: copy.deepcopy(implementation),
    )
    return fake_state, context, snapshot, dependencies


def _valid_fake_vectors(context: dict[str, Any]) -> np.ndarray:
    first = context["index"]["embeddings"][d111.EXPECTED_MEMORY_IDS[0]]
    second = context["index"]["embeddings"][d111.EXPECTED_MEMORY_IDS[1]]
    return np.asarray([first, second, first], dtype=np.float32)


def test_d112_receipt_binds_exact_approval_and_keeps_later_actions_closed(
    exact_input: tuple[dict[str, Any], dict[str, Any], Path, dict[str, str]],
) -> None:
    input_state, context, _snapshot, _dependencies = exact_input
    receipt = d112.build_d112_probe_receipt(
        execution_claimed_at="2026-08-06T17:00:00Z",
        input_state=input_state,
        context=context,
    )
    body = receipt["semantic_body"]
    scope = body["authorized_scope"]

    assert body["d111_candidate"]["candidate_id"] == d112.EXPECTED_CANDIDATE_ID
    assert body["d111_candidate"]["semantic_body_hash"] == d112.EXPECTED_CANDIDATE_BODY_SHA
    assert body["d111_candidate"]["file_sha256"] == d112.EXPECTED_CANDIDATE_FILE_SHA
    assert body["authorized_action_hash"] == d112.EXPECTED_ACTION_HASH
    assert scope["maximum_executions"] == 1
    assert scope["local_embedding_model_load_count"] == 1
    assert scope["local_batch_encode_call_count"] == 1
    assert scope["local_batch_query_row_count"] == 3
    assert scope["automatic_retry_authorized"] is False
    assert scope["legacy_retrieve_memory_authorized"] is False
    assert scope["runtime_memory_injection_authorized"] is False
    assert scope["agent_run_authorized"] is False
    assert scope["score_policy_change_authorized"] is False
    assert scope["retrieval_experiment_authorized"] is False
    assert scope["core_campaign_authorized"] is False
    assert body["reviewer_identity_authenticated"] is False
    assert body["cryptographic_signature_verified"] is False


def test_d112_scoring_records_all_components_rank_and_phase_control(
    exact_input: tuple[dict[str, Any], dict[str, Any], Path, dict[str, str]],
) -> None:
    _input_state, context, _snapshot, _dependencies = exact_input
    vectors = _valid_fake_vectors(context)
    rows, descriptors = d112._validate_query_vectors(vectors)
    result = d112._score_diagnostic(
        query_vectors=rows,
        queries=context["queries"],
        index=context["index"],
    )

    assert result["score_row_count"] == 9
    assert len(result["probe_results"]) == 3
    assert descriptors[0]["float32_sha256"] == descriptors[2]["float32_sha256"]
    assert all(row["runtime_selection_executed"] is False for row in result["probe_results"])
    assert all(row["memory_text_returned"] is False for row in result["probe_results"])
    for probe in result["probe_results"]:
        assert [row["rank"] for row in probe["candidates"]] == [1, 2, 3]
        assert probe["candidates"] == sorted(
            probe["candidates"], key=lambda row: (-row["final_score"], row["memory_id"])
        )
        for candidate in probe["candidates"]:
            assert set(candidate["components"]) == set(d111.SCORE_WEIGHTS)
            assert candidate["final_score"] == sum(
                candidate["weighted_components"][key] for key in d111.SCORE_WEIGHTS
            )
            assert candidate["diagnostic_threshold_pass"] == (
                candidate["final_score"] >= d111.SELECTIVE_THRESHOLD
            )
    assert all(
        delta == pytest.approx(0.15, abs=1e-12)
        for delta in result["moto_phase_control_score_deltas"].values()
    )


@pytest.mark.parametrize("kind", ["dtype", "shape", "nan", "norm"])
def test_d112_invalid_query_vectors_fail_closed(
    kind: str,
    exact_input: tuple[dict[str, Any], dict[str, Any], Path, dict[str, str]],
) -> None:
    _input_state, context, _snapshot, _dependencies = exact_input
    vectors = _valid_fake_vectors(context)
    if kind == "dtype":
        vectors = vectors.astype(np.float64)
    elif kind == "shape":
        vectors = vectors[:2]
    elif kind == "nan":
        vectors[0, 0] = np.nan
    else:
        vectors[0] = 0

    with pytest.raises(d112.D112ProbeError, match="query embedding|query vector"):
        d112._validate_query_vectors(vectors)


def test_d112_fake_success_is_one_use_and_never_calls_runtime_retrieval(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    exact_input: tuple[dict[str, Any], dict[str, Any], Path, dict[str, str]],
) -> None:
    _state, context, snapshot, _dependencies = _install_fake_input(
        monkeypatch, tmp_path, exact_input
    )
    calls = {"load": 0, "encode": 0, "retrieval": 0}

    def forbidden(*_args, **_kwargs):
        calls["retrieval"] += 1
        raise AssertionError("D-112 crossed an unapproved runtime boundary")

    monkeypatch.setattr("patchloop.memory.retrieval.retrieve_memory", forbidden)
    monkeypatch.setattr("patchloop.memory.retrieval._query_embedding", forbidden)
    monkeypatch.setattr("patchloop.memory.retrieval._render_raw_trace", forbidden)

    def loader(path: Path, config: dict[str, Any]) -> object:
        calls["load"] += 1
        assert path == snapshot
        assert config["device"] == "cpu"
        assert config["local_files_only"] is True
        assert config["trust_remote_code"] is False
        return object()

    def encoder(_model: object, texts: list[str], config: dict[str, Any]) -> np.ndarray:
        calls["encode"] += 1
        assert texts == [row["query"] for row in context["queries"]]
        assert config["normalize_embeddings"] is True
        return _valid_fake_vectors(context)

    result = d112.execute_d112_scoring_diagnostic(
        repository=tmp_path,
        model_loader=loader,
        batch_encoder=encoder,
    )

    assert result["ok"] is True
    assert result["score_row_count"] == 9
    assert calls == {"load": 1, "encode": 1, "retrieval": 0}
    with pytest.raises(d112.D112ProbeError, match="already consumed"):
        d112.execute_d112_scoring_diagnostic(
            repository=tmp_path,
            model_loader=loader,
            batch_encoder=encoder,
        )
    assert calls == {"load": 1, "encode": 1, "retrieval": 0}


def test_d112_failure_after_claim_stays_consumed_without_gate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    exact_input: tuple[dict[str, Any], dict[str, Any], Path, dict[str, str]],
) -> None:
    _state, _context, _snapshot, _dependencies = _install_fake_input(
        monkeypatch, tmp_path, exact_input
    )
    loads = 0

    def loader(_path: Path, _config: dict[str, Any]) -> object:
        nonlocal loads
        loads += 1
        raise RuntimeError("controlled local load failure")

    with pytest.raises(d112.D112ProbeError, match="failed after claim"):
        d112.execute_d112_scoring_diagnostic(repository=tmp_path, model_loader=loader)

    assert (tmp_path / d112.DEFAULT_PROBE_RECEIPT_PATH).is_file()
    assert not (tmp_path / d112.DEFAULT_COMPLETION_GATE_PATH).exists()
    with pytest.raises(d112.D112ProbeError, match="already consumed"):
        d112.execute_d112_scoring_diagnostic(repository=tmp_path, model_loader=loader)
    assert loads == 1


def test_d112_rehashed_score_tamper_fails_portable_validation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    exact_input: tuple[dict[str, Any], dict[str, Any], Path, dict[str, str]],
) -> None:
    _state, context, _snapshot, _dependencies = _install_fake_input(
        monkeypatch, tmp_path, exact_input
    )
    d112.execute_d112_scoring_diagnostic(
        repository=tmp_path,
        model_loader=lambda _path, _config: object(),
        batch_encoder=lambda _model, _texts, _config: _valid_fake_vectors(context),
    )
    gate_path = tmp_path / d112.DEFAULT_COMPLETION_GATE_PATH
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    gate["semantic_body"]["diagnostic_scoring"]["probe_results"][0]["candidates"][0][
        "final_score"
    ] += 0.01
    body_hash = sha256_text(canonical_json(gate["semantic_body"]))
    gate["semantic_body_hash"] = body_hash
    gate["gate_id"] = f"d112_{body_hash.removeprefix('sha256:')}"
    gate_path.write_bytes(d112._pretty_json(gate))

    with pytest.raises(d112.D112ProbeError, match="recorded diagnostic scores"):
        d112.validate_d112_completion_gate(repository=tmp_path)


def test_d112_checked_in_execution_is_exact_and_later_authority_stays_closed() -> None:
    result = d112.validate_d112_completion_gate(
        repository=ROOT,
        verify_current_implementation=True,
        verify_current_inputs=True,
    )

    assert result["ok"] is True
    assert result["score_row_count"] == 9
    assert result["retrieval_ready"] is False
    assert result["retrieval_experiment_authorized"] is False
    assert result["runtime_memory_injection_count"] == 0
    assert result["score_policy_correction_authorized"] is False
    assert result["core_campaign_unlocked"] is False
    assert result["analysis_ready"] is False
    assert result["provider_calls_made"] == 0
    assert result["evaluator_calls_made"] == 0
    assert result["added_model_cost_usd"] == 0


def test_d112_checked_in_validator_never_loads_or_encodes_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("portable validation attempted another model execution")

    monkeypatch.setattr(d112, "_default_model_loader", forbidden)
    monkeypatch.setattr(d112, "_default_batch_encoder", forbidden)
    result = d112.validate_d112_completion_gate(repository=ROOT)
    assert result["ok"] is True
