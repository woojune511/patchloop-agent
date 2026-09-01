from __future__ import annotations

import socket
import subprocess
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from patchloop.evals.fresh_acquisition_preregistration import SAME_REPOSITORY_TARGETS
from patchloop.evals.fresh_candidate_registry import (
    FileBinding,
    FreshPublicSourceSnapshot,
    PublicCandidateRow,
    QualifiedFreshCandidateRegistry,
    QualifiedRegistryAuthority,
    build_fresh_candidate_registry,
    public_row_hash,
    source_snapshot_bytes,
)
from patchloop.evals.fresh_task_admission import (
    AdmissionAttempt,
    FreshTaskAdmissionError,
    FreshTaskAdmissionProjection,
    RemainingIdentityAudit,
    TaskPackageBinding,
    admission_attempt,
    admission_evidence,
    project_fresh_task_admission,
    task_admission_projection_bytes,
)
from patchloop.util import sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def _sha(value: int) -> str:
    return "sha256:" + f"{value:064x}"


def _row(ordinal: int, *, instance_id: str, repository: str) -> PublicCandidateRow:
    owner, repo = repository.split("/", 1)
    body = {
        "source_ordinal": ordinal,
        "canonical_public_instance_id": instance_id,
        "upstream_repository": repository,
        "issue_or_pull_request_url": f"https://github.com/{owner}/{repo}/pull/{2000 + ordinal}",
        "upstream_base_commit": f"{ordinal * 2:040x}",
        "resolution_commit": f"{ordinal * 2 + 1:040x}",
        "issue_created_at": "2026-04-01T00:00:00Z",
        "resolution_merged_at": "2026-04-02T00:00:00Z",
        "license_spdx": "Apache-2.0",
        "license_compatibility": "pass",
        "public_difficulty_tier": "hard",
        "environment_image": f"registry.example/{owner}/{repo}@sha256:{ordinal:064x}",
    }
    return PublicCandidateRow(**body, public_row_hash=public_row_hash(body))


def _rows() -> tuple[PublicCandidateRow, ...]:
    rows: list[PublicCandidateRow] = []
    for target_index, repository in enumerate(SAME_REPOSITORY_TARGETS):
        candidate_count = 3 if target_index == 0 else 1
        for candidate_index in range(candidate_count):
            rows.append(
                _row(
                    len(rows) + 1,
                    instance_id=f"same-{target_index + 1}-{candidate_index + 1}-fresh",
                    repository=repository,
                )
            )
    for candidate_index in range(20):
        rows.append(
            _row(
                len(rows) + 1,
                instance_id=f"neworg1-{candidate_index:02d}-fresh",
                repository="neworg1/newrepo1",
            )
        )
    for repository_index in range(2, 7):
        rows.append(
            _row(
                len(rows) + 1,
                instance_id=f"neworg{repository_index}-00-fresh",
                repository=f"neworg{repository_index}/newrepo{repository_index}",
            )
        )
    return tuple(rows)


def _snapshot(rows: tuple[PublicCandidateRow, ...]) -> FreshPublicSourceSnapshot:
    body = {
        "schema_version": "lean-fresh-public-source-snapshot-v1",
        "snapshot_id": "task-admission-synthetic-2026-08",
        "candidate_source_family": "SWE-rebench-leaderboard",
        "source_url": "https://example.invalid/task-admission-snapshot",
        "source_revision": "d" * 40,
        "source_published_at": "2026-08-17T00:00:00Z",
        "source_window_start_exclusive": "2026-03-17T23:59:59Z",
        "source_window_end_inclusive": "2026-08-16T23:59:59Z",
        "immutable_revision_asserted": True,
        "earliest_qualifying_revision_asserted": True,
        "complete_frozen_window_asserted": True,
        "raw_source_file_bytes": 234_567,
        "raw_source_file_sha256": _sha(100),
        "normalization_rule": (
            "public-identity-provenance-difficulty-license-and-image-fields-only-v1"
        ),
        "query_universe": "every-row-in-bound-immutable-source-snapshot",
        "solution_or_test_patch_fields_included": False,
        "oracle_fields_included": False,
        "private_fields_included": False,
        "external_completeness_assertions_qualified": False,
        "raw_source_row_count": len(rows),
        "declared_source_row_count": len(rows),
        "rows": rows,
    }
    hashed = {
        key: [row.model_dump(mode="json") for row in value] if key == "rows" else value
        for key, value in body.items()
    }
    return FreshPublicSourceSnapshot(**body, content_hash=sha256_json(hashed))


