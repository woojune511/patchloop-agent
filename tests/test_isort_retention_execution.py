"""I3 real gateway/local-fixture tests; inert transport, no isort execution."""

from __future__ import annotations

import copy
import inspect
import json
from unittest.mock import patch

import pytest
import test_isort_table_execution as table
import test_isort_uptake_execution as inherited
from test_checkpoint_continuation import stop_steps
from test_isort_table_execution import parent_source as parent_source  # noqa: F401
from test_isort_table_execution import source as source  # noqa: F401

from diagnostics import isort_retention_checkpoint as checkpoint
from diagnostics import isort_retention_execution as execution
from diagnostics.checkpoint_continuation import ScriptedClient
from patchloop.dev import runner
from patchloop.dev.state import DevJournal
from patchloop.util import canonical_json, sha256_json


def prepared(source, tmp_path):
    group = execution.Invocation(DevJournal(tmp_path / "group", "run_dev_retainfixture"))
    with patch.object(runner, "_resolve_task_file", lambda _: (source.task_dir, source.package)):
        branch = checkpoint.restore_branch(
            source.original,
            source.cut,
            copy.deepcopy(source.feedback),
            tmp_path / "I3",
            started=group.started,
            deadline=group.deadline,
            expected_request=copy.deepcopy(source.expected),
        )
    return branch, group


CONTRACTS = [
    (name, extra)
    for name, extra in table.CONTRACTS
    if name != "test_first_packet_native_order_source_currency_and_normal_second_state"
]


@pytest.mark.parametrize(
    "name,extra", CONTRACTS, ids=[n.removeprefix("test_") + str(e) for n, e in CONTRACTS]
)
def test_unchanged_contract(name, extra, source, tmp_path, monkeypatch):
    monkeypatch.setattr(inherited, "execution", execution)
    monkeypatch.setattr(inherited, "prepared", prepared)
    function = getattr(inherited, name)
    available = {"source": source, "tmp_path": tmp_path, **extra}
    function(**{k: available[k] for k in inspect.signature(function).parameters})


def read_call(number):
    call = inherited.call(
        "read_file",
        {
            "path": "mini_data_utils/csvlite.py",
            "start_line": 1,
            "end_line": 90,
        },
        "inspect",
    )
    call["action_id"] = f"retention_read_{number}"
    return call


def run(branch, group, client, **kwargs):
    with execution.offline_environment(branch, client, fixture_evaluation=True) as probes:
        result = execution.run_row(
            branch,
            group,
            "SYNTHETIC_ORACLE",
            client=client,
            reviewer=kwargs.get("reviewer", execution.inert_reviewer),
        )
    return result, probes


def state(request):
    return json.loads(request["input"][-1]["content"])["state"]


def test_handoff_same_segment_edit_historical_check_submit_and_seals(source, tmp_path):
    before = DevJournal(source.root, source.run_id).path.read_bytes()
    branch, group = prepared(source, tmp_path)
    client = ScriptedClient([[read_call(1)], [read_call(2)], *inherited.edit_steps(two=True)])
    result, probes = run(branch, group, client)
    assert result["result"]["terminal"] == "EVALUATOR_PASS", result
    assert result["new_generations"] == result["new_counts"] == 6
    assert result["accepted_new_edits"] == 2 and not result["stop_remaining"]
    views = [state(r) for r in client.created]
    assert views[0]["segment_handoff"]["segment_id"] != views[1]["segment_handoff"]["segment_id"]
    assert views[1]["segment_handoff"]["segment_id"] == views[2]["segment_handoff"]["segment_id"]
    for view in views[:3]:
        assert view[checkpoint.FIELD] == branch.feedback
        assert view["current_diff"] == branch.observed_candidate_diff
        assert checkpoint.HISTORICAL_FIELD not in view
    for view in views[3:]:
        assert checkpoint.FIELD not in view
        assert view[checkpoint.HISTORICAL_FIELD] == {
            "observed_candidate_diff": branch.observed_candidate_diff,
            "observation": branch.feedback,
        }
        assert view["current_diff"]["patch_hash"] != branch.observed_candidate_diff["patch_hash"]
    assert result["C"] == result["R"] == "PASS"  # Explicitly synthetic mechanical grades.
    assert result["continuity_and_recheck_effect"] == result["model_uptake"] == "NOT_RUN"
    assert result["U"] == "NOT_OBSERVABLE" and result["provider_calls"] == 0
    events = branch.journal.events()[branch.inherited_events :]
    kinds = [e["event_type"] for e in events]
    assert kinds.index("isort_uptake_U_sealed") < kinds.index("isort_retention_CR_sealed")
    assert kinds.index("isort_retention_CR_sealed") < kinds.index("isort_uptake_terminal_oracle")
    assert kinds.index("isort_uptake_terminal_oracle") < kinds.index("evaluator_finished")
    deliveries = [e for e in events if e["event_type"] == "isort_retention_input_dispatched"]
    assert len(deliveries) == 6
    for event in deliveries:
        data = event["payload"]
        ordinary = json.loads(checkpoint.read_bound(data["ordinary_input"]))
        retained = json.loads(checkpoint.read_bound(data["retained_input"]))
        recovered = copy.deepcopy(retained)
        view = json.loads(recovered[-1]["content"])
        view["state"].pop(data["placement"])
        recovered[-1]["content"] = canonical_json(view)
        assert recovered == ordinary
        assert data["input_hash"] == sha256_json(retained)
    assert all("SYNTHETIC_ORACLE" not in canonical_json(r) for r in client.created)
    assert sum(len(p.calls) for p in probes) == 1
    assert before == DevJournal(source.root, source.run_id).path.read_bytes()


