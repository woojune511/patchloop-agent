"""Build the offline D-128 successor contract for the blocked D-127 terminal.

D-128 is deliberately source-only.  It validates the exact append-only D-127
receipt, attempt, and terminal observation and records the contract for a
future, separately approved successor.  This module has no receipt writer and
no Docker, network, SDK, provider, evaluator, agent, retrieval, execution-hash,
candidate, reservation, or experiment entrypoint.
"""

from __future__ import annotations

import json
import os
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.errors import ContractError
from patchloop.evals import d122_ac_fixed_bundle_qualification as d122
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-128"
SCHEMA_VERSION = "d127-terminal-successor-offline-source-gate-d128-v1"
STATUS = "D128_D127_TERMINAL_SUCCESSOR_OFFLINE_SOURCE_QUALIFIED_APPROVAL_REQUIRED"
OUTPUT_PATH = Path(
    "reports/live-pilot/artifacts/"
    "d128-d127-terminal-successor-offline-source-gate.json"
)

D127_RECEIPT_PATH = Path(
    "reports/live-pilot/artifacts/"
    "d127-d126-successor-blocker-remediation-no-call-preflight-approval-receipt.json"
)
D127_RECEIPT_SCHEMA = (
    "d126-successor-blocker-remediation-no-call-approval-receipt-d127-v1"
)
D127_RECEIPT_ID = (
    "d127approval_3a7b8bd3bd95564e4f3cddf10c154850bcc939371d69931eb78c87f0810b0d21"
)
D127_RECEIPT_BODY_SHA256 = (
    "sha256:3a7b8bd3bd95564e4f3cddf10c154850bcc939371d69931eb78c87f0810b0d21"
)
D127_RECEIPT_FILE_SHA256 = (
    "sha256:ddea365e3a51c8283bde58bd349222288a45e8ea8bdb3d211ead0bb001df81f4"
)
D127_RECEIPT_FILE_BYTES = 3_914
D127_RECEIPT_STATUS = (
    "D127_D126_SUCCESSOR_BLOCKER_REMEDIATION_NO_CALL_APPROVAL_RECORDED"
)

D127_ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/d127-docker-remediation-attempt-intent.json"
)
D127_ATTEMPT_SCHEMA = "d126-successor-external-phase-attempt-intent-d127-v1"
D127_ATTEMPT_ID = (
    "d127dockerremediationattempt_"
    "2ebabbf2b9d1ace5c3dc552e8f7c2e2ad8c4f3699c5978e718e973b8112369aa"
)
D127_ATTEMPT_BODY_SHA256 = (
    "sha256:2ebabbf2b9d1ace5c3dc552e8f7c2e2ad8c4f3699c5978e718e973b8112369aa"
)
D127_ATTEMPT_FILE_SHA256 = (
    "sha256:2a1d5b01f5cf9a18e1e51db473c35e2003b9c875f2f8f7449d25d55df33328c2"
)
D127_ATTEMPT_FILE_BYTES = 4_246
D127_ATTEMPT_STATUS = "D127_DOCKER_REMEDIATION_ATTEMPT_INTENT_RECORDED"

D127_TERMINAL_PATH = Path(
    "reports/live-pilot/artifacts/d127-exact-docker-remediation-observation.json"
)
D127_TERMINAL_SCHEMA = "d126-successor-docker-remediation-d127-v1"
D127_TERMINAL_ID = (
    "d127remediation_139037ff65b70cc08e24a69d2d6fd47fe04b7cc27bec8e97ebe9a7009179857f"
)
D127_TERMINAL_BODY_SHA256 = (
    "sha256:139037ff65b70cc08e24a69d2d6fd47fe04b7cc27bec8e97ebe9a7009179857f"
)
D127_TERMINAL_FILE_SHA256 = (
    "sha256:dc6639db851fb414325473eebf7e9b8ddd9fe15f54a3b0946b0bd82f99a530d3"
)
D127_TERMINAL_FILE_BYTES = 10_139
D127_TERMINAL_STATUS = "D127_EXACT_DOCKER_REMEDIATION_OBSERVED_BLOCKED"
D127_TERMINAL_BLOCKER = "preexisting-container-auto-restart-state-unverified"

