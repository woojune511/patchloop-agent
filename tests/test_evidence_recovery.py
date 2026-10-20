"""Offline source delivery and reproduction identity, not repair-quality evidence."""

from __future__ import annotations

import copy
import json

import httpx
import pytest
from test_dev_history_search import deliver, items
from test_dev_planning import request as mock_request
from test_dev_probe_action_replay import restore
from test_dev_probe_cases import CANDIDATE, ExecutingProbe
from test_dev_probes import context
from test_dev_tools import mutation_call, read_calls

from diagnostics import discovery_case_selection, paired_observation
from patchloop.artifacts import ArtifactStore
from patchloop.dev import reproduction, runner
from patchloop.dev.contracts import DevModelTurn, RequestedTool
from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.dev.history_evidence import EvidenceHistory, separate
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.source_recovery import expand
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas
from patchloop.util import canonical_json, sha256_bytes


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("evidence recovery tests must not send provider requests")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def exchange(call, result):
    return [
        {"type": "function_call", "call_id": call.action_id, "name": call.name,
         "arguments": canonical_json(call.arguments)},
        {"type": "function_call_output", "call_id": call.action_id,
         "output": result.model_dump_json()},
    ]


def test_source_search_recovers_delivered_body_after_loss_without_cache_leak(gateway_factory):
    gateway, journal, workspace = gateway_factory()
    gateway.history_search_policy = "public-v1"
    store = ArtifactStore(journal.root / "artifacts")
    search, read = read_calls()
    original = gateway.execute(read)
    data = items(exchanges=exchange(read, original))
    deliver(journal, store, data)
    visible = gateway.execute(search)
    assert "source_recovery" not in visible.output
    deliver(journal, store, items(), turn="handoff")
    lost_call = search.model_copy(update={"action_id": "after-loss"})
    recovered = gateway.execute(lost_call)
    assert recovered.status == "succeeded"
    assert recovered.output["spans"][0]["content"] == original.output["spans"][0]["content"]
    assert recovered.output["source_recovery"]["recovered"][0]["action_id"] == read.action_id
    recovered_read = recovered.output["source_recovery"]["recovered"][0]
    assert recovered_read["delivery"] == "complete_observed_read"
    assert sum(len(s["content"]) for s in recovered.output["spans"]) <= 24_000
    deliver(journal, store, items(exchanges=exchange(lost_call, recovered)), turn="restored")
    current = restore(gateway, journal, workspace, gateway.public_task, None)
    current.history_search_policy = "public-v1"
    # Recovery is an identical receipt, but a fresh search observes current visibility.
    assert current.execute(lost_call).replayed
    fresh = current.execute(search.model_copy(update={"action_id": "already-delivered"}))
    assert "source_recovery" not in fresh.output
    assert fresh.output["spans"][0]["content"] == visible.output["spans"][0]["content"]


def test_source_recovery_never_uses_undelivered_or_old_version_body(gateway_factory):
    gateway, journal, _ = gateway_factory()
    gateway.history_search_policy = "public-v1"
    search, read = read_calls()
    original = gateway.execute(read)
    result = gateway.execute(search)
    assert "source_recovery" not in result.output  # Executed but never sent to the model.
    store = ArtifactStore(journal.root / "artifacts")
    deliver(journal, store, items(exchanges=exchange(read, original)))
    deliver(journal, store, items(), turn="handoff")
    assert gateway.execute(mutation_call(gateway)).status == "succeeded"
    result = gateway.execute(search.model_copy(update={"action_id": "edited-search"}))
    assert result.output["source_recovery"]["recovered"] == []
    assert result.output["source_recovery"]["omitted"][0]["delivery"].startswith("old_file_version")
    assert result.output["spans"][0]["file_hash"] != original.output["spans"][0]["file_hash"]


def test_recovery_overflow_keeps_all_search_hits_and_exact_record_pointer(gateway_factory):
    gateway, _, _ = gateway_factory()
    search, read = read_calls()
    original, hit = gateway.execute(read), gateway.execute(search)
    history = EvidenceHistory()
    history.ingest(items(exchanges=exchange(read, original)), sequence=1,
                   turn_id="old", input_hash="old")
    history.ingest(items(), sequence=2, turn_id="new", input_hash="new")
    before = copy.deepcopy(hit.output)
    result = expand(hit.output, history, set(), limit=len(hit.output["spans"][0]["content"]))
    assert result["spans"] == before["spans"] and hit.output == before
    omitted = result["source_recovery"]["omitted"][0]
    assert omitted["delivery"] == "omitted_size_limit"
    assert history.records[omitted["record_id"]]["body"]["result"]["action_id"] == read.action_id


