from __future__ import annotations

import json
import socket
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

import patchloop.evals.fresh_candidate_registry as registry_module
from patchloop.errors import ContractError
from patchloop.evals.fresh_acquisition_preregistration import SAME_REPOSITORY_TARGETS
from patchloop.evals.fresh_candidate_registry import (
    FreshCandidateRegistry,
    FreshCandidateRegistryError,
    FreshPublicSourceSnapshot,
    PublicCandidateRow,
    build_fresh_candidate_registry,
    load_fresh_candidate_registry,
    load_public_source_snapshot,
    materialize_fresh_candidate_registry,
    public_row_hash,
    registry_bytes,
    source_snapshot_bytes,
)
from patchloop.util import sha256_bytes, sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def _row(
    ordinal: int,
    *,
    instance_id: str,
    repository: str,
    created_at: str = "2026-04-01T00:00:00Z",
    merged_at: str = "2026-04-02T00:00:00Z",
    difficulty: str = "hard",
    license_compatibility: str = "pass",
) -> PublicCandidateRow:
    owner, repo = repository.split("/", 1)
    body = {
        "source_ordinal": ordinal,
        "canonical_public_instance_id": instance_id,
        "upstream_repository": repository,
        "issue_or_pull_request_url": f"https://github.com/{owner}/{repo}/pull/{1000 + ordinal}",
        "upstream_base_commit": f"{ordinal * 2:040x}",
        "resolution_commit": f"{ordinal * 2 + 1:040x}",
        "issue_created_at": created_at,
        "resolution_merged_at": merged_at,
        "license_spdx": "Apache-2.0",
        "license_compatibility": license_compatibility,
        "public_difficulty_tier": difficulty,
        "environment_image": f"registry.example/{owner}/{repo}@sha256:{ordinal:064x}",
    }
    return PublicCandidateRow(**body, public_row_hash=public_row_hash(body))


def _qualifying_rows() -> tuple[PublicCandidateRow, ...]:
    rows: list[PublicCandidateRow] = []
    for index, repository in enumerate(SAME_REPOSITORY_TARGETS, start=1):
        rows.append(
            _row(
                index,
                instance_id=f"same-{index}-fresh",
                repository=repository,
            )
        )
    for index in range(6):
        ordinal = len(rows) + 1
        rows.append(
            _row(
                ordinal,
                instance_id=f"cross-{index + 1}-fresh",
                repository=f"neworg{index + 1}/newrepo{index + 1}",
            )
        )
    return tuple(rows)


def _mixed_rows() -> tuple[PublicCandidateRow, ...]:
    rows = list(_qualifying_rows())
    rows.extend(
        [
            _row(
                len(rows) + 1,
                instance_id="same-one-alternative",
                repository=SAME_REPOSITORY_TARGETS[0],
            ),
            _row(
                len(rows) + 2,
                instance_id="cross-one-alternative",
                repository="neworg1/newrepo1",
            ),
            _row(
                len(rows) + 3,
                instance_id="dagster-io__dagster-33605",
                repository="brandnew/identity-overlap",
            ),
            _row(
                len(rows) + 4,
                instance_id="outside-window",
                repository="outside/window",
                created_at="2026-03-01T00:00:00Z",
                merged_at="2026-03-02T00:00:00Z",
            ),
            _row(
                len(rows) + 5,
                instance_id="easy-candidate",
                repository="easy/repository",
                difficulty="easy",
            ),
            _row(
                len(rows) + 6,
                instance_id="license-failed",
                repository="license/repository",
                license_compatibility="fail",
            ),
            _row(
                len(rows) + 7,
                instance_id="existing-nontarget-repo",
                repository="getmoto/moto",
            ),
        ]
    )
    return tuple(rows)


