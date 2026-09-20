"""Public quotation plumbing; a real quotation does not establish task correctness."""

from __future__ import annotations

import copy
import json

import httpx
import pytest
from test_dev_notes_lifecycle_v15 import SimulatedCrash, _gateway, _mutation, _read, _restart
from test_dev_verification_flow_v17 import _completed_check

from patchloop.agent.model import ModelTurn
from patchloop.agent.model import RequestedTool as ProviderTool
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import PublicTask
from patchloop.dev import requirement_reference as references
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest, TextReplacementIntent
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.errors import ActionConflict
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_json

DESCRIPTION = "Set editable to one for every input. No input-specific exception is required."


def public_task():
    return PublicTask.model_validate({
        "task_id": "generic-editable-value", "split": "smoke",
        "repository": {"url": "snapshot://generic", "base_commit": "sha256:" + "a" * 64,
                       "language": "python"},
        "issue": {"title": "Update the editable value", "description": DESCRIPTION},
        "constraints": {"allowed_paths": ["src.py"], "max_diff_lines": 50,
                        "max_changed_files": 1},
        "visible_checks": [{"id": "behavior", "command": ["python", "check.py"]}],
    })


def cited(excerpt=DESCRIPTION):
    return {"task_id": "generic-editable-value", "excerpt": excerpt}


def setup_gateway(tmp_path):
    gateway = _gateway(tmp_path)
    gateway.public_task = public_task()
    _read(gateway)
    return gateway


@pytest.mark.parametrize(("value", "status", "code"), [
    (None, "omitted", "missing_reference"),
    ("a quotation", "invalid", "invalid_reference_shape"),
    ([], "invalid", "invalid_reference_shape"),
    ({}, "invalid", "invalid_reference_shape"),
    ({"task_id": 1, "excerpt": DESCRIPTION}, "invalid", "invalid_reference_shape"),
    (cited("x" * 601), "invalid", "invalid_reference_shape"),
    (cited(""), "invalid", "invalid_reference_shape"),
    (cited(" "), "invalid", "excerpt_mismatch"),
    (cited("Set editable to two for every input."), "invalid", "excerpt_mismatch"),
    (cited(DESCRIPTION.lower()), "invalid", "excerpt_mismatch"),
    ({**cited(), "task_id": "another-task"}, "invalid", "task_id_mismatch"),
    ({**cited(), "private_path": "not-a-public-source"}, "invalid", "invalid_reference_shape"),
])
def test_annotation_errors_do_not_become_source_evidence_or_provider_action_errors(
    value, status, code,
):
    result = references.bind(value, public_task())
    assert result == {"status": status, "diagnostics": [code],
                      "validation_scope": "public_source_identity_only"}
    assert len(canonical_json(result)) < 200
    call = _mutation("edit")
    call.arguments["requirement_ref"] = value
    provider = ModelTurn(tool_calls=[ProviderTool(
        name=call.name, action_id=call.action_id,
        arguments={**call.arguments, "turn_decision": call.turn_decision.model_dump(mode="json")},
    )])
    converted = runner._turn_from_openai(provider)
    assert converted.error_code is None
    assert converted.tool_calls[0].arguments == call.arguments
    assert TextReplacementIntent.model_validate(call.arguments).requirement_ref == value


def test_exact_unicode_multiline_excerpt_and_public_only_hash():
    task = public_task()
    task.issue.description = "모든 입력을 유지한다.\nSecond line remains exact.\n"
    excerpt = "입력을 유지한다.\nSecond line"
    receipt = references.bind({"task_id": task.task_id, "excerpt": excerpt}, task)
    assert receipt["status"] == "matched"
    assert receipt["reference"] == {
        "task_id": task.task_id, "task_version": task.task_version,
        "public_task_hash": sha256_json(task.model_dump(mode="json")),
        "field": "issue.description", "excerpt": excerpt,
        "source_span": {"start": task.issue.description.index(excerpt),
                        "end": task.issue.description.index(excerpt) + len(excerpt)},
        "match_mode": "exact",
    }
    assert receipt["validation_scope"] == "public_source_identity_only"


