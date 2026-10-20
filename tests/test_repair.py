from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from patchloop import repair
from patchloop.artifacts import ArtifactStore
from patchloop.cli import app
from patchloop.dev import runner
from patchloop.dev.contracts import DevLimits, DevRunRequest
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError, ResumeContractMismatch
from patchloop.git_execution import run_git
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.util import directory_hash


@pytest.fixture
def request_file(tmp_path, smoke_package):
    manager = WorkspaceManager(repository_root() / "fixtures/repositories", tmp_path / "source")
    source = manager.create(
        "public", smoke_package.public.repository.url, smoke_package.public.repository.base_commit,
    )
    public = smoke_package.public.model_dump(mode="json")
    public.update(schema_version="repair-task-v1", split="repair")
    public["repository"].update(
        url="https://example.invalid/public.git",
        base_commit=run_git(source, "rev-parse", "HEAD").stdout.strip(),
    )
    task = tmp_path / "public.yaml"
    task.write_text(yaml.safe_dump(public), encoding="utf-8")
    request = tmp_path / "request.json"
    request.write_text(json.dumps({
        "task": "public.yaml", "source": str(source), "state_root": str(tmp_path / "state"),
        "provider": "mock", "model": "mock-dev", "sandbox": {"backend": "local"},
    }), encoding="utf-8")
    return request


def load_request(path):
    raw = json.loads(path.read_text())
    raw["task"] = path.parent / raw["task"]
    return repair.RepairRunRequest.model_validate(raw)


def no_evaluation(*args, **kwargs):
    pytest.fail("public repair must never load or execute private evaluation")


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
def test_public_cli_delivers_checked_patch_and_preserves_original(
    request_file, monkeypatch, context_policy,
):
    raw = json.loads(request_file.read_text())
    raw["context_policy"] = context_policy
    request_file.write_text(json.dumps(raw))
    request = load_request(request_file)
    original_source = request.source / "mini_data_utils/csvlite.py"
    original_source.write_text(original_source.read_text() + "\n# uncommitted source edit\n")
    (request.source / "untracked.txt").write_text("not part of the pinned public commit")
    before = directory_hash(request.source)
    monkeypatch.setattr(runner, "load_task_package", no_evaluation)
    monkeypatch.setattr(runner.EvaluationEngine, "evaluate", no_evaluation)
    original = runner.MockDevAdapter.next_turn
    inputs = []

    def observed(self, context, tools):
        inputs.append(json.loads(context))
        for tool in tools:
            if tool["name"] == "finish_task":
                assert "NOT_RUN" in tool["description"]
        return original(self, context, tools)

    monkeypatch.setattr(runner.MockDevAdapter, "next_turn", observed)
    result = CliRunner().invoke(app, ["repair", "--request", str(request_file)])
    assert result.exit_code == 0, result.output
    invocation = json.loads(result.output)
    run = invocation["runs"][0]
    assert run["terminal"] == "PATCH_READY"
    assert run["acceptance"] == "NOT_RUN" and run["evaluator"] is None
    assert invocation["cost_nanos"] == 0
    assert directory_hash(request.source) == before
    workspace = request.state_root / "workspaces" / run["run_id"] / "repo"
    assert not (workspace / "untracked.txt").exists()
    assert "uncommitted source edit" not in (workspace / "mini_data_utils/csvlite.py").read_text()
    assert inputs and all(p["public_task"]["split"] == "repair" for p in inputs)
    assert "private_spec_hash" not in json.dumps(inputs)
    delivery = run["delivery"]
    receipt = json.loads(Path(delivery["public_verification"]["path"]).read_text())
    checks = [e["payload"]["result"]["output"] for e in receipt["public_checks"]]
    assert checks and checks[-1]["passed"]
    assert checks[-1]["diff_hash"] == delivery["patch"]["content_hash"]
    assert "io.StringIO" in Path(delivery["patch"]["path"]).read_text()
    journal = DevJournal(request.state_root, run["run_id"])
    envelope = journal.load_envelope().model_dump(mode="json")
    assert "private_spec_hash" not in envelope and "evaluator_image_digest" not in envelope
    assert not any(e["event_type"] == "evaluator_finished" for e in journal.events())
    before_events = journal.events()
    again = repair.run_repair(request.model_copy(update={"resume_run_id": run["run_id"]}))
    assert again["runs"][0] == run
    assert journal.events() == before_events


@pytest.mark.parametrize("boundary", ["mutation_before_receipt", "check_receipt", "action_finished",
                                     "submission_recorded", "repair_delivered"])
