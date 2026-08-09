from __future__ import annotations

import ast
import copy
import json
import os
import shutil
import socket
import subprocess
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from patchloop.agent import model as agent_model
from patchloop.agent import runner as agent_runner
from patchloop.evals import (
    d127_d126_successor_no_call_preflight as d127_external,
)
from patchloop.evals import (
    d127_docker_remediation,
    d127_pricing_capture,
)
from patchloop.evals import (
    d128_d127_terminal_successor_offline as d128,
)
from patchloop.evals import runner as eval_runner
from patchloop.memory import retrieval
from patchloop.sandbox import runner as sandbox_runner
from patchloop.util import canonical_json, sha256_bytes, sha256_text

REPOSITORY = Path(__file__).resolve().parents[1]
MODULE_PATH = Path("patchloop/evals/d128_d127_terminal_successor_offline.py")
SCRIPT_PATH = Path("scripts/build_d128_d127_terminal_successor_offline.py")

EXPECTED_APPROVED_SCOPE = (
    "record-a-new-exact-d128-successor-user-approval-receipt",
    "use-the-exact-approved-docker-cli-identity",
    "observe-an-already-running-docker-desktop-linux-daemon-read-only",
    "pull-only-moto-and-babel-exact-digest-images-when-confirmed-absent",
    "capture-bounded-replayable-openai-official-pricing-evidence",
    "run-sdk-credential-presence-official-endpoint-no-call-preflight",
    "create-append-only-d128-attempt-terminal-preflight-and-gate-evidence",
    "modify-related-source-tests-docs-and-create-local-git-commit",
)
EXPECTED_NOT_AUTHORIZED = (
    "agent-start-docker-desktop-or-daemon",
    "container-create-start-run-or-exec",
    "pull-or-load-any-image-other-than-the-two-exact-approved-digests",
    "provider-evaluator-or-agent-execution",
    "runtime-memory-injection-or-retrieval",
    "execution-hash-or-execution-candidate-creation",
    "cost-reservation-or-spend",
    "four-row-ac-execution",
)


def _forbidden(label: str):
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(f"D-128 crossed forbidden {label} boundary")

    return fail


@pytest.fixture(autouse=True)
def zero_external_boundaries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", _forbidden("subprocess"))
    monkeypatch.setattr(subprocess, "Popen", _forbidden("subprocess"))
    monkeypatch.setattr(os, "system", _forbidden("shell"))
    monkeypatch.setattr(socket, "socket", _forbidden("socket/network"))
    monkeypatch.setattr(socket, "create_connection", _forbidden("socket/network"))
    monkeypatch.setattr(agent_model, "OpenAI", _forbidden("provider"))
    monkeypatch.setattr(agent_runner.AgentRunner, "start", _forbidden("agent run"))
    monkeypatch.setattr(agent_runner.AgentRunner, "resume", _forbidden("agent run"))
    monkeypatch.setattr(
        agent_runner,
        "issue_live_execution_authorization",
        _forbidden("execution hash"),
    )
    monkeypatch.setattr(
        agent_runner,
        "issue_campaign_cost_reservation_authorization",
        _forbidden("cost reservation"),
    )
    monkeypatch.setattr(eval_runner, "preflight_suite", _forbidden("suite preflight"))
    monkeypatch.setattr(eval_runner, "evaluate_suite", _forbidden("evaluator"))
    monkeypatch.setattr(retrieval, "retrieve_memory", _forbidden("retrieval"))
    monkeypatch.setattr(retrieval, "_query_embedding", _forbidden("retrieval"))
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "available", _forbidden("Docker"))
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "run_check", _forbidden("Docker"))
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "run_probe", _forbidden("Docker"))
    monkeypatch.setattr(
        d127_docker_remediation,
        "remediate_docker_environment",
        _forbidden("Docker remediation"),
    )
    monkeypatch.setattr(
        d127_docker_remediation,
        "observe_docker_readiness",
        _forbidden("Docker readiness"),
    )
    monkeypatch.setattr(
        d127_pricing_capture,
        "capture_official_pricing_evidence",
        _forbidden("official pricing network"),
    )
    monkeypatch.setattr(
        d127_external,
        "run_d127_external_remediation_and_preflight",
        _forbidden("D-127 external preflight"),
    )


