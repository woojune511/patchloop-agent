from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.evals.fresh_all_cross_successor import (
    CANDIDATE_IDS,
    MEMBERSHIP_BYTES,
    MEMBERSHIP_PATH,
    MEMBERSHIP_SHA256,
    OBSERVATION_PATH,
    PLAN_PATH,
    PREREG_PATH,
    REGISTRY_PATH,
    SUITE_PATH,
    ActivationPlan,
    AllCrossPreregistration,
    FreshAllCrossSuccessorError,
    MetadataSuite,
    PublicRegistryQualification,
    artifact_bytes,
    build_all,
    load_all_cross_successor,
    materialize_all_cross_successor,
)
from patchloop.util import sha256_bytes, sha256_json
from scripts.capture_lean_fresh_all_cross_membership import capture

REPOSITORY = Path(__file__).resolve().parents[1]


def _rehash(body: dict[str, Any]) -> dict[str, Any]:
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return body


def test_exact_successor_loads_and_freezes_all_cross_panel() -> None:
    preregistration, registry, suite, plan = load_all_cross_successor(REPOSITORY)

    assert isinstance(preregistration, AllCrossPreregistration)
    assert isinstance(registry, PublicRegistryQualification)
    assert isinstance(suite, MetadataSuite)
    assert isinstance(plan, ActivationPlan)
    assert preregistration.exact_candidate_ids == CANDIDATE_IDS
    assert tuple(task.task_id for task in suite.tasks) == CANDIDATE_IDS
    assert len({task.repository.lower() for task in suite.tasks}) == 12
    assert len(suite.rows) == 48
    assert plan.first_blocked_gate == 3
    assert plan.candidate_hash is None
    assert plan.no_call_preflight_artifact is None


def test_successor_artifacts_are_append_only_and_idempotent() -> None:
    paths = [REPOSITORY / path for path in (PREREG_PATH, REGISTRY_PATH, SUITE_PATH, PLAN_PATH)]
    before = [(path.read_bytes(), path.stat().st_mtime_ns) for path in paths]
    first = materialize_all_cross_successor(REPOSITORY)
    second = materialize_all_cross_successor(REPOSITORY)
    after = [(path.read_bytes(), path.stat().st_mtime_ns) for path in paths]

    assert first == second
    assert after == before


def test_public_membership_capture_is_exact_and_selected_hashes_match() -> None:
    raw = (REPOSITORY / MEMBERSHIP_PATH).read_bytes()
    rows = json.loads(raw)
    assert len(raw) == MEMBERSHIP_BYTES
    assert sha256_bytes(raw) == MEMBERSHIP_SHA256
    assert len(rows) == 111

    _, registry, _, _ = build_all(REPOSITORY)
    membership = {
        row["task_version"]["package"]["name"].lower(): (
            "sha256:" + row["task_version"]["content_hash"].removeprefix("sha256:")
        )
        for row in rows
    }
    assert all(
        membership[candidate.instance.lower()] == candidate.package_content_sha256
        for candidate in registry.candidates
    )


