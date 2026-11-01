"""Registered file batches preserve source scope, checks and durable recovery."""

from __future__ import annotations

import json
import shutil

import pytest
from pydantic import ValidationError

from patchloop.dev import file_edits, file_transaction, runner
from patchloop.dev.contracts import (
    DevRunRequest,
    FileEditIntent,
    PublicTurnDecision,
    RequestedTool,
)
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas, validate_tool_batch
from patchloop.errors import ActionConflict, ContractError
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root

SOURCE = "mini_data_utils/csvlite.py"
CREATED = "mini_data_utils/csv_support.py"
OTHER = "mini_data_utils/other_support.py"
TEST = "tests/test_csvlite.py"


def source_read(path=SOURCE, action="read-source"):
    return RequestedTool(name="read_file", action_id=action, arguments={
        "path": path, "start_line": None, "end_line": None,
    }, turn_decision=PublicTurnDecision(
        mode="inspect", basis="Observe the current file before an exact edit.",
        evidence_goal="Find the relevant source anchor.",
    ))


def edit(path, old, new, occurrence=1):
    return {"path": path, "old_text": old, "new_text": new, "occurrence": occurrence}


def batch(action="batch", edits=None, *, undo=None):
    if edits is None and undo is None:
        edits = [edit(CREATED, None, "VALUE = 1\n"),
                 edit(SOURCE, "physical_line", "record_line", "all")]
    return RequestedTool(name="edit_files", action_id=action, arguments={
        "edits": edits, "undo_action_id": undo,
        "hypothesis": "Apply the related source changes as one recoverable candidate.",
        "expected_behavior": "The parser keeps its public behavior and all original tests.",
    })


def check(action="check-current"):
    return RequestedTool(name="run_check", action_id=action,
                         arguments={"check_id": "existing-unit-tests"},
                         turn_decision=PublicTurnDecision(mode="verify", basis="Check this diff."))


def expanded_gateway(gateway_factory):
    gateway, journal, workspace = gateway_factory()
    gateway.public_task.constraints.max_changed_files = 3
    gateway.public_task.constraints.max_diff_lines = 80
    gateway.public_task.constraints.public_api_changes_allowed = True
    return gateway, journal, workspace


def restart(gateway):
    return DevToolGateway(workspace=gateway.workspace, public_task=gateway.public_task,
                          sandbox=gateway.sandbox, journal=gateway.journal, limits=gateway.limits)


def test_create_and_observed_edit_are_one_action_with_readable_searchable_new_source(
    gateway_factory,
):
    gateway, journal, workspace = expanded_gateway(gateway_factory)
    before = (workspace / SOURCE).read_bytes()
    assert gateway.execute(source_read()).status == "succeeded"
    call = batch()
    assert validate_tool_batch([call]) == "single_action"
    result = gateway.execute_batch([call])[0]
    assert result.status == "succeeded", result.message
    assert (workspace / SOURCE).read_bytes() == before.replace(b"physical_line", b"record_line")
    assert (workspace / CREATED).read_bytes() == b"VALUE = 1\n"
    assert set(gateway.current_diff.changed_files) == {SOURCE, CREATED}
    assert gateway.current_diff.untracked_files == []
    assert gateway.accepted_mutations == 1
    assert result.workspace_diff_hash == gateway.current_diff_hash
    assert result.output["baseline_diff_hash"] != gateway.current_diff_hash
    assert len([e for e in journal.events() if e["event_type"] == "action_finished"
                and e["payload"]["action_id"] == call.action_id]) == 1

    read = gateway.execute(source_read(CREATED, "read-created"))
    assert read.status == "succeeded" and "VALUE = 1" in json.dumps(read.output)
    search = gateway.execute(RequestedTool(
        name="search_files", action_id="search-created",
        arguments={"query": "VALUE = 1", "path_glob": "mini_data_utils/**"},
        turn_decision=PublicTurnDecision(mode="inspect", basis="Locate the new helper.",
                                        evidence_goal="Find the created source by text."),
    ))
    assert search.status == "succeeded"
    assert [span["path"] for span in search.output["spans"]] == [CREATED]