@pytest.fixture
def repository() -> Iterator[Path]:
    root = REPOSITORY / f"tmp-d128-test-{uuid.uuid4().hex}"
    assert not root.exists()
    root.mkdir()
    required = {
        d128.D127_RECEIPT_PATH,
        d128.D127_ATTEMPT_PATH,
        d128.D127_TERMINAL_PATH,
        *d128.IMPLEMENTATION_PATHS,
    }
    try:
        for relative in required:
            source = REPOSITORY / relative
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
        assert not (root / d128.OUTPUT_PATH).exists()
        yield root
    finally:
        if root.exists():
            assert root.resolve(strict=True).parent == REPOSITORY.resolve(strict=True)
            shutil.rmtree(root)


def _expected_binding(
    *,
    path: Path,
    schema: str,
    artifact_id: str,
    body_hash: str,
    file_bytes: int,
    file_hash: str,
    status: str,
    recorded_at: str,
) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "schema_version": schema,
        "artifact_id": artifact_id,
        "semantic_body_hash": body_hash,
        "file_bytes": file_bytes,
        "file_sha256": file_hash,
        "status": status,
        "recorded_at": recorded_at,
        "artifact_mutated": False,
    }


def test_exact_d127_predecessor_chain_is_bound_and_terminal(repository: Path) -> None:
    chain = d128._predecessor_chain(repository)

    assert chain["receipt"] == _expected_binding(
        path=d128.D127_RECEIPT_PATH,
        schema="d126-successor-blocker-remediation-no-call-approval-receipt-d127-v1",
        artifact_id="d127approval_3a7b8bd3bd95564e4f3cddf10c154850bcc939371d69931eb78c87f0810b0d21",
        body_hash="sha256:3a7b8bd3bd95564e4f3cddf10c154850bcc939371d69931eb78c87f0810b0d21",
        file_bytes=3_914,
        file_hash="sha256:ddea365e3a51c8283bde58bd349222288a45e8ea8bdb3d211ead0bb001df81f4",
        status="D127_D126_SUCCESSOR_BLOCKER_REMEDIATION_NO_CALL_APPROVAL_RECORDED",
        recorded_at="2026-08-08T20:08:40.722363Z",
    )
    assert chain["attempt"] == _expected_binding(
        path=d128.D127_ATTEMPT_PATH,
        schema="d126-successor-external-phase-attempt-intent-d127-v1",
        artifact_id="d127dockerremediationattempt_2ebabbf2b9d1ace5c3dc552e8f7c2e2ad8c4f3699c5978e718e973b8112369aa",
        body_hash="sha256:2ebabbf2b9d1ace5c3dc552e8f7c2e2ad8c4f3699c5978e718e973b8112369aa",
        file_bytes=4_246,
        file_hash="sha256:2a1d5b01f5cf9a18e1e51db473c35e2003b9c875f2f8f7449d25d55df33328c2",
        status="D127_DOCKER_REMEDIATION_ATTEMPT_INTENT_RECORDED",
        recorded_at="2026-08-08T20:23:32.540016Z",
    )
    assert chain["terminal"] == _expected_binding(
        path=d128.D127_TERMINAL_PATH,
        schema="d126-successor-docker-remediation-d127-v1",
        artifact_id="d127remediation_139037ff65b70cc08e24a69d2d6fd47fe04b7cc27bec8e97ebe9a7009179857f",
        body_hash="sha256:139037ff65b70cc08e24a69d2d6fd47fe04b7cc27bec8e97ebe9a7009179857f",
        file_bytes=10_139,
        file_hash="sha256:dc6639db851fb414325473eebf7e9b8ddd9fe15f54a3b0946b0bd82f99a530d3",
        status="D127_EXACT_DOCKER_REMEDIATION_OBSERVED_BLOCKED",
        recorded_at="2026-08-08T20:23:35.218004Z",
    )
    assert chain["terminal_blocker"] == "preexisting-container-auto-restart-state-unverified"
    assert chain["terminal_is_idempotent_and_not_retryable"] is True
    assert chain["d127_pricing_preflight_and_gate_descendants_absent"] is True


