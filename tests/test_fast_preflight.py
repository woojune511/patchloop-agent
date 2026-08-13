from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from patchloop.cli import app
from patchloop.environment import exact_openai_api_key_environment
from patchloop.errors import ContractError
from patchloop.evals import runner as eval_runner


def _git_result(command: list[str], status: str) -> subprocess.CompletedProcess[str]:
    if command[1:] == ["rev-parse", "HEAD"]:
        return subprocess.CompletedProcess(command, 0, "a" * 40 + "\n", "")
    if command[1:] == ["status", "--porcelain=v1", "-z", "--untracked-files=all"]:
        return subprocess.CompletedProcess(command, 0, status, "")
    raise AssertionError(f"unexpected Git command: {command}")


def test_git_state_allows_documentation_only_dirt_without_claiming_full_clean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status = " M docs/00-index.md\0?? README.md\0 M AGENTS.md\0"
    monkeypatch.setattr(
        eval_runner.subprocess,
        "run",
        lambda command, **_kwargs: _git_result(command, status),
    )

    observed = eval_runner._git_state()

    assert observed["clean"] is False
    assert observed["execution_clean"] is True
    assert observed["dirty_paths"] == ["AGENTS.md", "README.md", "docs/00-index.md"]
    assert observed["ignored_documentation_paths"] == observed["dirty_paths"]
    assert observed["execution_dirty_paths"] == []


def test_git_state_keeps_executable_source_dirt_blocking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status = " M docs/current-status.md\0 M patchloop/cli.py\0"
    monkeypatch.setattr(
        eval_runner.subprocess,
        "run",
        lambda command, **_kwargs: _git_result(command, status),
    )

    observed = eval_runner._git_state()

    assert observed["clean"] is False
    assert observed["execution_clean"] is False
    assert observed["ignored_documentation_paths"] == ["docs/current-status.md"]
    assert observed["execution_dirty_paths"] == ["patchloop/cli.py"]


def test_exact_env_loader_accepts_only_openai_key_and_restores_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# repository credential\nOPENAI_API_KEY='fake-child-secret'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENAI_API_KEY", "fake-parent-secret")

    with exact_openai_api_key_environment(env_file):
        assert os.environ["OPENAI_API_KEY"] == "fake-child-secret"

    assert os.environ["OPENAI_API_KEY"] == "fake-parent-secret"


