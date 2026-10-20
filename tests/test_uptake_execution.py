"""Provider-free continuation contracts; synthetic results are not repair evidence."""

from __future__ import annotations

import copy
import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from test_checkpoint_continuation import call as base_call
from test_checkpoint_continuation import stop_steps
from test_mutation_advice_checkpoint import source as source  # noqa: F401

from diagnostics import uptake_checkpoint as checkpoint
from diagnostics import uptake_execution as execution
from diagnostics.checkpoint_continuation import ScriptedClient, inherited_reads
from patchloop.agent.model import (
    EncryptedReasoningContinuationItem,
    FunctionCallContinuationRef,
    ModelTurn,
    RequestedTool,
)
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, TaskEnvironment
from patchloop.dev import runner
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.cost import pricing_for_model
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.dev.state import DevJournal
from patchloop.util import sha256_bytes


def call(name, arguments, mode):
    value = base_call(name, arguments, mode)
    if mode == "inspect":
        value["arguments"]["turn_decision"]["evidence_goal"] = "Read the public source."
    return value


def prepared(source, tmp_path, cell="B1"):
    parent = DevJournal(source.root, source.run_id)
    cut = [e for e in parent.events() if e["event_type"] == "model_input_prepared"][-1]
    selected = json.loads(
        ArtifactStore(source.root / "artifacts").read_bytes(
            Artifact.model_validate(cut["payload"]["artifact"])
        )
    )["request"]
    selected["input"].append({"role": "developer", "content": "Frozen test instruction."})
    seed = call(
        "run_probe",
        {"question": "Synthetic target observation.", "python_source": "print('SYNTHETIC_ONLY')"},
        "verify",
    )
    seed["action_id"] = "saved_" + cell
    store = ArtifactStore(tmp_path / "seed")
    public = store.put_json({"tool_calls": [seed]})
    row = {
        "cell": cell,
        "sample_id": "sample_" + cell,
        "action_id": seed["action_id"],
        "probe": {"content_hash": sha256_bytes(seed["arguments"]["python_source"].encode())},
        "public_response": public.model_dump(mode="json"),
        "recorded_sample_active_ms": 20,
        "new_generation_cap": 6,
        "new_count_cap": 6,
        "new_cost_cap_usd": "3.50",
        "new_tool_action_cap_including_seed_probe": 18,
    }
    saved = ModelTurn(
        tool_calls=[RequestedTool(**seed)],
        provider_continuation=(
            EncryptedReasoningContinuationItem(
                id="saved_reasoning", encrypted_content="opaque_fixture", status="completed"
            ),
            FunctionCallContinuationRef(action_id=seed["action_id"]),
        ),
        input_tokens=100,
        requested_input_tokens=100,
        output_tokens=20,
        output_item_count=2,
        non_tool_output_item_count=1,
        output_item_types=("reasoning", "function_call"),
        response_status="completed",
    )
    task_dir, package = runner._resolve_task_file(source.public_path)
    package = package.model_copy(
        update={
            "environment": TaskEnvironment(
                evaluator_image="test/image@sha256:" + "a" * 64, image_digest="sha256:" + "a" * 64
            )
        }
    )
    with patch.object(runner, "_resolve_task_file", lambda _: (task_dir, package)):
        branch = checkpoint.restore_branch(
            source,
            cut["sequence"],
            selected,
            saved,
            {"cost_nanos": 12345, "synthetic": True},
            row,
            tmp_path / cell,
        )
    group = execution.Invocation(DevJournal(tmp_path / "group", "run_dev_fixtureuptake"))
    return branch, group


def run(branch, group, client, observation=None, *, fixture_evaluation=False):
    with execution.offline_environment(
        branch,
        client,
        execution.synthetic_observation(branch.row) if observation is None else observation,
        fixture_evaluation=fixture_evaluation,
    ) as probes:
        result = execution.run_row(branch, group, "print('SYNTHETIC_ORACLE')", client=client)
    return result, probes