def intent(task, **changes):
    return {
        "requirement_quote": task.issue.title,
        "entrypoint": "mini_data_utils.csvlite.parse_rows",
        "input_conditions": "One quoted newline inside a two-column record.",
        "environment_conditions": "Import the current workspace parser with normal defaults.",
        "expected_json": json.dumps([["h", "v"], ["first\nsecond", "x"]]),
        **changes,
    }


def probe(task, action="original", *, source=CANDIDATE, replay=None, binding=True):
    return RequestedTool(name="run_probe", action_id=action, arguments={
        "question": None if replay else "Does the public parser preserve the quoted newline?",
        "python_source": None if replay else source,
        "replay_action_id": replay,
        "reproduction": intent(task) if binding and replay is None else None,
    }, turn_decision={"mode": "verify", "basis": "Compare the same public reproduction."})


def test_same_reproduction_before_after_restart_and_handoff_remains_scoped(
    gateway_factory, smoke_package,
):
    gateway, journal, workspace = gateway_factory()
    backend = ExecutingProbe()
    gateway.probe_sandbox = backend
    original = gateway.execute(probe(gateway.public_task))
    assert original.status == "succeeded", original
    assert original.output["reproduction"]["comparison"] == "mismatched"
    assert gateway.reproduction_review(diff_hash=gateway.current_diff_hash)["items"][0][
        "evidence"]["status"] == "REFUTED"
    assert original.output["reproduction"]["call_observation"]["calls"][0]["arguments"]
    gateway.execute_batch(read_calls())
    assert gateway.execute(mutation_call(gateway)).status == "succeeded"
    current = restore(gateway, journal, workspace, gateway.public_task, backend)
    replay_call = probe(gateway.public_task, "recheck", replay="original")
    replay = current.execute(replay_call)
    assert replay.status == "succeeded", replay
    assert replay.output["reproduction"]["comparison"] == "matched"
    assert replay.output["source_hash"] == sha256_bytes(CANDIDATE.encode())
    assert replay.output["execution_source_hash"] == sha256_bytes(backend.sources[0].encode())
    assert backend.sources[0] == backend.sources[1]
    assert current.execute(replay_call).replayed and backend.calls == 2
    review = current.reproduction_review(diff_hash=current.current_diff_hash)
    assert review["items"][0]["comparison_status"] == "mismatch_to_match"
    assert review["items"][0]["evidence"]["status"] == "SUPPORTED"
    assert review["items"][0]["repair_success"] == "not_assessed"
    assert review["items"][0]["requirement_mapping"] == "model_authored_unverified"
    assert review["required"]["status"] == "UNKNOWN"
    assert not current.checks_by_diff
    state = compact_model_state(context(current, smoke_package), [])
    handoff = assemble_model_input(system_prompt="fixed", state=state, history=[],
                                   context_policy="segmented-v1")
    assert reconstruct_state(handoff)["reproduction_review"] == review
    history = EvidenceHistory()
    history.ingest(handoff, sequence=1, turn_id="handoff", input_hash="input")
    assert "reproduction_review" not in canonical_json(history.records)
    split = separate({"call": {"tool": "run_probe", "arguments": replay_call.arguments},
                      "result": replay.model_dump(mode="json")})
    assert "/result/output/reproduction/binding/definition" in split["annotations"]
    assert "expected_json" not in canonical_json(split["observed"])
    assert current.reproduction_review(diff_hash="later-diff")["items"][0][
        "comparison_status"] == "current_diff_not_observed"
    assert current.reproduction_review(diff_hash="later-diff")["items"][0][
        "evidence"]["status"] == "UNKNOWN"