@pytest.mark.parametrize("space", ["\n", "\r\n", "\t", "  ", "\u00a0"])
def test_whitespace_only_match_retains_original_unicode_source_span(space):
    task = public_task()
    original = f"모든{space}입력을{space}유지한다."
    task.issue.description = f"Before. {original} After."
    receipt = references.bind(cited("  모든 입력을 유지한다. \n"), task)
    assert receipt["status"] == "matched"
    reference = receipt["reference"]
    assert reference["excerpt"] == original
    assert reference["match_mode"] == "whitespace"
    assert reference["source_span"] == {"start": 8, "end": 8 + len(original)}
    assert reference["public_task_hash"] == sha256_json(task.model_dump(mode="json"))
    assert references.project(receipt, task) == receipt


def test_exact_excerpt_keeps_its_edge_whitespace():
    task = public_task()
    task.issue.description = "Intro.\nKeep all inputs.\nOutro."
    excerpt = "\nKeep all inputs.\n"
    reference = references.bind(cited(excerpt), task)["reference"]
    assert reference["excerpt"] == excerpt and reference["match_mode"] == "exact"
    assert reference["source_span"] == {"start": 6, "end": 24}


@pytest.mark.parametrize(("description", "excerpt"), [
    ("Keep inputs. Keep inputs.", "Keep inputs."),
    ("Keep\ninputs. Keep inputs.", "Keep inputs."),
    ("one one one", "one one"),
])
def test_ambiguous_normalized_occurrences_including_overlaps_are_rejected(description, excerpt):
    task = public_task()
    task.issue.description = description
    assert references.bind(cited(excerpt), task) == {
        "status": "invalid", "diagnostics": ["ambiguous_excerpt"],
        "validation_scope": "public_source_identity_only",
    }


@pytest.mark.parametrize("excerpt", [
    "Keep every input.", "keep all inputs.", "Keep all inputs!", "Keepall inputs.",
    "Keep a ll inputs.", "Keep .* inputs.",
])
def test_whitespace_matching_never_changes_words_case_punctuation_or_token_boundaries(excerpt):
    task = public_task()
    task.issue.description = "Keep\nall inputs."
    assert references.bind(cited(excerpt), task)["diagnostics"] == ["excerpt_mismatch"]


def test_original_source_expansion_respects_the_existing_excerpt_bound():
    task = public_task()
    task.issue.description = "Keep" + " " * 600 + "inputs."
    assert references.bind(cited("Keep inputs."), task)["diagnostics"] == [
        "source_excerpt_too_long"]


@pytest.mark.parametrize("span", [None, {"start": -1, "end": 2}, {"start": 0, "end": 999},
                                  {"start": False, "end": 2}, {"start": 1, "end": 4}])
def test_saved_source_span_is_validated_without_silently_finding_a_new_one(span):
    task = public_task()
    receipt = references.bind(cited(), task)
    receipt["reference"]["source_span"] = span
    frozen = copy.deepcopy(receipt)
    assert references.project(receipt, task)["status"] == "stale"
    assert receipt == frozen


def test_legacy_receipts_keep_admission_result_without_new_matching():
    task = public_task()
    receipt = references.bind(cited(), task)
    del receipt["reference"]["source_span"]
    del receipt["reference"]["match_mode"]
    task.issue.description = f"{DESCRIPTION}\n{DESCRIPTION}"
    receipt["reference"]["public_task_hash"] = sha256_json(task.model_dump(mode="json"))
    assert references.bind(cited(), task)["diagnostics"] == ["ambiguous_excerpt"]
    assert references.project(receipt, task) == receipt
    old_invalid = {"status": "invalid", "diagnostics": ["excerpt_mismatch"],
                   "validation_scope": "public_source_identity_only"}
    task.issue.description = "Keep\ninputs."
    assert references.bind(cited("Keep inputs."), task)["status"] == "matched"
    assert references.project(old_invalid, task) == old_invalid


