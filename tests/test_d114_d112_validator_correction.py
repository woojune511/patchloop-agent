from __future__ import annotations

import builtins
import copy
import json
import shutil
import socket
from pathlib import Path
from typing import Any

import pytest

from patchloop.memory import d114_d112_validator_correction as d114
from patchloop.util import canonical_json, sha256_text

REPOSITORY = Path(__file__).resolve().parents[1]


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _d112_pair() -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        _json(REPOSITORY / d114.DEFAULT_D112_RECEIPT_PATH),
        _json(REPOSITORY / d114.DEFAULT_D112_GATE_PATH),
    )


def _rehash(payload: dict[str, Any], *, id_field: str, prefix: str) -> None:
    body_hash = sha256_text(canonical_json(payload["semantic_body"]))
    payload["semantic_body_hash"] = body_hash
    payload[id_field] = prefix + body_hash.removeprefix("sha256:")


def _set_nested(payload: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    selected: dict[str, Any] = payload
    for key in path[:-1]:
        selected = selected[key]
    selected[path[-1]] = value


def _copy(relative: str | Path, destination: Path) -> None:
    source = REPOSITORY / relative
    target = destination / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _copy_minimal_sealed_repository(destination: Path) -> None:
    for relative in (
        d114.DEFAULT_D112_RECEIPT_PATH,
        d114.DEFAULT_D112_GATE_PATH,
        d114.DEFAULT_D110_INDEX_PATH,
        d114.DEFAULT_D110_MARKER_PATH,
        *(Path(spec["path"]) for spec in d114.PUBLIC_TASK_SPECS.values()),
    ):
        _copy(relative, destination)


def _copy_materialization_repository(destination: Path) -> None:
    paths = {
        d114.DEFAULT_D113_PREFLIGHT_PATH,
        d114.DEFAULT_D113_CANDIDATE_PATH,
        d114.DEFAULT_D113_SOURCE_GATE_PATH,
        *(Path(spec["path"]) for spec in d114.PROTECTED_FILE_SPECS),
        *(Path(spec["path"]) for spec in d114.PUBLIC_TASK_SPECS.values()),
        *d114.D114_IMPLEMENTATION_PATHS,
    }
    for relative in sorted(paths, key=lambda value: value.as_posix()):
        _copy(relative, destination)


def test_exact_checked_in_d112_pair_passes_sealed_historical_validation() -> None:
    result = d114.validate_d112_history(
        repository=REPOSITORY,
        mode=d114.ValidationMode.SEALED_HISTORICAL,
    )

    assert result["validation_mode"] == "sealed-historical"
    assert result["sealed_historical_validation_passed"] is True
    assert result["current_input_validation_executed"] is False
    assert result["d112_receipt_expected_payload_full_equality"] is True
    assert result["d112_gate_expected_payload_full_equality"] is True
    assert result["approval_execution_completion_chronology_valid"] is True
    assert result["portable_score_replay_exact"] is True
    assert result["score_row_count"] == 9
    assert result["all_diagnostic_no_match"] is True


@pytest.mark.parametrize(
    ("target", "path"),
    [
        ("receipt", ("unknown_root",)),
        ("receipt", ("semantic_body", "unknown_body")),
        ("receipt", ("semantic_body", "claim_semantics", "unknown_claim")),
        ("gate", ("unknown_root",)),
        ("gate", ("semantic_body", "unknown_body")),
        ("gate", ("semantic_body", "qualification", "unknown_qualification")),
        ("gate", ("semantic_body", "evidence_boundary", "unknown_boundary")),
        ("gate", ("semantic_body", "authority", "unknown_authority")),
    ],
)
def test_unknown_root_body_claim_and_gate_fields_fail(
    target: str, path: tuple[str, ...]
) -> None:
    receipt, gate = _d112_pair()
    selected = receipt if target == "receipt" else gate
    _set_nested(selected, path, True)
    if path[0] == "semantic_body":
        _rehash(
            selected,
            id_field="receipt_id" if target == "receipt" else "gate_id",
            prefix="d112probereceipt_" if target == "receipt" else "d112_",
        )

    with pytest.raises(d114.D114CorrectionError, match="key set mismatch"):
        d114.validate_d112_history(
            repository=REPOSITORY,
            mode="sealed-historical",
            _receipt_payload=receipt,
            _gate_payload=gate,
        )


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("semantic_body", "milestone"), "D-112-mutated"),
        (("semantic_body", "evidence_kind"), "mutated-kind"),
        (("semantic_body", "approval_reference_mode"), "mutated-mode"),
        (("semantic_body", "approver_kind"), "automation"),
        (("semantic_body", "approver_label"), "mutated-reviewer"),
        (
            (
                "semantic_body",
                "claim_semantics",
                "receipt_is_one_use_consumption_marker",
            ),
            False,
        ),
        (
            ("semantic_body", "claim_semantics", "completion_gate_required_for_success"),
            False,
        ),
    ],
)
def test_each_previously_unchecked_receipt_field_flip_fails(
    path: tuple[str, ...], replacement: Any
) -> None:
    receipt, gate = _d112_pair()
    _set_nested(receipt, path, replacement)
    _rehash(receipt, id_field="receipt_id", prefix="d112probereceipt_")

    with pytest.raises(d114.D114CorrectionError, match="full expected historical payload"):
        d114.validate_d112_history(
            repository=REPOSITORY,
            mode="sealed-historical",
            _receipt_payload=receipt,
            _gate_payload=gate,
        )