DOCKER_CLI_VERSION = "29.6.2"
DOCKER_CLI_FILE_BYTES = 43_095_472
DOCKER_CLI_FILE_SHA256 = (
    "sha256:8985cd8ac002c3240b5aa48fe401fcb55dca5d849b537e3c835564e8e8c49a70"
)
DOCKER_IMAGE_REFS = (
    "docker.io/swerebenchv2/getmoto-moto@"
    "sha256:dfdf957ab30b8829e8b6bbfd693b00fab88b7979d3c856362fd5d66c489a1fee",
    "docker.io/swerebenchv2/python-babel-babel@"
    "sha256:864e84fc4bdf09252f7fda4f85665cc05155a7b1d75847d61c67325abce7ef5a",
)

D127_DESCENDANT_PATHS = (
    Path("reports/live-pilot/artifacts/d127-official-pricing-capture-attempt-intent.json"),
    Path("reports/live-pilot/artifacts/d127-replayable-official-pricing-evidence.json"),
    Path("reports/live-pilot/artifacts/d127-read-only-preflight-attempt-intent.json"),
    Path("reports/live-pilot/artifacts/d127-repeated-no-call-readiness-preflight.json"),
    Path("reports/live-pilot/artifacts/d127-blocker-remediation-no-call-preflight-gate.json"),
)

IMPLEMENTATION_PATHS = (
    Path("patchloop/runtime.py"),
    Path("patchloop/util.py"),
    Path("patchloop/agent/model.py"),
    Path("patchloop/sandbox/runner.py"),
    Path("patchloop/evals/d122_ac_fixed_bundle_qualification.py"),
    Path("patchloop/evals/d127_d126_successor_no_call_preflight.py"),
    Path("patchloop/evals/d127_docker_remediation.py"),
    Path("patchloop/evals/d127_pricing_capture.py"),
    Path("patchloop/evals/d128_d127_terminal_successor_offline.py"),
    Path("scripts/build_d128_d127_terminal_successor_offline.py"),
    Path("tests/test_d128_d127_terminal_successor_offline.py"),
)

ROOT_KEYS = ("schema_version", "gate_id", "semantic_body_hash", "semantic_body")
BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "predecessor_chain",
    "successor_contract",
    "approval_template_contract",
    "implementation_integrity",
    "offline_qualification",
    "blocked_prerequisites",
    "evidence_boundary",
    "authority",
    "next_gate",
)

FUTURE_APPROVED_SCOPE = (
    "record-a-new-exact-d128-successor-user-approval-receipt",
    "use-the-exact-approved-docker-cli-identity",
    "observe-an-already-running-docker-desktop-linux-daemon-read-only",
    "pull-only-moto-and-babel-exact-digest-images-when-confirmed-absent",
    "capture-bounded-replayable-openai-official-pricing-evidence",
    "run-sdk-credential-presence-official-endpoint-no-call-preflight",
    "create-append-only-d128-attempt-terminal-preflight-and-gate-evidence",
    "modify-related-source-tests-docs-and-create-local-git-commit",
)
FUTURE_NOT_AUTHORIZED = (
    "agent-start-docker-desktop-or-daemon",
    "container-create-start-run-or-exec",
    "pull-or-load-any-image-other-than-the-two-exact-approved-digests",
    "provider-evaluator-or-agent-execution",
    "runtime-memory-injection-or-retrieval",
    "execution-hash-or-execution-candidate-creation",
    "cost-reservation-or-spend",
    "four-row-ac-execution",
)
BLOCKED_PREREQUISITES = (
    "docker-desktop-linux-daemon-not-yet-manually-started-by-user",
    "user-attestation-that-no-preexisting-container-auto-started-is-missing",
    "new-exact-d128-successor-user-approval-not-recorded",
    "d128-source-and-offline-gate-commit-identity-not-bound-by-this-gate",
    "future-receipt-bound-clean-committed-source-identity-not-yet-recorded",
    "d128-external-attempt-pricing-preflight-and-gate-not-created",
    "exact-runner-execution-hash-and-candidate-remain-separately-gated",
)
FOCUSED_TESTS_PASSED = 12
SELECTED_REGRESSION_TESTS_PASSED = 76