def test_helper_pass_and_changed_predicate_cannot_resolve_original(gateway_factory):
    gateway, _, _ = gateway_factory()
    backend = ExecutingProbe()
    gateway.probe_sandbox = backend
    gateway.execute(probe(gateway.public_task))
    helper = gateway.execute(probe(gateway.public_task, "helper", source="print(1)", binding=False))
    assert helper.output["verification_scope"] == "helper_or_unbound_diagnostic"
    changed = probe(gateway.public_task, "changed-purpose")
    changed.arguments["reproduction"]["expected_json"] = "null"
    assert gateway.execute(changed).status == "succeeded"
    review = gateway.reproduction_review(diff_hash=gateway.current_diff_hash)
    assert review["helper_or_unbound_executions"] == 1 and len(review["items"]) == 2
    assert all(row["repair_success"] == "not_assessed" for row in review["items"])
    override = probe(gateway.public_task, "bad-replay", replay="original")
    override.arguments["reproduction"] = intent(gateway.public_task)
    assert gateway.execute(override).status == "failed"
    assert backend.calls == 3
    assert gateway.reproduction_review(diff_hash=gateway.current_diff_hash)[
        "helper_or_unbound_executions"] == 1


@pytest.mark.parametrize("adapter", ["case_selection", "paired_observation"])
def test_diagnostic_adapters_preserve_bound_reproduction_and_action_recovery(
    gateway_factory, adapter,
):
    original, journal, workspace = gateway_factory()
    gateway_type = (discovery_case_selection.CaseSelectionGateway if adapter == "case_selection"
                    else paired_observation.gateway_type(DevToolGateway))
    backend = ExecutingProbe()
    gateway = gateway_type(workspace=workspace, public_task=original.public_task,
                           sandbox=original.sandbox, journal=journal, limits=original.limits,
                           probe_sandbox=backend)
    call = probe(gateway.public_task)
    result = gateway.execute(call)
    assert result.status == "succeeded", result
    receipt = result.output["reproduction"]
    assert receipt["comparison"] == "mismatched"
    assert receipt["call_observation"]["calls"][0]["arguments"]
    assert gateway.execute(call).replayed and backend.calls == 1
    replay = gateway.execute(probe(gateway.public_task, "repeat", replay="original"))
    assert replay.output["reproduction"]["binding"] == receipt["binding"]
    assert replay.output["reproduction"]["comparison"] == "mismatched"
    invalid = probe(gateway.public_task, "bad-declaration")
    invalid.arguments["reproduction"]["entrypoint"] = "not a qualified name"
    assert gateway.execute(invalid).status == "failed" and backend.calls == 2
    assert gateway.reproduction_review(diff_hash=gateway.current_diff_hash)[
        "required"]["status"] == "UNKNOWN"


@pytest.mark.parametrize("source", [
    "print([[\"h\", \"v\"], [\"first\\nsecond\", \"x\"]])",  # No target call.
    "import missing_setup_dependency",  # Setup failure is not the reported bug.
    CANDIDATE + "\nprint('extra non-JSON output')",
])
def test_unobserved_call_or_unusable_output_is_not_compared(gateway_factory, source):
    gateway, _, _ = gateway_factory()
    gateway.probe_sandbox = ExecutingProbe()
    result = gateway.execute(probe(gateway.public_task, source=source))
    assert result.status == "succeeded"
    assert result.output["reproduction"]["comparison"] == "not_compared"
    assert result.output["reproduction"]["repair_success"] == "not_assessed"


def test_reproduction_schema_public_quote_and_original_source_limit(gateway_factory):
    tool = dev_tool_schemas(finish_enabled=False, allowed_tools={"run_probe"})[0]
    assert tool["strict"] is True
    schema = tool["parameters"]
    assert set(schema["required"]) == set(schema["properties"])
    choices = schema["properties"]["purpose"]["anyOf"]
    bound = choices[1]
    assert not bound["additionalProperties"] and set(bound["required"]) == set(bound["properties"])
    assert choices[0]["properties"]["kind"]["enum"] == ["helper"]
    assert bound["properties"]["kind"]["enum"] == ["original_requirement"]
    assert choices[2] == {"type": "null"}
    assert bound["properties"]["entrypoint"] == {
        "type": "string", "minLength": 3, "maxLength": 200,
    }
    assert reproduction.Intent.model_json_schema()["properties"]["entrypoint"]["pattern"] == (
        r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+$"
    )
    gateway, _, _ = gateway_factory()
    backend = ExecutingProbe()
    gateway.probe_sandbox = backend
    call = probe(gateway.public_task)
    call.arguments["reproduction"]["requirement_quote"] = "not in the public task"
    assert gateway.execute(call).status == "failed"
    oversized = gateway.execute(probe(gateway.public_task, "oversized", source="#" + "a" * 7998))
    assert oversized.status == "failed" and "8000-character" in oversized.message
    assert backend.calls == 0