def test_ambiguous_reference_remains_nonblocking_and_replays_its_original_result(tmp_path):
    gateway = setup_gateway(tmp_path)
    gateway.public_task.issue.description = f"{DESCRIPTION}\n{DESCRIPTION}"
    call = _mutation("ambiguous-reference")
    call.arguments["requirement_ref"] = cited()
    result = gateway.execute(call)
    assert result.status == "succeeded"
    assert result.output["mutation"]["requirement_reference"]["diagnostics"] == [
        "ambiguous_excerpt"]
    _completed_check(gateway, "check")
    assert gateway.ready_to_submit()
    assert _restart(gateway).execute(call).output == result.output


@pytest.mark.parametrize("change", ["task_id", "task_version", "description", "checks"])
def test_saved_reference_cannot_be_rebound_even_when_excerpt_still_occurs(change):
    task = public_task()
    receipt = references.bind(cited(), task)
    frozen = copy.deepcopy(receipt)
    changed = task.model_copy(deep=True)
    if change == "description":
        changed.issue.description += " Later public requirement."
    elif change == "checks":
        changed.visible_checks[0].command.append("new-case")
    elif change == "task_id":
        changed.task_id = "other-task"
    else:
        changed.task_version += 1
    assert DESCRIPTION in changed.issue.description
    assert references.project(receipt, changed) == {
        "status": "stale", "diagnostics": ["public_task_identity_changed"],
        "validation_scope": "public_source_identity_only",
    }
    assert receipt == frozen


def test_unconditional_requirement_keeps_unverified_interpretation_and_allows_finish(tmp_path):
    gateway = setup_gateway(tmp_path)
    call = _mutation("edit")
    call.arguments["requirement_ref"] = cited()
    # Deliberately wrong model interpretation: exact quotation is not entailment.
    call.arguments["expected_behavior"] = "The value becomes two for every input."
    result = gateway.execute(call)
    assert result.status == "succeeded"
    receipt = result.output["mutation"]["requirement_reference"]
    assert receipt["status"] == "matched"
    assert receipt["reference"]["excerpt"] == DESCRIPTION
    checked = _completed_check(gateway, "check")
    card = runner._attempt_card(checked, gateway)
    expectation = card["mutation_expectation"]
    assert "requirement_reference" not in expectation
    assert expectation["expected_behavior"] == call.arguments["expected_behavior"]
    assert expectation["interpretation_status"] == "model_authored_unverified"
    assert expectation["diff_hash"] == checked.workspace_diff_hash
    assert gateway.ready_to_submit()
    gateway.journal.append("attempt_card", card)
    rejected = _mutation("bad-edit", old="absent")
    rejected.arguments["requirement_ref"] = cited("No input-specific exception is required.")
    assert gateway.execute(rejected).status == "failed"
    restored = _restart(gateway)
    assert runner._attempt_card(checked, restored) == card
    assert restored.ready_to_submit()
    saved_bytes = restored.journal.path.read_bytes()
    restored.public_task.issue.description += " New public requirement."
    current = restored.actionable_last_successful_mutation()
    assert current["requirement_reference"]["status"] == "stale"
    assert runner._attempt_card(checked, restored) == card
    assert result.output["mutation"]["requirement_reference"] == receipt
    assert restored.journal.path.read_bytes() == saved_bytes


def test_legacy_absence_keeps_intent_and_action_hashes_and_completed_replay(tmp_path):
    gateway = setup_gateway(tmp_path)
    call = _mutation("legacy-edit")
    expected_plan = sha256_json(call.arguments)
    assert TextReplacementIntent.model_validate(call.arguments).model_dump(mode="json") == (
        call.arguments
    )
    expected_input = sha256_json({"tool": call.name, "arguments": call.arguments,
                                 "turn_decision": call.turn_decision.model_dump(mode="json")})
    result = gateway.execute(call)
    assert result.status == "succeeded"
    assert result.input_hash == expected_input
    assert result.output["mutation"]["plan_hash"] == expected_plan
    assert "requirement_reference" not in result.output["mutation"]
    frozen = gateway.journal.path.read_bytes()
    replay = _restart(gateway).execute(call)
    assert replay.replayed and replay.output == result.output
    assert gateway.journal.path.read_bytes() == frozen
    call.arguments["requirement_ref"] = None
    with pytest.raises(ActionConflict, match="different input"):
        _restart(gateway).execute(call)


