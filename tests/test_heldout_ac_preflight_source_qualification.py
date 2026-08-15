from __future__ import annotations

import ast
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from patchloop.evals import heldout_ac_preflight_source_qualification as source_q
from patchloop.evals.heldout_ac_preflight_source_qualification import (
    OUTPUT_PATH,
    QUALIFICATION_ID,
    R2_PATH,
    R3_PATH,
    R4_PATH,
    R5_PATH,
    R6_PATH,
    R7_CAMPAIGN_EVIDENCE_PATH,
    R7_PATH,
    R8_PATH,
    R9_PATH,
    R10_PATH,
    R11_CAMPAIGN_EVIDENCE_PATH,
    R11_PATH,
    R12_PATH,
    R13_PATH,
    R14_CAMPAIGN_EVIDENCE_PATH,
    R14_PATH,
    R15_CAMPAIGN_EVIDENCE_PATH,
    R15_PATH,
    SCHEMA_VERSION,
    SOURCE_ENTRYPOINTS,
    STATUS,
    _build_candidate,
    load_heldout_ac_preflight_source_binding,
    run_heldout_ac_preflight_source_qualification,
    validate_heldout_ac_preflight_source_qualification,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def isolated_r16_output(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    relative = Path(".patchloop") / f"heldout-ac-preflight-source-r16-{uuid4().hex}.json"
    selected = ROOT / relative
    assert not selected.exists()
    monkeypatch.setattr(source_q, "OUTPUT_PATH", relative)
    try:
        yield selected
    finally:
        if selected.exists() or selected.is_symlink():
            selected.unlink()


def test_offline_candidate_binds_preflight_closure_without_observation() -> None:
    payload = _build_candidate(
        ROOT,
        recorded_at=datetime(2026, 8, 15, 12, 30, tzinfo=UTC),
    )

    assert payload.status == STATUS
    assert payload.schema_version == SCHEMA_VERSION
    assert payload.schema_version == "heldout-ac-preflight-dispatch-source-qualification-v15"
    assert payload.qualification_id == QUALIFICATION_ID
    assert payload.qualification_id.endswith("20260815-r16")
    assert OUTPUT_PATH.as_posix() == (
        "reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r16.json"
    )
    assert payload.source_entrypoints == tuple(item.as_posix() for item in SOURCE_ENTRYPOINTS)
    assert "patchloop/agent/runner.py" in payload.import_closure
    assert "patchloop/evals/heldout_ac_preflight.py" in payload.import_closure
    assert "patchloop/evals/heldout_ac_preflight_source_qualification.py" in (
        payload.import_closure
    )
    source_paths = {item.path for item in payload.source_files}
    validation_paths = {item.path for item in payload.validation_files}
    assert "patchloop/evals/heldout_ac_r14_campaign_evidence.py" in source_paths
    assert "patchloop/evals/heldout_ac_r15_campaign_evidence.py" in source_paths
    assert "scripts/build_heldout_ac_r14_campaign_evidence.py" in validation_paths
    assert "scripts/build_heldout_ac_r15_campaign_evidence.py" in validation_paths
    assert "tests/test_heldout_ac_r14_runtime_evidence_index.py" in validation_paths
    assert "tests/test_heldout_ac_r15_runtime_evidence_index.py" in validation_paths
    assert payload.projection.scheduled_rows == 48
    assert payload.projection.r15_predecessor_bytes_preserved is True
    assert payload.projection.r15_campaign_inconclusive_index_bound is True
    assert payload.projection.r15_historical_reason_and_post_runtime_attribution_distinct is True
    assert payload.projection.r15_observed_started_cost_bound is True
    assert payload.projection.r15_reauthentication_retry_or_runtime_authority_granted is False
    assert payload.projection.append_only_48_row_dispatcher_bound is True
    assert payload.projection.one_use_campaign_identity_ignores_observed_at is True
    assert payload.projection.atomic_terminal_cost_settlement_bound is True
    assert payload.projection.durable_started_cost_observation_bound is True
    assert payload.projection.typed_evaluator_and_agent_terminal_sidecars_bound is True
    assert payload.projection.persisted_v2_authentication_bound is True
    assert payload.projection.current_candidate_schema == "heldout-ac-execution-candidate-v3"
    assert payload.projection.current_persisted_evidence_schema == (
        "heldout-ac-authenticated-persisted-evidence-v5"
    )
    assert payload.projection.current_persisted_row_schema == (
        "heldout-ac-authenticated-persisted-row-v2"
    )
    assert payload.projection.candidate_v3_realized_schedule_bound is True
    assert payload.projection.candidate_runtime_tuple_recomputed_before_plan_write is True
    assert payload.projection.current_prior_row_requires_persisted_v5_row_v2 is True
    assert payload.projection.prior_row_runtime_cost_usage_budget_revalidated is True
    assert (
        payload.projection.known_r7_r11_r14_r15_exact_result_content_journal_triple_required is True
    )
    assert payload.projection.persisted_campaign_replay_validator_bound is True
    assert payload.projection.historical_v1_campaign_replay_bound is True
    assert payload.projection.current_dispatch_source_loader_bound_without_literal_id is True
    assert payload.projection.preregistered_analysis_unlock_bound is True
    assert payload.projection.official_completion_and_analysis_envelope_persisted is True
    assert payload.projection.execution_candidates_created == 0
    assert payload.projection.approved_plans_created == 0
    assert payload.authority.git_docker_sdk_or_credential_observation_authorized is False
    assert payload.authority.credential_values_observed == 0
    assert payload.authority.provider_calls_made == 0
    assert payload.authority.docker_calls_made == 0
    assert payload.authority.added_model_cost_usd == 0.0


def test_r16_binds_exact_r15_source_and_campaign_predecessors() -> None:
    payload = _build_candidate(
        ROOT,
        recorded_at=datetime(2026, 8, 15, 12, 30, tzinfo=UTC),
    )

    assert payload.predecessor.model_dump(mode="json") == {
        "path": R15_PATH.as_posix(),
        "file_bytes": 24_713,
        "file_sha256": ("sha256:0ed3be6f51213867acc4f27560f87ae33103e5ee60deb237affe942a7ebd6cbc"),
        "source_qualification_hash": (
            "sha256:f0e100d44f713cde134882025481b0038bfb0b4d880f4192e0558dc806e6809c"
        ),
        "evaluator_source_hash": (
            "sha256:d04b90cc92c8888b1e21f6911b201511180230e62db055d5dd5bb4cb3fbac95c"
        ),
        "original_schema_version": "heldout-ac-preflight-dispatch-source-qualification-v14",
        "original_qualification_id": ("core-ac-fixed-bundle-heldout-preflight-source-20260815-r15"),
        "original_status": STATUS,
        "successor_reason": "r15-campaign-inconclusive-v2-terminal-result-binding-successor",
    }
    campaign = payload.campaign_predecessor
    assert campaign.path == R15_CAMPAIGN_EVIDENCE_PATH.as_posix()
    assert campaign.file_bytes == 12_209
    assert campaign.file_sha256 == (
        "sha256:7aaca2be0797ea36f12e125dc85dd582bdc5f63ad5afd7449cc2d2cf77d46c54"
    )
    assert campaign.content_hash == (
        "sha256:85b211c637eeff05805c8bef1ba3790a6beab8cef98a8680c48fa74f496a56eb"
    )
    assert campaign.approval_consumed is True
    assert campaign.disposition == "inconclusive-matrix"
    assert campaign.terminal_settled_runs == 2
    assert campaign.observed_unsettled_runs == 1
    assert campaign.not_started_runs == 45
    assert campaign.settled_model_cost_nanos == 200_233_500
    assert campaign.observed_unsettled_model_cost_nanos == 911_878_500
    assert campaign.observed_started_model_cost_nanos == 1_112_112_000
    assert campaign.historical_reason_code == "DURABLE_EVIDENCE_AUTHENTICATION_FAILED"
    assert campaign.post_runtime_attribution_code == (
        "TRACE_QUALIFICATION_V2_TERMINAL_RESULT_SCHEMA_MISMATCH"
    )
    assert campaign.historical_reason_preserved_without_relabeling is True
    assert campaign.historical_typed_diagnosis_code_observed is False
    assert campaign.post_runtime_deterministic_attribution is True
    assert campaign.post_runtime_attribution_changes_historical_reason is False
    assert campaign.historical_row_reclassified is False
    assert campaign.attribution_only is True
    assert campaign.r15_campaign_is_immutable_and_consumed is True
    assert campaign.historical_runtime_files_mutated is False
    assert campaign.historical_row_reauthentication_authorized is False
    assert campaign.retry_replacement_or_resume_performed is False
    assert campaign.candidate_creation_authorized is False
    assert campaign.future_execution_authorized is False
    assert campaign.future_spend_authorized is False


def test_r16_does_not_hardcode_or_reverse_import_future_execution_source_r8() -> None:
    source = (ROOT / "patchloop/evals/heldout_ac_preflight_source_qualification.py").read_text(
        encoding="utf-8"
    )
    imported_modules = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert "patchloop.evals.heldout_ac_execution_source_qualification" not in imported_modules
    assert "heldout-ac-execution-source-qualification-r8.json" not in source


def test_r2_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R2_PATH
    assert len(selected.read_bytes()) == 15_725
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:5a06587069932599fd18aa7c2a3e72be098ccc0887b3b5906a6f5a0891391589"
    )


def test_r3_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R3_PATH
    assert len(selected.read_bytes()) == 18_334
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:88831118d5da9b9d0a826a49ef585a3532195003e78f8cb67c8b243ba4d4ff16"
    )