def test_capture_replay_performs_no_network_call(monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.capture_lean_fresh_all_cross_membership as capture_module

    def bomb(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("existing public capture replay must not contact the network")

    monkeypatch.setattr(capture_module, "urlopen", bomb)
    summary = capture(
        REPOSITORY,
        REPOSITORY / ".tmp" / "harbor-source-f03db62",
        Path(MEMBERSHIP_PATH),
    )
    assert summary["network_calls"] == 0
    assert summary["existing_file_validated"] is True


def test_design_change_is_source_feasibility_only_and_not_original_prereg_rewrite() -> None:
    preregistration, registry, _, _ = load_all_cross_successor(REPOSITORY)
    design = preregistration.design_change
    assert design["predecessor_disposition"] == "preserved-unsatisfied-not-amended"
    assert design["change_trigger"] == "public-source-feasibility-only-not-ac-outcomes"
    assert design["original_design"] == {
        "same_repository_tasks": 6,
        "cross_repository_tasks": 6,
    }
    assert design["successor_design"] == {
        "same_repository_tasks": 0,
        "cross_repository_tasks": 12,
    }
    assert design["july_snapshot_covers_original_window_through_2026_08_16"] is False
    assert (
        registry.qualification_limits["original-window-through-2026-08-16-completeness-established"]
        is False
    )


def test_schedule_is_adjacent_balanced_and_reverses_each_task() -> None:
    _, _, suite, _ = load_all_cross_successor(REPOSITORY)
    for task in suite.tasks:
        rep_one = [row for row in suite.rows if row.task_id == task.task_id and row.repetition == 1]
        rep_two = [row for row in suite.rows if row.task_id == task.task_id and row.repetition == 2]
        assert rep_one[1].order == rep_one[0].order + 1
        assert rep_two[1].order == rep_two[0].order + 1
        assert rep_one[0].condition != rep_two[0].condition
    for wave in range(1, 5):
        rows = [row for row in suite.rows if row.wave == wave]
        assert len(rows) == 12
        assert sum(row.condition == "no_memory" for row in rows[::2]) == 3


def test_authority_is_closed_everywhere() -> None:
    preregistration, registry, suite, plan = load_all_cross_successor(REPOSITORY)
    for value in (preregistration, registry, suite, plan):
        authority = value.authority
        assert authority.provider_calls_authorized is False
        assert authority.agent_runs_authorized is False
        assert authority.task_package_materialization_authorized is False
        assert authority.candidate_creation_authorized is False
        assert authority.preflight_authorized is False
        assert authority.approval_granted is False
        assert authority.spend_authorized is False
        assert authority.authorized_cost_usd == 0.0


def test_registry_does_not_overclaim_raw_admission_replay() -> None:
    _, registry, suite, plan = load_all_cross_successor(REPOSITORY)
    assert registry.status.endswith("ADMISSION_RAW_REPLAY_PENDING")
    assert (
        registry.qualification_limits["raw-docker-and-evaluator-admission-evidence-checked-in"]
        is False
    )
    assert registry.qualification_limits["task-admission-producer-source-qualified"] is False
    assert suite.status == "METADATA_SUITE_FROZEN_EXECUTION_CLOSED"
    assert plan.gates[2].completion_evidence == (
        "missing-checked-in-replayable-admission-evidence-bundle"
    )


def test_rehashed_design_drift_is_rejected() -> None:
    preregistration, _, _, _ = load_all_cross_successor(REPOSITORY)
    body = preregistration.model_dump(mode="json")
    body["design_change"]["r16-outcomes_used_to_select-these-tasks"] = True
    _rehash(body)
    with pytest.raises(ValidationError, match="design change differs"):
        AllCrossPreregistration.model_validate(body)


def test_rehashed_schedule_treatment_drift_is_rejected() -> None:
    _, _, suite, _ = load_all_cross_successor(REPOSITORY)
    body = suite.model_dump(mode="json")
    body["rows"][0]["condition"] = body["rows"][1]["condition"]
    body["schedule_hash"] = sha256_json(body["rows"])
    _rehash(body)
    with pytest.raises(ValidationError, match="task-condition cells differ"):
        MetadataSuite.model_validate(body)


def test_extra_fields_and_nonexact_authority_fail_closed() -> None:
    preregistration, _, _, _ = load_all_cross_successor(REPOSITORY)
    extra = preregistration.model_dump(mode="json")
    extra["execution_hash"] = "sha256:" + "a" * 64
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AllCrossPreregistration.model_validate(extra)

    opened = preregistration.model_dump(mode="json")
    opened["authority"]["candidate_creation_authorized"] = True
    _rehash(opened)
    with pytest.raises(ValidationError):
        AllCrossPreregistration.model_validate(opened)


def test_builder_reads_no_task_or_private_path(monkeypatch: pytest.MonkeyPatch) -> None:
    original = Path.read_bytes
    seen: list[Path] = []

    def tracked(path: Path) -> bytes:
        resolved = path.resolve()
        seen.append(resolved)
        assert "tasks" not in {part.lower() for part in resolved.parts}
        assert ".patchloop" not in {part.lower() for part in resolved.parts}
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", tracked)
    build_all(REPOSITORY)
    relative = {path.relative_to(REPOSITORY).as_posix() for path in seen}
    assert relative == {
        "data/dataset-manifest.yaml",
        "experiments/lean-harness-fresh-acquisition-preregistration-20260817-v1.json",
        "experiments/lean-harness-runtime-source-qualification-20260817-v1.json",
        "reports/fresh-panel/artifacts/fresh-all-cross-search-observation-v1.json",
        "reports/fresh-panel/raw/harbor-swe-rebench-07-2026-r1-membership.json",
        "reports/heldout-ac/artifacts/heldout-ac-r16-campaign-complete-r1.json",
    }


def test_successor_module_has_no_runtime_or_external_execution_imports() -> None:
    source = (REPOSITORY / "patchloop" / "evals" / "fresh_all_cross_successor.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not any(
        name.startswith(prefix)
        for name in imported
        for prefix in (
            "openai",
            "socket",
            "subprocess",
            "docker",
            "patchloop.agent.runner",
            "patchloop.task_loader",
            "patchloop.evals.heldout_ac_dispatcher",
        )
    )


def test_output_byte_hashes_match_bindings() -> None:
    values = load_all_cross_successor(REPOSITORY)
    for path, value in zip(
        (PREREG_PATH, REGISTRY_PATH, SUITE_PATH, PLAN_PATH), values, strict=True
    ):
        raw = (REPOSITORY / path).read_bytes()
        assert raw == artifact_bytes(value)
        assert sha256_bytes(raw).startswith("sha256:")


def test_bound_input_drift_fails_closed(tmp_path: Path) -> None:
    required = {
        "data/dataset-manifest.yaml",
        "experiments/lean-harness-fresh-acquisition-preregistration-20260817-v1.json",
        "experiments/lean-harness-runtime-source-qualification-20260817-v1.json",
        "reports/fresh-panel/artifacts/fresh-all-cross-search-observation-v1.json",
        "reports/fresh-panel/raw/harbor-swe-rebench-07-2026-r1-membership.json",
        "reports/heldout-ac/artifacts/heldout-ac-r16-campaign-complete-r1.json",
    }
    for relative in required:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((REPOSITORY / relative).read_bytes())
    observation = tmp_path / OBSERVATION_PATH
    observation.write_bytes(observation.read_bytes() + b" ")
    with pytest.raises(FreshAllCrossSuccessorError, match="binding differs"):
        build_all(tmp_path)