def test_undo_preserves_unrelated_later_edit_and_replay_has_no_second_mutation(gateway_factory):
    gateway, journal, workspace = expanded_gateway(gateway_factory)
    before = (workspace / SOURCE).read_bytes()
    gateway.execute(source_read())
    original = batch()
    assert gateway.execute(original).status == "succeeded"
    unrelated = batch("unrelated", [edit(OTHER, None, "OTHER = 7\n")])
    assert gateway.execute(unrelated).status == "succeeded"
    undo = batch("undo", undo=original.action_id)
    result = gateway.execute(undo)
    assert result.status == "succeeded", result.message
    assert (workspace / SOURCE).read_bytes() == before
    assert not (workspace / CREATED).exists()
    assert (workspace / OTHER).read_bytes() == b"OTHER = 7\n"
    assert gateway.current_diff.changed_files == [OTHER]
    assert gateway.accepted_mutations == 3
    saved = journal.path.read_bytes()
    resumed = restart(gateway)
    replay = resumed.execute(undo)
    assert replay.replayed and resumed.accepted_mutations == 3
    assert replay.model_dump(exclude={"replayed"}) == result.model_dump(exclude={"replayed"})
    assert journal.path.read_bytes() == saved
    conflicting = undo.model_copy(
        update={"arguments": {**undo.arguments, "hypothesis": "Different"}}
    )
    with pytest.raises(ActionConflict):
        resumed.execute(conflicting)
    assert journal.path.read_bytes() == saved


def test_undo_rejects_changed_affected_file_without_disturbing_candidate(gateway_factory):
    gateway, _, workspace = expanded_gateway(gateway_factory)
    gateway.execute(source_read())
    assert gateway.execute(batch()).status == "succeeded"
    assert gateway.execute(source_read(CREATED, "read-created")).status == "succeeded"
    later = batch("later", [edit(CREATED, "VALUE = 1", "VALUE = 2")])
    assert gateway.execute(later).status == "succeeded"
    before = WorkspaceManager.diff_summary(workspace)
    result = gateway.execute(batch("stale-undo", undo="batch"))
    assert result.status == "failed"
    assert gateway.current_diff.patch == before.patch
    assert (workspace / CREATED).read_bytes() == b"VALUE = 2\n"
    assert gateway.accepted_mutations == 2


@pytest.mark.parametrize("reason", [
    "unobserved", "scope", "path_scope", "create_overwrite", "unknown_undo",
])
def test_rejected_transaction_leaves_all_files_untouched(gateway_factory, reason):
    gateway, _, workspace = expanded_gateway(gateway_factory)
    before = (workspace / SOURCE).read_bytes()
    call = batch()
    if reason != "unobserved":
        gateway.execute(source_read())
    if reason == "scope":
        gateway.public_task.constraints.max_changed_files = 1
    elif reason == "path_scope":
        call = batch(edits=[edit("outside_helper.py", None, "VALUE = 1\n")])
    elif reason == "create_overwrite":
        call = batch(edits=[edit(SOURCE, None, "replacement\n")])
    elif reason == "unknown_undo":
        call = batch(undo="not-an-accepted-action")
    result = gateway.execute(call)
    assert result.status == "failed", reason
    assert (workspace / SOURCE).read_bytes() == before
    assert not (workspace / CREATED).exists()
    assert not (workspace / "outside_helper.py").exists()
    assert gateway.current_diff.patch == "" and gateway.current_diff.untracked_files == []
    assert gateway.accepted_mutations == 0


def test_second_file_write_failure_rolls_back_created_file_and_index(gateway_factory, monkeypatch):
    gateway, _, workspace = expanded_gateway(gateway_factory)
    before = (workspace / SOURCE).read_bytes()
    gateway.execute(source_read())
    original_write = file_transaction._write_one
    failed = False

    def fail_once(folder, change, content):
        nonlocal failed
        if change.path == SOURCE and not failed:
            failed = True
            raise OSError("synthetic second-file write failure")
        return original_write(folder, change, content)

    monkeypatch.setattr(file_transaction, "_write_one", fail_once)
    result = gateway.execute(batch())
    assert failed and result.status == "failed"
    assert (workspace / SOURCE).read_bytes() == before
    assert not (workspace / CREATED).exists()
    assert gateway.current_diff.patch == "" and gateway.current_diff.untracked_files == []
    assert gateway.accepted_mutations == 0