def test_r4_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R4_PATH
    assert len(selected.read_bytes()) == 18_354
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:5616484bc441baad27d5edd435aacdec7be292141a2f68b30bf9ae6dd9a45100"
    )


def test_r5_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R5_PATH
    assert len(selected.read_bytes()) == 18_415
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:6a46651ed3774ae3192e5674c57452220306d191f1f98ab76626e1cf5798bf5b"
    )


def test_r6_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R6_PATH
    assert len(selected.read_bytes()) == 18_413
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:10ccf88e9255c6ae0a0d8246ca8f2d478137bac03b7ffd7e6f59d23b938e942b"
    )


def test_r7_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R7_PATH
    assert len(selected.read_bytes()) == 18_414
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:d4bf85b1d0e26bc9a6f2bdc9fb809ab6ca04020d6cf9f766ba194b56773581c7"
    )


def test_r7_campaign_evidence_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R7_CAMPAIGN_EVIDENCE_PATH
    assert len(selected.read_bytes()) == 7_854
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:dd50a53a1c19e1214a575c3b37b82400b8961bf9a38e72f39a2aa87b3390b906"
    )


def test_r8_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R8_PATH
    assert len(selected.read_bytes()) == 19_351
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:296716c801a627e05d45755f0cf6f164f1296c91c5084715f59b3d1f446e7fd3"
    )


