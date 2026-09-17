"""Public diagnostic evidence: a mismatch is distinct from an incomplete execution."""

from __future__ import annotations

import json
import shutil
from dataclasses import replace
from types import SimpleNamespace

import pytest

from diagnostics import profile_scope_check as check
from diagnostics import profile_scope_program as program
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.repository import DiffSummary
from patchloop.sandbox.runner import SandboxResult
from patchloop.task_loader import load_public_task
from patchloop.util import sha256_bytes


def receipt(behavior="correct"):
    rows = []
    for field in program.FIELDS:
        for origin in program.ORIGINS:
            expected = program.expected_message(field, origin)
            actual = dict(expected)
            if behavior == "overbroad":
                actual[field] = ""
            elif behavior == "missing":
                actual.pop(field, None)
            rows.append({
                "case": f"{origin}:{field}", "profile_origin": origin, "field": field,
                "mode": "field", "provider": "openai", "model": program.MODEL_NAME,
                "message_kind": "tool_only_without_thinking",
                "actual": actual, "expected": expected, "passed": actual == expected,
            })
    passed = sum(row["passed"] for row in rows)
    rows.append({"summary": {"passed": passed, "failed": 4 - passed}, "project_modules": {
        name: "/workspace/pydantic_ai_slim/" + name.replace(".", "/") + ".py"
        for name in ("pydantic_ai", "pydantic_ai.models.openai", "pydantic_ai.profiles.openai",
                     "pydantic_ai.providers.deepseek")
    }})
    stdout = "\n".join(json.dumps(row) for row in rows) + "\n"
    return SandboxResult(command=check.registered_check().command, exit_code=int(passed != 4),
                         stdout=stdout, stderr="", duration_ms=1, timed_out=False,
                         truncated=False, original_output_bytes=len(stdout.encode()))


@pytest.mark.parametrize("behavior,ordinary,supplied", [
    ("correct", True, True), ("overbroad", False, True), ("missing", True, False),
])
def test_complete_matrix_distinguishes_preservation_from_missing_requirement(
    behavior, ordinary, supplied,
):
    rows = check.observations(receipt(behavior))
    assert [row["passed"] for row in rows] == [ordinary, supplied, ordinary, supplied]


@pytest.mark.parametrize("override", [
    {"timed_out": True}, {"deadline_exhausted": True}, {"cleanup_failed": True},
    {"truncated": True}, {"exit_code": None}, {"exit_code": 2}, {"exit_code": 137},
])
def test_infrastructure_loss_is_never_a_confirmed_case_failure(override):
    with pytest.raises(ContractError, match="incomplete or uncertain"):
        check.observations(replace(receipt("overbroad"), **override))


@pytest.mark.parametrize("corruption", [
    "empty", "missing_case", "duplicate_case", "changed_trigger", "wrong_expected",
    "false_pass", "wrong_summary", "image_import", "wrong_exit", "malformed",
])
def test_partial_or_inconsistent_receipts_cannot_certify_the_contrast(corruption):
    result = receipt("overbroad")
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    if corruption == "empty":
        rows = []
    elif corruption == "missing_case":
        rows.pop(0)
    elif corruption == "duplicate_case":
        rows[1] = rows[0]
    elif corruption == "changed_trigger":
        rows[0]["mode"] = "auto"
    elif corruption == "wrong_expected":
        rows[0]["expected"] = rows[0]["actual"]
        rows[0]["passed"] = True
    elif corruption == "false_pass":
        rows[0]["passed"] = True
    elif corruption == "wrong_summary":
        rows[-1]["summary"] = {"passed": 4, "failed": 0}
    elif corruption == "image_import":
        rows[-1]["project_modules"]["pydantic_ai"] = "/pydantic-ai/pydantic_ai/__init__.py"
    elif corruption == "wrong_exit":
        result = replace(result, exit_code=0)
    elif corruption == "malformed":
        rows[0] = None
    result = replace(result, stdout="\n".join(json.dumps(row) for row in rows))
    with pytest.raises(ContractError, match="public contrast output"):
        check.observations(result)


def test_check_uses_fixed_public_program_with_existing_dependency_environment():
    public = load_public_task(check.TASK / "public.yaml")
    original = public.visible_checks[0]
    diagnostic = check.registered_check()
    assert diagnostic.command[:2] == [original.command[0], "-c"]
    assert diagnostic.command[2] == check.PROGRAM.read_text(encoding="utf-8")
    assert diagnostic.environment == original.environment
    assert diagnostic.timeout_seconds == original.timeout_seconds
    assert diagnostic.output_limit_bytes == original.output_limit_bytes
    assert diagnostic.id not in {item.id for item in public.visible_checks}
    compile(diagnostic.command[2], "<public-contrast>", "exec")