def _qualified_registry(tmp_path: Path) -> QualifiedFreshCandidateRegistry:
    snapshot_path = tmp_path / "task-admission-source.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_bytes(source_snapshot_bytes(_snapshot(_rows())))
    projection = build_fresh_candidate_registry(
        REPOSITORY, snapshot_path.relative_to(REPOSITORY).as_posix()
    )
    body: dict[str, Any] = {
        "schema_version": "lean-fresh-qualified-public-candidate-registry-v1",
        "registry_id": projection.registry_id.replace(
            "lean-fresh-candidate-registry-",
            "lean-fresh-qualified-candidate-registry-",
            1,
        ),
        "status": "QUALIFIED_PUBLIC_REGISTRY_TASK_ADMISSION_PENDING",
        "source_completeness_qualification_binding": FileBinding(
            path="experiments/synthetic-source-completeness-qualification.json",
            file_bytes=1,
            file_sha256=_sha(101),
            content_hash=_sha(102),
            role="raw-source-completeness-qualification",
        ),
        "projection": projection,
        "authority": QualifiedRegistryAuthority(
            raw_source_completeness_qualification_files_read=1,
            selector_raw_source_files_read=0,
            task_package_files_read=0,
            private_task_files_read=0,
            oracle_or_reference_patch_fields_read=0,
            r16_row_outcomes_or_traces_read=0,
            network_calls=0,
            docker_calls=0,
            provider_calls=0,
            evaluator_calls=0,
            agent_runs=0,
            added_model_cost_usd=0,
            source_snapshot_externally_qualified=True,
            candidate_registry_qualified=True,
            task_admission_authorized=False,
            fresh_task_panel_materialized=False,
            full_experiment_preregistered=False,
            candidate_created=False,
            approval_granted=False,
            execution_authorized=False,
            official_analysis_authorized=False,
            memory_effect_claim_authorized=False,
        ),
        "next_gate": (
            "audit-the-qualified-public-transcript-before-any-task-package-private-evaluator-"
            "or-runtime-activation"
        ),
    }
    hashed = {
        key: value.model_dump(mode="json") if isinstance(value, BaseModel) else value
        for key, value in body.items()
    }
    return QualifiedFreshCandidateRegistry(**body, content_hash=sha256_json(hashed))


