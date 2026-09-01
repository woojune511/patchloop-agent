from __future__ import annotations

import os
from pathlib import Path

import pytest

from patchloop.environment import OPENAI_API_KEY
from patchloop.errors import ContractError
from patchloop.evals.rapid_cli import dispatch_rapid_public_development_cli


def test_rehearsal_never_reads_or_exports_env_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.env"
    observed: list[str | None] = []

    result = dispatch_rapid_public_development_cli(
        mode="rehearse",
        repository=tmp_path,
        env_file=missing,
        approve_live_cost=False,
        approved_execution_hash=None,
        rehearse=lambda **_: observed.append(os.environ.get(OPENAI_API_KEY)) or {"ok": True},
        execute=lambda **_: pytest.fail("execute callback was dispatched"),
    )

    assert result == {"ok": True}
    assert observed == [os.environ.get(OPENAI_API_KEY)]


def test_execute_loads_only_for_callback_and_restores_parent(tmp_path: Path) -> None:
    env_file = tmp_path / "rapid.env"
    env_file.write_text("OPENAI_API_KEY=test-value-not-a-live-key\n", encoding="utf-8")
    sentinel = "parent-value"
    previous = os.environ.get(OPENAI_API_KEY)
    os.environ[OPENAI_API_KEY] = sentinel
    observed: list[str | None] = []
    try:
        result = dispatch_rapid_public_development_cli(
            mode="execute",
            repository=tmp_path,
            env_file=env_file,
            approve_live_cost=True,
            approved_execution_hash="sha256:" + "1" * 64,
            rehearse=lambda **_: pytest.fail("rehearsal callback was dispatched"),
            execute=lambda **kwargs: (
                observed.append(os.environ.get(OPENAI_API_KEY))
                or {"approved_execution_hash": kwargs["approved_execution_hash"]}
            ),
        )
        assert result == {"approved_execution_hash": "sha256:" + "1" * 64}
        assert observed == ["test-value-not-a-live-key"]
        assert os.environ[OPENAI_API_KEY] == sentinel
    finally:
        if previous is None:
            os.environ.pop(OPENAI_API_KEY, None)
        else:
            os.environ[OPENAI_API_KEY] = previous


def test_execute_requires_explicit_env_file_before_dispatch(tmp_path: Path) -> None:
    dispatched = False

    def execute(**_: object) -> dict:
        nonlocal dispatched
        dispatched = True
        return {}

    with pytest.raises(ContractError, match="explicit --env-file"):
        dispatch_rapid_public_development_cli(
            mode="execute",
            repository=tmp_path,
            env_file=None,
            approve_live_cost=True,
            approved_execution_hash="sha256:" + "1" * 64,
            rehearse=lambda **_: {},
            execute=execute,
        )
    assert dispatched is False


def test_execute_rejects_missing_authority_before_reading_env_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.env"

    with pytest.raises(ContractError, match="explicit cost approval"):
        dispatch_rapid_public_development_cli(
            mode="execute",
            repository=tmp_path,
            env_file=missing,
            approve_live_cost=False,
            approved_execution_hash=None,
            rehearse=lambda **_: {},
            execute=lambda **_: pytest.fail("execute callback was dispatched"),
        )


def test_rehearsal_rejects_paid_authority_flags(tmp_path: Path) -> None:
    with pytest.raises(ContractError, match="must not carry"):
        dispatch_rapid_public_development_cli(
            mode="rehearse",
            repository=tmp_path,
            env_file=None,
            approve_live_cost=True,
            approved_execution_hash=None,
            rehearse=lambda **_: {},
            execute=lambda **_: {},
        )