def test_approval_after_execution_fails_before_full_payload_comparison() -> None:
    receipt, gate = _d112_pair()
    receipt["semantic_body"]["approval_recorded_at"] = "2026-08-06T17:16:21Z"
    _rehash(receipt, id_field="receipt_id", prefix="d112probereceipt_")

    with pytest.raises(d114.D114CorrectionError, match="approval occurs after execution"):
        d114.validate_d112_history(
            repository=REPOSITORY,
            mode="sealed-historical",
            _receipt_payload=receipt,
            _gate_payload=gate,
        )


def test_execution_after_completion_fails_before_full_payload_comparison() -> None:
    receipt, gate = _d112_pair()
    receipt["semantic_body"]["execution_claimed_at"] = "2026-08-06T17:18:34Z"
    _rehash(receipt, id_field="receipt_id", prefix="d112probereceipt_")

    with pytest.raises(d114.D114CorrectionError, match="execution occurs after completion"):
        d114.validate_d112_history(
            repository=REPOSITORY,
            mode="sealed-historical",
            _receipt_payload=receipt,
            _gate_payload=gate,
        )


def test_fully_rehashed_paired_receipt_and_gate_tamper_fails() -> None:
    receipt, gate = _d112_pair()
    receipt["semantic_body"]["claim_semantics"][
        "receipt_is_one_use_consumption_marker"
    ] = False
    _rehash(receipt, id_field="receipt_id", prefix="d112probereceipt_")
    gate["semantic_body"]["probe_receipt"] = d114._receipt_binding_for_payload(receipt)
    _rehash(gate, id_field="gate_id", prefix="d112_")

    with pytest.raises(d114.D114CorrectionError, match="full expected historical payload"):
        d114.validate_d112_history(
            repository=REPOSITORY,
            mode="sealed-historical",
            _receipt_payload=receipt,
            _gate_payload=gate,
        )


def test_sealed_historical_mode_does_not_invoke_current_input_loader() -> None:
    calls = 0

    def forbidden_loader(_repository: Path) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise AssertionError("sealed mode called the current-input loader")

    result = d114.validate_d112_history(
        repository=REPOSITORY,
        mode=d114.ValidationMode.SEALED_HISTORICAL,
        current_input_loader=forbidden_loader,
    )

    assert calls == 0
    assert result["snapshot_rehydration_performed"] is False
    assert result["installed_embedding_dependency_check_performed"] is False


def test_current_input_mode_is_explicit_and_compares_the_complete_input() -> None:
    receipt, _ = _d112_pair()
    expected = copy.deepcopy(receipt["semantic_body"]["pre_execution_input"])
    calls = 0

    def current_loader(_repository: Path) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return expected

    result = d114.validate_d112_history(
        repository=REPOSITORY,
        mode=d114.ValidationMode.CURRENT_INPUT,
        current_input_loader=current_loader,
    )

    assert calls == 1
    assert result["validation_mode"] == "current-input"
    assert result["current_input_validation_executed"] is True
    assert result["current_input_validation_passed"] is True
    assert result["current_input_loader_kind"] == "injected-not-audited"
    assert result["snapshot_rehydration_performed"] is None
    assert result["installed_embedding_dependency_check_performed"] is None
    assert result["model_load_count"] is None


def test_current_input_drift_and_legacy_skip_style_mode_fail() -> None:
    receipt, _ = _d112_pair()
    drifted = copy.deepcopy(receipt["semantic_body"]["pre_execution_input"])
    drifted["fingerprint"] = "sha256:" + "0" * 64

    with pytest.raises(d114.D114CorrectionError, match="current D-112 input differs"):
        d114.validate_d112_history(
            repository=REPOSITORY,
            mode="current-input",
            current_input_loader=lambda _repository: drifted,
        )
    with pytest.raises(d114.D114CorrectionError, match="validation mode is invalid"):
        d114.validate_d112_history(repository=REPOSITORY, mode="skip-current")


