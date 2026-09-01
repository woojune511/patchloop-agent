from __future__ import annotations

import ast
import json
import shutil
from pathlib import Path

import pytest

from patchloop.errors import ContractError
from patchloop.evals.fresh_source_registry_observation import (
    HARBOR_HEAD,
    OBSERVATION_ID,
    OUTPUT_PATH,
    PREDECESSOR_PATH,
    FreshSourceRegistryObservationError,
    build_fresh_source_registry_observation,
    load_fresh_source_registry_observation,
    materialize_fresh_source_registry_observation,
    observation_bytes,
)
from patchloop.util import sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    predecessor = root / PREDECESSOR_PATH
    predecessor.parent.mkdir(parents=True)
    shutil.copyfile(REPOSITORY / PREDECESSOR_PATH, predecessor)
    return root


def test_build_freezes_official_metadata_observation_without_snapshot_authority() -> None:
    value = build_fresh_source_registry_observation(REPOSITORY)

    assert value.observation_id == OBSERVATION_ID
    assert value.official_client_source.head_commit == HARBOR_HEAD
    assert [query.row_count for query in value.queries] == [4, 0, 3]
    assert value.decision.harbor_current_status_established is True
    assert value.decision.exact_august_monthly_package_visible is False
    assert value.decision.qualifying_post_window_snapshot_observed is False
    assert value.decision.qualifying_snapshot_absence_proven is False
    assert value.decision.raw_source_completeness_qualified is False
    assert value.decision.observation_is_selector_input is False
    assert value.authority.total_recorded_network_gets == 6
    assert value.authority.dataset_task_membership_requests == 0
    assert value.authority.task_archive_or_file_requests == 0
    assert value.authority.task_rows_downloaded == 0
    assert value.authority.solution_test_oracle_private_fields_read == 0
    assert value.authority.candidate_registry_materialized is False
    assert value.authority.execution_authorized is False


def test_observed_packages_and_versions_are_exact_and_public_metadata_only() -> None:
    value = build_fresh_source_registry_observation(REPOSITORY)

    assert [(row.org, row.name) for row in value.observed_rows.packages] == [
        ("ibragim-badertdinov", "swe-rebench-07-2026"),
        ("swe-rebench", "swe-rebench-leaderboard"),
        ("openthoughts", "tasktrove-swe-rebench-patched-oracle"),
        ("openthoughts", "tasktrove-swe-rebench-v2-patched-oracle"),
    ]
    assert value.observed_rows.exact_august_packages == ()
    assert [(row.package, row.revision, row.tags) for row in value.observed_rows.versions] == [
        ("swe-rebench/swe-rebench-leaderboard", 1, ()),
        ("swe-rebench/swe-rebench-leaderboard", 2, ("latest",)),
        (
            "ibragim-badertdinov/swe-rebench-07-2026",
            1,
            ("2026-07", "latest"),
        ),
    ]
    for query in value.queries:
        assert "dataset_version_task" not in query.canonical_query
        assert "archive" not in query.canonical_query
        assert "file" not in query.canonical_query


def test_materialize_is_new_only_canonical_and_idempotent(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    first = materialize_fresh_source_registry_observation(root)
    selected = root / OUTPUT_PATH
    raw = selected.read_bytes()
    before = selected.stat().st_mtime_ns

    second = materialize_fresh_source_registry_observation(root)

    assert first == second
    assert raw == observation_bytes(first) == selected.read_bytes()
    assert selected.stat().st_mtime_ns == before
    assert load_fresh_source_registry_observation(root) == first


def test_load_rejects_rehashed_semantic_drift(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    value = build_fresh_source_registry_observation(root)
    body = value.model_dump(mode="json")
    body["decision"]["harbor_current_status_established"] = False
    body["content_hash"] = sha256_json(
        {key: item for key, item in body.items() if key != "content_hash"}
    )
    selected = root / OUTPUT_PATH
    selected.parent.mkdir(parents=True, exist_ok=True)
    selected.write_text(
        json.dumps(body, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(FreshSourceRegistryObservationError):
        load_fresh_source_registry_observation(root)


def test_build_rejects_predecessor_byte_drift(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    selected = root / PREDECESSOR_PATH
    selected.write_bytes(selected.read_bytes() + b"\n")

    with pytest.raises(
        FreshSourceRegistryObservationError,
        match="availability v3 predecessor differs",
    ):
        build_fresh_source_registry_observation(root)


def test_load_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    selected = root / OUTPUT_PATH
    selected.parent.mkdir(parents=True, exist_ok=True)
    selected.write_text('{"schema_version":"x","schema_version":"y"}\n', encoding="utf-8")

    with pytest.raises(FreshSourceRegistryObservationError, match="duplicate JSON key"):
        load_fresh_source_registry_observation(root)


def test_load_rejects_outside_repository_path(tmp_path: Path) -> None:
    with pytest.raises(ContractError):
        load_fresh_source_registry_observation(REPOSITORY, str(tmp_path / "outside.json"))


def test_module_has_no_network_download_or_runtime_import_surface() -> None:
    source_path = REPOSITORY / "patchloop/evals/fresh_source_registry_observation.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports = {
        node.names[0].name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
    }
    imports.update(
        node.module.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imports.isdisjoint(
        {
            "docker",
            "httpx",
            "openai",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        }
    )
    source = source_path.read_text(encoding="utf-8")
    assert "download_dataset(" not in source
    assert "task_loader" not in source
    assert "AgentRunner" not in source


def test_checked_in_artifact_matches_offline_builder() -> None:
    value = load_fresh_source_registry_observation(REPOSITORY)
    assert value == build_fresh_source_registry_observation(REPOSITORY)
    assert (REPOSITORY / OUTPUT_PATH).read_bytes() == observation_bytes(value)