@pytest.mark.parametrize("cell", ["B1", "B2"])
def test_saved_decision_first_delivery_and_subsequent_instruction(source, tmp_path, cell):
    original = DevJournal(source.root, source.run_id).path.read_bytes()
    branch, group = prepared(source, tmp_path, cell)
    client = ScriptedClient(
        [
            [
                call(
                    "read_file",
                    {"path": "mini_data_utils/csvlite.py", "start_line": 1, "end_line": 90},
                    "inspect",
                )
            ],
            *stop_steps(),
        ]
    )
    result, probes = run(branch, group, client)
    assert result["result"]["terminal"] == "AGENT_STOPPED", result
    assert result["first_input_verified"] and result["exposure"]["exposed"]
    assert result["new_counts"] == result["new_generations"] == 2
    assert result["new_tool_actions"] == 3
    assert result["provider_calls"] == result["billed_cost_nanos"] == 0
    assert result["final_diff"]["status"] == "SEALED"
    assert result["final_diff"]["submission"] is False
    assert probes[0].calls == [branch.row["action_id"]]
    assert branch.request.agent_policy == branch.envelope.agent_policy == "current"
    for request in client.created:
        assert request["input"][-1] == branch.selected["input"][-1]
        state = reconstruct_state(request["input"][:-1], context_policy="segmented-v1")
        assert state["remaining_budget"]["accepted_mutations"] == 1
        assert state["remaining_budget"]["model_calls"] <= 6
        assert state["remaining_budget"]["tool_actions"] <= 17
    assert DevJournal(source.root, source.run_id).path.read_bytes() == original
    assert group.ledger.spent_nanos == result["provisional_cost_nanos"]
    # Already-paid seed cost and inherited usage never enter the new group ledger.
    assert result["provisional_cost_nanos"] == 2 * (100 * 2500 + 20 * 15000)
    with pytest.raises(Exception, match="cannot be retried"):
        run(branch, group, ScriptedClient(stop_steps()))


@pytest.mark.parametrize("kind", ["no_contradiction", "missing", "setup", "partial"])
def test_unexposed_never_counts_or_generates(source, tmp_path, kind):
    branch, group = prepared(source, tmp_path)
    observation = execution.synthetic_observation(branch.row, disconfirm=kind != "no_contradiction")
    if kind == "missing":
        observation["stdout"] = "No target observation."
    elif kind == "setup":
        observation["setup_checks"]["status"] = "failed"
    elif kind == "partial":
        observation.update(stdout="{'cte_line': '     my", truncated=True)
    client = ScriptedClient(stop_steps())
    result, _ = run(branch, group, client, observation)
    assert not result["exposure"]["exposed"]
    assert result["new_counts"] == result["new_generations"] == 0
    assert not client.counted and not client.created
    assert not result["stop_remaining"] and result["billing_known"]
    assert "UNEXPOSED" in result["stop_reason"]


@pytest.mark.parametrize("cell", ["B1", "B2"])
def test_ancillary_error_and_irrelevant_truncation_are_not_blanket_veto(cell):
    row = {"cell": cell, "action_id": "saved", "probe": {"content_hash": "source"}}
    output = {
        **execution.synthetic_observation(row),
        "status": "failed",
        "source_hash": "source",
        "truncated": True,
        "exit_code": 1,
    }
    result = SimpleNamespace(action_id="saved", tool="run_probe", output=output, error_code=None)
    assert execution.exposure_gate(row, result)["exposed"]
    output["stdout"] = output["stdout"].replace("     my_id,", "        my_id,")
    if cell == "B2":
        output["stdout"] = output["stdout"].replace(
            "'cte_leading_spaces': 5", "'cte_leading_spaces': 8"
        )
    assert not execution.exposure_gate(row, result)["exposed"]