@pytest.mark.parametrize(
    "body",
    [
        "OPENAI_API_KEY=fake-secret\nOPENAI_BASE_URL=https://example.invalid\n",
        "OPENAI_API_KEY=fake-secret\nOPENAI_API_KEY=fake-secret-2\n",
        "UNRELATED=fake-secret\n",
        "OPENAI_API_KEY=\n",
    ],
)
def test_exact_env_loader_rejects_nonexact_membership_without_leaking_values(
    tmp_path: Path,
    body: str,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(body, encoding="utf-8")

    with (
        pytest.raises(ContractError) as captured,
        exact_openai_api_key_environment(env_file),
    ):
        pytest.fail("invalid credential file must not enter its environment scope")

    rendered = str(captured.value)
    assert "fake-secret" not in rendered
    assert "https://example.invalid" not in rendered


def test_preflight_command_validates_exact_env_without_exporting_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suite = tmp_path / "suite.yaml"
    suite.write_text("schema_version: test\n", encoding="utf-8")
    env_file = tmp_path / ".env"
    secret = "fake-fast-preflight-secret"
    env_file.write_text(f"OPENAI_API_KEY={secret}\n", encoding="utf-8")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    observed: dict[str, Any] = {}
    child_environments: list[tuple[bool, bool]] = []

    def fake_git(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        explicit_env = kwargs.get("env")
        child_environments.append(
            (
                "OPENAI_API_KEY" in os.environ,
                isinstance(explicit_env, dict) and "OPENAI_API_KEY" in explicit_env,
            )
        )
        return _git_result(command, "")

    monkeypatch.setattr(eval_runner.subprocess, "run", fake_git)

    def fake_preflight(
        path: Path,
        *,
        credential_present: bool | None = None,
    ) -> dict[str, Any]:
        observed["path"] = path
        observed["credential_present"] = credential_present
        observed["credential_exported"] = bool(os.environ.get("OPENAI_API_KEY"))
        eval_runner._git_state()
        return {
            "execution_hash": "sha256:" + "a" * 64,
            "execution_candidate_ready": True,
            "ready": False,
            "blockers": [
                {"code": "LIVE_COST_NOT_APPROVED", "message": "approval required"},
                {"code": "APPROVAL_HASH_MISMATCH", "message": "hash approval required"},
            ],
        }

    monkeypatch.setattr(eval_runner, "preflight_suite", fake_preflight)

    result = CliRunner().invoke(
        app,
        ["preflight", "--suite", str(suite), "--env-file", str(env_file)],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["execution_candidate_ready"] is True
    assert observed == {
        "path": suite,
        "credential_present": True,
        "credential_exported": False,
    }
    assert secret not in result.stdout
    assert "OPENAI_API_KEY" not in os.environ
    assert child_environments == [(False, False), (False, False)]


def test_evaluate_preflight_only_validates_env_without_exporting_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suite = tmp_path / "suite.yaml"
    suite.write_text("schema_version: test\n", encoding="utf-8")
    env_file = tmp_path / ".env"
    secret = "fake-evaluate-preflight-secret"
    env_file.write_text(f"OPENAI_API_KEY={secret}\n", encoding="utf-8")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    observed: dict[str, Any] = {}

    def fake_preflight(
        path: Path,
        *,
        approve_live_cost: bool,
        approved_execution_hash: str | None,
        credential_present: bool | None,
    ) -> dict[str, Any]:
        observed.update(
            {
                "path": path,
                "approve_live_cost": approve_live_cost,
                "approved_execution_hash": approved_execution_hash,
                "credential_present": credential_present,
                "credential_exported": "OPENAI_API_KEY" in os.environ,
            }
        )
        return {"ready": True}

    monkeypatch.setattr(eval_runner, "preflight_suite", fake_preflight)

    result = CliRunner().invoke(
        app,
        [
            "evaluate",
            "--suite",
            str(suite),
            "--preflight-only",
            "--env-file",
            str(env_file),
        ],
    )

    assert result.exit_code == 0
    assert observed == {
        "path": suite,
        "approve_live_cost": False,
        "approved_execution_hash": None,
        "credential_present": True,
        "credential_exported": False,
    }
    assert secret not in result.stdout
    assert "OPENAI_API_KEY" not in os.environ


def test_preflight_command_retries_only_transient_failures_and_stops_at_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suite = tmp_path / "suite.yaml"
    suite.write_text("schema_version: test\n", encoding="utf-8")
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=fake-secret\n", encoding="utf-8")
    results = iter(
        [
            {
                "execution_candidate_ready": False,
                "ready": False,
                "blockers": [
                    {"code": "DOCKER_UNAVAILABLE", "message": "not ready"},
                    {"code": "LIVE_COST_NOT_APPROVED", "message": "approval required"},
                    {"code": "APPROVAL_HASH_MISMATCH", "message": "hash required"},
                ],
            },
            {
                "execution_candidate_ready": True,
                "ready": False,
                "blockers": [
                    {"code": "LIVE_COST_NOT_APPROVED", "message": "approval required"},
                    {"code": "APPROVAL_HASH_MISMATCH", "message": "hash required"},
                ],
            },
        ]
    )
    calls = 0

    def fake_preflight(
        _path: Path,
        *,
        credential_present: bool | None = None,
    ) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        assert credential_present is True
        assert "OPENAI_API_KEY" not in os.environ
        return next(results)

    monkeypatch.setattr(eval_runner, "preflight_suite", fake_preflight)

    result = CliRunner().invoke(
        app,
        [
            "preflight",
            "--suite",
            str(suite),
            "--env-file",
            str(env_file),
            "--max-attempts",
            "3",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert calls == 2
    assert payload["preflight_attempt_count"] == 2
    assert payload["preflight_attempts"][0] == {
        "attempt": 1,
        "execution_candidate_ready": False,
        "blocker_codes": [
            "APPROVAL_HASH_MISMATCH",
            "DOCKER_UNAVAILABLE",
            "LIVE_COST_NOT_APPROVED",
        ],
        "transient_only": True,
    }
    assert payload["preflight_attempts"][1]["execution_candidate_ready"] is True


def test_preflight_command_does_not_retry_credential_or_schema_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suite = tmp_path / "suite.yaml"
    suite.write_text("schema_version: test\n", encoding="utf-8")
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=fake-secret\n", encoding="utf-8")
    calls = 0

    def fake_preflight(
        _path: Path,
        *,
        credential_present: bool | None = None,
    ) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        assert credential_present is True
        assert "OPENAI_API_KEY" not in os.environ
        return {
            "execution_candidate_ready": False,
            "ready": False,
            "blockers": [{"code": "DATASET_HASH_MISMATCH", "message": "source drift"}],
        }

    monkeypatch.setattr(eval_runner, "preflight_suite", fake_preflight)

    result = CliRunner().invoke(
        app,
        [
            "preflight",
            "--suite",
            str(suite),
            "--env-file",
            str(env_file),
            "--max-attempts",
            "3",
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert calls == 1
    assert payload["preflight_attempt_count"] == 1
    assert payload["preflight_attempts"][0]["transient_only"] is False


def test_preflight_command_retries_process_timeout_without_rendering_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suite = tmp_path / "suite.yaml"
    suite.write_text("schema_version: test\n", encoding="utf-8")
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=fake-secret\n", encoding="utf-8")
    calls = 0

    def fake_preflight(
        _path: Path,
        *,
        credential_present: bool | None = None,
    ) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        assert credential_present is True
        assert "OPENAI_API_KEY" not in os.environ
        if calls == 1:
            raise subprocess.TimeoutExpired(["local-preflight"], 1)
        return {
            "execution_candidate_ready": True,
            "ready": False,
            "blockers": [
                {"code": "LIVE_COST_NOT_APPROVED", "message": "approval required"},
                {"code": "APPROVAL_HASH_MISMATCH", "message": "hash required"},
            ],
        }

    monkeypatch.setattr(eval_runner, "preflight_suite", fake_preflight)

    result = CliRunner().invoke(
        app,
        [
            "preflight",
            "--suite",
            str(suite),
            "--env-file",
            str(env_file),
            "--max-attempts",
            "2",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert calls == 2
    assert payload["preflight_attempts"][0]["blocker_codes"] == ["PROCESS_TIMEOUT"]