def test_r9_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R9_PATH
    assert len(selected.read_bytes()) == 19_353
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:e72c619c0ec0272694f7a9edf1dadb39b9b4fcffa0ebedcf17dcc4ba3e355854"
    )


def test_r10_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R10_PATH
    assert len(selected.read_bytes()) == 19_353
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:7b3382208d57f14ba5929d405464c49bb81137bac56043583764889b73d96f21"
    )


def test_r11_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R11_PATH
    assert len(selected.read_bytes()) == 19_359
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:45b21684520968903ab57afc7a4e0d9f4e66022ad0752140d24b988ba0df747f"
    )


def test_r11_campaign_correction_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R11_CAMPAIGN_EVIDENCE_PATH
    assert len(selected.read_bytes()) == 18_525
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:1badf8a78ba142f9868a3b9e836fa83df7beb0248f9c5e745fd205fd0185f48c"
    )


def test_r12_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R12_PATH
    assert len(selected.read_bytes()) == 21_550
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:21d38740e1c69c60204bf234f4a75502cf4b0fe549780914cb8e2789db9cb9f9"
    )


def test_r13_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R13_PATH
    assert len(selected.read_bytes()) == 21_539
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:f55cf62163b68f0a5d1d890a58b54dfa31f60ed90ac0da466bfe9b08e35b922f"
    )