@pytest.mark.parametrize("failure", ["write", "result"])
def test_unconfirmed_rollback_stays_pending_and_can_resume(gateway_factory, monkeypatch, failure):
    gateway, journal, workspace = expanded_gateway(gateway_factory)
    before = (workspace / SOURCE).read_bytes()
    gateway.execute(source_read())
    original_write = file_transaction._write_one
    call = batch()

    def fail_write_or_rollback(folder, change, content):
        if (change.path == CREATED and content is None) or (
                failure == "write" and change.path == SOURCE):
            raise OSError("synthetic write or rollback failure")
        return original_write(folder, change, content)

    def fail_result(*args, **kwargs):
        raise OSError("synthetic result construction failure")

    with monkeypatch.context() as scoped:
        scoped.setattr(file_transaction, "_write_one", fail_write_or_rollback)
        if failure == "result":
            scoped.setattr(file_edits, "result", fail_result)
        with pytest.raises(file_transaction.FileTransactionUncertain):
            gateway.execute(call)
    assert not any(e["event_type"] == "action_finished"
                   and e["payload"].get("action_id") == call.action_id
                   for e in journal.events())
    assert gateway.accepted_mutations == 0
    resumed = restart(gateway)
    result = resumed.execute(call)
    assert result.status == "succeeded", result.message
    assert (workspace / SOURCE).read_bytes() == before.replace(b"physical_line", b"record_line")
    assert (workspace / CREATED).read_bytes() == b"VALUE = 1\n"
    assert resumed.accepted_mutations == 1
    for kind in ("action_started", "action_finished"):
        assert sum(e["event_type"] == kind and e["payload"].get("action_id") == call.action_id
                   for e in journal.events()) == 1


class Crash(BaseException):
    pass


@pytest.mark.parametrize("boundary", ["admission", "first_file", "finished"])
def test_crash_resumes_admitted_batch_once_across_partial_new_file_state(
    gateway_factory, monkeypatch, boundary,
):
    gateway, journal, workspace = expanded_gateway(gateway_factory)
    before = (workspace / SOURCE).read_bytes()
    gateway.execute(source_read())
    call = batch()
    original_append, original_write = DevJournal.append, file_transaction._write_one
    writes, crashed = [], False

    def append(self, event_type, payload=None):
        nonlocal crashed
        result = original_append(self, event_type, payload)
        target = "action_started" if boundary == "admission" else "action_finished"
        if (not crashed and boundary != "first_file" and event_type == target
                and payload.get("action_id") == call.action_id):
            crashed = True
            raise Crash
        return result

    def write(folder, change, content):
        nonlocal crashed
        original_write(folder, change, content)
        writes.append(change.path)
        if not crashed and boundary == "first_file":
            crashed = True
            raise Crash

    monkeypatch.setattr(DevJournal, "append", append)
    monkeypatch.setattr(file_transaction, "_write_one", write)
    with pytest.raises(Crash):
        gateway.execute(call)
    if boundary == "first_file":
        assert (workspace / CREATED).exists() and (workspace / SOURCE).read_bytes() == before
    resumed = restart(gateway)
    result = resumed.execute(call)
    assert result.status == "succeeded", result.message
    assert writes == [CREATED, SOURCE]
    assert (workspace / CREATED).read_bytes() == b"VALUE = 1\n"
    assert (workspace / SOURCE).read_bytes() == before.replace(b"physical_line", b"record_line")
    assert resumed.accepted_mutations == 1
    for kind in ("action_started", "action_finished"):
        assert sum(e["event_type"] == kind and e["payload"].get("action_id") == call.action_id
                   for e in journal.events()) == 1
    saved = journal.path.read_bytes()
    assert restart(resumed).execute(call).replayed
    assert journal.path.read_bytes() == saved and writes == [CREATED, SOURCE]


def test_each_new_diff_needs_fresh_checks_and_original_tests_cannot_be_replaced(gateway_factory):
    gateway, _, workspace = expanded_gateway(gateway_factory)
    gateway.execute(source_read())
    assert gateway.execute(check("base-check")).status == "succeeded"
    assert gateway.visible_checks_pass()
    assert gateway.execute(batch()).status == "succeeded"
    assert not gateway.visible_checks_pass()
    assert [row["status"] for row in gateway.visible_check_status()] == ["NOT_RUN"]
    assert gateway.execute(check()).status == "succeeded" and gateway.visible_checks_pass()
    candidate = gateway.current_diff.patch
    gateway.public_task.constraints.allowed_paths = ["mini_data_utils/**", "tests/**"]
    gateway.public_task.constraints.forbidden_paths = []
    gateway.public_task.constraints.additive_test_roots = ["tests"]
    original = (workspace / TEST).read_text(encoding="utf-8")
    assert gateway.execute(source_read(TEST, "read-test")).status == "succeeded"
    rejected = gateway.execute(batch("replace-tests", [edit(TEST, original, "pass\n")]))
    assert rejected.status == "failed"
    assert (workspace / TEST).read_text(encoding="utf-8") == original
    assert gateway.current_diff.patch == candidate
    assert gateway.accepted_mutations == 1
    assert gateway.visible_checks_pass()


