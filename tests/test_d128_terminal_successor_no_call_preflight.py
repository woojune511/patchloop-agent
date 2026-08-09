from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from patchloop.evals import d128_terminal_successor_no_call_preflight as d128
from patchloop.util import canonical_json, sha256_bytes

TIMESTAMP = "2026-08-09T00:00:00Z"
SOURCE_COMMIT = "a" * 40
SOURCE_TREE = "b" * 40
RECEIPT_COMMIT = "c" * 40
RECEIPT_TREE = "d" * 40
SECRET = "d128-test-secret-must-never-be-rendered"


def _source_identity() -> dict[str, Any]:
    return {
        "commit": SOURCE_COMMIT,
        "tree": SOURCE_TREE,
        "parents": [d128.D128_EVIDENCE_COMMIT],
        "branch": "codex/d128-test",
        "source_paths_and_index_clean": True,
        "git_cli_observation": {},
    }


def _ready_docker_observation(
    *,
    command_count: int = 6,
    pull_count: int = 0,
) -> dict[str, Any]:
    return {
        "passed": True,
        "daemon_start_attempted": False,
        "daemon_start_count": 0,
        "container_create_start_run_exec_count": 0,
        "docker_workload_call_count": 0,
        "docker_cli_command_count": command_count,
        "read_only_daemon_or_image_call_count": 6,
        "image_pull_call_count": pull_count,
        "image_store_mutation_count": pull_count,
        "exact_authorized_images": list(d128.DOCKER_IMAGE_REFS),
        "observed_blockers": [],
    }


def _blocked_docker_observation() -> dict[str, Any]:
    return {
        "passed": False,
        "daemon_start_attempted": False,
        "daemon_start_count": 0,
        "container_create_start_run_exec_count": 0,
        "docker_workload_call_count": 0,
        "docker_cli_command_count": 3,
        "read_only_daemon_or_image_call_count": 3,
        "image_pull_call_count": 0,
        "image_store_mutation_count": 0,
        "exact_authorized_images": list(d128.DOCKER_IMAGE_REFS),
        "observed_blockers": [d128.docker_remediation.DAEMON_UNAVAILABLE_BLOCKER],
    }