def test_successor_scope_and_template_are_source_only(repository: Path) -> None:
    successor = d128._successor_contract()["contract"]
    template = d128._approval_template_contract()

    assert d128.FUTURE_APPROVED_SCOPE == EXPECTED_APPROVED_SCOPE
    assert d128.FUTURE_NOT_AUTHORIZED == EXPECTED_NOT_AUTHORIZED
    assert successor["manual_prerequisites"] == {
        "docker_desktop_linux_daemon_started_manually_by_user": False,
        "user_confirmed_no_preexisting_container_auto_started": False,
        "agent_must_not_start_docker_desktop_or_daemon": True,
        "manual_state_change_does_not_reopen_d127": True,
    }
    assert successor["future_approved_scope"] == list(EXPECTED_APPROVED_SCOPE)
    assert successor["future_explicitly_not_authorized"] == list(EXPECTED_NOT_AUTHORIZED)
    assert successor["future_source_and_receipt_boundary"] == {
        "receipt_must_be_new_append_only_and_tracked_at_source_head": True,
        "receipt_must_bind_exact_clean_commit_tree_parent_and_module_bytes": True,
        "source_and_receipt_must_be_rechecked_before_each_external_phase": True,
        "future_evidence_commit_must_add_only_exact_successor_artifacts_and_docs": True,
    }
    assert successor["future_external_failure_boundary"] == {
        "attempt_intent_must_be_durable_before_each_first_external_call": True,
        "attempt_must_bind_receipt_source_modules_and_exact_phase_scope": True,
        "orphaned_attempt_must_block_retry_without_new_exact_user_approval": True,
        "terminal_must_record_actual_activity_counts_after_any_external_action": True,
        "existing_terminal_is_idempotent_and_must_not_be_rewritten": True,
    }
    assert successor["future_receipt_identity_boundary"] == {
        "approval_is_self_attested": True,
        "approval_is_authenticated_or_signed": False,
        "no_identity_upgrade_claim_is_permitted": True,
    }
    assert successor["new_receipt_requires_future_exact_user_message"] is True
    assert successor["offline_gate_is_not_an_approval_receipt"] is True
    assert successor["external_entrypoint_present_in_this_module"] is False
    assert template["approved_scope"] == list(EXPECTED_APPROVED_SCOPE)
    assert template["explicitly_not_authorized"] == list(EXPECTED_NOT_AUTHORIZED)
    assert template["rendering_this_template_records_approval"] is False
    assert template["generic_proceed_message_is_exact_approval"] is False
    assert template["receipt_must_be_tracked_at_clean_source_head_before_external_action"]
    assert template["approval_is_self_attested"] is True
    assert template["approval_is_authenticated_or_signed"] is False
    assert {
        Path("patchloop/runtime.py"),
        Path("patchloop/util.py"),
        Path("patchloop/evals/d122_ac_fixed_bundle_qualification.py"),
    }.issubset(d128.IMPLEMENTATION_PATHS)

    result = d128.run_d128_offline_source_gate(repository=repository)
    rendered = d128.render_d128_successor_approval_template(repository=repository)
    assert result["gate_id"] in rendered
    assert result["semantic_body_hash"] in rendered
    assert result["file_sha256"] in rendered
    assert str(result["file_bytes"]) in rendered
    rendered_items = (*EXPECTED_APPROVED_SCOPE, *EXPECTED_NOT_AUTHORIZED)
    assert all(f"- {item}" in rendered for item in rendered_items)


def test_gate_is_canonical_idempotent_and_validates(repository: Path) -> None:
    predecessor_before = {
        path: (repository / path).read_bytes()
        for path in (d128.D127_RECEIPT_PATH, d128.D127_ATTEMPT_PATH, d128.D127_TERMINAL_PATH)
    }

    first = d128.run_d128_offline_source_gate(repository=repository)
    output = repository / d128.OUTPUT_PATH
    raw = output.read_bytes()
    payload = json.loads(raw)
    second = d128.run_d128_offline_source_gate(repository=repository)

    assert first == second == d128.validate_d128_offline_source_gate(repository=repository)
    assert raw == output.read_bytes() == d128._canonical_bytes(payload)
    assert payload["semantic_body_hash"] == sha256_text(canonical_json(payload["semantic_body"]))
    assert payload["gate_id"] == f"d128_{payload['semantic_body_hash'].removeprefix('sha256:')}"
    assert first["file_bytes"] == len(raw)
    assert first["file_sha256"] == sha256_bytes(raw)
    assert predecessor_before == {
        path: (repository / path).read_bytes() for path in predecessor_before
    }


