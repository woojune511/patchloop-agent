from __future__ import annotations

import ast
import shutil
from pathlib import Path

import pytest

from patchloop.evals.fresh_source_metadata_discovery import (
    OBSERVATION_PATH,
    OUTPUT_PATH,
    STATUS,
    FreshSourceMetadataDiscovery,
    FreshSourceMetadataDiscoveryError,
    VersionMetadata,
    build_fresh_source_metadata_discovery,
    discover_metadata_candidates,
    discovery_bytes,
    load_fresh_source_metadata_discovery,
    materialize_fresh_source_metadata_discovery,
)
from patchloop.evals.fresh_source_registry_observation import (
    PREDECESSOR_PATH as OBSERVATION_PREDECESSOR_PATH,
)
from patchloop.util import sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    for relative in (OBSERVATION_PATH, OBSERVATION_PREDECESSOR_PATH):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPOSITORY / relative, target)
    return root


def _version(
    *,
    package: str = "ibragim-badertdinov/swe-rebench-08-2026",
    published_at: str = "2026-08-17T00:00:00Z",
    revision: int = 1,
    yanked: bool = False,
    suffix: str = "1",
) -> VersionMetadata:
    return VersionMetadata(
        id=f"00000000-0000-0000-0000-{suffix.zfill(12)}",
        package=package,
        revision=revision,
        content_hash="sha256:" + suffix[-1] * 64,
        published_at=published_at,
        yanked=yanked,
    )


def test_current_observation_is_blocked_before_raw_capture() -> None:
    value = build_fresh_source_metadata_discovery(REPOSITORY)

    assert value.status == STATUS
    assert len(value.projection.transcript) == 3
    assert value.projection.candidates == ()
    assert {row.disposition for row in value.projection.transcript} == {
        "rejected-not-after-frozen-window"
    }
    assert value.current_decision.versions_rejected_pre_window == 3
    assert value.current_decision.disallowed_matching_package_names_observed == 2
    assert value.current_decision.disallowed_package_task_rows_read == 0
    assert value.authority.network_calls == 0
    assert value.authority.task_rows_read == 0
    assert value.authority.candidate_registry_materialized is False
    assert value.authority.execution_authorized is False


def test_post_window_metadata_is_only_pending_raw_completeness() -> None:
    projection = discover_metadata_candidates([_version()])

    assert len(projection.candidates) == 1
    candidate = projection.candidates[0]
    assert candidate.status == "PENDING_RAW_CAPTURE_AND_COMPLETENESS"
    assert candidate.qualifying_snapshot_asserted is False
    assert candidate.selector_authorized is False
    assert projection.transcript[0].selector_eligible is False
    assert projection.transcript[0].raw_completeness_qualified is False


def test_candidate_order_is_deterministic_and_does_not_use_mutable_tags() -> None:
    later = _version(
        package="swe-rebench/swe-rebench-leaderboard",
        published_at="2026-08-18T00:00:00Z",
        revision=3,
        suffix="3",
    )
    earlier = _version(published_at="2026-08-17T00:00:00Z", suffix="2")

    projection = discover_metadata_candidates([later, earlier])

    assert [candidate.version for candidate in projection.candidates] == [earlier, later]
    assert [candidate.rank for candidate in projection.candidates] == [1, 2]
    assert all(
        "tag" not in candidate.model_dump(mode="json") for candidate in projection.candidates
    )


def test_oracle_named_package_never_becomes_a_source_candidate() -> None:
    oracle = _version(
        package="openthoughts/tasktrove-swe-rebench-patched-oracle",
        suffix="4",
    )

    projection = discover_metadata_candidates([oracle])

    assert projection.candidates == ()
    assert projection.transcript[0].disposition == "rejected-disallowed-source-package"


@pytest.mark.parametrize(
    ("version", "reason"),
    [
        (
            _version(published_at="2026-08-16T23:59:59Z", suffix="5"),
            "rejected-not-after-frozen-window",
        ),
        (_version(yanked=True, suffix="6"), "rejected-yanked-version"),
    ],
)
def test_window_boundary_and_yanked_versions_fail_closed(
    version: VersionMetadata, reason: str
) -> None:
    projection = discover_metadata_candidates([version])

    assert projection.candidates == ()
    assert projection.transcript[0].disposition == reason


def test_materialize_is_new_only_and_idempotent(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    first = materialize_fresh_source_metadata_discovery(root)
    selected = root / OUTPUT_PATH
    raw = selected.read_bytes()
    before = selected.stat().st_mtime_ns

    second = materialize_fresh_source_metadata_discovery(root)

    assert first == second
    assert raw == discovery_bytes(first) == selected.read_bytes()
    assert selected.stat().st_mtime_ns == before


def test_rehashed_current_version_drift_is_rejected(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    value = build_fresh_source_metadata_discovery(root)
    body = value.model_dump(mode="json")
    body["projection"]["transcript"][0]["version"]["published_at"] = "2026-06-25T00:00:00Z"
    body["content_hash"] = sha256_json(
        {key: item for key, item in body.items() if key != "content_hash"}
    )
    selected = root / OUTPUT_PATH
    selected.parent.mkdir(parents=True, exist_ok=True)
    selected.write_bytes(discovery_bytes(FreshSourceMetadataDiscovery.model_validate(body)))

    with pytest.raises(FreshSourceMetadataDiscoveryError, match="facts differ"):
        load_fresh_source_metadata_discovery(root)


def test_observation_byte_drift_is_rejected(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    selected = root / OBSERVATION_PATH
    selected.write_bytes(selected.read_bytes() + b"\n")

    with pytest.raises(FreshSourceMetadataDiscoveryError, match="observation bytes differ"):
        build_fresh_source_metadata_discovery(root)


def test_duplicate_json_keys_are_rejected(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    selected = root / OUTPUT_PATH
    selected.parent.mkdir(parents=True, exist_ok=True)
    selected.write_text('{"status":"x","status":"y"}\n', encoding="utf-8")

    with pytest.raises(FreshSourceMetadataDiscoveryError, match="duplicate JSON key"):
        load_fresh_source_metadata_discovery(root)


def test_module_has_no_network_task_or_runtime_import_surface() -> None:
    source_path = REPOSITORY / "patchloop/evals/fresh_source_metadata_discovery.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
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
        {"docker", "httpx", "openai", "requests", "socket", "subprocess", "urllib"}
    )
    assert "dataset_version_task" not in source
    assert "download_dataset(" not in source
    assert "task_loader" not in source
    assert "AgentRunner" not in source


def test_checked_in_artifact_matches_offline_builder() -> None:
    value = load_fresh_source_metadata_discovery(REPOSITORY)
    assert value == build_fresh_source_metadata_discovery(REPOSITORY)
    assert (REPOSITORY / OUTPUT_PATH).read_bytes() == discovery_bytes(value)