def _configure_repository(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    (root / d128.RECEIPT_PATH.parent).mkdir(parents=True, exist_ok=True)
    source = _source_identity()
    modules = [
        {
            "role": "d128-orchestrator",
            "path": "patchloop/evals/d128_terminal_successor_no_call_preflight.py",
            "file_bytes": 1,
            "file_sha256": "sha256:" + "1" * 64,
            "source_blob_oid": "1" * 40,
        }
    ]
    cli = {
        "file_name": "docker.exe",
        "file_bytes": d128.DOCKER_CLI_BYTES,
        "file_sha256": d128.DOCKER_CLI_SHA256,
        "approved_version": d128.DOCKER_CLI_VERSION,
        "version_bound_by_exact_approved_file_identity": True,
        "version_process_observation_performed": False,
    }
    sdk = {
        "passed": True,
        "network_call_count": 0,
        "synthetic_endpoint_probe": {
            "passed": True,
            "transport_attempt_count": 0,
        },
    }
    snapshot = {
        "observation": {"passed": True},
        "docker_cli_command_count": 3,
    }
    pricing = {
        "observed_at": TIMESTAMP,
        "public_get_request_count": 1,
        "decoded_entity_bytes": 1,
        "decoded_entity_sha256": "sha256:" + "2" * 64,
    }
    state: dict[str, Any] = {
        "source": source,
        "modules": modules,
        "cli": cli,
        "sdk": sdk,
        "snapshot": snapshot,
        "snapshot_queue": [],
        "docker": _ready_docker_observation(),
        "pricing": pricing,
        "events": [],
        "calls": {"docker": 0, "pricing": 0, "snapshot": 0},
    }

    monkeypatch.setattr(d128, "_now", lambda: TIMESTAMP)
    monkeypatch.setattr(
        d128,
        "_source_identity",
        lambda _root, *, allowed_outputs=(): copy.deepcopy(state["source"]),
    )
    monkeypatch.setattr(d128, "_validate_source_commit_topology", lambda *_a, **_k: None)
    monkeypatch.setattr(
        d128,
        "_loaded_module_bindings",
        lambda _root, *, source_commit: copy.deepcopy(state["modules"]),
    )
    monkeypatch.setattr(d128, "_validate_loaded_module_bindings", lambda *_a, **_k: None)
    monkeypatch.setattr(d128, "_validate_receipt_commit_identity", lambda *_a, **_k: None)
    monkeypatch.setattr(
        d128,
        "_offline_gate_binding",
        lambda _root: {
            "path": d128.OFFLINE_GATE_PATH.as_posix(),
            "schema_version": d128.offline.SCHEMA_VERSION,
            "gate_id": d128.D128_GATE_ID,
            "semantic_body_hash": d128.D128_BODY_SHA256,
            "file_bytes": d128.D128_FILE_BYTES,
            "file_sha256": d128.D128_FILE_SHA256,
            "status": d128.offline.STATUS,
            "recorded_at": TIMESTAMP,
            "evidence_commit": {
                "commit": d128.D128_EVIDENCE_COMMIT,
                "tree": d128.D128_EVIDENCE_TREE,
                "parents": list(d128.D128_EVIDENCE_PARENTS),
                "gate_blob_oid": d128.D128_GATE_BLOB_OID,
                "gate_bytes_match_commit": True,
            },
            "artifact_mutated": False,
        },
    )

    def receipt_commit_identity(
        selected_root: Path,
        *,
        source: dict[str, Any],
        allowed_outputs: tuple[Path, ...],
    ) -> dict[str, Any]:
        del source, allowed_outputs
        return {
            "commit": RECEIPT_COMMIT,
            "tree": RECEIPT_TREE,
            "parents": [SOURCE_COMMIT],
            "branch": "codex/d128-test",
            "receipt_binding": d128._artifact_binding(selected_root, d128.RECEIPT_PATH),
            "receipt_only_child_of_source": True,
            "source_module_bytes_unchanged": True,
        }

    monkeypatch.setattr(d128, "_current_receipt_commit_identity", receipt_commit_identity)
    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    for name in d128.FORBIDDEN_ROUTING_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    for name in d128.FORBIDDEN_PYTHON_ROUTING_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(d128.d127, "_approved_docker_cli_identity", lambda: copy.deepcopy(cli))
    monkeypatch.setattr(d128.d127, "_model_factory_contract", lambda _root: {"passed": True})
    monkeypatch.setattr(d128.importlib.metadata, "version", lambda _name: "1.2.3")
    monkeypatch.setattr(d128.d127, "_locked_openai_version", lambda _root: "1.2.3")
    monkeypatch.setattr(
        d128.sys,
        "executable",
        str(root / ".venv" / "Scripts" / "python.exe"),
    )
    monkeypatch.setattr(d128, "_sdk_observation", lambda *_a, **_k: copy.deepcopy(state["sdk"]))
    monkeypatch.setattr(d128.d127, "_validate_sdk_observation", lambda *_a, **_k: None)
    monkeypatch.setattr(
        d128.d127,
        "_require_current_sdk_matches_artifact",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        d128.docker_remediation,
        "validate_docker_no_start_remediation_observation",
        lambda value: value,
    )
    monkeypatch.setattr(
        d128.docker_remediation,
        "validate_docker_readiness_snapshot",
        lambda value: value,
    )
    monkeypatch.setattr(
        d128.pricing_capture,
        "validate_official_pricing_evidence",
        lambda value: value,
    )
    monkeypatch.setattr(
        d128.docker_remediation,
        "approved_cli_binding",
        lambda: copy.deepcopy(state["cli"]),
    )

    def remediate() -> dict[str, Any]:
        state["calls"]["docker"] += 1
        state["events"].append("docker")
        assert (root / d128.DOCKER_ATTEMPT_PATH).is_file()
        assert not (root / d128.DOCKER_PATH).exists()
        return copy.deepcopy(state["docker"])

    def capture() -> dict[str, Any]:
        state["calls"]["pricing"] += 1
        state["events"].append("pricing")
        assert (root / d128.DOCKER_PATH).is_file()
        assert (root / d128.PRICING_ATTEMPT_PATH).is_file()
        assert not (root / d128.PRICING_PATH).exists()
        return copy.deepcopy(state["pricing"])

    def observe() -> dict[str, Any]:
        state["calls"]["snapshot"] += 1
        state["events"].append("snapshot")
        assert (root / d128.PRICING_PATH).is_file()
        assert (root / d128.PREFLIGHT_ATTEMPT_PATH).is_file()
        assert not (root / d128.PREFLIGHT_PATH).exists()
        queue = state["snapshot_queue"]
        value = queue.pop(0) if queue else state["snapshot"]
        return copy.deepcopy(value)

    monkeypatch.setattr(
        d128.docker_remediation,
        "remediate_already_running_docker_environment",
        remediate,
    )
    monkeypatch.setattr(d128.docker_remediation, "observe_docker_readiness", observe)
    monkeypatch.setattr(d128.pricing_capture, "capture_official_pricing_evidence", capture)
    return state


def _create_receipt(root: Path) -> dict[str, Any]:
    return d128.create_d128_approval_receipt(repository=root)


def test_receipt_binds_exact_gate_commit_source_scope_and_manual_attestation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _configure_repository(tmp_path, monkeypatch)

    first = _create_receipt(tmp_path)
    raw = (tmp_path / d128.RECEIPT_PATH).read_bytes()
    payload = json.loads(raw)
    body = payload["semantic_body"]
    second = _create_receipt(tmp_path)

    assert first == second
    assert raw == (tmp_path / d128.RECEIPT_PATH).read_bytes() == d128._pretty_bytes(payload)
    assert body["predecessor_binding"]["gate_id"] == d128.D128_GATE_ID
    assert body["predecessor_binding"]["semantic_body_hash"] == d128.D128_BODY_SHA256
    assert body["predecessor_binding"]["file_sha256"] == d128.D128_FILE_SHA256
    assert body["predecessor_binding"]["file_bytes"] == d128.D128_FILE_BYTES
    assert body["predecessor_binding"]["evidence_commit"] == {
        "commit": d128.D128_EVIDENCE_COMMIT,
        "tree": d128.D128_EVIDENCE_TREE,
        "parents": list(d128.D128_EVIDENCE_PARENTS),
        "gate_blob_oid": d128.D128_GATE_BLOB_OID,
        "gate_bytes_match_commit": True,
    }
    assert body["source_identity"] == state["source"]
    assert body["loaded_module_bindings"] == state["modules"]
    assert body["approval"]["approved_scope"] == list(d128.APPROVED_SCOPE)
    assert body["approval"]["explicitly_not_authorized"] == list(d128.NOT_AUTHORIZED)
    assert body["manual_prerequisite_attestation"] == d128._manual_attestation()
    assert first["external_activity_started"] is False
    assert SECRET not in raw.decode("utf-8")


def test_receipt_collision_and_orphaned_downstream_are_never_overwritten(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collision_root = tmp_path / "collision"
    _configure_repository(collision_root, monkeypatch)
    collision = b"unapproved-existing-receipt"
    (collision_root / d128.RECEIPT_PATH).write_bytes(collision)

    with pytest.raises(d128.D128PreflightError):
        _create_receipt(collision_root)
    assert (collision_root / d128.RECEIPT_PATH).read_bytes() == collision

    orphan_root = tmp_path / "orphan"
    _configure_repository(orphan_root, monkeypatch)
    orphan = b"orphaned-docker-attempt"
    (orphan_root / d128.DOCKER_ATTEMPT_PATH).write_bytes(orphan)
    with pytest.raises(d128.D128PreflightError, match="downstream evidence"):
        _create_receipt(orphan_root)
    assert (orphan_root / d128.DOCKER_ATTEMPT_PATH).read_bytes() == orphan
    assert not (orphan_root / d128.RECEIPT_PATH).exists()


def test_source_and_receipt_commit_topologies_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source_identity()
    required_rows = [["A", path.as_posix()] for path in d128._SOURCE_REQUIRED_PATHS]
    monkeypatch.setattr(d128.d127, "_validate_source_identity", lambda *_a, **_k: None)
    monkeypatch.setattr(d128, "_source_commit_changes", lambda *_a, **_k: required_rows)
    d128._validate_source_commit_topology(tmp_path, source)

    wrong_parent = {**source, "parents": ["f" * 40]}
    with pytest.raises(d128.D128PreflightError, match="sole child"):
        d128._validate_source_commit_topology(tmp_path, wrong_parent)

    monkeypatch.setattr(
        d128,
        "_source_commit_changes",
        lambda *_a, **_k: [*required_rows, ["M", "unrelated.txt"]],
    )
    with pytest.raises(d128.D128PreflightError, match="unrelated paths"):
        d128._validate_source_commit_topology(tmp_path, source)

    receipt_path = tmp_path / d128.RECEIPT_PATH
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_bytes(
        d128._pretty_bytes(
            d128._artifact_envelope(
                d128.RECEIPT_SCHEMA,
                "d128approval_",
                {"recorded_at": TIMESTAMP},
            )
        )
    )
    receipt_binding = d128._artifact_binding(tmp_path, d128.RECEIPT_PATH)

    def git_output(_root: Path, *args: str) -> str:
        if args[0] == "rev-list":
            return f"{RECEIPT_COMMIT} {SOURCE_COMMIT}"
        if args[0] == "rev-parse":
            return RECEIPT_TREE
        if args[0] == "diff":
            return f"A\t{d128.RECEIPT_PATH.as_posix()}"
        raise AssertionError(args)

    monkeypatch.setattr(d128.d127, "_run_git", git_output)
    monkeypatch.setattr(
        d128.d127,
        "_run_git_bytes",
        lambda *_a, **_k: receipt_path.read_bytes(),
    )
    receipt_commit = {
        "commit": RECEIPT_COMMIT,
        "tree": RECEIPT_TREE,
        "parents": [SOURCE_COMMIT],
        "branch": "codex/d128-test",
        "receipt_binding": receipt_binding,
        "receipt_only_child_of_source": True,
        "source_module_bytes_unchanged": True,
    }
    d128._validate_receipt_commit_identity(tmp_path, receipt_commit, source=source)

    def replaced_receipt(_root: Path, *args: str) -> str:
        value = git_output(_root, *args)
        return value.replace("A\t", "M\t") if args[0] == "diff" else value

    monkeypatch.setattr(d128.d127, "_run_git", replaced_receipt)
    with pytest.raises(d128.D128PreflightError, match="add only"):
        d128._validate_receipt_commit_identity(tmp_path, receipt_commit, source=source)


def test_static_prerequisites_are_secret_safe_and_zero_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _configure_repository(tmp_path, monkeypatch)
    receipt = _create_receipt(tmp_path)

    result = d128.check_d128_static_prerequisites(repository=tmp_path)
    rendered = canonical_json(result)

    assert result["status"] == d128.STATIC_READY_STATUS
    assert result["receipt"]["artifact_id"] == receipt["artifact_id"]
    assert result["credential"] == {
        "name": "OPENAI_API_KEY",
        "present": True,
        "value_hash_length_or_prefix_persisted": False,
    }
    assert all(result["sdk_metadata_checks_without_client_construction"].values())
    assert result["openai_sdk_installed_version"] == "1.2.3"
    assert result["openai_sdk_locked_version"] == "1.2.3"
    assert result["sdk_client_constructed"] is False
    assert set(result["external_activity"].values()) == {0}
    assert result["artifact_created_by_static_check"] is False
    assert state["calls"] == {"docker": 0, "pricing": 0, "snapshot": 0}
    assert SECRET not in rendered


@pytest.mark.parametrize(
    ("remediation_commands", "pulls", "expected_total"),
    [(6, 0, 12), (7, 1, 13), (8, 2, 14)],
)
def test_ready_path_is_attempt_first_exact_pull_bounded_and_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    remediation_commands: int,
    pulls: int,
    expected_total: int,
) -> None:
    state = _configure_repository(tmp_path, monkeypatch)
    state["docker"] = _ready_docker_observation(
        command_count=remediation_commands,
        pull_count=pulls,
    )
    _create_receipt(tmp_path)

    first = d128.run_d128_external_no_call_preflight(repository=tmp_path)

    assert first["status"] == d128.GATE_READY_STATUS
    assert first["environment_ready_for_execution_hash"] is True
    assert first["docker_cli_command_count"] == expected_total
    assert first["docker_image_store_mutation_count"] == pulls
    assert first["official_public_get_request_count"] == 1
    assert first["docker_desktop_or_daemon_start_count"] == 0
    assert first["container_create_start_run_exec_count"] == 0
    assert first["execution_hash_created"] is False
    assert first["execution_candidate_created"] is False
    assert first["cost_reserved_or_spent_usd"] == "0"
    assert state["events"] == ["docker", "pricing", "snapshot", "snapshot"]
    assert state["calls"] == {"docker": 1, "pricing": 1, "snapshot": 2}
    before = {path: (tmp_path / path).read_bytes() for path in d128._EXTERNAL_OUTPUT_PATHS}

    second = d128.run_d128_external_no_call_preflight(repository=tmp_path)

    assert second == first
    assert state["calls"] == {"docker": 1, "pricing": 1, "snapshot": 2}
    assert before == {path: (tmp_path / path).read_bytes() for path in d128._EXTERNAL_OUTPUT_PATHS}


def test_daemon_down_is_terminal_without_start_pull_pricing_or_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _configure_repository(tmp_path, monkeypatch)
    state["docker"] = _blocked_docker_observation()
    _create_receipt(tmp_path)

    first = d128.run_d128_external_no_call_preflight(repository=tmp_path)
    second = d128.run_d128_external_no_call_preflight(repository=tmp_path)

    assert first == second
    assert first["status"] == d128.DOCKER_BLOCKED_STATUS
    assert first["observed_blockers"] == [d128.docker_remediation.DAEMON_UNAVAILABLE_BLOCKER]
    assert first["docker_cli_command_count"] == 3
    assert first["docker_image_store_mutation_count"] == 0
    assert first["docker_desktop_or_daemon_start_count"] == 0
    assert first["pricing_attempt_created"] is False
    assert first["read_only_preflight_attempt_created"] is False
    assert first["gate_created"] is False
    assert state["calls"] == {"docker": 1, "pricing": 0, "snapshot": 0}
    assert (tmp_path / d128.DOCKER_ATTEMPT_PATH).is_file()
    assert (tmp_path / d128.DOCKER_PATH).is_file()
    assert not (tmp_path / d128.PRICING_ATTEMPT_PATH).exists()
    assert not (tmp_path / d128.GATE_PATH).exists()


def test_orphaned_attempt_blocks_retry_after_uncertain_external_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _configure_repository(tmp_path, monkeypatch)
    _create_receipt(tmp_path)
    calls = 0

    def fail_after_attempt() -> dict[str, Any]:
        nonlocal calls
        calls += 1
        assert (tmp_path / d128.DOCKER_ATTEMPT_PATH).is_file()
        raise RuntimeError("uncertain Docker boundary failure")

    monkeypatch.setattr(
        d128.docker_remediation,
        "remediate_already_running_docker_environment",
        fail_after_attempt,
    )

    with pytest.raises(RuntimeError, match="uncertain Docker boundary failure"):
        d128.run_d128_external_no_call_preflight(repository=tmp_path)
    assert (tmp_path / d128.DOCKER_ATTEMPT_PATH).is_file()
    assert not (tmp_path / d128.DOCKER_PATH).exists()

    with pytest.raises(d128.D128PreflightError, match="orphaned docker-image-readiness"):
        d128.run_d128_external_no_call_preflight(repository=tmp_path)
    assert calls == 1
    assert state["calls"]["pricing"] == 0


def test_helper_contract_drift_fails_before_attempt_or_external_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _configure_repository(tmp_path, monkeypatch)
    _create_receipt(tmp_path)
    monkeypatch.setattr(
        d128.docker_remediation,
        "APPROVED_CLI_SHA256",
        "sha256:" + "0" * 64,
    )

    with pytest.raises(d128.D128PreflightError, match="Docker helper constants differ"):
        d128.run_d128_external_no_call_preflight(repository=tmp_path)

    assert state["calls"] == {"docker": 0, "pricing": 0, "snapshot": 0}
    assert not (tmp_path / d128.DOCKER_ATTEMPT_PATH).exists()


def test_unstable_read_only_snapshots_create_blocked_gate_without_live_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _configure_repository(tmp_path, monkeypatch)
    state["snapshot_queue"] = [
        {"observation": {"passed": True}, "docker_cli_command_count": 3},
        {
            "observation": {"passed": True, "drift": "second-snapshot"},
            "docker_cli_command_count": 3,
        },
    ]
    _create_receipt(tmp_path)

    result = d128.run_d128_external_no_call_preflight(repository=tmp_path)

    assert result["status"] == d128.GATE_BLOCKED_STATUS
    assert result["environment_ready_for_execution_hash"] is False
    assert result["observed_blockers"] == ["read-only-docker-readiness-snapshots-are-not-stable"]
    assert result["execution_hash_created"] is False
    assert result["execution_candidate_created"] is False
    assert result["provider_evaluator_agent_calls_made"] == 0
    assert result["cost_reserved_or_spent_usd"] == "0"


def test_rehashed_gate_tamper_and_phase_order_violation_fail_without_repair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_repository(tmp_path, monkeypatch)
    _create_receipt(tmp_path)
    d128.run_d128_external_no_call_preflight(repository=tmp_path)
    gate_path = tmp_path / d128.GATE_PATH
    payload = json.loads(gate_path.read_bytes())
    payload["semantic_body"]["authority"]["execution_hash_authorized_or_created"] = True
    tampered = d128._pretty_bytes(
        d128._artifact_envelope(
            d128.GATE_SCHEMA,
            "d128_",
            payload["semantic_body"],
        )
    )
    gate_path.write_bytes(tampered)

    with pytest.raises(d128.D128PreflightError, match="gate body differs"):
        d128.validate_d128_no_call_gate(repository=tmp_path)
    assert gate_path.read_bytes() == tampered

    order_root = tmp_path / "order"
    _configure_repository(order_root, monkeypatch)
    _create_receipt(order_root)
    collision = b"terminal-without-attempt"
    (order_root / d128.DOCKER_PATH).write_bytes(collision)
    with pytest.raises(d128.D128PreflightError, match="terminal exists without attempt"):
        d128.run_d128_external_no_call_preflight(repository=order_root)
    assert (order_root / d128.DOCKER_PATH).read_bytes() == collision


def test_all_artifacts_preserve_explicit_non_authority_and_secret_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_repository(tmp_path, monkeypatch)
    _create_receipt(tmp_path)
    result = d128.run_d128_external_no_call_preflight(repository=tmp_path)

    receipt = json.loads((tmp_path / d128.RECEIPT_PATH).read_bytes())["semantic_body"]
    assert receipt["authority"]["docker_desktop_or_daemon_start_authorized"] is False
    assert receipt["authority"]["container_create_start_run_exec_authorized"] is False
    assert receipt["authority"]["provider_evaluator_agent_execution_authorized"] is False
    assert receipt["authority"]["runtime_memory_injection_or_retrieval_authorized"] is False
    assert receipt["authority"]["execution_hash_or_candidate_authorized"] is False
    assert receipt["authority"]["cost_reservation_or_spend_authorized"] is False
    assert receipt["authority"]["four_row_ac_execution_authorized"] is False

    for path in d128._EXTERNAL_OUTPUT_PATHS:
        raw = (tmp_path / path).read_bytes()
        assert SECRET.encode() not in raw
        body = json.loads(raw)["semantic_body"]
        authority = body.get("authority", {})
        for key in (
            "execution_hash_created",
            "execution_candidate_created",
        ):
            if key in authority:
                assert authority[key] is False
        if "cost_reserved_or_spent_usd" in authority:
            assert authority["cost_reserved_or_spent_usd"] == "0"

    gate = json.loads((tmp_path / d128.GATE_PATH).read_bytes())["semantic_body"]
    assert gate["authority"] == {
        "approved_successor_observations_completed": True,
        "docker_desktop_or_daemon_start_authorized_or_performed": False,
        "provider_evaluator_agent_execution_authorized_or_performed": False,
        "runtime_memory_injection_or_retrieval_authorized_or_performed": False,
        "container_create_start_run_exec_authorized_or_performed": False,
        "execution_hash_authorized_or_created": False,
        "execution_candidate_authorized_or_created": False,
        "cost_reservation_or_spend_authorized_or_performed": False,
        "cost_reserved_or_spent_usd": "0",
    }
    assert result["environment_ready_for_execution_hash"] is True
    assert result["execution_hash_created"] is False
    assert result["execution_candidate_created"] is False


def test_artifact_binding_uses_canonical_file_hash_and_size(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_repository(tmp_path, monkeypatch)
    _create_receipt(tmp_path)
    raw = (tmp_path / d128.RECEIPT_PATH).read_bytes()

    binding = d128._artifact_binding(tmp_path, d128.RECEIPT_PATH)

    assert binding["file_bytes"] == len(raw)
    assert binding["file_sha256"] == sha256_bytes(raw)
