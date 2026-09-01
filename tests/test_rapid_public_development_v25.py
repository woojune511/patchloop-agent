from __future__ import annotations

import copy
import json
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from patchloop.contracts import RunManifest
from patchloop.errors import ContractError, HarnessAdmissionError, RecoveryError
from patchloop.evals import rapid_public_development_v25 as rapid
from patchloop.evals.rapid_v26_batch_image_binding import (
    frozen_r22_candidate,
    r22_contract_bytes,
    validate_v26_batch_image_binding,
)
from patchloop.evals.rapid_v26_package_binding import (
    CONTRACT_ADMISSION_ADDITIONS,
    REVIEWED_CONTRACT_SHA256,
    V26_REVIEW_FILE_SHA256,
    reviewed_contract_bytes,
)
from patchloop.util import sha256_bytes, sha256_json
from scripts import run_rapid_public_development_v30 as rapid_script

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def forbid_external_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    original_popen = subprocess.Popen

    def blocked(*_args: Any, **_kwargs: Any) -> Any:
        pytest.fail("R22 offline test crossed an external dispatch boundary")

    def local_git_identity_only(args: Any, *rest: Any, **kwargs: Any) -> Any:
        if (
            args == ["git", "rev-parse", "HEAD"]
            and kwargs.get("cwd") == ROOT
            and not kwargs.get("shell", False)
        ):
            return original_popen(args, *rest, **kwargs)
        return blocked(args, *rest, **kwargs)

    monkeypatch.setattr(rapid.DockerSandbox, "available", staticmethod(blocked))
    monkeypatch.setattr(rapid.DockerSandbox, "image_identity", blocked)
    monkeypatch.setattr(rapid.AgentRunner, "start", blocked)
    monkeypatch.setattr(rapid.OpenAIResponsesAdapter, "next_turn", blocked)
    monkeypatch.setattr(rapid.OpenAIResponsesAdapter, "execute_request", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(subprocess, "Popen", local_git_identity_only)


@pytest.fixture
def candidate() -> dict[str, Any]:
    return frozen_r22_candidate(ROOT)


def _rehash(candidate: dict[str, Any]) -> None:
    candidate["schedule_hash"] = sha256_json(candidate["schedule"])
    candidate["cost_control_hash"] = sha256_json(candidate["cost_control"])
    candidate["execution_hash"] = sha256_json(rapid._execution_body(candidate))
    candidate["content_hash"] = sha256_json(
        {k: v for k, v in candidate.items() if k != "content_hash"}
    )


def test_candidate_v30_is_exact_balanced_six_row_package_ab(candidate: dict[str, Any]) -> None:
    assert candidate["candidate_revision"] == 30
    assert candidate["design_kind"] == "balanced-interleaved-product-package-ab"
    assert candidate["official"] is False
    assert candidate["execution_authorized"] is False
    assert candidate["provider_calls_made"] == candidate["docker_calls_made"] == 0
    assert candidate["added_model_cost_usd"] == 0
    assert [(r["order"], r["variant"], r["repetition"]) for r in candidate["schedule"]] == list(
        rapid.EXPECTED_SCHEDULE
    )
    assert candidate["cost_control"]["full_schedule_reserve_nanos"] == 7_200_000_000
    assert candidate["cost_control"]["hard_cap_nanos"] == 7_500_000_000
    evidence = candidate["selection_evidence"]
    assert evidence["consumed_r21"]["retry_allowed"] is False
    decision = evidence["activation_decision"]
    assert decision["adopted"] is True
    assert decision["control_rows"] == decision["treatment_rows"] == 3
    assert decision["single_mechanism_attribution_allowed"] is False
    assert decision["runner_continuity_check_included"] is False
    assert decision["task_successor_created"] is False
    assert rapid.candidate_bytes(candidate) == rapid.candidate_bytes(frozen_r22_candidate(ROOT))


def test_reviewed_package_preserves_runtime_and_historical_bytes() -> None:
    assert validate_v26_batch_image_binding(ROOT)["historical_artifacts_rewritten"] is False
    first = frozen_r22_candidate(ROOT)["selection_evidence"]["treatment_lean_v26"]
    second = frozen_r22_candidate(ROOT)["selection_evidence"]["treatment_lean_v26"]
    assert first == second
    assert first["activation_review"]["file_sha256"] == V26_REVIEW_FILE_SHA256
    delta = first["admission_only_source_delta"]
    assert delta["reviewed"]["file_sha256"] == REVIEWED_CONTRACT_SHA256
    assert delta["exact_addition_count"] == 3
    assert delta["reviewed_bytes_recovered"] is True
    assert delta["agent_policy_changed"] is False
    assert first["historical_artifacts_rewritten"] is False
    assert first["runner_continuity_check_included"] is False


@pytest.mark.parametrize("mutation", ["unrelated", "allowlist", "duplicate", "missing"])
def test_admission_delta_is_an_exact_byte_allowlist_not_normalization(mutation: str) -> None:
    raw = r22_contract_bytes((ROOT / "patchloop/contracts.py").read_bytes())
    assert sha256_bytes(reviewed_contract_bytes(raw)) == REVIEWED_CONTRACT_SHA256
    fragment = CONTRACT_ADMISSION_ADDITIONS[0].encode()
    changed = {
        "unrelated": raw + b"\n# unrelated policy change\n",
        "allowlist": raw.replace(b"20260831-r22", b"20260831-r23"),
        "duplicate": raw + fragment,
        "missing": raw.replace(fragment, b"", 1),
    }[mutation]
    with pytest.raises(RecoveryError, match="admission-only"):
        reviewed_contract_bytes(changed)


def test_reviewed_agent_source_drift_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    read = Path.read_bytes
    target = ROOT / "patchloop/agent/workflow_r21_reliability_successor.py"

    def changed(path: Path) -> bytes:
        raw = read(path)
        return raw + b"\n# drift\n" if path == target else raw

    monkeypatch.setattr(Path, "read_bytes", changed)
    with pytest.raises(RecoveryError, match="Reviewed V26 input changed"):
        validate_v26_batch_image_binding(ROOT)


def test_all_six_manifests_bind_the_two_exact_runtimes_and_equal_resources(
    candidate: dict[str, Any],
) -> None:
    prepared = rapid._prepare_batch(candidate, authority_kind="rehearsal", repository=ROOT)
    assert prepared.verifier_id == rapid.VERIFIER_ID
    assert len(prepared.manifests) == 6
    equal_fields = (
        "task_id",
        "task_version",
        "public_spec_hash",
        "private_spec_hash",
        "base_commit",
        "model",
        "budget",
        "memory",
        "agent_image_digest",
        "evaluator_image_digest",
        "sandbox_backend",
        "created_at",
    )
    first = prepared.manifests[0]
    for row, manifest in zip(candidate["schedule"], prepared.manifests, strict=True):
        runtime = rapid.VARIANT_CONTRACTS[row["variant"]]
        assert manifest.tool_schema_version == runtime["tool_schema_version"]
        assert manifest.context_policy_version == runtime["context_policy_version"]
        for field in equal_fields:
            assert getattr(manifest, field) == getattr(first, field)
        assert rapid.rapid_v25_registered_plan_matches_manifest(
            plan=prepared.plan, manifest=manifest
        )


def test_cross_arm_runtime_tamper_fails_before_capability(candidate: dict[str, Any]) -> None:
    changed = copy.deepcopy(candidate)
    changed["schedule"][0]["tool_schema_version"] = "v27"
    changed["schedule"][0]["context_policy_version"] = "phase-evidence-v36"
    row = changed["schedule"][0]
    row["schedule_row_id"] = sha256_json({k: v for k, v in row.items() if k != "schedule_row_id"})
    _rehash(changed)
    with pytest.raises(HarnessAdmissionError, match="incompatible"):
        rapid._prepare_batch(changed, authority_kind="rehearsal", repository=ROOT)


@pytest.mark.parametrize(
    "field,value",
    [
        ("evaluator_reached_rows_min", 1),
        ("max_mean_settled_cost_ratio", 2.0),
        ("fresh_read_before_correction", False),
        ("quality_claim_allowed", True),
    ],
)
def test_rehashed_relaxed_promotion_gate_is_rejected(
    candidate: dict[str, Any],
    field: str,
    value: Any,
) -> None:
    changed = copy.deepcopy(candidate)
    changed["promotion_criteria"][field] = value
    _rehash(changed)
    with pytest.raises(RecoveryError, match="criteria or cost"):
        rapid.candidate_bytes(changed)


def test_rehashed_schedule_or_cost_drift_is_rejected(candidate: dict[str, Any]) -> None:
    changed = copy.deepcopy(candidate)
    changed["schedule"].reverse()
    _rehash(changed)
    with pytest.raises(RecoveryError, match="identity differs"):
        rapid.candidate_bytes(changed)
    changed = copy.deepcopy(candidate)
    changed["cost_control"]["hard_cap_nanos"] += 1
    _rehash(changed)
    with pytest.raises(RecoveryError, match="criteria or cost"):
        rapid.candidate_bytes(changed)


def test_foreign_runtime_is_rejected_by_manifest_admission(candidate: dict[str, Any]) -> None:
    manifest = rapid.build_rapid_v25_run_manifest(candidate, 2, repository=ROOT)
    payload = manifest.model_dump(mode="python")
    payload["tool_schema_version"] = "v25"
    payload["context_policy_version"] = "phase-evidence-v32"
    with pytest.raises(ValueError):
        RunManifest.model_validate(payload)


def test_two_real_order_rehearsals_cover_both_arms_and_never_dispatch(
    candidate: dict[str, Any],
) -> None:
    # Historical receipt audit only: never rehearse the stopped candidate again.
    raw = (ROOT / rapid.REHEARSAL_PATH).read_bytes()
    assert sha256_bytes(raw) == (
        "sha256:a9718145f65e851081edc440cec15e8fb42471268d8a9d102b0f2f7e274c4388"
    )
    first = json.loads(raw)
    second = json.loads(raw)
    assert first["execution_hash"] == candidate["execution_hash"]
    assert rapid.rehearsal_bytes(first) == rapid.rehearsal_bytes(second)
    assert first["verified_manifest_count"] == 6
    assert first["stage_sequence"] == list(rapid._REHEARSAL_STAGE_SEQUENCE)
    assert first["first_provider_boundary"]["provider_dispatch_blocked"] is True
    assert first["second_provider_boundary"]["provider_dispatch_blocked"] is True
    assert first["inter_row_transition"]["decision_persisted_before_capability"] is True
    for key in (
        "provider_calls_made",
        "docker_calls_made",
        "task_calls_made",
        "evaluator_calls_made",
        "visible_check_calls_made",
    ):
        assert first[key] == 0


@pytest.mark.parametrize("approval,execution_hash", [(False, None), (True, "sha256:" + "0" * 64)])
def test_no_approval_or_wrong_hash_stops_before_any_external_work(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    approval: bool,
    execution_hash: str | None,
) -> None:
    monkeypatch.setattr(rapid, "load_rapid_public_development_v25_candidate", lambda *_: candidate)
    monkeypatch.setattr(rapid, "_result_bundle_path", lambda *_: tmp_path / "unstarted.jsonl")
    with pytest.raises(ContractError, match="exact hash and cost-cap approval"):
        rapid.run_rapid_public_development_v25(
            repository=ROOT, approve_live_cost=approval, approved_execution_hash=execution_hash
        )
    assert not (tmp_path / "unstarted.jsonl").exists()


def test_rehearsal_cli_does_not_load_env_file_or_enter_execute(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected = {"no_call": True}
    missing = tmp_path / "missing.env"
    monkeypatch.setattr(rapid_script, "rehearse_rapid_public_development_v25", lambda **_: expected)
    monkeypatch.setattr(rapid_script, "run_rapid_public_development_v25", lambda **_: pytest.fail())
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_rapid_public_development_v30.py", "--mode", "rehearse", "--env-file", str(missing)],
    )
    rapid_script.main()
    assert json.loads(capsys.readouterr().out) == expected
    assert not missing.exists()