def test_schema_requires_one_explicit_operation_and_mutations_cannot_be_batched():
    schema = next(s for s in dev_tool_schemas(finish_enabled=False)
                  if s["name"] == "edit_files")
    parameters = schema["parameters"]
    assert set(parameters["properties"]) == {
        "edits", "undo_action_id", "hypothesis", "expected_behavior",
    }
    assert set(parameters["required"]) == set(parameters["properties"])
    assert parameters["additionalProperties"] is False
    children = next(item for item in parameters["properties"]["edits"]["anyOf"]
                    if item.get("type") == "array")["items"]
    assert set(children["required"]) == {"path", "old_text", "new_text", "occurrence"}
    assert children["additionalProperties"] is False
    args = batch().arguments
    for invalid in ({**args, "edits": None}, {**args, "undo_action_id": "earlier"},
                    {**args, "edits": [args["edits"][0]] * 2}):
        with pytest.raises(ValidationError):
            FileEditIntent.model_validate(invalid)
    with pytest.raises(ContractError):
        validate_tool_batch([batch(), source_read()])
    with pytest.raises(ContractError):
        validate_tool_batch([batch(), batch("other")])


def test_mock_file_batch_delivers_new_helper_to_isolated_evaluation(tmp_path, monkeypatch):
    # Copy the existing evaluator package opaquely; only public scope changes.
    task = tmp_path / "task"
    shutil.copytree(repository_root() / "tasks/smoke/csv-quoted-newline", task)
    public = task / "public.yaml"
    text = public.read_text(encoding="utf-8")
    public.write_text(text.replace("max_changed_files: 1", "max_changed_files: 3")
                     .replace("max_diff_lines: 20", "max_diff_lines: 80")
                     .replace("public_api_changes_allowed: false",
                              "public_api_changes_allowed: true"), encoding="utf-8")
    captured = []

    class FileMock(MockDevAdapter):
        def _next_action(self, context, tools):
            turn = super()._next_action(context, tools)
            for index, call in enumerate(turn.tool_calls):
                if call.name != "replace_text":
                    continue
                assert "edit_files" in {tool["name"] for tool in tools}
                turn.tool_calls[index] = batch("mock-file-batch", [
                    edit(CREATED, None, "import csv\nimport io\n\n"
                         "def rows_from_text(text):\n"
                         "    return list(csv.reader(io.StringIO(text, newline=\"\")))\n"),
                    edit(SOURCE, self.mutation.old_text,
                         "from .csv_support import rows_from_text\n\n\n"
                         "def parse_rows(text: str) -> list[list[str]]:\n"
                         "    return rows_from_text(text)"),
                ])
            captured.extend(call.name for call in turn.tool_calls)
            return turn

    monkeypatch.setattr(runner, "MockDevAdapter", FileMock)
    state = tmp_path / "state"
    result = runner.run_dev(DevRunRequest(provider="mock", model="mock-dev",
                                        task=public, state_root=state))
    run = result["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS", run
    assert run["evaluator"]["task_acceptance"] == "PASS"
    assert run["evaluator"]["safety_state"] == "NOT_RUN"
    assert captured == ["search_files", "read_file", "edit_files", "run_check", "finish_task"]
    assert run["accepted_mutations"] == 1 and run["call_counts"]["tool"] == 5
    workspace = state / "workspaces" / run["run_id"] / "repo"
    delivered = WorkspaceManager.diff_summary(workspace)
    assert set(delivered.changed_files) == {SOURCE, CREATED}
    assert delivered.patch_hash == run["artifact_hashes"]["submitted_patch"]
    assert (workspace / CREATED).read_text(encoding="utf-8").startswith("import csv\nimport io")