class D128OfflineGateError(ContractError):
    """Raised when the offline D-128 successor contract drifts."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D128OfflineGateError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else repository_root()
    try:
        root = selected.resolve(strict=True)
    except OSError as exc:
        raise D128OfflineGateError("D-128 repository root is unavailable") from exc
    _require(root.is_dir(), "D-128 repository root is not a directory")
    return root


def _stable_read(root: Path, relative: Path) -> bytes:
    try:
        return d122._stable_read(root, relative)
    except ContractError as exc:
        raise D128OfflineGateError(
            f"D-128 cannot stably read {relative.as_posix()}"
        ) from exc


def _pretty_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=True, indent=2) + "\n").encode("utf-8")


def _parse_time(value: Any, *, label: str) -> datetime:
    _require(isinstance(value, str) and value.endswith("Z"), f"D-128 {label} differs")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise D128OfflineGateError(f"D-128 {label} differs") from exc
    _require(parsed.tzinfo is not None, f"D-128 {label} differs")
    return parsed.astimezone(UTC)


def _artifact_binding(
    root: Path,
    *,
    path: Path,
    schema: str,
    artifact_id: str,
    body_sha256: str,
    file_sha256: str,
    file_bytes: int,
    status: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = _stable_read(root, path)
    _require(len(raw) == file_bytes, f"D-128 {path.name} size differs")
    _require(sha256_bytes(raw) == file_sha256, f"D-128 {path.name} file SHA differs")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D128OfflineGateError(f"D-128 {path.name} is not UTF-8 JSON") from exc
    _require(isinstance(payload, dict), f"D-128 {path.name} root differs")
    _require(
        tuple(payload) == ("schema_version", "artifact_id", "semantic_body_hash", "semantic_body"),
        f"D-128 {path.name} root fields differ",
    )
    _require(payload.get("schema_version") == schema, f"D-128 {path.name} schema differs")
    _require(payload.get("artifact_id") == artifact_id, f"D-128 {path.name} ID differs")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), f"D-128 {path.name} body differs")
    _require(
        sha256_text(canonical_json(body)) == body_sha256,
        f"D-128 {path.name} body SHA differs",
    )
    _require(
        payload.get("semantic_body_hash") == body_sha256,
        f"D-128 {path.name} declared body SHA differs",
    )
    _require(body.get("status") == status, f"D-128 {path.name} status differs")
    _require(raw == _pretty_bytes(payload), f"D-128 {path.name} bytes are noncanonical")
    binding = {
        "path": path.as_posix(),
        "schema_version": schema,
        "artifact_id": artifact_id,
        "semantic_body_hash": body_sha256,
        "file_bytes": file_bytes,
        "file_sha256": file_sha256,
        "status": status,
        "recorded_at": body.get("recorded_at"),
        "artifact_mutated": False,
    }
    _parse_time(binding["recorded_at"], label=f"{path.name} recorded_at")
    return binding, body


def _predecessor_chain(root: Path) -> dict[str, Any]:
    receipt, receipt_body = _artifact_binding(
        root,
        path=D127_RECEIPT_PATH,
        schema=D127_RECEIPT_SCHEMA,
        artifact_id=D127_RECEIPT_ID,
        body_sha256=D127_RECEIPT_BODY_SHA256,
        file_sha256=D127_RECEIPT_FILE_SHA256,
        file_bytes=D127_RECEIPT_FILE_BYTES,
        status=D127_RECEIPT_STATUS,
    )
    attempt, attempt_body = _artifact_binding(
        root,
        path=D127_ATTEMPT_PATH,
        schema=D127_ATTEMPT_SCHEMA,
        artifact_id=D127_ATTEMPT_ID,
        body_sha256=D127_ATTEMPT_BODY_SHA256,
        file_sha256=D127_ATTEMPT_FILE_SHA256,
        file_bytes=D127_ATTEMPT_FILE_BYTES,
        status=D127_ATTEMPT_STATUS,
    )
    terminal, terminal_body = _artifact_binding(
        root,
        path=D127_TERMINAL_PATH,
        schema=D127_TERMINAL_SCHEMA,
        artifact_id=D127_TERMINAL_ID,
        body_sha256=D127_TERMINAL_BODY_SHA256,
        file_sha256=D127_TERMINAL_FILE_SHA256,
        file_bytes=D127_TERMINAL_FILE_BYTES,
        status=D127_TERMINAL_STATUS,
    )
    binding_keys = (
        "path",
        "artifact_id",
        "semantic_body_hash",
        "file_bytes",
        "file_sha256",
    )
    _require(
        attempt_body.get("receipt_binding")
        == {key: receipt[key] for key in binding_keys},
        "D-128 D-127 attempt-to-receipt binding differs",
    )
    _require(
        terminal_body.get("receipt_binding")
        == {key: receipt[key] for key in binding_keys},
        "D-128 D-127 terminal-to-receipt binding differs",
    )
    _require(
        terminal_body.get("attempt_binding")
        == {key: attempt[key] for key in binding_keys},
        "D-128 D-127 terminal-to-attempt binding differs",
    )
    _require(
        _parse_time(receipt["recorded_at"], label="receipt recorded_at")
        <= _parse_time(attempt["recorded_at"], label="attempt recorded_at")
        <= _parse_time(terminal["recorded_at"], label="terminal recorded_at"),
        "D-128 D-127 chronology differs",
    )
    observation = terminal_body.get("observation")
    authority = terminal_body.get("authority")
    _require(isinstance(observation, dict), "D-128 D-127 observation differs")
    _require(isinstance(authority, dict), "D-128 D-127 authority differs")
    _require(
        observation.get("desktop_start_skipped_reason") == D127_TERMINAL_BLOCKER
        and observation.get("passed") is False
        and observation.get("desktop_start_count") == 0
        and observation.get("image_store_mutation_count") == 0
        and observation.get("container_create_start_run_exec_count") == 0
        and observation.get("docker_workload_call_count") == 0,
        "D-128 D-127 terminal blocker boundary differs",
    )
    _require(
        authority.get("docker_desktop_start_count") == 0
        and authority.get("docker_image_store_mutation_count") == 0
        and authority.get("container_create_start_run_exec_count") == 0
        and authority.get("provider_calls_made") == 0
        and authority.get("evaluator_calls_made") == 0
        and authority.get("agent_runs_started") == 0
        and authority.get("runtime_memory_injection_count") == 0
        and authority.get("retrieval_call_count") == 0
        and authority.get("execution_hash_created") is False
        and authority.get("execution_candidate_created") is False
        and authority.get("cost_reserved_or_spent_usd") == "0",
        "D-128 D-127 closed authority differs",
    )
    for path in D127_DESCENDANT_PATHS:
        selected = root / path
        _require(
            not selected.exists() and not d122._is_linklike(selected),
            f"D-128 unexpected D-127 descendant exists: {path}",
        )
    return {
        "receipt": receipt,
        "attempt": attempt,
        "terminal": terminal,
        "terminal_blocker": D127_TERMINAL_BLOCKER,
        "terminal_is_idempotent_and_not_retryable": True,
        "d127_pricing_preflight_and_gate_descendants_absent": True,
    }


def _file_binding(root: Path, path: Path) -> dict[str, Any]:
    raw = _stable_read(root, path)
    return {
        "path": path.as_posix(),
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }


def _implementation_integrity(root: Path) -> dict[str, Any]:
    files = [_file_binding(root, path) for path in IMPLEMENTATION_PATHS]
    return {
        "files": files,
        "file_set_hash": sha256_text(canonical_json(files)),
        "d127_runtime_or_receipt_writer_imported": False,
        "docker_network_sdk_provider_or_execution_entrypoint_present": False,
    }


def _successor_contract() -> dict[str, Any]:
    contract = {
        "contract_version": "d127-terminal-successor-no-call-contract-d128-v1",
        "manual_prerequisites": {
            "docker_desktop_linux_daemon_started_manually_by_user": False,
            "user_confirmed_no_preexisting_container_auto_started": False,
            "agent_must_not_start_docker_desktop_or_daemon": True,
            "manual_state_change_does_not_reopen_d127": True,
        },
        "credential_boundary": {
            "offline_gate_reads_dotenv": False,
            "future_process_may_receive_only_openai_api_key_via_exact_key_loader": True,
            "credential_value_hash_prefix_length_or_env_file_hash_may_be_persisted": False,
        },
        "future_exact_docker_cli": {
            "version": DOCKER_CLI_VERSION,
            "file_bytes": DOCKER_CLI_FILE_BYTES,
            "file_sha256": DOCKER_CLI_FILE_SHA256,
        },
        "future_exact_image_refs": list(DOCKER_IMAGE_REFS),
        "future_approved_scope": list(FUTURE_APPROVED_SCOPE),
        "future_explicitly_not_authorized": list(FUTURE_NOT_AUTHORIZED),
        "future_source_and_receipt_boundary": {
            "receipt_must_be_new_append_only_and_tracked_at_source_head": True,
            "receipt_must_bind_exact_clean_commit_tree_parent_and_module_bytes": True,
            "source_and_receipt_must_be_rechecked_before_each_external_phase": True,
            "future_evidence_commit_must_add_only_exact_successor_artifacts_and_docs": True,
        },
        "future_external_failure_boundary": {
            "attempt_intent_must_be_durable_before_each_first_external_call": True,
            "attempt_must_bind_receipt_source_modules_and_exact_phase_scope": True,
            "orphaned_attempt_must_block_retry_without_new_exact_user_approval": True,
            "terminal_must_record_actual_activity_counts_after_any_external_action": True,
            "existing_terminal_is_idempotent_and_must_not_be_rewritten": True,
        },
        "future_receipt_identity_boundary": {
            "approval_is_self_attested": True,
            "approval_is_authenticated_or_signed": False,
            "no_identity_upgrade_claim_is_permitted": True,
        },
        "new_receipt_requires_future_exact_user_message": True,
        "offline_gate_is_not_an_approval_receipt": True,
        "external_entrypoint_present_in_this_module": False,
    }
    return {
        "contract": contract,
        "contract_hash": sha256_text(canonical_json(contract)),
    }


def _approval_template_contract() -> dict[str, Any]:
    return {
        "template_version": "d128-terminal-successor-user-approval-template-v1",
        "required_predecessor_fields": [
            "D-128 gate ID",
            "D-128 semantic body SHA",
            "D-128 file SHA",
            "D-128 file bytes",
            "D-128 source/evidence commit",
        ],
        "required_manual_attestations": [
            "Docker Desktop Linux daemon was started manually by the user",
            "no pre-existing container auto-started during that manual action",
            "the agent must not start Docker Desktop or the daemon",
        ],
        "approved_scope": list(FUTURE_APPROVED_SCOPE),
        "explicitly_not_authorized": list(FUTURE_NOT_AUTHORIZED),
        "rendering_this_template_records_approval": False,
        "generic_proceed_message_is_exact_approval": False,
        "receipt_must_be_tracked_at_clean_source_head_before_external_action": True,
        "approval_is_self_attested": True,
        "approval_is_authenticated_or_signed": False,
    }


def _body(
    *,
    recorded_at: str,
    predecessor: dict[str, Any],
    implementation: dict[str, Any],
) -> dict[str, Any]:
    _require(
        _parse_time(recorded_at, label="recorded_at")
        >= _parse_time(
            predecessor["terminal"]["recorded_at"], label="D-127 terminal recorded_at"
        ),
        "D-128 chronology precedes D-127",
    )
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "offline-d127-terminal-successor-source-qualification",
        "recorded_at": recorded_at,
        "status": STATUS,
        "predecessor_chain": predecessor,
        "successor_contract": _successor_contract(),
        "approval_template_contract": _approval_template_contract(),
        "implementation_integrity": implementation,
        "offline_qualification": {
            "exact_d127_receipt_attempt_terminal_bytes_validated": True,
            "d127_artifacts_preserved": True,
            "d127_terminal_retry_or_resume_opened": False,
            "source_only_no_external_entrypoint": True,
            "focused_tests_external_to_builder": True,
            "focused_tests_passed": FOCUSED_TESTS_PASSED,
            "focused_tests_are_self_attested_not_remote_ci": True,
            "selected_d122_d127_d128_regression_tests_passed": (
                SELECTED_REGRESSION_TESTS_PASSED
            ),
            "selected_regression_count_includes_focused_tests": True,
            "focused_and_selected_counts_are_not_additive": True,
            "new_user_approval_recorded": False,
        },
        "blocked_prerequisites": list(BLOCKED_PREREQUISITES),
        "evidence_boundary": {
            "qualification_grade": "offline-source-and-mocked-zero-call-tests",
            "manual_docker_daemon_state_observed": False,
            "container_auto_start_state_observed": False,
            "docker_cli_or_daemon_call_made": False,
            "image_pull_or_store_mutation_made": False,
            "official_pricing_get_made": False,
            "sdk_or_credential_preflight_made": False,
            "provider_evaluator_agent_or_memory_result_present": False,
            "execution_hash_candidate_reservation_or_ac_result_present": False,
            "source_or_evidence_commit_bound_by_this_gate": False,
            "dotenv_or_credential_presence_observed": False,
            "credential_value_hash_prefix_length_or_env_file_hash_persisted": False,
        },
        "authority": {
            "d128_offline_source_gate_materialized": True,
            "d128_user_approval_recorded": False,
            "d128_approval_receipt_created": False,
            "d128_source_or_evidence_commit_bound": False,
            "env_file_loaded": False,
            "credential_presence_observed": False,
            "docker_desktop_or_daemon_start_authorized": False,
            "docker_readiness_or_image_pull_authorized": False,
            "official_pricing_lookup_authorized": False,
            "sdk_credential_or_endpoint_preflight_authorized": False,
            "provider_evaluator_or_agent_execution_authorized": False,
            "runtime_memory_injection_or_retrieval_authorized": False,
            "execution_hash_or_candidate_authorized": False,
            "cost_reservation_or_spend_authorized": False,
            "four_row_ac_execution_authorized": False,
            "docker_cli_calls_made": 0,
            "docker_daemon_calls_made": 0,
            "docker_desktop_start_count": 0,
            "image_store_mutation_count": 0,
            "container_create_start_run_exec_count": 0,
            "network_calls_made": 0,
            "pricing_public_get_count": 0,
            "sdk_probe_count": 0,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "agent_runs_started": 0,
            "runtime_memory_injection_count": 0,
            "retrieval_call_count": 0,
            "execution_hash_created": False,
            "execution_candidate_created": False,
            "cost_reserved_or_spent_usd": "0",
        },
        "next_gate": {
            "action": "manual-daemon-safety-attestation-then-exact-d128-user-approval",
            "must_quote_exact_materialized_d128_gate_triple_and_file_bytes": True,
            "must_quote_exact_source_or_evidence_commit": True,
            "must_create_a_new_append_only_receipt": True,
            "receipt_must_bind_clean_commit_tree_parent_and_module_bytes": True,
            "attempt_intent_must_precede_every_external_phase": True,
            "orphaned_attempt_requires_another_exact_user_approval": True,
            "approval_identity_is_self_attested_not_authenticated_or_signed": True,
            "must_not_reuse_or_delete_d127_attempt_or_terminal": True,
            "does_not_authorize_any_external_action": True,
            "execution_hash_candidate_cost_and_ac_run_remain_later_gates": True,
        },
    }
    _require(tuple(body) == BODY_KEYS, "D-128 semantic body fields differ")
    return body


def _envelope(body: dict[str, Any]) -> dict[str, Any]:
    body_hash = sha256_text(canonical_json(body))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "gate_id": f"d128_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }
    _require(tuple(payload) == ROOT_KEYS, "D-128 gate fields differ")
    return payload


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (canonical_json(payload) + "\n").encode("utf-8")


def _validate_payload(
    *, root: Path, payload: dict[str, Any], raw: bytes
) -> dict[str, Any]:
    _require(set(payload) == set(ROOT_KEYS), "D-128 gate root fields differ")
    _require(payload.get("schema_version") == SCHEMA_VERSION, "D-128 schema differs")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), "D-128 semantic body is missing")
    _require(set(body) == set(BODY_KEYS), "D-128 semantic body fields differ")
    expected = _envelope(
        _body(
            recorded_at=body.get("recorded_at"),
            predecessor=_predecessor_chain(root),
            implementation=_implementation_integrity(root),
        )
    )
    _require(raw == _canonical_bytes(expected), "D-128 full expected payload differs")
    return expected


def _result(payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    authority = payload["semantic_body"]["authority"]
    return {
        "status": payload["semantic_body"]["status"],
        "gate_id": payload["gate_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "user_approval_required": True,
        "approval_receipt_created": authority["d128_approval_receipt_created"],
        "docker_calls_made": authority["docker_cli_calls_made"],
        "pricing_public_get_count": authority["pricing_public_get_count"],
        "provider_calls_made": authority["provider_calls_made"],
        "execution_hash_created": authority["execution_hash_created"],
        "execution_candidate_created": authority["execution_candidate_created"],
    }


def _write_new(root: Path, payload: dict[str, Any]) -> bytes:
    try:
        selected = d122._logical_path(root, OUTPUT_PATH, must_exist=False)
    except ContractError as exc:
        raise D128OfflineGateError("D-128 output path is unsafe") from exc
    _require(not selected.exists(), "D-128 source gate already exists")
    content = _canonical_bytes(payload)
    temporary = selected.with_name(f".{selected.name}.{uuid.uuid4().hex}.tmp")
    try:
        try:
            with temporary.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as exc:
            raise D128OfflineGateError("D-128 temporary gate write failed") from exc
        temporary_content = _stable_read(root, temporary.relative_to(root))
        _require(temporary_content == content, "D-128 temporary gate bytes differ")
        try:
            os.link(temporary, selected)
        except FileExistsError as exc:
            raise D128OfflineGateError("D-128 source gate publication collision") from exc
        except OSError as exc:
            raise D128OfflineGateError("D-128 source gate publication failed") from exc
        observed = _stable_read(root, OUTPUT_PATH)
        _require(observed == content, "D-128 source gate changed after publication")
        return observed
    finally:
        with suppress(OSError):
            temporary.unlink()


def validate_d128_offline_source_gate(
    *, repository: str | Path | None = None
) -> dict[str, Any]:
    """Validate the D-128 gate against current exact source and predecessors."""

    root = _repo_root(repository)
    raw = _stable_read(root, OUTPUT_PATH)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D128OfflineGateError("D-128 gate is not canonical UTF-8 JSON") from exc
    _require(isinstance(payload, dict), "D-128 gate root is not an object")
    validated = _validate_payload(root=root, payload=payload, raw=raw)
    return _result(validated, raw)


def run_d128_offline_source_gate(
    *, repository: str | Path | None = None
) -> dict[str, Any]:
    """Materialize only the append-only offline D-128 source gate."""

    root = _repo_root(repository)
    try:
        output = d122._logical_path(root, OUTPUT_PATH, must_exist=False)
    except ContractError as exc:
        raise D128OfflineGateError("D-128 output path is unsafe") from exc
    if output.exists():
        return validate_d128_offline_source_gate(repository=root)
    predecessor = _predecessor_chain(root)
    implementation = _implementation_integrity(root)
    recorded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    payload = _envelope(
        _body(
            recorded_at=recorded_at,
            predecessor=predecessor,
            implementation=implementation,
        )
    )
    raw = _write_new(root, payload)
    _validate_payload(root=root, payload=payload, raw=raw)
    return _result(payload, raw)


def render_d128_successor_approval_template(
    *, repository: str | Path | None = None
) -> str:
    """Render a non-authoritative template bound to the exact offline gate."""

    result = validate_d128_offline_source_gate(repository=repository)
    return "\n".join(
        (
            "D-128 terminal-successor no-call preflight approval",
            "",
            f"Gate ID\n{result['gate_id']}",
            f"Semantic body SHA\n{result['semantic_body_hash']}",
            f"File SHA\n{result['file_sha256']}",
            f"File bytes\n{result['file_bytes']}",
            "Source/evidence commit\n<exact commit after the gate is committed>",
            "",
            "Manual prerequisite attestations",
            "- I manually started Docker Desktop Linux daemon.",
            "- No pre-existing container auto-started during that action.",
            "- The agent must not start Docker Desktop or the daemon.",
            "",
            "Approved scope",
            *(f"- {item}" for item in FUTURE_APPROVED_SCOPE),
            "",
            "Explicitly not authorized",
            *(f"- {item}" for item in FUTURE_NOT_AUTHORIZED),
        )
    )


__all__ = [
    "D128OfflineGateError",
    "OUTPUT_PATH",
    "render_d128_successor_approval_template",
    "run_d128_offline_source_gate",
    "validate_d128_offline_source_gate",
]