@pytest.mark.parametrize("completed", [False, True])
def test_legacy_journal_without_annotation_keeps_pending_and_completed_recovery(
    tmp_path, monkeypatch, completed,
):
    gateway = setup_gateway(tmp_path)
    call = _mutation("old-edit")
    append = DevJournal.append
    crashed = False

    def legacy_append(self, event_type, payload=None):
        nonlocal crashed
        payload = copy.deepcopy(payload)
        if event_type == "action_started":
            payload.pop("mutation_requirement_reference", None)
        if event_type == "action_finished":
            payload["result"]["output"]["mutation"].pop("requirement_reference", None)
        event = append(self, event_type, payload)
        target = "action_finished" if completed else "action_started"
        if not crashed and event_type == target:
            crashed = True
            raise SimulatedCrash()
        return event

    monkeypatch.setattr(DevJournal, "append", legacy_append)
    with pytest.raises(SimulatedCrash):
        gateway.execute(call)
    restored = _restart(gateway)
    result = restored.execute(call)
    assert result.status == "succeeded" and result.replayed is completed
    assert "requirement_reference" not in result.output["mutation"]
    assert result.output["mutation"]["plan_hash"] == sha256_json(call.arguments)
    assert restored.accepted_mutations == 1
    assert "requirement_reference" not in restored.actionable_last_successful_mutation()


def test_next_accepted_edit_does_not_inherit_an_earlier_reference(tmp_path):
    gateway = setup_gateway(tmp_path)
    first = _mutation("first")
    first.arguments["requirement_ref"] = cited()
    assert gateway.execute(first).status == "succeeded"
    old_check = _completed_check(gateway, "first-check")
    old_review = runner._attempt_card(old_check, gateway)
    frozen = copy.deepcopy(old_review)
    second = _mutation("second", "editable = 1", "editable = 2")
    result = gateway.execute(second)
    assert result.status == "succeeded"
    assert "requirement_reference" not in result.output["mutation"]
    assert "mutation_expectation" not in runner._attempt_card(old_check, gateway)
    new_review = runner._attempt_card(_completed_check(gateway, "second-check"), gateway)
    assert "requirement_reference" not in new_review["mutation_expectation"]
    assert old_review == frozen


@pytest.mark.parametrize("boundary", ["after_admission", "after_replace", "after_result"])
@pytest.mark.parametrize("stale", [False, True])
def test_crash_recovery_preserves_admission_reference_and_single_mutation(
    tmp_path, monkeypatch, boundary, stale,
):
    gateway = setup_gateway(tmp_path)
    gateway.public_task.issue.description = DESCRIPTION.replace(" ", "\n")
    call = _mutation("interrupted")
    call.arguments["requirement_ref"] = cited()
    append = DevJournal.append
    replace = WorkspaceManager.atomic_replace_source
    crashed = False
    writes = 0

    def intercept_append(self, event_type, payload=None):
        nonlocal crashed
        event = append(self, event_type, payload)
        target = "action_started" if boundary == "after_admission" else "action_finished"
        if (not crashed and boundary != "after_replace" and event_type == target
                and payload.get("action_id") == call.action_id):
            crashed = True
            raise SimulatedCrash()
        return event

    def intercept_replace(*args):
        nonlocal crashed, writes
        replace(*args)
        writes += 1
        if not crashed and boundary == "after_replace":
            crashed = True
            raise SimulatedCrash()

    monkeypatch.setattr(DevJournal, "append", intercept_append)
    monkeypatch.setattr(WorkspaceManager, "atomic_replace_source", staticmethod(intercept_replace))
    with pytest.raises(SimulatedCrash):
        gateway.execute(call)
    admission = next(event["payload"] for event in gateway.journal.events()
                     if event["event_type"] == "action_started"
                     and event["payload"]["action_id"] == call.action_id)
    original = copy.deepcopy(admission["mutation_requirement_reference"])
    assert original["reference"]["match_mode"] == "whitespace"
    restored = _restart(gateway)
    if stale:
        restored.public_task.issue.description += " New public requirement."
    result = restored.execute(call)
    assert result.status == "succeeded" and writes == 1
    assert restored.accepted_mutations == 1
    # Completed replay preserves the original receipt; the current projection marks staleness.
    expected = "stale" if stale and boundary != "after_result" else "matched"
    assert result.output["mutation"]["requirement_reference"]["status"] == expected
    projection = restored.actionable_last_successful_mutation()
    assert projection["requirement_reference"]["status"] == ("stale" if stale else "matched")
    assert admission["mutation_requirement_reference"] == original
    if not stale:
        assert result.output["mutation"]["requirement_reference"] == original
    frozen = restored.journal.path.read_bytes()
    assert _restart(restored).execute(call).replayed
    assert restored.journal.path.read_bytes() == frozen