def test_minimal_portable_repository_needs_no_snapshot_model_or_dependency_versions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _copy_minimal_sealed_repository(tmp_path)
    assert not (tmp_path / ".patchloop").exists()
    original_import = builtins.__import__
    forbidden = (
        "patchloop.memory.d112",
        "patchloop.memory.d111",
        "patchloop.memory.d106",
        "sentence_transformers",
        "transformers",
        "torch",
        "numpy",
        "importlib.metadata",
    )

    def guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.startswith(forbidden):
            raise AssertionError(f"portable mode imported forbidden module {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    result = d114.validate_d112_history(
        repository=tmp_path,
        mode=d114.ValidationMode.SEALED_HISTORICAL,
        current_input_loader=lambda _repository: (_ for _ in ()).throw(AssertionError()),
    )

    assert result["portable_score_replay_exact"] is True
    assert result["model_load_count"] == 0
    assert result["model_encode_count"] == 0
    assert result["snapshot_rehydration_performed"] is False
    assert result["installed_embedding_dependency_check_performed"] is False


def test_runtime_calls_remain_zero_and_claims_stay_narrow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from patchloop.memory import retrieval

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("sealed validation crossed a forbidden runtime boundary")

    monkeypatch.setattr(retrieval, "retrieve_memory", forbidden)
    monkeypatch.setattr(retrieval, "_query_embedding", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    result = d114.validate_d112_history(repository=REPOSITORY, mode="sealed-historical")

    assert result["retrieval_calls"] == 0
    assert result["runtime_memory_injection_count"] == 0
    assert result["agent_runs"] == 0
    assert result["provider_calls_made"] == 0
    assert result["evaluator_calls_made"] == 0
    assert result["network_claim"] == "source-path-and-self-attestation-only"
    assert result["os_socket_block_verified"] is False
    assert result["query_embedding_semantic_fidelity_recomputed"] is False


def test_vector_validation_rejects_json_booleans_instead_of_coercing_them() -> None:
    with pytest.raises(d114.D114CorrectionError, match="non-numeric JSON value"):
        d114._validate_vector([True] * d114.VECTOR_DIMENSION, label="tampered vector")


def test_d112_and_index_bytes_remain_unchanged_across_read_only_reruns() -> None:
    before = {
        spec["path"]: (REPOSITORY / spec["path"]).read_bytes()
        for spec in d114.PROTECTED_FILE_SPECS
    }
    first = d114.validate_d112_history(repository=REPOSITORY, mode="sealed-historical")
    second = d114.validate_d112_history(repository=REPOSITORY, mode="sealed-historical")
    after = {
        spec["path"]: (REPOSITORY / spec["path"]).read_bytes()
        for spec in d114.PROTECTED_FILE_SPECS
    }

    assert first == second
    assert before == after


@pytest.mark.parametrize("preexisting", ["receipt", "gate"])
def test_preexisting_output_fails_before_creating_the_other_output(
    tmp_path: Path, preexisting: str
) -> None:
    _copy_materialization_repository(tmp_path)
    receipt_path = tmp_path / d114.DEFAULT_APPROVAL_RECEIPT_PATH
    gate_path = (tmp_path / d114.DEFAULT_COMPLETION_GATE_PATH).resolve()
    selected = receipt_path if preexisting == "receipt" else gate_path
    selected.parent.mkdir(parents=True, exist_ok=True)
    selected.write_bytes(b"existing")

    with pytest.raises(d114.D114CorrectionError):
        d114.execute_d114_correction(repository=tmp_path)

    assert selected.read_bytes() == b"existing"
    other = gate_path if preexisting == "receipt" else receipt_path
    assert not other.exists()


def test_gate_collision_after_receipt_commit_is_consumed_without_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _copy_materialization_repository(tmp_path)
    original_write = d114._write_new_fsynced
    gate_path = tmp_path / d114.DEFAULT_COMPLETION_GATE_PATH

    def collide_on_gate(path: Path, content: bytes) -> None:
        if path == gate_path:
            path.write_bytes(b"gate-race")
        original_write(path, content)

    monkeypatch.setattr(d114, "_write_new_fsynced", collide_on_gate)
    with pytest.raises(d114.D114CorrectionError, match="already consumed"):
        d114.execute_d114_correction(repository=tmp_path)

    receipt_path = tmp_path / d114.DEFAULT_APPROVAL_RECEIPT_PATH
    assert receipt_path.exists()
    assert gate_path.read_bytes() == b"gate-race"
    with pytest.raises(d114.D114CorrectionError, match="already consumed"):
        d114.execute_d114_correction(repository=tmp_path)


def test_receipt_exclusive_create_race_does_not_create_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _copy_materialization_repository(tmp_path)
    original_write = d114._write_new_fsynced
    receipt_path = (tmp_path / d114.DEFAULT_APPROVAL_RECEIPT_PATH).resolve()
    gate_path = tmp_path / d114.DEFAULT_COMPLETION_GATE_PATH

    def collide_on_receipt(path: Path, content: bytes) -> None:
        if path == receipt_path:
            path.write_bytes(b"receipt-race")
        original_write(path, content)

    monkeypatch.setattr(d114, "_write_new_fsynced", collide_on_receipt)
    with pytest.raises(d114.D114CorrectionError, match="already consumed"):
        d114.execute_d114_correction(repository=tmp_path)

    assert receipt_path.read_bytes() == b"receipt-race"
    assert not gate_path.exists()


def test_implementation_change_after_claim_leaves_consumed_partial_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _copy_materialization_repository(tmp_path)
    original_validate = d114.validate_d112_history
    script_path = tmp_path / d114.D114_IMPLEMENTATION_PATHS[1]

    def validate_then_mutate(**kwargs: Any) -> dict[str, Any]:
        result = original_validate(**kwargs)
        script_path.write_bytes(script_path.read_bytes() + b"\n")
        return result

    monkeypatch.setattr(d114, "validate_d112_history", validate_then_mutate)
    with pytest.raises(d114.D114CorrectionError, match="implementation changed"):
        d114.execute_d114_correction(repository=tmp_path)

    assert (tmp_path / d114.DEFAULT_APPROVAL_RECEIPT_PATH).exists()
    assert not (tmp_path / d114.DEFAULT_COMPLETION_GATE_PATH).exists()
    with pytest.raises(d114.D114CorrectionError, match="already consumed"):
        d114.execute_d114_correction(repository=tmp_path)

def test_one_use_materialization_and_repeatable_read_only_validation(tmp_path: Path) -> None:
    _copy_materialization_repository(tmp_path)

    gate = d114.execute_d114_correction(repository=tmp_path)
    first = d114.validate_d114_correction_evidence(repository=tmp_path)
    second = d114.validate_d114_correction_evidence(repository=tmp_path)

    assert gate["gate_id"] == first["gate_id"] == second["gate_id"]
    body = gate["semantic_body"]
    assert body["authority"]["append_only_successor_validator_implemented"] is True
    assert body["authority"]["original_d112_validator_modified"] is False
    assert body["authority"]["score_policy_correction_authorized"] is False
    assert body["authority"]["retrieval_ready"] is False
    assert body["authority"]["runtime_memory_injection_count"] == 0
    assert body["authority"]["agent_runs"] == 0
    assert body["authority"]["core_campaign_unlocked"] is False
    assert body["evidence_boundary"]["os_socket_block_verified"] is False
    assert body["evidence_boundary"]["global_one_use_or_cross_clone_exclusion_proved"] is False
    with pytest.raises(d114.D114CorrectionError, match="already consumed"):
        d114.execute_d114_correction(repository=tmp_path)


@pytest.mark.parametrize("artifact", ["receipt", "gate"])
def test_noncanonical_d114_artifact_bytes_are_rejected(
    tmp_path: Path, artifact: str
) -> None:
    _copy_materialization_repository(tmp_path)
    d114.execute_d114_correction(repository=tmp_path)
    relative = (
        d114.DEFAULT_APPROVAL_RECEIPT_PATH
        if artifact == "receipt"
        else d114.DEFAULT_COMPLETION_GATE_PATH
    )
    path = tmp_path / relative
    payload = _json(path)
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")

    with pytest.raises(d114.D114CorrectionError, match=f"{artifact} is not the exact canonical"):
        d114.validate_d114_correction_evidence(repository=tmp_path)


def test_checked_in_d114_evidence_validates_after_materialization() -> None:
    receipt_path = REPOSITORY / d114.DEFAULT_APPROVAL_RECEIPT_PATH
    gate_path = REPOSITORY / d114.DEFAULT_COMPLETION_GATE_PATH
    if not receipt_path.exists() and not gate_path.exists():
        pytest.skip("D-114 one-use correction evidence has not been materialized yet")
    if receipt_path.exists() != gate_path.exists():
        pytest.fail("partial D-114 evidence: receipt and gate existence differ")

    result = d114.validate_d114_correction_evidence(repository=REPOSITORY)

    assert result["sealed_historical_validation"]["portable_score_replay_exact"] is True
    assert result["sealed_historical_validation"]["score_row_count"] == 9