def test_production_output_is_absent_or_current_valid_without_materializing() -> None:
    output = REPOSITORY / d128.OUTPUT_PATH
    if not output.exists():
        assert not output.is_symlink()
        return

    before = output.read_bytes()
    result = d128.validate_d128_offline_source_gate(repository=REPOSITORY)
    assert result["status"] == d128.STATUS
    assert output.read_bytes() == before


def test_imports_and_public_api_expose_no_external_entrypoint(repository: Path) -> None:
    source = (repository / MODULE_PATH).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    identifiers: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])
        elif isinstance(node, ast.Name):
            identifiers.add(node.id)
        elif isinstance(node, ast.Attribute):
            identifiers.add(node.attr)

    assert imported_roots.isdisjoint(
        {"docker", "httpx", "openai", "requests", "socket", "subprocess", "urllib"}
    )
    assert identifiers.isdisjoint(
        {
            "OpenAI",
            "DockerSandbox",
            "capture_official_pricing_evidence",
            "observe_docker_readiness",
            "remediate_docker_environment",
            "run_d127_external_remediation_and_preflight",
        }
    )
    assert d128.__all__ == [
        "D128OfflineGateError",
        "OUTPUT_PATH",
        "render_d128_successor_approval_template",
        "run_d128_offline_source_gate",
        "validate_d128_offline_source_gate",
    ]
    assert not any("receipt" in name or "external" in name for name in d128.__all__)
    d128.run_d128_offline_source_gate(repository=repository)


def test_missing_predecessor_fails_before_output(repository: Path) -> None:
    missing = repository / d128.D127_ATTEMPT_PATH
    missing.unlink()

    with pytest.raises(d128.D128OfflineGateError, match="cannot stably read"):
        d128.run_d128_offline_source_gate(repository=repository)

    assert not (repository / d128.OUTPUT_PATH).exists()


def test_tampered_predecessor_fails_before_output(repository: Path) -> None:
    terminal = repository / d128.D127_TERMINAL_PATH
    payload = json.loads(terminal.read_bytes())
    payload["semantic_body"]["authority"]["provider_calls_made"] = 1
    body_hash = sha256_text(canonical_json(payload["semantic_body"]))
    payload["semantic_body_hash"] = body_hash
    payload["artifact_id"] = f"d127remediation_{body_hash.removeprefix('sha256:')}"
    tampered = d128._pretty_bytes(payload)
    terminal.write_bytes(tampered)

    with pytest.raises(d128.D128OfflineGateError, match="file SHA differs"):
        d128.run_d128_offline_source_gate(repository=repository)

    assert terminal.read_bytes() == tampered
    assert not (repository / d128.OUTPUT_PATH).exists()