def _evidence(
    *,
    token: int,
    manifest_sha256: str,
    difficulty: str = "hard",
    reference_passes: int = 3,
    bad_patches: int = 8,
    base_visible: str = "PASS",
    base_hidden: str = "FAIL",
    reference_visible: str = "PASS",
    reference_hidden: str = "PASS",
    reference_scope: str = "PASS",
    reference_safety: str = "PASS",
    package: TaskPackageBinding | None | object = ...,
    identity: RemainingIdentityAudit | None | object = ...,
    license_compatible: bool = True,
    confound_code: str | None = None,
):
    if confound_code is not None:
        return admission_evidence(
            audit_completed=False,
            confound_code=confound_code,
            difficulty_tier="not-run",
            official_reference_pass_count=0,
            rejected_bad_patch_count=0,
            base_visible_verdict="NOT_RUN",
            base_hidden_verdict="NOT_RUN",
            reference_visible_verdict="NOT_RUN",
            reference_hidden_verdict="NOT_RUN",
            reference_scope_verdict="NOT_RUN",
            reference_safety_verdict="NOT_RUN",
            task_package_binding=None,
            remaining_identity_audit=None,
            license_compatible=False,
            producer_source_hash=_sha(900),
            producer_validation_hash=_sha(901),
        )
    default_package = TaskPackageBinding(
        task_id=f"fresh-task-{token}",
        task_version=1,
        task_path=f"tasks/fresh/fresh-task-{token}",
        environment_image=f"registry.example/fresh@sha256:{token + 1000:064x}",
        public_spec_sha256=_sha(token + 2000),
        private_spec_sha256=_sha(token + 3000),
        evaluator_contract_hash=_sha(token + 4000),
        task_package_hash=_sha(token + 5000),
    )
    selected_package = default_package if package is ... else package
    default_identity = RemainingIdentityAudit(
        comparison_manifest_file_sha256=manifest_sha256,
        task_id_and_version_disjoint=True,
        solution_lineage_id=f"fresh-solution-lineage-{token}",
        solution_lineage_disjoint=True,
        public_spec_hash_disjoint=True,
        private_spec_hash_disjoint=True,
    )
    selected_identity = default_identity if identity is ... else identity
    return admission_evidence(
        audit_completed=True,
        confound_code=None,
        difficulty_tier=difficulty,
        official_reference_pass_count=reference_passes,
        rejected_bad_patch_count=bad_patches,
        base_visible_verdict=base_visible,
        base_hidden_verdict=base_hidden,
        reference_visible_verdict=reference_visible,
        reference_hidden_verdict=reference_hidden,
        reference_scope_verdict=reference_scope,
        reference_safety_verdict=reference_safety,
        task_package_binding=selected_package,
        remaining_identity_audit=selected_identity,
        license_compatible=license_compatible,
        producer_source_hash=_sha(900),
        producer_validation_hash=_sha(901),
    )


def _attempt(
    registry: QualifiedFreshCandidateRegistry,
    *,
    sequence: int,
    stratum: str,
    target: str | None,
    position: int,
    candidate_id: str,
    evidence=None,
) -> AdmissionAttempt:
    candidate = next(
        row
        for row in registry.projection.ranked_candidates
        if row.canonical_public_instance_id == candidate_id
    )
    selected_evidence = evidence or _evidence(
        token=sequence,
        manifest_sha256=registry.projection.current_manifest_binding.file_sha256,
    )
    return admission_attempt(
        sequence=sequence,
        stratum=stratum,
        same_repository_target=target,
        queue_position=position,
        canonical_public_instance_id=candidate.canonical_public_instance_id,
        upstream_repository=candidate.upstream_repository,
        ranking_hash=candidate.ranking_hash,
        public_row_hash=candidate.public_row_hash,
        evidence=selected_evidence,
    )


def _complete_attempts(registry: QualifiedFreshCandidateRegistry) -> tuple[AdmissionAttempt, ...]:
    attempts: list[AdmissionAttempt] = []
    sequence = 1
    for target_index, target in enumerate(SAME_REPOSITORY_TARGETS):
        for position, candidate_id in enumerate(
            registry.projection.same_repository_queues[target], start=1
        ):
            evidence = _evidence(
                token=sequence,
                manifest_sha256=registry.projection.current_manifest_binding.file_sha256,
                difficulty="easy" if target_index == 0 and position == 1 else "hard",
            )
            attempts.append(
                _attempt(
                    registry,
                    sequence=sequence,
                    stratum="same",
                    target=target,
                    position=position,
                    candidate_id=candidate_id,
                    evidence=evidence,
                )
            )
            sequence += 1
            if evidence.difficulty_tier == "hard":
                break
    accepted_cross: set[str] = set()
    for position, candidate_id in enumerate(registry.projection.cross_repository_queue, start=1):
        attempt = _attempt(
            registry,
            sequence=sequence,
            stratum="cross",
            target=None,
            position=position,
            candidate_id=candidate_id,
        )
        attempts.append(attempt)
        sequence += 1
        accepted_cross.add(attempt.upstream_repository)
        if len(accepted_cross) == 6:
            break
    return tuple(attempts)