def test_r14_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R14_PATH
    assert len(selected.read_bytes()) == 21_984
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:259407d7c30113096844541b01f93ea18e78c5dd0d471c261311657acd7135a3"
    )


def test_r14_campaign_index_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R14_CAMPAIGN_EVIDENCE_PATH
    assert len(selected.read_bytes()) == 12_856
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:21cda8f99aa835b196aa54cc6f7ad2483942f43d986fd935ce511a0d6974cd7b"
    )


def test_r15_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R15_PATH
    assert len(selected.read_bytes()) == 24_713
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:0ed3be6f51213867acc4f27560f87ae33103e5ee60deb237affe942a7ebd6cbc"
    )


def test_r15_campaign_index_predecessor_bytes_are_preserved() -> None:
    selected = ROOT / R15_CAMPAIGN_EVIDENCE_PATH
    assert len(selected.read_bytes()) == 12_209
    assert sha256_bytes(selected.read_bytes()) == (
        "sha256:7aaca2be0797ea36f12e125dc85dd582bdc5f63ad5afd7449cc2d2cf77d46c54"
    )


def test_preflight_source_artifact_replays_and_exports_binding(
    isolated_r16_output: Path,
) -> None:
    created = run_heldout_ac_preflight_source_qualification(repository=ROOT)
    summary = validate_heldout_ac_preflight_source_qualification(repository=ROOT)
    binding = load_heldout_ac_preflight_source_binding(repository=ROOT)
    raw = isolated_r16_output.read_bytes()

    assert summary == created
    assert summary["status"] == STATUS
    assert summary["source_qualification_hash"] == binding.source_qualification_hash
    assert summary["evaluator_source_hash"] == binding.evaluator_source_hash
    assert binding.qualification_file.file_bytes == len(raw)
    assert binding.qualification_file.file_sha256 == sha256_bytes(raw)
    assert summary["execution_candidate_created"] is False
    assert summary["approved_plan_created"] is False
    assert summary["campaign_journal_created"] is False
    assert summary["credential_values_observed"] == 0
    assert summary["provider_calls_made"] == 0


def test_preflight_source_rerun_is_byte_and_mtime_stable(isolated_r16_output: Path) -> None:
    selected = isolated_r16_output
    run_heldout_ac_preflight_source_qualification(repository=ROOT)
    before = selected.read_bytes()
    before_mtime = selected.stat().st_mtime_ns
    summary = run_heldout_ac_preflight_source_qualification(repository=ROOT)

    assert summary["status"] == STATUS
    assert selected.read_bytes() == before
    assert selected.stat().st_mtime_ns == before_mtime


def test_preflight_source_rejects_rehashed_authority_escalation() -> None:
    payload = _build_candidate(
        ROOT,
        recorded_at=datetime(2026, 8, 15, 12, 30, tzinfo=UTC),
    )
    body = payload.model_dump(mode="json")
    body["authority"]["provider_evaluator_or_agent_execution_authorized"] = True
    with pytest.raises(ValidationError):
        type(payload).model_validate(body)


def test_preflight_source_qualification_does_not_observe_runtime_surfaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import patchloop.environment as environment
    import patchloop.sandbox.runner as sandbox_runner

    def bomb(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("source qualification crossed a no-call runtime boundary")

    monkeypatch.setattr(environment, "exact_openai_api_key_present", bomb)
    monkeypatch.setattr(sandbox_runner.DockerSandbox, "available", bomb)
    payload = _build_candidate(
        ROOT,
        recorded_at=datetime(2026, 8, 15, 12, 30, tzinfo=UTC),
    )
    assert payload.authority.sdk_calls_made == 0
    assert payload.authority.docker_calls_made == 0