def test_d127_descendants_are_rejected_without_mutation(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for descendant in d128.D127_DESCENDANT_PATHS:
        selected = repository / descendant
        selected.parent.mkdir(parents=True, exist_ok=True)
        collision = f"orphaned:{descendant.as_posix()}".encode()
        selected.write_bytes(collision)

        with pytest.raises(d128.D128OfflineGateError, match="unexpected D-127 descendant"):
            d128.run_d128_offline_source_gate(repository=repository)

        assert selected.read_bytes() == collision
        assert not (repository / d128.OUTPUT_PATH).exists()
        selected.unlink()

    dangling = repository / d128.D127_DESCENDANT_PATHS[0]
    original_is_linklike = d128.d122._is_linklike
    monkeypatch.setattr(
        d128.d122,
        "_is_linklike",
        lambda path: path == dangling or original_is_linklike(path),
    )
    with pytest.raises(d128.D128OfflineGateError, match="unexpected D-127 descendant"):
        d128.run_d128_offline_source_gate(repository=repository)
    assert not dangling.exists()
    assert not (repository / d128.OUTPUT_PATH).exists()


def test_implementation_drift_invalidates_gate_without_repair(repository: Path) -> None:
    d128.run_d128_offline_source_gate(repository=repository)
    output = repository / d128.OUTPUT_PATH
    original = output.read_bytes()
    implementation = repository / "patchloop/agent/model.py"
    implementation.write_bytes(implementation.read_bytes() + b"\n# D-128 drift\n")

    with pytest.raises(d128.D128OfflineGateError, match="full expected payload differs"):
        d128.validate_d128_offline_source_gate(repository=repository)
    with pytest.raises(d128.D128OfflineGateError, match="full expected payload differs"):
        d128.run_d128_offline_source_gate(repository=repository)

    assert output.read_bytes() == original


def test_output_collisions_and_linklike_paths_are_never_repaired(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = repository / d128.OUTPUT_PATH
    for collision in (b"", b'{"schema_version":', b"unapproved-existing-bytes"):
        output.write_bytes(collision)
        with pytest.raises(d128.D128OfflineGateError):
            d128.run_d128_offline_source_gate(repository=repository)
        assert output.read_bytes() == collision
        output.unlink()

    output.mkdir()
    with pytest.raises(d128.D128OfflineGateError):
        d128.run_d128_offline_source_gate(repository=repository)
    assert output.is_dir()
    output.rmdir()

    target = output.with_suffix(".target")
    target.write_bytes(b"D-128 target must remain unchanged")
    try:
        output.symlink_to(target)
    except OSError:
        output.write_bytes(b"simulated-linklike-output")
        original = d128.d122._is_linklike
        monkeypatch.setattr(
            d128.d122,
            "_is_linklike",
            lambda path: path == output or original(path),
        )
    with pytest.raises(d128.D128OfflineGateError, match="stably read|unsafe"):
        d128.run_d128_offline_source_gate(repository=repository)
    assert target.read_bytes() == b"D-128 target must remain unchanged"


def test_fully_rehashed_gate_authority_unknown_and_chronology_tamper_fail(
    repository: Path,
) -> None:
    d128.run_d128_offline_source_gate(repository=repository)
    output = repository / d128.OUTPUT_PATH
    original = output.read_bytes()
    original_payload = json.loads(original)

    def authority(body: dict[str, Any]) -> None:
        body["authority"]["official_pricing_lookup_authorized"] = True

    def unknown(body: dict[str, Any]) -> None:
        body["unapproved_future_field"] = False

    def chronology(body: dict[str, Any]) -> None:
        body["recorded_at"] = "2000-01-01T00:00:00Z"

    for mutate in (authority, unknown, chronology):
        body = copy.deepcopy(original_payload["semantic_body"])
        mutate(body)
        tampered = d128._canonical_bytes(d128._envelope(body))
        output.write_bytes(tampered)

        with pytest.raises(d128.D128OfflineGateError):
            d128.validate_d128_offline_source_gate(repository=repository)

        assert output.read_bytes() == tampered
        output.write_bytes(original)

    assert d128.validate_d128_offline_source_gate(repository=repository)["status"] == d128.STATUS


def test_result_and_payload_report_all_authority_zero(repository: Path) -> None:
    result = d128.run_d128_offline_source_gate(repository=repository)
    payload = json.loads((repository / d128.OUTPUT_PATH).read_bytes())
    authority = payload["semantic_body"]["authority"]
    boundary = payload["semantic_body"]["evidence_boundary"]

    assert result["status"] == d128.STATUS
    assert result["user_approval_required"] is True
    assert result["approval_receipt_created"] is False
    assert result["docker_calls_made"] == 0
    assert result["pricing_public_get_count"] == 0
    assert result["provider_calls_made"] == 0
    assert result["execution_hash_created"] is False
    assert result["execution_candidate_created"] is False
    assert authority["d128_offline_source_gate_materialized"] is True
    assert authority["d128_user_approval_recorded"] is False
    assert authority["d128_approval_receipt_created"] is False
    assert all(
        authority[key] is False
        for key in (
            "docker_desktop_or_daemon_start_authorized",
            "docker_readiness_or_image_pull_authorized",
            "official_pricing_lookup_authorized",
            "sdk_credential_or_endpoint_preflight_authorized",
            "provider_evaluator_or_agent_execution_authorized",
            "runtime_memory_injection_or_retrieval_authorized",
            "execution_hash_or_candidate_authorized",
            "cost_reservation_or_spend_authorized",
            "four_row_ac_execution_authorized",
            "execution_hash_created",
            "execution_candidate_created",
        )
    )
    assert [
        authority["docker_cli_calls_made"],
        authority["docker_desktop_start_count"],
        authority["image_store_mutation_count"],
        authority["pricing_public_get_count"],
        authority["sdk_probe_count"],
        authority["provider_calls_made"],
        authority["evaluator_calls_made"],
        authority["agent_runs_started"],
        authority["runtime_memory_injection_count"],
        authority["retrieval_call_count"],
        authority["cost_reserved_or_spent_usd"],
    ] == [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, "0"]
    assert all(value is False for value in boundary.values() if isinstance(value, bool))