def _snapshot(rows: tuple[PublicCandidateRow, ...]) -> FreshPublicSourceSnapshot:
    body = {
        "schema_version": "lean-fresh-public-source-snapshot-v1",
        "snapshot_id": "synthetic-2026-08",
        "candidate_source_family": "SWE-rebench-leaderboard",
        "source_url": "https://example.invalid/public-snapshot",
        "source_revision": "f" * 40,
        "source_published_at": "2026-08-17T00:00:00Z",
        "source_window_start_exclusive": "2026-03-17T23:59:59Z",
        "source_window_end_inclusive": "2026-08-16T23:59:59Z",
        "immutable_revision_asserted": True,
        "earliest_qualifying_revision_asserted": True,
        "complete_frozen_window_asserted": True,
        "raw_source_file_bytes": 123_456,
        "raw_source_file_sha256": "sha256:" + "a" * 64,
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


def _write_snapshot(path: Path, rows: tuple[PublicCandidateRow, ...]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(source_snapshot_bytes(_snapshot(rows)))
    return path.relative_to(REPOSITORY).as_posix()


def _reordinal(rows: tuple[PublicCandidateRow, ...]) -> tuple[PublicCandidateRow, ...]:
    result: list[PublicCandidateRow] = []
    for ordinal, row in enumerate(rows, start=1):
        body = row.model_dump(mode="json", exclude={"public_row_hash"})
        body["source_ordinal"] = ordinal
        result.append(PublicCandidateRow(**body, public_row_hash=public_row_hash(body)))
    return tuple(result)


def _build(
    tmp_path: Path, rows: tuple[PublicCandidateRow, ...] | None = None
) -> FreshCandidateRegistry:
    source_path = _write_snapshot(tmp_path / "source.json", rows or _mixed_rows())
    return build_fresh_candidate_registry(REPOSITORY, source_path)


def test_complete_public_transcript_builds_deterministic_admission_queues(
    tmp_path: Path,
) -> None:
    value = _build(tmp_path)

    assert value.status == "OFFLINE_PUBLIC_REGISTRY_PROJECTION_ADMISSION_PENDING"
    assert value.source_row_count == 19
    assert value.queued_candidate_count == 14
    assert value.rejected_row_count == 5
    assert value.distinct_cross_repository_count == 6
    assert value.public_pool_sufficient_for_admission is True
    assert all(value.same_repository_queues[repo] for repo in SAME_REPOSITORY_TARGETS)
    assert len(value.cross_repository_queue) == 7
    assert len(value.query_transcript) == value.source_row_count

    cross_hashes = {
        row.canonical_public_instance_id: row.ranking_hash
        for row in value.ranked_candidates
        if row.stratum == "cross"
    }
    assert list(value.cross_repository_queue) == sorted(
        value.cross_repository_queue,
        key=lambda instance: (cross_hashes[instance], instance),
    )


def test_public_filter_rejections_are_typed_and_complete(tmp_path: Path) -> None:
    value = _build(tmp_path)
    rejections = {
        row.canonical_public_instance_id: row.rejection_code
        for row in value.query_transcript
        if row.decision == "rejected"
    }

    assert rejections == {
        "dagster-io__dagster-33605": "current-manifest-source-identity-overlap",
        "outside-window": "outside-frozen-source-window",
        "easy-candidate": "below-medium-difficulty",
        "license-failed": "license-incompatible",
        "existing-nontarget-repo": "existing-nontarget-repository",
    }


def test_task_admission_and_source_qualification_remain_closed(tmp_path: Path) -> None:
    value = _build(tmp_path)
    authority = value.authority

    assert value.task_admission_state == "pending-task-package-private-evaluator-and-identity-audit"
    assert value.query_transcript_scope.endswith("task-admission-rejections-not-yet-observed")
    assert value.admission_queue_policy.cross_repository_target_count == 6
    assert len(value.admission_queue_policy.full_admission_requires) == 8
    assert value.pending_admission_identity_dimensions == (
        "task-id-and-version",
        "solution-lineage-id",
        "public-or-private-spec-hash",
    )
    assert authority.offline_registry_projection_created is True
    assert authority.source_snapshot_externally_qualified is False
    assert authority.candidate_registry_qualified is False
    assert authority.task_admission_authorized is False
    assert authority.task_package_files_read == 0
    assert authority.oracle_or_reference_patch_fields_read == 0
    assert authority.network_calls == authority.provider_calls == 0
    assert authority.docker_calls == authority.evaluator_calls == authority.agent_runs == 0
    assert authority.execution_authorized is False
    assert authority.official_analysis_authorized is False


def test_insufficient_pool_stops_without_relaxation(tmp_path: Path) -> None:
    rows = _reordinal(
        tuple(
            row
            for row in _qualifying_rows()
            if row.upstream_repository != SAME_REPOSITORY_TARGETS[-1]
        )
    )
    value = _build(tmp_path, rows)

    assert value.status == "OFFLINE_PUBLIC_REGISTRY_PROJECTION_INSUFFICIENT_POOL"
    assert value.public_pool_sufficient_for_admission is False
    assert value.same_repository_queues[SAME_REPOSITORY_TARGETS[-1]] == ()
    assert value.task_admission_state == "stopped-insufficient-public-pool-without-relaxation"


def test_build_reads_only_preregistration_manifest_and_normalized_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_path = _write_snapshot(tmp_path / "source.json", _mixed_rows())
    reads: list[Path] = []
    original = Path.read_bytes

    def tracked(path: Path) -> bytes:
        reads.append(path.resolve(strict=False))
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", tracked)
    build_fresh_candidate_registry(REPOSITORY, source_path)

    relative = {path.relative_to(REPOSITORY).as_posix() for path in reads}
    assert relative == {
        "data/dataset-manifest.yaml",
        "experiments/lean-harness-fresh-acquisition-preregistration-20260817-v1.json",
        source_path,
    }
    assert all("tasks/" not in path for path in relative)
    assert all(".patchloop/" not in path for path in relative)
    assert all("r16" not in path.lower() for path in relative)


def test_build_performs_no_network_or_child_process_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def bomb(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("registry builder attempted external execution")

    monkeypatch.setattr(socket, "create_connection", bomb)
    monkeypatch.setattr(socket.socket, "connect", bomb)
    monkeypatch.setattr(subprocess, "Popen", bomb)
    _build(tmp_path)


def test_module_has_no_task_loader_runner_or_external_execution_imports() -> None:
    source = Path(registry_module.__file__).read_text(encoding="utf-8").lower()
    for forbidden in (
        "from patchloop.agent",
        "from patchloop.task_loader",
        "from patchloop.evals.runner",
        "import subprocess",
        "import socket",
        "import openai",
        "import docker",
        "import requests",
        "import httpx",
        "import urllib",
    ):
        assert forbidden not in source


def test_materialization_is_append_only_and_idempotent(tmp_path: Path) -> None:
    source_path = _write_snapshot(tmp_path / "source.json", _mixed_rows())
    output = tmp_path / "registry.json"
    output_path = output.relative_to(REPOSITORY).as_posix()

    first = materialize_fresh_candidate_registry(
        REPOSITORY,
        source_snapshot_path=source_path,
        output_path=output_path,
    )
    before = output.stat().st_mtime_ns
    second = materialize_fresh_candidate_registry(
        REPOSITORY,
        source_snapshot_path=source_path,
        output_path=output_path,
    )

    assert first == second
    assert output.stat().st_mtime_ns == before
    assert output.read_bytes() == registry_bytes(first)


def test_generic_experiment_loader_rejects_registry_projection(tmp_path: Path) -> None:
    from patchloop.evals.runner import load_suite

    output = tmp_path / "registry.json"
    output.write_bytes(registry_bytes(_build(tmp_path / "input")))
    with pytest.raises(ContractError, match="experiment contract validation failed"):
        load_suite(output)


def test_private_or_solution_fields_are_rejected_from_source_snapshot(tmp_path: Path) -> None:
    snapshot = _snapshot(_qualifying_rows()).model_dump(mode="json")
    snapshot["rows"][0]["solution_patch"] = "forbidden"
    snapshot["content_hash"] = sha256_json(
        {key: value for key, value in snapshot.items() if key != "content_hash"}
    )
    path = tmp_path / "private-drift.json"
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(FreshCandidateRegistryError, match="contract is invalid"):
        load_public_source_snapshot(REPOSITORY, path.relative_to(REPOSITORY).as_posix())


def test_source_and_output_paths_reject_task_runtime_and_absolute_locations(
    tmp_path: Path,
) -> None:
    source_path = _write_snapshot(tmp_path / "source.json", _qualifying_rows())

    with pytest.raises(FreshCandidateRegistryError, match="task or runtime state"):
        load_public_source_snapshot(REPOSITORY, "tasks/forbidden-source.json")
    with pytest.raises(FreshCandidateRegistryError, match="repository-relative"):
        load_public_source_snapshot(REPOSITORY, str((tmp_path / "source.json").resolve()))
    with pytest.raises(FreshCandidateRegistryError, match="task or runtime state"):
        materialize_fresh_candidate_registry(
            REPOSITORY,
            source_snapshot_path=source_path,
            output_path=".patchloop/forbidden-registry.json",
        )
    with pytest.raises(FreshCandidateRegistryError, match="only be materialized under .tmp"):
        materialize_fresh_candidate_registry(
            REPOSITORY,
            source_snapshot_path=source_path,
            output_path="reports/unqualified-registry.json",
        )


def test_snapshot_completeness_and_post_window_publication_fail_closed() -> None:
    body = _snapshot(_qualifying_rows()).model_dump(mode="json")
    body["raw_source_row_count"] -= 1
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError, match="does not account for every raw row"):
        FreshPublicSourceSnapshot.model_validate(body)

    body = _snapshot(_qualifying_rows()).model_dump(mode="json")
    body["source_published_at"] = "2026-08-16T23:59:59Z"
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError, match="published after the frozen window"):
        FreshPublicSourceSnapshot.model_validate(body)


def test_snapshot_duplicate_identity_and_nonexact_types_fail_closed() -> None:
    rows = list(_qualifying_rows())
    duplicate_body = rows[-1].model_dump(mode="json", exclude={"public_row_hash"})
    duplicate_body["source_ordinal"] = len(rows) + 1
    duplicate_body["public_row_hash"] = public_row_hash(duplicate_body)
    rows.append(PublicCandidateRow.model_validate(duplicate_body))
    with pytest.raises(ValidationError, match="duplicate public identity"):
        _snapshot(tuple(rows))

    row_body = _qualifying_rows()[0].model_dump(mode="json")
    row_body["source_ordinal"] = 1.0
    with pytest.raises(ValidationError):
        PublicCandidateRow.model_validate(row_body)


@pytest.mark.parametrize(
    ("section", "field", "replacement"),
    [
        ("authority", "execution_authorized", True),
        ("authority", "source_snapshot_externally_qualified", True),
        ("root", "public_pool_sufficient_for_admission", False),
        ("root", "queued_candidate_count", 13),
    ],
)
def test_fully_rehashed_registry_drift_is_rejected(
    tmp_path: Path, section: str, field: str, replacement: object
) -> None:
    source_path = _write_snapshot(tmp_path / "source.json", _mixed_rows())
    value = build_fresh_candidate_registry(REPOSITORY, source_path)
    body = value.model_dump(mode="json")
    if section == "root":
        body[field] = replacement
    else:
        body[section][field] = replacement
    body["content_hash"] = sha256_json(
        {key: item for key, item in body.items() if key != "content_hash"}
    )
    output = tmp_path / f"drift-{section}-{field}.json"
    output.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises((FreshCandidateRegistryError, ValidationError)):
        load_fresh_candidate_registry(REPOSITORY, output.relative_to(REPOSITORY).as_posix())


def test_snapshot_and_registry_hashes_bind_canonical_bytes(tmp_path: Path) -> None:
    source_path = _write_snapshot(tmp_path / "source.json", _mixed_rows())
    snapshot, raw = load_public_source_snapshot(REPOSITORY, source_path)
    registry = build_fresh_candidate_registry(REPOSITORY, source_path)

    assert sha256_bytes(raw) == registry.source_snapshot_binding.file_sha256
    assert snapshot.content_hash == registry.source_snapshot_binding.content_hash
    assert registry.content_hash == sha256_json(
        registry.model_dump(mode="json", exclude={"content_hash"})
    )