def _replace_evidence(attempt: AdmissionAttempt, **changes: Any) -> AdmissionAttempt:
    attempt_body = attempt.model_dump(mode="json", exclude={"attempt_hash"})
    evidence_body = attempt_body["evidence"]
    evidence_body.update(changes)
    evidence_body.pop("evidence_hash", None)
    evidence_body["evidence_hash"] = sha256_json(evidence_body)
    attempt_body["evidence"] = evidence_body
    return AdmissionAttempt(**attempt_body, attempt_hash=sha256_json(attempt_body))


def test_complete_projection_follows_frozen_queues_and_stays_unqualified(
    tmp_path: Path,
) -> None:
    registry = _qualified_registry(tmp_path)
    value = project_fresh_task_admission(registry, _complete_attempts(registry))

    assert value.status == "OFFLINE_TASK_ADMISSION_PROJECTION_COMPLETE_UNQUALIFIED"
    assert value.accepted_same_repository_count == 6
    assert value.accepted_cross_repository_count == 6
    assert value.complete_panel_shape_present is True
    assert any(row.rejection_code == "cross-repository-already-admitted" for row in value.decisions)
    assert value.decisions[0].rejection_code == "below-medium-difficulty-audit"
    assert value.authority.task_admission_evidence_source_qualified is False
    assert value.authority.task_admission_authorized is False
    assert value.authority.fresh_task_panel_materialized is False
    assert value.authority.execution_authorized is False


def test_attempt_skip_or_reorder_fails_closed(tmp_path: Path) -> None:
    registry = _qualified_registry(tmp_path)
    attempts = _complete_attempts(registry)

    with pytest.raises(FreshTaskAdmissionError, match="skips or reorders"):
        project_fresh_task_admission(registry, attempts[1:])


@pytest.mark.parametrize(
    ("changes", "expected_code"),
    [
        ({"difficulty_tier": "easy"}, "below-medium-difficulty-audit"),
        ({"official_reference_pass_count": 2}, "reference-pass-count-insufficient"),
        ({"rejected_bad_patch_count": 7}, "bad-patch-rejection-count-insufficient"),
        ({"base_hidden_verdict": "PASS"}, "base-visible-hidden-contract-failed"),
        ({"reference_safety_verdict": "FAIL"}, "reference-verdict-bundle-failed"),
        ({"task_package_binding": None}, "task-binding-incomplete"),
        ({"remaining_identity_audit": None}, "remaining-identity-overlap"),
        ({"license_compatible": False}, "license-incompatible"),
    ],
)
def test_each_admission_gate_has_a_typed_rejection(
    tmp_path: Path,
    changes: dict[str, Any],
    expected_code: str,
) -> None:
    registry = _qualified_registry(tmp_path)
    attempts = list(_complete_attempts(registry))
    target = SAME_REPOSITORY_TARGETS[1]
    selected = next(
        index for index, attempt in enumerate(attempts) if attempt.same_repository_target == target
    )
    attempts[selected] = _replace_evidence(attempts[selected], **changes)

    value = project_fresh_task_admission(registry, attempts[: selected + 1])

    assert value.status == "OFFLINE_TASK_ADMISSION_PROJECTION_STOPPED_INSUFFICIENT_UNQUALIFIED"
    assert value.decisions[-1].rejection_code == expected_code
    assert value.accepted_same_repository_count == 1
    assert value.accepted_cross_repository_count == 0