@pytest.fixture
def session(tmp_path, monkeypatch):
    task = tmp_path / "public-only-task"
    task.mkdir()
    for name in ("public.yaml", "environment.yaml"):
        shutil.copyfile(check.TASK / name, task / name)
    monkeypatch.setattr(check, "TASK", task)
    patch = tmp_path / "supplied.diff"
    patch.write_text(
        "diff --git a/pydantic_ai_slim/pydantic_ai/models/openai.py "
        "b/pydantic_ai_slim/pydantic_ai/models/openai.py\n"
        "--- a/pydantic_ai_slim/pydantic_ai/models/openai.py\n"
        "+++ b/pydantic_ai_slim/pydantic_ai/models/openai.py\n"
        "@@ -1 +1 @@\n-old\n+new\n", encoding="utf-8", newline="\n",
    )
    state = SimpleNamespace(checks=[], workspaces=[], image_available=True,
                            base_result=receipt("missing"), candidate_result=receipt("overbroad"))
    source = SimpleNamespace(model_dump=lambda **kw: {"test_public_source": True})
    monkeypatch.setattr(check, "admission_hash", lambda path: "sha256:" + "a" * 64)
    monkeypatch.setattr(check, "load_source", lambda *args, **kw: (source, tmp_path))

    class Manager:
        def __init__(self, fixture_root, workspace_root, **kwargs):
            self.root = workspace_root
            self.patch = ""

        def create(self, label, *args):
            state.workspaces.append(label)
            path = self.root / label
            path.mkdir(parents=True)
            return path

        def apply_patch(self, workspace, path):
            assert path.read_bytes() == patch.read_bytes()
            self.patch = path.read_text(encoding="utf-8")

        def diff_summary(self, workspace):
            return DiffSummary([], int(bool(self.patch)), 0, self.patch, [])

        patch_changed_files = staticmethod(check.WorkspaceManager.patch_changed_files)

    class Sandbox:
        def __init__(self, image):
            self.image = image

        def image_identity(self):
            return self.image.split("@")[-1] if state.image_available else None

        def run_check(self, workspace, registered, **kwargs):
            state.checks.append((workspace, registered, kwargs))
            return state.base_result if len(state.checks) == 1 else state.candidate_result

    monkeypatch.setattr(check, "WorkspaceManager", Manager)
    monkeypatch.setattr(check, "DockerSandbox", Sandbox)
    state.arguments = {"prepared_source": tmp_path / "unused-prepared.json",
                       "candidate_patch": patch, "output": tmp_path / "evidence"}
    return state


def test_complete_behavior_failure_continues_but_never_becomes_acceptance(session):
    result = check.run(**session.arguments)
    assert result["status"] == "COMPLETE" and result["task_acceptance"] == "NOT_ASSESSED"
    assert result["private_evaluation"] == "NOT_RUN" and not result["official"]
    assert session.workspaces == ["base", "candidate"] and len(session.checks) == 2
    assert session.checks[0][1] == session.checks[1][1]
    identities = [call[2]["execution_identity"] for call in session.checks]
    assert identities[0]["manifest_hash"] == identities[1]["manifest_hash"]
    assert identities[0]["action_id"] != identities[1]["action_id"]
    events = DevJournal(session.arguments["output"], "run_dev_profilescope").events()
    assert events[-1]["event_type"] == "public_contrast_closed"
    assert len([event for event in events if event["event_type"] == "public_contrast_started"]) == 2


@pytest.mark.parametrize("failure", ["image", "source", "patch", "cleanup", "partial"])
def test_uncertainty_stops_without_fallback_or_second_execution(session, monkeypatch, failure):
    if failure == "image":
        session.image_available = False
    elif failure == "source":
        def missing(*args, **kwargs):
            raise ContractError("missing prepared source")
        monkeypatch.setattr(check, "load_source", missing)
    elif failure == "patch":
        session.arguments["candidate_patch"].write_text(
            "diff --git a/tests/private.py b/tests/private.py\n", encoding="utf-8", newline="\n")
    elif failure == "cleanup":
        session.base_result = replace(session.base_result, cleanup_failed=True)
    elif failure == "partial":
        session.base_result = replace(session.base_result, stdout="")
    with pytest.raises(ContractError):
        check.run(**session.arguments)
    assert len(session.checks) == (1 if failure in {"cleanup", "partial"} else 0)
    assert "candidate" not in session.workspaces
    events = DevJournal(session.arguments["output"], "run_dev_profilescope").events()
    assert events[-1]["event_type"] == "public_contrast_stopped"
    assert not (session.arguments["output"] / "result.json").exists()


def test_existing_evidence_cannot_be_reused_or_overwritten(session):
    root = session.arguments["output"]
    root.mkdir()
    marker = root / "receipt.txt"
    marker.write_text("original", encoding="utf-8")
    before = sha256_bytes(marker.read_bytes())
    with pytest.raises(FileExistsError):
        check.run(**session.arguments)
    assert sha256_bytes(marker.read_bytes()) == before
    assert not session.checks and not session.workspaces


def test_repository_cannot_be_used_for_generated_evidence(session):
    session.arguments["output"] = check.repository_root() / "unused-diagnostic-state"
    with pytest.raises(ContractError, match="outside the repository"):
        check.run(**session.arguments)
    assert not session.arguments["output"].exists()