def test_public_completion_crash_recovery_does_not_repeat_actions(
    request_file, monkeypatch, boundary,
):
    request = load_request(request_file)
    append = DevJournal.append
    run_ids = []

    class Crash(BaseException):
        pass

    def crash(self, event_type, payload):
        if (boundary == "mutation_before_receipt" and event_type == "action_finished"
                and payload["result"]["tool"] == "replace_text"):
            run_ids.append(self.run_id)
            raise Crash("simulated process interruption")
        event = append(self, event_type, payload)
        if ((event_type == boundary and (boundary != "action_finished"
                                        or payload["result"]["tool"] == "finish_task"))
                or (boundary == "check_receipt" and event_type == "action_finished"
                    and payload["result"]["tool"] == "run_check")):
            run_ids.append(self.run_id)
            raise Crash("simulated process interruption")
        return event

    monkeypatch.setattr(DevJournal, "append", crash)
    with pytest.raises(Crash, match="interruption"):
        repair.run_repair(request)
    monkeypatch.setattr(DevJournal, "append", append)
    if boundary == "repair_delivered":
        # A durable completion needs neither the original source nor the sandbox.
        request.source.rename(request.source.with_name("source-unavailable"))
        monkeypatch.setattr(runner, "prepared_sandbox", no_evaluation)
        monkeypatch.setattr(runner.MockDevAdapter, "__init__", no_evaluation)
    resumed = repair.run_repair(request.model_copy(update={"resume_run_id": run_ids[0]}))
    assert resumed["runs"][0]["terminal"] == "PATCH_READY"
    events = DevJournal(request.state_root, run_ids[0]).events()
    ids = [e["payload"]["action_id"] for e in events if e["event_type"] == "action_finished"]
    assert len(ids) == len(set(ids)) == 5
    assert sum(e["event_type"] == "repair_delivered" for e in events) == 1
    assert resumed["runs"][0]["accepted_mutations"] == 1


def test_failed_public_check_never_delivers_patch(request_file):
    request = load_request(request_file)
    task = yaml.safe_load(request.task.read_text())
    task["visible_checks"][0]["command"] = ["python", "-c", "raise SystemExit(1)"]
    request.task.write_text(yaml.safe_dump(task))
    request = request.model_copy(update={"limits": DevLimits(max_model_calls=4)})
    result = repair.run_repair(request)["runs"][0]
    assert result["terminal"] != "PATCH_READY"
    assert "delivery" not in result and result["acceptance"] == "NOT_RUN"


def test_public_limit_and_disallowed_mutation_remain_enforced(request_file):
    request = load_request(request_file)
    task = yaml.safe_load(request.task.read_text())
    task["constraints"]["max_diff_lines"] = 1
    request.task.write_text(yaml.safe_dump(task))
    request = request.model_copy(update={"limits": DevLimits(max_model_calls=2)})
    run = repair.run_repair(request)["runs"][0]
    assert run["terminal"] == "LIMIT_REACHED"
    assert run["accepted_mutations"] == 0 and "delivery" not in run


def test_public_request_is_not_a_dev_task_and_rejects_private_material(request_file):
    request = load_request(request_file)
    with pytest.raises(ContractError):
        runner.run_dev(DevRunRequest(provider="mock", model="mock-dev", task=request.task))
    raw = yaml.safe_load(request.task.read_text())
    dev_public = {**raw, "schema_version": "task-public-v1", "split": "smoke"}
    dev_task = request.task.parent / "dev-public.yaml"
    dev_task.write_text(yaml.safe_dump(dev_public))
    with pytest.raises(ContractError):
        runner.run_dev(DevRunRequest(provider="mock", model="mock-dev", task=dev_task))
    raw["private"] = {"reference_patch": "irrelevant.patch"}
    request.task.write_text(yaml.safe_dump(raw))
    with pytest.raises(ContractError, match="Extra inputs"):
        repair.run_repair(request)
    with pytest.raises(ValidationError):
        repair.RepairRunRequest.model_validate({**request.model_dump(), "provider": "openai"})


def test_prepared_image_failure_stops_before_any_provider_call(request_file, monkeypatch):
    raw = load_request(request_file).model_dump()
    raw.update(provider="openai", model="gpt-5.4-mini-2026-03-17", max_cost_usd="1",
               env_file=request_file.parent / "unused.env", sandbox={
                   "backend": "docker", "image": "public@sha256:" + "a" * 64,
                   "image_digest": "sha256:" + "a" * 64,
               })
    monkeypatch.setattr(runner, "_require_tracked_clean_paths", lambda *a, **k: None)
    monkeypatch.setattr(repair.DockerSandbox, "available", lambda **k: True)
    monkeypatch.setattr(repair.DockerSandbox, "image_identity", lambda *a, **k: None)
    monkeypatch.setattr(runner.OpenAIResponsesAdapter, "__init__", no_evaluation)
    run = repair.run_repair(raw)["runs"][0]
    assert run["terminal"] == "PREFLIGHT_FAILED"
    assert run["cost_nanos"] == 0 and run["call_counts"]["model"] == 0


def test_resume_identity_and_delivery_integrity(request_file):
    request = load_request(request_file)
    run = repair.run_repair(request)["runs"][0]
    resume = request.model_copy(update={"resume_run_id": run["run_id"]})
    with pytest.raises(ResumeContractMismatch):
        repair.run_repair(resume.model_copy(update={"limits": DevLimits(max_accepted_mutations=5)}))
    journal = DevJournal(request.state_root, run["run_id"])
    Path(run["delivery"]["patch"]["path"]).write_text("corrupt")
    with pytest.raises(RecoveryError):
        repair.load_delivery(journal, ArtifactStore(request.state_root / "artifacts"),
                             journal.load_envelope())
    with pytest.raises(RecoveryError):
        repair.run_repair(resume)