def test_infrastructure_confound_stops_without_continuation(tmp_path: Path) -> None:
    registry = _qualified_registry(tmp_path)
    attempts = list(_complete_attempts(registry))
    attempts[0] = _replace_evidence(
        attempts[0],
        audit_completed=False,
        confound_code="evaluator-qualification-failed",
        difficulty_tier="not-run",
        official_reference_pass_count=0,
        rejected_bad_patch_count=0,
        base_visible_verdict="NOT_RUN",
        base_hidden_verdict="NOT_RUN",
        reference_visible_verdict="NOT_RUN",
        reference_hidden_verdict="NOT_RUN",
        reference_scope_verdict="NOT_RUN",
        reference_safety_verdict="NOT_RUN",
        task_package_binding=None,
        remaining_identity_audit=None,
        license_compatible=False,
    )

    value = project_fresh_task_admission(registry, attempts[:1])
    assert value.status == "OFFLINE_TASK_ADMISSION_PROJECTION_STOPPED_CONFOUNDED_UNQUALIFIED"
    assert value.decisions[0].confound_code == "evaluator-qualification-failed"

    with pytest.raises(FreshTaskAdmissionError, match="continues after"):
        project_fresh_task_admission(registry, attempts[:2])


def test_manifest_identity_drift_and_new_panel_duplicate_are_rejected(tmp_path: Path) -> None:
    registry = _qualified_registry(tmp_path)
    attempts = list(_complete_attempts(registry))
    target = SAME_REPOSITORY_TARGETS[1]
    selected = next(
        index for index, attempt in enumerate(attempts) if attempt.same_repository_target == target
    )
    identity = attempts[selected].evidence.remaining_identity_audit
    assert identity is not None
    attempts[selected] = _replace_evidence(
        attempts[selected],
        remaining_identity_audit={
            **identity.model_dump(mode="json"),
            "comparison_manifest_file_sha256": _sha(9999),
        },
    )
    drift = project_fresh_task_admission(registry, attempts[: selected + 1])
    assert drift.decisions[-1].rejection_code == "remaining-identity-overlap"

    attempts = list(_complete_attempts(registry))
    first_accepted = next(row for row in attempts if row.evidence.difficulty_tier == "hard")
    selected = next(
        index for index, attempt in enumerate(attempts) if attempt.same_repository_target == target
    )
    attempts[selected] = _replace_evidence(
        attempts[selected],
        task_package_binding=first_accepted.evidence.task_package_binding.model_dump(mode="json"),
        remaining_identity_audit=(
            first_accepted.evidence.remaining_identity_audit.model_dump(mode="json")
        ),
    )
    duplicate = project_fresh_task_admission(registry, attempts[: selected + 1])
    assert duplicate.decisions[-1].rejection_code == "remaining-identity-overlap"


def test_projection_is_io_free_and_contains_hashes_not_private_contents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = _qualified_registry(tmp_path)
    attempts = _complete_attempts(registry)

    def bomb(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("task admission projection attempted external I/O")

    monkeypatch.setattr(Path, "read_bytes", bomb)
    monkeypatch.setattr(socket, "create_connection", bomb)
    monkeypatch.setattr(subprocess, "Popen", bomb)
    value = project_fresh_task_admission(registry, attempts)
    raw = task_admission_projection_bytes(value)

    assert b"private_spec_sha256" in raw
    assert b"solution_patch" not in raw
    assert b'"reference_patch":' not in raw
    assert b"hidden_assertion" not in raw
    assert value.authority.consumer_private_task_files_read == 0
    assert value.authority.docker_calls == value.authority.provider_calls == 0


def test_rehashed_projection_semantic_drift_and_extra_fields_are_rejected(
    tmp_path: Path,
) -> None:
    registry = _qualified_registry(tmp_path)
    value = project_fresh_task_admission(registry, _complete_attempts(registry))
    body = value.model_dump(mode="json")
    body["accepted_same_repository_count"] = 5
    body["content_hash"] = sha256_json(
        {key: item for key, item in body.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError, match="decision counts differ"):
        FreshTaskAdmissionProjection.model_validate(body)

    evidence = value.decisions[0].model_dump(mode="json")
    evidence["unexpected"] = True
    with pytest.raises(ValidationError, match="Extra inputs"):
        type(value.decisions[0]).model_validate(evidence)