def test_reproduction_entrypoint_validation_remains_before_probe_execution(gateway_factory):
    gateway, _, _ = gateway_factory()
    backend = ExecutingProbe()
    gateway.probe_sandbox = backend
    for entrypoint in ("a.b", "pkg._Type.method1", "a." + "b" * 198, "a.bé"):
        parsed = reproduction.Intent.model_validate(
            intent(gateway.public_task, entrypoint=entrypoint),
        )
        assert parsed.entrypoint == entrypoint
    invalid = ("helper", "a..b", "a/b", "a.1b", "a.b()", "a." + "b" * 199, None, 123)
    for index, entrypoint in enumerate(invalid):
        call = probe(gateway.public_task, f"invalid-entrypoint-{index}")
        call.arguments["reproduction"]["entrypoint"] = entrypoint
        result = gateway.execute(call)
        assert result.status == "failed" and "entrypoint" in result.message
    assert backend.calls == 0


def test_same_program_observed_input_change_and_incomplete_trace_do_not_pair(gateway_factory):
    gateway, journal, _ = gateway_factory()
    gateway.probe_sandbox = ExecutingProbe()
    first = gateway.execute(probe(gateway.public_task))
    original = next(e for e in journal.events() if e["event_type"] == "action_finished")
    later = copy.deepcopy(original)
    result = later["payload"]["result"]
    result["action_id"] = "recheck"
    result["workspace_diff_hash"] = "changed-diff"
    result["output"]["reproduction"]["comparison"] = "matched"
    trace = result["output"]["reproduction"]["call_observation"]
    trace["calls"][0]["arguments"] = {"text": "other"}
    review = reproduction.review([original, later], "changed-diff")
    assert review["items"][0]["comparison_status"] == "observed_call_or_setup_changed"
    damaged = {**first.output, "stderr": "", "status": "passed", "exit_code": 0}
    bound = first.output["reproduction"]["binding"]
    assert reproduction.compare(damaged, bound)["reproduction"]["comparison"] == "not_compared"


def test_wrong_execution_identity_preserves_receipt_without_comparison(gateway_factory):
    class WrongIdentity(ExecutingProbe):
        def run_probe(self, *args, **kwargs):
            return {**super().run_probe(*args, **kwargs), "source_hash": "wrong"}

    gateway, _, _ = gateway_factory()
    gateway.probe_sandbox = WrongIdentity()
    result = gateway.execute(probe(gateway.public_task))
    assert result.error_code == "RECOVERY_ERROR"
    assert result.output["source_hash"] == "wrong"
    assert result.output["execution_policy"]["cleanup_status"] == "confirmed"
    assert "reproduction" not in result.output


def test_segmented_reproduction_reaches_submission_and_isolated_mock_evaluation(
    tmp_path, monkeypatch, smoke_package,
):
    backend = ExecutingProbe()

    class ReproduceThenMock(MockDevAdapter):
        def next_turn(self, context, tools):
            state = json.loads(context)
            review = state["reproduction_review"]
            if not review["items"]:
                return DevModelTurn(tool_calls=[probe(smoke_package.public)])
            case = review["items"][0]
            if case["comparison_status"] == "current_diff_not_observed":
                return DevModelTurn(tool_calls=[probe(smoke_package.public, "recheck",
                                                     replay="original")])
            return super().next_turn(context, tools)

    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    monkeypatch.setattr(runner, "MockDevAdapter", ReproduceThenMock)
    request = mock_request(tmp_path, policy="none").model_copy(update={
        "enable_probes": True, "context_policy": "segmented-v1",
        "history_search_policy": "public-v1",
    })
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert backend.calls == 2 and backend.sources[0] == backend.sources[1]
    from patchloop.dev.state import DevJournal

    events = DevJournal(tmp_path, result["run_id"]).events()
    finish = next(e["payload"]["result"] for e in events
                  if e["event_type"] == "action_finished"
                  and e["payload"]["result"]["tool"] == "finish_task")
    scope = finish["output"]["reproduction_review"]
    assert scope["items"][0]["comparison_status"] == "mismatch_to_match"
    assert scope["items"][0]["evidence"]["status"] == "SUPPORTED"
    assert scope["required"]["status"] == "UNKNOWN"
    assert scope["items"][0]["repair_success"] == "not_assessed"
    assert result["evaluator"]["claim_eligible"] is False
    assert result["evaluator"]["safety_state"] == "NOT_RUN"
