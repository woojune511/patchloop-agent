from __future__ import annotations

import copy
import json
import os
import socket
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from patchloop import runtime as runtime_module
from patchloop.errors import ContractError
from patchloop.evals import runner as eval_runner
from patchloop.util import sha256_bytes

R2_SUITE = Path("experiments/dev-validation-ac-fixed-bundle-readiness-20260808-r2.yaml")
SOURCE_COMMIT = "a" * 40


class InjectedFinalizationCrash(BaseException):
    pass


def _forbidden(label: str):
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(f"{label} is forbidden during finalization recovery")

    return fail


def _projection(check_id: str) -> dict[str, Any]:
    return {
        "schema_version": "qualification-gate-check-projection-v1",
        "check_id": check_id,
        "check_count": 1,
        "passed": True,
    }


@pytest.fixture
def ac_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    root = tmp_path / "runtime"
    monkeypatch.setenv("OPENAI_API_KEY", "offline-placeholder-not-used")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: root)
    monkeypatch.setattr(
        eval_runner,
        "utc_now",
        lambda: datetime(2026, 8, 9, 0, tzinfo=UTC),
    )
    monkeypatch.setattr(
        eval_runner,
        "_git_state",
        lambda: {"available": True, "commit": SOURCE_COMMIT, "clean": True},
    )
    monkeypatch.setattr(
        eval_runner,
        "_docker_image_state",
        lambda images: {
            "available": True,
            "images": [
                {"image": image, "identity": image.rsplit("@", 1)[-1], "ready": True}
                for image in sorted(set(images))
            ],
        },
    )
    monkeypatch.setattr(
        eval_runner,
        "_openai_sdk_state",
        lambda: {"installed": True, "version": "offline-test-sdk"},
    )
    monkeypatch.setattr(runtime_module, "git_commit", lambda: SOURCE_COMMIT)
    monkeypatch.setattr(runtime_module, "version", lambda _package: "offline-test-sdk")
    monkeypatch.setattr(socket, "socket", _forbidden("network socket"))
    monkeypatch.setattr(socket, "create_connection", _forbidden("network connection"))

    preflight = eval_runner.preflight_suite(R2_SUITE)
    approved = copy.deepcopy(preflight)
    approved["approval"] = {
        **approved["approval"],
        "invocation_approve_live_cost": True,
        "invocation_approved_execution_hash": preflight["execution_hash"],
        "matches_execution_hash": True,
    }
    approved["blockers"] = []
    approved["ready"] = True
    monkeypatch.setattr(
        eval_runner,
        "preflight_suite",
        lambda *_args, **_kwargs: copy.deepcopy(approved),
    )
    monkeypatch.setattr(
        eval_runner,
        "_assert_live_environment_unchanged",
        lambda _preflight: None,
    )

    started_run_ids: list[str] = []

    class FakeRunner:
        def start(self, _task: str, *, manifest, **_kwargs: Any) -> dict[str, Any]:
            started_run_ids.append(manifest.run_id)
            return {
                "run_id": manifest.run_id,
                "agent_submission_status": "completed",
                "evaluation_status": "completed",
                "scope_compliant_success": False,
                "official": True,
                "verdicts": {
                    "hidden_tests": "fail",
                    "regression_tests": "pass",
                    "scope_policy": "pass",
                    "safety_policy": "pass",
                },
                "outcome_kind": "task_failure",
                "terminal_error": None,
                "usage": {
                    "input_tokens": 1_000,
                    "cached_input_tokens": 100,
                    "cache_write_input_tokens": 0,
                    "output_tokens": 50,
                    "reasoning_output_tokens": 20,
                    "model_calls": 1,
                    "tool_calls": 1,
                    "wall_clock_ms": 1_000,
                    "model_cost_usd": 999.0,
                },
            }

    monkeypatch.setattr(eval_runner, "AgentRunner", FakeRunner)
    monkeypatch.setattr(
        eval_runner,
        "_qualify_terminal_run",
        lambda run_id, _task: {
            "schema_version": "trace-qualification-v1",
            "run_id": run_id,
            "qualified": True,
            "trace_integrity_passed": True,
            "leakage_scan_passed": True,
            "evaluation_reached": True,
            "outcome_kind": "task_failure",
            "qualification_hash": "sha256:" + "1" * 64,
            "source_evidence_hash": "sha256:" + "2" * 64,
            "usage_reconciliation": _projection("usage_reconciliation"),
            "persisted_result": _projection("persisted_result"),
        },
    )

    def unavailable_usage(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise ContractError("durable settlement fixture is unavailable")

    monkeypatch.setattr(
        eval_runner,
        "_load_full_schedule_durable_usage_evidence",
        unavailable_usage,
    )

    def execute(
        fault_injector=None,
    ) -> dict[str, Any]:
        return eval_runner.evaluate_suite(
            R2_SUITE,
            approve_live_cost=True,
            approved_execution_hash=preflight["execution_hash"],
            _finalization_fault_injector=fault_injector,
        )

    return {
        "root": root,
        "preflight": approved,
        "execution_hash": preflight["execution_hash"],
        "started_run_ids": started_run_ids,
        "execute": execute,
    }


def _paths(context: dict[str, Any]) -> tuple[Path, Path, Path, Path]:
    return eval_runner._ac_finalization_paths(
        context["execution_hash"],
        root=context["root"],
    )


def _journal_events(journal: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]


def _crash_at(stage: str):
    def inject(observed: str) -> None:
        if observed == stage:
            raise InjectedFinalizationCrash(stage)

    return inject


def _forbid_recovery_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    class ForbiddenRunner:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise AssertionError("AgentRunner construction is forbidden during recovery")

    monkeypatch.setattr(eval_runner, "AgentRunner", ForbiddenRunner)
    monkeypatch.setattr(eval_runner, "preflight_suite", _forbidden("preflight"))
    monkeypatch.setattr(
        eval_runner,
        "_assert_live_environment_unchanged",
        _forbidden("live environment check"),
    )
    monkeypatch.setattr(
        eval_runner,
        "issue_live_execution_authorization",
        _forbidden("live authorization"),
    )
    monkeypatch.setattr(eval_runner, "load_task_package", _forbidden("task load"))
    monkeypatch.setattr(eval_runner, "_git_state", _forbidden("git"))
    monkeypatch.setattr(eval_runner, "_docker_image_state", _forbidden("Docker"))
    monkeypatch.setattr(eval_runner, "_openai_sdk_state", _forbidden("SDK"))
    monkeypatch.setattr(subprocess, "run", _forbidden("subprocess"))


@pytest.mark.parametrize(
    "stage",
    [
        "after_prepared_result_fsync",
        "after_result_publish",
        "after_campaign_completed_append",
    ],
)
def test_ac_finalization_recovers_each_durable_fault_boundary_without_live_calls(
    ac_runtime: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    with pytest.raises(InjectedFinalizationCrash, match=stage):
        ac_runtime["execute"](_crash_at(stage))

    _plan, journal, prepared, output = _paths(ac_runtime)
    assert prepared.is_file()
    before = _journal_events(journal)
    if stage == "after_prepared_result_fsync":
        assert not output.exists()
        assert before[-1]["event_type"] != "CampaignCompleted"
    elif stage == "after_result_publish":
        assert prepared.samefile(output)
        assert before[-1]["event_type"] != "CampaignCompleted"
    else:
        assert prepared.samefile(output)
        assert before[-1]["event_type"] == "CampaignCompleted"

    _forbid_recovery_calls(monkeypatch)
    recovered = eval_runner.recover_ac_campaign_finalization(
        ac_runtime["execution_hash"],
        root=ac_runtime["root"],
    )

    assert len(ac_runtime["started_run_ids"]) == 1
    assert recovered["path"] == str(output)
    assert prepared.samefile(output)
    assert prepared.read_bytes() == output.read_bytes()
    after = _journal_events(journal)
    assert [event["event_type"] for event in after].count("CampaignCompleted") == 1
    assert after[-1]["payload"]["result_hash"] == sha256_bytes(output.read_bytes())
    sealed = journal.read_bytes()
    repeated = eval_runner.recover_ac_campaign_finalization(
        ac_runtime["execution_hash"],
        root=ac_runtime["root"],
    )
    assert repeated == recovered
    assert journal.read_bytes() == sealed


def test_ac_normal_finalization_publishes_before_campaign_completed(
    ac_runtime: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _plan, _journal, prepared, output = _paths(ac_runtime)
    original = eval_runner._append_campaign_event
    observed_completion = False

    def observe(*args: Any, event_type: str, **kwargs: Any) -> str:
        nonlocal observed_completion
        if event_type == "CampaignCompleted":
            observed_completion = True
            assert prepared.is_file()
            assert output.is_file()
            assert prepared.samefile(output)
            assert kwargs["payload"]["result_hash"] == sha256_bytes(output.read_bytes())
        return original(*args, event_type=event_type, **kwargs)

    monkeypatch.setattr(eval_runner, "_append_campaign_event", observe)
    result = ac_runtime["execute"]()

    assert observed_completion is True
    assert result["path"] == str(output)


def test_ac_recovery_refuses_unprepared_completed_rows_without_resuming(
    ac_runtime: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = eval_runner._write_ac_prepared_result

    def crash_before_prepare(*_args: Any, **_kwargs: Any) -> None:
        raise InjectedFinalizationCrash("before prepared result")

    monkeypatch.setattr(eval_runner, "_write_ac_prepared_result", crash_before_prepare)
    with pytest.raises(InjectedFinalizationCrash, match="before prepared result"):
        ac_runtime["execute"]()
    monkeypatch.setattr(eval_runner, "_write_ac_prepared_result", original)
    _forbid_recovery_calls(monkeypatch)

    with pytest.raises(ContractError, match="cannot resume any row"):
        eval_runner.recover_ac_campaign_finalization(
            ac_runtime["execution_hash"],
            root=ac_runtime["root"],
        )
    assert len(ac_runtime["started_run_ids"]) == 1


@pytest.mark.parametrize("collision", [b"foreign", b"exact-copy"])
def test_ac_recovery_preserves_foreign_or_ambiguous_final_result_collision(
    ac_runtime: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    collision: bytes,
) -> None:
    with pytest.raises(InjectedFinalizationCrash):
        ac_runtime["execute"](_crash_at("after_prepared_result_fsync"))
    _plan, journal, prepared, output = _paths(ac_runtime)
    selected = prepared.read_bytes() if collision == b"exact-copy" else collision
    output.write_bytes(selected)
    before_journal = journal.read_bytes()
    _forbid_recovery_calls(monkeypatch)

    with pytest.raises(ContractError, match="collision|ambiguous ownership"):
        eval_runner.recover_ac_campaign_finalization(
            ac_runtime["execution_hash"],
            root=ac_runtime["root"],
        )

    assert output.read_bytes() == selected
    assert journal.read_bytes() == before_journal
    assert _journal_events(journal)[-1]["event_type"] != "CampaignCompleted"


def test_ac_recovery_preserves_racing_result_publication(
    ac_runtime: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(InjectedFinalizationCrash):
        ac_runtime["execute"](_crash_at("after_prepared_result_fsync"))
    _plan, journal, _prepared, output = _paths(ac_runtime)
    before_journal = journal.read_bytes()
    original_link = os.link

    def race(_source: Path, target: Path, *_args: Any, **_kwargs: Any) -> None:
        Path(target).write_bytes(b"racing-owner")
        raise FileExistsError(str(target))

    monkeypatch.setattr(os, "link", race)
    _forbid_recovery_calls(monkeypatch)
    with pytest.raises(ContractError, match="collision"):
        eval_runner.recover_ac_campaign_finalization(
            ac_runtime["execution_hash"],
            root=ac_runtime["root"],
        )
    monkeypatch.setattr(os, "link", original_link)

    assert output.read_bytes() == b"racing-owner"
    assert journal.read_bytes() == before_journal


@pytest.mark.parametrize("kind", ["directory", "symlink"])
def test_ac_recovery_rejects_non_regular_final_result_collision(
    ac_runtime: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    with pytest.raises(InjectedFinalizationCrash):
        ac_runtime["execute"](_crash_at("after_prepared_result_fsync"))
    _plan, journal, _prepared, output = _paths(ac_runtime)
    simulated_reparse = False
    if kind == "directory":
        output.mkdir()
    else:
        target = output.with_name("foreign-result-target.json")
        target.write_bytes(b"foreign-target")
        try:
            output.symlink_to(target)
        except OSError:
            simulated_reparse = True
            output.write_bytes(b"simulated-reparse")
            original_reparse_check = eval_runner._path_is_reparse_or_symlink
            monkeypatch.setattr(
                eval_runner,
                "_path_is_reparse_or_symlink",
                lambda path: path == output or original_reparse_check(path),
            )
    before = journal.read_bytes()
    _forbid_recovery_calls(monkeypatch)

    with pytest.raises(ContractError, match="final A/C result"):
        eval_runner.recover_ac_campaign_finalization(
            ac_runtime["execution_hash"],
            root=ac_runtime["root"],
        )

    if kind == "directory":
        assert output.is_dir()
    elif simulated_reparse:
        assert output.read_bytes() == b"simulated-reparse"
    else:
        assert output.is_symlink()
    assert journal.read_bytes() == before


def test_ac_recovery_rejects_fully_rehashed_prepared_semantic_tamper(
    ac_runtime: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(InjectedFinalizationCrash):
        ac_runtime["execute"](_crash_at("after_prepared_result_fsync"))
    _plan, journal, prepared, output = _paths(ac_runtime)
    payload = json.loads(prepared.read_text(encoding="utf-8"))
    payload["completed_runs"] = 4
    prepared.write_bytes(json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"))
    before = journal.read_bytes()
    _forbid_recovery_calls(monkeypatch)

    with pytest.raises(ContractError, match="aggregates"):
        eval_runner.recover_ac_campaign_finalization(
            ac_runtime["execution_hash"],
            root=ac_runtime["root"],
        )

    assert not output.exists()
    assert journal.read_bytes() == before


def test_partial_temp_write_never_claims_the_deterministic_prepared_path(
    ac_runtime: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _plan, journal, prepared, output = _paths(ac_runtime)
    original_open = Path.open
    temporary_paths: list[Path] = []

    class PartialWriteStream:
        def __init__(self, stream) -> None:
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *_args: Any) -> None:
            self.stream.close()

        def write(self, content: bytes) -> int:
            self.stream.write(content[:17])
            self.stream.flush()
            raise OSError("injected partial temporary write")

        def flush(self) -> None:
            self.stream.flush()

        def fileno(self) -> int:
            return self.stream.fileno()

    def partial_open(path: Path, *args: Any, **kwargs: Any):
        stream = original_open(path, *args, **kwargs)
        if (
            path.parent == prepared.parent
            and path.name.startswith(".acprep-")
            and path.name.endswith(".tmp")
        ):
            temporary_paths.append(path)
            return PartialWriteStream(stream)
        return stream

    monkeypatch.setattr(Path, "open", partial_open)
    with pytest.raises(ContractError, match="temporary A/C prepared result"):
        ac_runtime["execute"]()
    monkeypatch.setattr(Path, "open", original_open)

    assert temporary_paths
    assert all(not path.exists() for path in temporary_paths)
    assert not prepared.exists()
    assert not prepared.is_symlink()
    assert not output.exists()
    assert _journal_events(journal)[-1]["event_type"] != "CampaignCompleted"

    _forbid_recovery_calls(monkeypatch)
    with pytest.raises(ContractError, match="cannot resume any row"):
        eval_runner.recover_ac_campaign_finalization(
            ac_runtime["execution_hash"],
            root=ac_runtime["root"],
        )


@pytest.mark.parametrize("kind", ["partial-file", "directory"])
def test_ac_initial_finalization_rejects_prepared_path_collision(
    ac_runtime: dict[str, Any],
    kind: str,
) -> None:
    _plan, journal, prepared, output = _paths(ac_runtime)
    prepared.parent.mkdir(parents=True, exist_ok=True)
    if kind == "partial-file":
        prepared.write_bytes(b'{"schema_version":')
    else:
        prepared.mkdir()

    with pytest.raises(ContractError, match="prepared A/C result"):
        ac_runtime["execute"]()

    if kind == "partial-file":
        assert prepared.read_bytes() == b'{"schema_version":'
    else:
        assert prepared.is_dir()
    assert not output.exists()
    assert _journal_events(journal)[-1]["event_type"] != "CampaignCompleted"