@pytest.mark.parametrize("edit", [False, True])
def test_no_handoff_is_not_exercised_and_no_edit_is_not_reduction(source, tmp_path, edit):
    branch, group = prepared(source, tmp_path)
    result, _ = run(branch, group, ScriptedClient(inherited.edit_steps() if edit else stop_steps()))
    assert result["C"] == "NOT_EXERCISED"
    assert result["R"] == ("PASS" if edit else "NOT_OBSERVABLE")


def test_exact_return_restores_current_form_without_altering_diff(source):
    request = copy.deepcopy(source.expected)
    view = json.loads(request["input"][-1]["content"])
    feedback = view["state"].pop(checkpoint.FIELD)
    seed = copy.deepcopy(view["state"]["current_diff"])
    for current in (seed, {**seed, "patch_hash": "different"}, seed):
        view["state"]["current_diff"] = current
        request["input"][-1]["content"] = canonical_json(view)
        delivered = checkpoint.retain_observation(request["input"], feedback, seed)
        result = json.loads(delivered[-1]["content"])["state"]
        assert result["current_diff"] == current
        assert (checkpoint.FIELD in result) == (current == seed)
        assert delivered[:-1] == request["input"][:-1]


@pytest.mark.parametrize(
    "field",
    [
        "working_plan",
        "completion_guidance",
        "current_diff",
        "working_notes",
        "workflow_gate",
        "native",
        "packet",
    ],
)
def test_later_input_drift_stops_before_count_or_dispatch(source, tmp_path, field):
    branch, group = prepared(source, tmp_path)
    original = execution.retain_observation
    calls = []

    def corrupt(items, feedback, seed):
        result = original(items, feedback, seed)
        calls.append(True)
        if len(calls) > 1:
            if field == "native":
                result.insert(-1, {"type": "reasoning", "encrypted_content": "TAMPER"})
            else:
                view = json.loads(result[-1]["content"])
                key = checkpoint.FIELD if field == "packet" else field
                view["state"][key] = "TAMPER"
                result[-1]["content"] = canonical_json(view)
        return result

    client = ScriptedClient([[read_call(1)], *stop_steps()])
    with patch.object(execution, "retain_observation", corrupt):
        result, probes = run(branch, group, client)
    assert result["stop_remaining"] and len(client.created) == len(client.counted) == 1
    assert result["U"] == result["C"] == result["R"] == "NOT_RUN"
    assert not any(p.calls for p in probes)


def test_later_oversize_stops_without_pruning_or_another_count(source, tmp_path):
    branch, group = prepared(source, tmp_path)
    client = ScriptedClient([[read_call(1)], *stop_steps()])
    original = client.count

    def count(**kwargs):
        if client.created:
            client.input_tokens = 60001
        return original(**kwargs)

    # ScriptedClient owns the finite count endpoint.
    client.responses.input_tokens.count = count
    result, _ = run(branch, group, client)
    assert len(client.created) == 1 and result["new_counts"] == 2, result
    assert "input-token bound" in result["stop_reason"]


def test_stale_current_packet_after_edit_is_denied_before_next_count(source, tmp_path):
    branch, group = prepared(source, tmp_path)
    original = execution.retain_observation

    def stale(items, feedback, seed):
        result = original(items, feedback, seed)
        view = json.loads(result[-1]["content"])
        if checkpoint.HISTORICAL_FIELD in view["state"]:
            del view["state"][checkpoint.HISTORICAL_FIELD]
            view["state"][checkpoint.FIELD] = feedback
            result[-1]["content"] = canonical_json(view)
        return result

    client = ScriptedClient(inherited.edit_steps())
    with patch.object(execution, "retain_observation", stale):
        result, probes = run(branch, group, client)
    assert result["accepted_new_edits"] == 1
    assert result["new_counts"] == result["new_generations"] == 1
    assert result["stop_remaining"] and result["U"] == result["C"] == result["R"] == "NOT_RUN"
    assert not any(p.calls for p in probes)


def test_invalid_r_review_blocks_all_seals_and_terminal_assessments(source, tmp_path):
    branch, group = prepared(source, tmp_path)

    def invalid(ref, packet, deadline):
        grade = execution.inert_reviewer(ref, packet, deadline)
        grade["probe_reviews"] = [{"sequence": 999999}]
        return grade

    result, probes = run(branch, group, ScriptedClient(inherited.edit_steps()), reviewer=invalid)
    assert result["stop_remaining"] and result["U"] == result["C"] == result["R"] == "NOT_RUN"
    assert not any(p.calls for p in probes)
    assert not any(
        e["event_type"]
        in {"isort_uptake_U_sealed", "isort_retention_CR_sealed", "evaluator_finished"}
        for e in branch.journal.events()
    )


@pytest.mark.parametrize(
    "name",
    [
        "test_action_ceiling_preserves_the_existing_completion_reserve",
        "test_review_timeout_never_enters_terminal_assessments",
    ],
)
def test_additional_unchanged_stops(name, source, tmp_path, monkeypatch):
    monkeypatch.setattr(table, "execution", execution)
    monkeypatch.setattr(table, "prepared", prepared)
    getattr(table, name)(source, tmp_path)
