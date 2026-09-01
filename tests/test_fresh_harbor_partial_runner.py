from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.evals.fresh_harbor_partial_runner import (
    CANDIDATE_PATH,
    EXPECTED_ARCHIVE_MEMBERS,
    EXPECTED_ROWS,
    HARBOR_COMMIT,
    HARBOR_TREE,
    SOURCE_QUALIFICATION_PATH,
    RunnerCandidate,
    _command_contract,
    _task_materialization_contract,
    artifact_bytes,
    build_candidate,
    build_source_qualification,
    load_candidate,
    load_source_qualification,
)
from patchloop.util import sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]
HARBOR_SOURCE = REPOSITORY / ".tmp" / "harbor-source-f03db62"


def test_source_qualification_binds_exact_clean_harbor_without_calls() -> None:
    value = build_source_qualification(REPOSITORY, HARBOR_SOURCE)

    assert value.harbor_source.commit == HARBOR_COMMIT
    assert value.harbor_source.tree == HARBOR_TREE
    assert value.harbor_source.tracked_worktree_clean is True
    assert value.authority.docker_calls == value.authority.network_calls == 0
    assert value.authority.private_reference_patches_read == 0
    assert value.authority.docker_execution_authorized is False


def test_command_and_materialization_contracts_are_closed() -> None:
    command = _command_contract()
    arguments = command["arguments"]

    assert command["shell"] is False
    assert command["environment"] == {"HARBOR_TELEMETRY": "off"}
    assert arguments[arguments.index("--agent") + 1] == "oracle"
    assert arguments[arguments.index("--env") + 1] == "docker"
    assert arguments[arguments.index("--n-attempts") + 1] == "1"
    assert arguments[arguments.index("--max-retries") + 1] == "0"
    assert arguments[arguments.index("--n-concurrent") + 1] == "1"
    assert "--model" not in arguments
    materialization = _task_materialization_contract()
    assert tuple(materialization["archive_members_exact"]) == EXPECTED_ARCHIVE_MEMBERS
    assert materialization["private-patch-agent-visible"] is False


def test_candidate_has_exact_144_rows_and_no_authority() -> None:
    value = build_candidate(REPOSITORY)

    assert len(value.rows) == EXPECTED_ROWS
    assert value.rows[0].order == 1
    assert value.rows[-1].order == EXPECTED_ROWS
    assert len({row.row_id for row in value.rows}) == EXPECTED_ROWS
    assert value.authority.candidate_materialized is True
    assert value.authority.execution_authorized is False
    assert value.authority.docker_calls == value.authority.evaluator_calls == 0


def test_checked_in_source_and_candidate_are_canonical() -> None:
    source, source_raw = load_source_qualification(REPOSITORY)
    candidate, candidate_raw = load_candidate(REPOSITORY)

    assert artifact_bytes(source) == source_raw
    assert artifact_bytes(candidate) == candidate_raw
    assert candidate.source_qualification_binding.content_hash == source.content_hash
    assert b"diff --git" not in candidate_raw
    assert b"private-case" not in candidate_raw


def test_rehashed_execution_or_authority_drift_is_rejected() -> None:
    value, _raw = load_candidate(REPOSITORY)
    body = value.model_dump(mode="json")
    body["command_contract"]["arguments"][body["command_contract"]["arguments"].index("1")] = "2"
    body["execution_hash"] = sha256_json(
        {
            key: item
            for key, item in body.items()
            if key not in {"execution_hash", "authority", "next_gate", "content_hash"}
        }
    )
    body["content_hash"] = sha256_json(
        {key: item for key, item in body.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError, match="command contract differs"):
        RunnerCandidate.model_validate(body)

    body = value.model_dump(mode="json")
    body["authority"]["execution_authorized"] = True
    with pytest.raises(ValidationError):
        RunnerCandidate.model_validate(body)


def test_artifact_paths_are_external_to_tasks_and_no_executor_is_exported() -> None:
    assert SOURCE_QUALIFICATION_PATH.startswith("reports/fresh-panel/artifacts/")
    assert CANDIDATE_PATH.startswith("experiments/")
    assert not SOURCE_QUALIFICATION_PATH.startswith("tasks/")
    assert not CANDIDATE_PATH.startswith("tasks/")

    import patchloop.evals.fresh_harbor_partial_runner as module

    assert not hasattr(module, "execute")
    assert not hasattr(module, "run_candidate")
