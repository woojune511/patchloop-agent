"""Opaque CLI contracts with fake task/evaluator objects; no private task reads."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from diagnostics import saved_candidate_acceptance as operator
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import ModelConfig, RunManifest
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.state import DevJournal
from patchloop.util import canonical_json, sha256_bytes, sha256_json, utc_now

HASH = "sha256:" + "1" * 64
PATCH = "public synthetic patch\n"
PATCH_HASH = sha256_bytes(PATCH.encode())
PRIVATE = "DO_NOT_PROJECT_EVALUATOR_DETAIL"


@pytest.fixture
def fake(tmp_path, monkeypatch):
    def forbidden(*_, **__):
        pytest.fail("external execution is forbidden")

    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr("subprocess.run", forbidden)
    # Replace the mapping without inspecting real credential values.
    monkeypatch.setattr(os, "environ", {"PATH": "system-path", "OPENAI_API_KEY": "fake-secret"})
    repo = tmp_path / "repo"
    public = repo / "tasks/dev-train/case/public.yaml"
    public.parent.mkdir(parents=True)
    public.write_text("public task", encoding="utf-8")
    script = repo / "diagnostics/operator.py"
    script.parent.mkdir()
    script.write_text("synthetic operator", encoding="utf-8")
    monkeypatch.setattr(operator, "__file__", str(script))
    workspace, prepared = tmp_path / "saved", tmp_path / "prepared/prepared-source.json"
    workspace.mkdir()
    prepared.parent.mkdir()
    prepared.write_text("synthetic public source manifest", encoding="utf-8")
    args = SimpleNamespace(public_task=str(public), workspace=str(workspace),
        prepared_source=str(prepared), output_root=str(tmp_path / "evaluation"),
        expected_diff_hash=PATCH_HASH, prepared_source_hash=HASH,
        deadline_seconds=390, public_checks_passed=True)
    state = SimpleNamespace(calls=0, loads=0, failure=False, verdict="pass",
                            patch_hash=PATCH_HASH, mutate=False, manifest=None)
    diff = SimpleNamespace(patch=PATCH, patch_hash=PATCH_HASH,
                           changed_files=["module.py"], untracked_files=[])

    class Manager:
        def __init__(self, *_args, **kwargs):
            assert kwargs["prepared_source"] == prepared
            assert kwargs["prepared_source_hash"] == HASH

        @staticmethod
        def diff_summary(*_args, **_kwargs):
            diff.patch_hash = state.patch_hash
            return diff

    class Sandbox:
        def __init__(self, image):
            assert image == "registered-image@" + HASH

        def image_identity(self, **_kwargs):
            assert "OPENAI_API_KEY" not in os.environ
            return HASH

    class Engine:
        def __init__(self, *_args):
            pass

        def evaluate(self, task_dir, patch_path, manifest, **kwargs):
            state.calls += 1
            state.manifest = manifest
            assert task_dir == public.parent and Path(patch_path).read_text("utf-8") == PATCH
            assert kwargs["submitted_patch_artifact"].content_hash == PATCH_HASH
            assert "OPENAI_API_KEY" not in os.environ
            print(PRIVATE)
            print(PRIVATE, file=sys.stderr)
            if state.failure:
                raise RuntimeError(PRIVATE)
            if state.mutate:
                state.patch_hash = HASH
            verdicts = {"hidden_tests": state.verdict, "regression_tests": "pass",
                        "scope_policy": "pass", "safety_policy": "pass"}
            return SimpleNamespace(
                evaluation_status="completed", scope_compliant_success=state.verdict == "pass",
                verdicts=SimpleNamespace(model_dump=lambda **_: verdicts),
                model_dump=lambda **_: {"verdicts": verdicts, "private_details": PRIVATE})

    def load_task(_path):
        state.loads += 1
        return SimpleNamespace(public=SimpleNamespace(split="dev-train", task_id="fake",
            task_version=1, repository=SimpleNamespace(base_commit="a" * 40,
                                                       url="snapshot://fake")),
            public_spec_hash=HASH, private_spec_hash=HASH, task_content_hash=HASH,
            environment=SimpleNamespace(evaluator_image="registered-image@" + HASH,
                                        image_digest=HASH))

    def load_source(path, url, revision, **kwargs):
        assert path == prepared and url == "snapshot://fake" and revision == "a" * 40
        assert kwargs["expected_hash"] == HASH
        return SimpleNamespace(git_commit="a" * 40), prepared.parent

    runtime = SimpleNamespace(ArtifactStore=ArtifactStore, ModelConfig=ModelConfig,
        RunManifest=RunManifest, ExecutionDeadline=ExecutionDeadline, DevJournal=DevJournal,
        WorkspaceManager=Manager, DockerSandbox=Sandbox, EvaluationEngine=Engine,
        load_task_package=load_task, load_source=load_source,
        run_git=lambda *_args, **_kwargs: SimpleNamespace(stdout="a" * 40 + "\n"),
        repository_root=lambda: repo, runtime_content_hash=lambda: HASH,
        dev_tool_surface_hash=lambda: HASH, git_commit=lambda **_: "b" * 40,
        canonical_json=canonical_json, sha256_bytes=sha256_bytes,
        sha256_json=sha256_json, utc_now=utc_now)
    monkeypatch.setattr(operator, "_runtime", lambda: runtime)
    return args, state


@pytest.mark.parametrize("verdict", ["pass", "fail"])
def test_one_evaluation_exposes_only_verdicts_and_hashes(fake, capsys, verdict):
    args, state = fake
    state.verdict = verdict
    result = operator.evaluate_saved_candidate(args)
    assert result["status"] == "COMPLETED" and result["stop_remaining"] is False
    assert result["acceptance"] == verdict and result["evaluator_dispatches"] == state.calls == 1
    assert result["synthetic_operator_submission"] is True
    assert state.manifest.model.provider == "mock"
    assert state.manifest.visible_check_diff_hash == PATCH_HASH
    assert PRIVATE not in json.dumps(result) and capsys.readouterr() == ("", "")
    root = Path(args.output_root)
    assert PRIVATE in (root / "engine-private.log").read_text("utf-8")
    assert PRIVATE in Path(result["evaluation_artifact_path"]).read_text("utf-8")
    events = DevJournal(root, operator.RUN_ID).events()
    assert [e["event_type"] for e in events].count("evaluation_started") == 1
    assert PRIVATE not in (root / "summary.json").read_text("utf-8")


def test_public_regression_attestation_required_but_no_diagnostic_case_gate(fake):
    args, state = fake
    args.public_checks_passed = False
    result = operator.evaluate_saved_candidate(args)
    assert result["status"] == "NOT_RUN_PUBLIC_CHECKS" and not result["stop_remaining"]
    assert state.loads == state.calls == 0 and result["evaluator_dispatches"] == 0


def test_identity_mismatch_stops_before_dispatch(fake):
    args, state = fake
    state.patch_hash = HASH
    result = operator.evaluate_saved_candidate(args)
    assert result["status"] == "PRECHECK_FAILED" and result["stop_remaining"]
    assert state.calls == result["evaluator_dispatches"] == 0


def test_uncertain_execution_is_private_and_cannot_reuse_root(fake, capsys):
    args, state = fake
    state.failure = True
    result = operator.evaluate_saved_candidate(args)
    assert result["status"] == "EVALUATION_UNCERTAIN" and result["stop_remaining"]
    assert PRIVATE not in json.dumps(result) and capsys.readouterr() == ("", "")
    assert result["evaluator_dispatches"] == state.calls == 1
    again = operator.evaluate_saved_candidate(args)
    assert again["status"] == "PRECHECK_FAILED" and again["stop_remaining"]
    assert state.calls == 1


@pytest.mark.parametrize("kind", ["error", "candidate_changed"])
def test_unsettled_verdict_or_changed_candidate_stops_remaining(fake, kind):
    args, state = fake
    state.verdict = "error" if kind == "error" else "pass"
    state.mutate = kind == "candidate_changed"
    result = operator.evaluate_saved_candidate(args)
    assert result["status"] == "EVALUATION_UNSETTLED" and result["stop_remaining"]
    assert state.calls == 1


def test_cli_never_emits_an_uncaught_exception_message(fake, monkeypatch, capsys):
    args, _ = fake
    monkeypatch.setattr(operator, "parser", lambda: SimpleNamespace(parse_args=lambda _: args))

    def fail(_args):
        raise RuntimeError(PRIVATE)

    monkeypatch.setattr(operator, "evaluate_saved_candidate", fail)
    assert operator.main([]) == 2
    captured = capsys.readouterr()
    assert PRIVATE not in captured.out and captured.err == ""
    assert json.loads(captured.out)["stop_remaining"] is True