@pytest.mark.parametrize(
    "failure,terminal",
    [
        ("count", "COUNT_TIMEOUT_OR_UNKNOWN"),
        ("transport", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("usage", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
    ],
)
def test_uncertainty_stops_all_without_retry(source, tmp_path, failure, terminal):
    branch, group = prepared(source, tmp_path)
    client = ScriptedClient(stop_steps(), failure=failure)
    result, _ = run(branch, group, client)
    assert result["result"]["terminal"] == terminal, result
    assert result["stop_remaining"] and group.stopped
    assert len(client.counted) == 1 and len(client.created) == (failure != "count")
    with pytest.raises(execution.BoundStop):
        group.check()


def test_known_malformed_response_is_settled_row_stop(source, tmp_path):
    branch, group = prepared(source, tmp_path)
    client = ScriptedClient([[call("nonexistent_tool", {}, "inspect")]])
    result, _ = run(branch, group, client)
    assert result["result"]["terminal"] in {"INCOMPLETE_RESPONSE", "PROTOCOL_VIOLATION"}, result
    assert result["billing_known"] and not result["stop_remaining"]
    assert result["new_counts"] == result["new_generations"] == 1
    assert not any(
        e["event_type"] == "protocol_correction"
        for e in branch.journal.events()[branch.inherited_events :]
    )


def simple_budget(tmp_path, *, clock=lambda: 0):
    group = execution.Invocation(DevJournal(tmp_path, "run_dev_budgetfixture"), clock=clock)
    branch = SimpleNamespace(
        request=SimpleNamespace(max_cost_usd=Decimal("4.50")),
        pricing=pricing_for_model("gpt-5.4-2026-03-05"),
        initial_spent_nanos=1_000_000_000,
        row={"cell": "B1"},
        provider_free=True,
    )
    return execution.RowBudget(branch, group), group


def paid_shape(budget, request=None):
    request = request or {"max_output_tokens": 25000}
    budget.counted(request, lambda: 60000)
    admission = budget.admit(60000)
    assert admission.output_ceiling == 25000
    assert admission.reserved_cost_nanos == 525_000_000
    budget.dispatch(request, 60000)


def test_sixth_response_settles_at_cap_and_rows_do_not_transfer(tmp_path):
    budget, group = simple_budget(tmp_path)
    for _ in range(6):
        paid_shape(budget)
        budget.settle(input_tokens=60000, cached_input_tokens=0, output_tokens=25000)
    assert budget.generations == budget.counts == 6
    assert budget.spent_nanos - budget.branch.initial_spent_nanos == 3_150_000_000
    with pytest.raises(execution.BoundStop, match="row call cap"):
        budget.before_count()
    second = execution.RowBudget(budget.branch, group)
    for _ in range(6):
        paid_shape(second)
        second.settle(input_tokens=60000, cached_input_tokens=0, output_tokens=25000)
    assert group.generations == group.counts == 12
    assert group.ledger.spent_nanos == 6_300_000_000
    with pytest.raises(execution.BoundStop, match="invocation call cap") as stopped:
        second.before_count()
    assert stopped.value.all_rows


def test_discarded_counts_consume_limit_no_stale_count_or_output_shrink(tmp_path):
    budget, group = simple_budget(tmp_path)
    for _ in range(6):
        assert budget.counted({"max_output_tokens": 25000}, lambda: 60001) == 60001
        assert budget.admit(60001) is None
    with pytest.raises(execution.BoundStop):
        budget.before_count()
    assert group.generations == 0 and group.counts == 6
    other = execution.RowBudget(budget.branch, group)
    other.counted({"max_output_tokens": 25000}, lambda: 100)
    assert other.admit(100)
    with pytest.raises(Exception, match="differs"):
        other.dispatch({"max_output_tokens": 24999}, 100)
    with pytest.raises(Exception, match="differs"):
        other.dispatch({"max_output_tokens": 25000}, 100)
    other.spent_nanos = other.cap_nanos - 374_000_000
    assert other.admit(100) is None  # no shrinking despite spare group money


def test_invocation_deadline_stops_admission_but_settles_dispatched_usage(tmp_path):
    now = [0]
    budget, group = simple_budget(tmp_path, clock=lambda: now[0])
    paid_shape(budget)
    now[0] = 2101
    budget.settle(input_tokens=60000, cached_input_tokens=0, output_tokens=25000)
    assert group.ledger.spent_nanos == 525_000_000
    with pytest.raises(execution.BoundStop) as stopped:
        budget.before_count()
    assert stopped.value.all_rows


def test_group_cost_denial_is_global_and_failed_recount_invalidates_count(tmp_path):
    budget, group = simple_budget(tmp_path)
    group.ledger.spent_nanos = group.ledger.cap_nanos - 500_000_000
    with pytest.raises(execution.BoundStop, match="invocation cost cap") as stopped:
        budget.admit(60000)
    assert stopped.value.all_rows
    group.ledger.spent_nanos = 0
    budget.counted({"max_output_tokens": 25000}, lambda: 100)

    def failure():
        raise TimeoutError("synthetic count failure")

    with pytest.raises(TimeoutError):
        budget.counted({"max_output_tokens": 25000}, failure)
    assert budget.pending is None and budget.counts == 2


def test_cached_usage_cannot_hide_output_ceiling_violation(tmp_path):
    budget, _ = simple_budget(tmp_path)
    paid_shape(budget)
    with pytest.raises(Exception, match="usage exceeds"):
        budget.settle(input_tokens=60000, cached_input_tokens=60000, output_tokens=25001)


@pytest.mark.parametrize("condition", ["settled_failure", "unexposed", "uncertainty"])
def test_fixed_roster_preserves_row_failures_and_global_stop(tmp_path, condition):
    _, group = simple_budget(tmp_path)
    prepared_cells = []

    def prepare(row):
        prepared_cells.append(row["cell"])
        return row

    def execute(row):
        return {
            "cell": row["cell"],
            "status": condition,
            "stop_remaining": condition == "uncertainty",
        }

    rows = execution.run_roster([{"cell": "B1"}, {"cell": "B2"}], group, prepare, execute)
    assert len(rows) == 2
    assert prepared_cells == (["B1"] if condition == "uncertainty" else ["B1", "B2"])
    if condition == "uncertainty":
        assert rows[1]["status"] == "NOT_RUN"


def test_cleanup_uncertainty_stops_before_model(source, tmp_path):
    branch, group = prepared(source, tmp_path)
    observation = {**execution.synthetic_observation(branch.row), "cleanup_failed": True}
    client = ScriptedClient(stop_steps())
    result, _ = run(branch, group, client, observation)
    assert result["stop_remaining"] and result["new_generations"] == result["new_counts"] == 0
    assert "cleanup" in result["stop_reason"]


def test_six_counts_without_dispatch_stop_cleanly_before_seventh(source, tmp_path):
    branch, group = prepared(source, tmp_path)
    client = ScriptedClient(stop_steps(), input_tokens=60001)
    # Count exhaustion itself is checked before opening another durable count.
    budget = execution.RowBudget(branch, group)
    for _ in range(6):
        budget.counted({"max_output_tokens": 25000}, lambda: 60001)
    with patch.object(execution, "RowBudget", lambda *args: budget):
        result, _ = run(branch, group, client)
    assert result["new_counts"] == 6 and result["new_generations"] == 0
    assert not client.counted and not client.created
    assert result["billing_known"] and not result["stop_remaining"]
    assert branch.journal.unresolved_input_count() is None


def test_oversized_first_exchange_is_counted_once_not_silently_replaced(source, tmp_path):
    branch, group = prepared(source, tmp_path)
    client = ScriptedClient(stop_steps(), input_tokens=60001)
    result, _ = run(branch, group, client)
    assert result["new_counts"] == 1 and result["new_generations"] == 0
    assert result["billing_known"] and not result["stop_remaining"]
    assert "input-token bound" in result["stop_reason"]
    assert len(client.counted) == 1 and not client.created


def test_full_cte_difference_and_specific_cte_assertion_use_original_rubric(tmp_path):
    row = {"cell": "B2", "action_id": "saved", "probe": {"content_hash": "source"}}
    expected = ["WITH example AS (", "    SELECT", "        my_id,", "expected rest"]
    output = {
        **execution.synthetic_observation(row, disconfirm=False, expected_lines=expected),
        "status": "passed",
        "source_hash": "source",
    }
    result = SimpleNamespace(action_id="saved", tool="run_probe", output=output, error_code=None)
    assert not execution.exposure_gate(row, result, expected)["exposed"]
    output["stdout"] = output["stdout"].replace("expected rest", "different rest")
    assert execution.exposure_gate(row, result, expected)["exposed"]
    program = (
        "cte_result = 'actual'\ncte_expected = 'expected'\nassert cte_result == cte_expected\n"
    )
    ref = ArtifactStore(tmp_path).put_text(program)
    row.update(cell="B1", probe=ref.model_dump(mode="json"))
    output = {
        **execution.synthetic_observation(row, disconfirm=False),
        "status": "failed",
        "source_hash": ref.content_hash,
        "stderr": '  File "<patchloop-probe>", line 3, in <module>\nAssertionError: actual',
    }
    result.output = output
    assert execution.exposure_gate(row, result)["exposed"]
    output["stderr"] = output["stderr"].replace("line 3", "line 4")
    assert not execution.exposure_gate(row, result)["exposed"]


def test_frozen_action_edit_and_time_budgets_are_tightened(source, tmp_path):
    branch, _ = prepared(source, tmp_path)
    old = DevJournal(source.root, source.run_id).load_envelope()
    counters = runner._restore_counters(branch.journal)
    assert branch.request.limits.max_model_calls - counters.model_calls == 6
    assert branch.request.limits.max_tool_actions - counters.tool_actions == 18
    assert branch.request.limits.max_accepted_mutations == 1
    assert branch.request.limits.max_protocol_recoveries == 0
    assert branch.request.limits.wall_time_seconds <= old.limits.wall_time_seconds
    solver = (
        branch.request.limits.wall_time_seconds
        - branch.request.evaluation_reserve_seconds
        - branch.journal.latest_active_elapsed_ms() / 1000
    )
    assert 0 < solver <= 600
    assert branch.request.evaluation_reserve_seconds == 330


def test_missing_seed_continuation_never_replaces_sample(source, tmp_path):
    branch, group = prepared(source, tmp_path)
    decision = branch.journal.events()[-1]["payload"]
    ref = Artifact.model_validate(decision["continuation_ref"]["artifact"])
    # This artifact belongs only to the disposable fixture fork.
    from pathlib import Path

    Path(ref.path).write_bytes(b"corrupt fixture")
    client = ScriptedClient(stop_steps())
    result, probes = run(branch, group, client)
    assert result["result"]["terminal"] == "PROVIDER_CONTINUATION_ERROR", result
    assert result["stop_remaining"]
    assert not client.counted and not client.created and not probes[0].calls


def test_imported_wire_tampering_and_missing_continuation_fail_closed(source, tmp_path):
    branch, _ = prepared(source, tmp_path)
    turn = next(
        e["payload"] for e in reversed(branch.journal.events()) if e["event_type"] == "turn_started"
    )
    with inherited_reads(branch), checkpoint.instruction_slot(branch.selected["input"][-1]):
        assert runner._load_active_model_input(turn, branch.store, context_policy="segmented-v1")
        bad = copy.deepcopy(turn)
        bad["native_history"]["uptake_overlay"]["wire_hash"] = "tampered"
        with pytest.raises(runner._ProviderContinuationError, match="unavailable or invalid"):
            runner._load_active_model_input(bad, branch.store, context_policy="segmented-v1")
    decision = branch.journal.events()[-1]["payload"]
    ref = decision["continuation_ref"]
    ref["order_hash"] = "sha256:" + "a" * 64
    with pytest.raises(Exception, match="metadata does not match"):
        runner._load_provider_continuation(
            branch.store, runner.ProviderContinuationRef.model_validate(ref)
        )


def test_fixture_edit_check_finish_uses_single_sealed_assessment(source, tmp_path):
    branch, group = prepared(source, tmp_path)
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    arguments = {
        k: getattr(mutation, k)
        for k in ("path", "old_text", "new_text", "hypothesis", "expected_behavior")
    }
    arguments.update(occurrence=1, causal_revision=None)
    client = ScriptedClient(
        [
            [call("replace_text", arguments, "mutate")],
            [call("run_check", {"check_id": "existing-unit-tests"}, "verify")],
            [call("finish_task", {}, "finish")],
        ]
    )
    result, probes = run(branch, group, client, fixture_evaluation=True)
    assert result["result"]["terminal"] == "EVALUATOR_PASS", result
    assert result["accepted_new_edits"] == 1
    events = branch.journal.events()[branch.inherited_events :]
    oracle = [e for e in events if e["event_type"] == "uptake_terminal_public_oracle"]
    submissions = [e for e in events if e["event_type"] == "submission_recorded"]
    assert len(oracle) == len(submissions) == 1
    assert oracle[0]["payload"]["patch_hash"] == submissions[0]["payload"]["patch_hash"]
    assert len([e for e in events if e["event_type"] == "evaluator_finished"]) == 1
    assert [p.calls for p in probes] == [[branch.row["action_id"]], ["uptake_final_public_oracle"]]
    assert "SYNTHETIC_ORACLE" not in json.dumps(client.created)
    assert not result["stop_remaining"]