def test_retired_reference_is_absent_from_current_provider_schema():
    for schema in dev_tool_schemas(finish_enabled=True, planning_policy="brief-v1"):
        params = schema["parameters"]
        assert "requirement_ref" not in params["properties"]
        assert "requirement_ref" not in params["required"]


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
@pytest.mark.parametrize("reference_kind", ["invalid", "exact", "whitespace"])
def test_legacy_reference_receipt_survives_without_repeating_it_in_check_review(
    tmp_path, monkeypatch, context_policy, reference_kind,
):
    supplied = []

    class ReferenceMock(MockDevAdapter):
        def next_turn(self, context, tools):
            turn = super().next_turn(context, tools)
            task = json.loads(context)["public_task"]
            for call in turn.tool_calls:
                if call.name == "replace_text":
                    value = {"task_id": task["task_id"], "excerpt": task["issue"]["description"]}
                    if reference_kind == "whitespace":
                        value["excerpt"] = " ".join(value["excerpt"].split())
                    call.arguments["requirement_ref"] = (
                        value if reference_kind != "invalid" else {"excerpt": ["invalid"]}
                    )
                    supplied.append((value, call.arguments["expected_behavior"]))
            return turn

    def no_network(*args, **kwargs):
        pytest.fail("reference delivery must not dispatch a provider request")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", no_network)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", no_network)
    monkeypatch.setattr(runner, "MockDevAdapter", ReferenceMock)
    run = runner.run_dev(DevRunRequest(
        provider="mock", model="mock-dev", state_root=tmp_path,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
        context_policy=context_policy, planning_policy="brief-v1",
    ))["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS"
    assert run["call_counts"] == {"model": 4, "input_count": 0, "tool": 5}
    assert run["evaluator"]["claim_eligible"] is False
    journal = DevJournal(tmp_path, run["run_id"])
    store = ArtifactStore(tmp_path / "artifacts")
    states = [
        reconstruct_state(runner._load_active_model_input(
            e["payload"], store, context_policy=context_policy,
        ), context_policy=context_policy)
        for e in journal.events() if e["event_type"] == "turn_started"
    ]
    final = states[-1]
    expectation = next(card["mutation_expectation"]
                       for card in final["recent_attempt_result_next_question"]
                       if "mutation_expectation" in card)
    mutation_result = next(
        e["payload"]["result"] for e in journal.events()
        if e["event_type"] == "action_finished"
        and e["payload"]["result"]["tool"] == "replace_text"
    )
    annotation = mutation_result["output"]["mutation"]["requirement_reference"]
    assert "requirement_reference" not in expectation
    assert expectation["expected_behavior"] == supplied[0][1]
    assert expectation["interpretation_status"] == "model_authored_unverified"
    if reference_kind != "invalid":
        assert annotation["status"] == "matched"
        reference = annotation["reference"]
        span = reference["source_span"]
        assert reference["excerpt"] == final["public_task"]["issue"]["description"][
            span["start"]:span["end"]]
        assert reference["match_mode"] == reference_kind
        assert annotation["reference"]["public_task_hash"] == sha256_json(final["public_task"])
    else:
        assert annotation["status"] == "invalid" and "reference" not in annotation
    assert expectation["diff_hash"] == final["current_diff"]["patch_hash"]
    assert final["public_task"] == states[0]["public_task"]
    assert final["visible_check_status"][0]["status"] == "PASS"
    assert "finish_task" in final["available_tool_names"]
    if context_policy == "segmented-v1":
        assert any(e["event_type"] == "context_segment_started" for e in journal.events())
