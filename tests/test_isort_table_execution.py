"""I2 uses I1's unchanged contract tests plus strict table/whole-request parity tests."""

from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import test_isort_uptake_execution as inherited
from test_checkpoint_continuation import stop_steps
from test_isort_uptake_execution import source as parent_source  # noqa: F401

from diagnostics import isort_table_checkpoint as checkpoint
from diagnostics import isort_table_execution as execution
from diagnostics import isort_uptake_execution as baseline
from diagnostics.checkpoint_continuation import ScriptedClient
from patchloop.dev import runner
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import canonical_json

_original_prepared = inherited.prepared


@pytest.fixture(scope="module")
def source(parent_source, tmp_path_factory):  # noqa: F811
    root = tmp_path_factory.mktemp("table-source")
    branch, group = _original_prepared(parent_source, root)
    feedback = branch.feedback
    specs = [
        ("type_opening", "opening", "item", "opening"),
        ("type_item", "item", "item", "opening"),
        ("plain_opening", "opening", "item", "item"),
        ("plain_item", "item", "item", "item"),
    ]
    feedback["cases"] = [
        {
            "case_id": name,
            "position": expected,
            "input": name,
            "expectation_basis": "original public issue example"
            if i == 0
            else "derived public control",
        }
        for i, (name, expected, _, _) in enumerate(specs)
    ]
    for index, snapshot in enumerate(feedback["snapshots"]):
        rows = []
        for case, spec in zip(feedback["cases"], specs, strict=True):
            actual = spec[2 + index]
            rows.append(
                {
                    "stage": "case_result",
                    "case_id": case["case_id"],
                    "input": case["input"],
                    "expected_position": case["position"],
                    "comments": [{"position": actual}],
                    "comment_preserved": True,
                    "import_ast_preserved": True,
                    "position_preserved": actual == case["position"],
                }
            )
        snapshot["receipt"]["stdout"] = "\n".join(canonical_json(r) for r in rows)
    client = ScriptedClient(stop_steps())
    with baseline.offline_environment(branch, client):
        result = baseline.run_row(
            branch, group, "UNEXECUTED", reviewer=baseline.inert_reviewer, client=client
        )
    assert result["first_input_verified"] and not result["stop_remaining"], result
    # The SDK adds a transport timeout; parity covers the counted/dispatched request.
    prepared_ref = [
        e["payload"]["artifact"]
        for e in branch.journal.events()
        if e["event_type"] == "model_input_prepared"
    ][-1]
    expected = json.loads(Path(prepared_ref["path"]).read_bytes())["request"]
    feedback["case_comparison"] = checkpoint.comparison_table(feedback)
    view = json.loads(expected["input"][-1]["content"])
    view["state"][checkpoint.FIELD] = copy.deepcopy(feedback)
    expected["input"][-1]["content"] = canonical_json(view)
    cut = [
        e
        for e in DevJournal(parent_source.root, parent_source.run_id).events()
        if e["event_type"] == "model_input_prepared"
    ][-1]["sequence"]
    return SimpleNamespace(
        **vars(parent_source),
        original=parent_source,
        feedback=feedback,
        expected=expected,
        cut=cut,
        package=branch.package,
        task_dir=branch.task_dir,
    )


def prepared(source, tmp_path):
    group = execution.Invocation(DevJournal(tmp_path / "group", "run_dev_tablefixture"))
    with patch.object(runner, "_resolve_task_file", lambda _: (source.task_dir, source.package)):
        branch = checkpoint.restore_branch(
            source.original,
            source.cut,
            copy.deepcopy(source.feedback),
            tmp_path / "I2",
            started=group.started,
            deadline=group.deadline,
            expected_request=copy.deepcopy(source.expected),
        )
    return branch, group


# Exercise the same explicit contracts through I2's executor and reconstructed first request.
CONTRACTS = [
    ("test_first_packet_native_order_source_currency_and_normal_second_state", {}),
    *[
        ("test_bad_first_exposure_stops_before_dispatch", {"bad": v})
        for v in ("source", "missing", "setup", "truncated", "origin", "native")
    ],
    *[
        ("test_uncertainty_stops_without_retry", {"failure": v})
        for v in ("count", "transport", "usage")
    ],
    ("test_malformed_settled_without_correction", {}),
    ("test_first_oversize_is_counted_once_without_pruning", {}),
    ("test_sixth_full_reservation_settles_at_deadline_then_stops", {}),
    *[
        ("test_no_uncounted_changed_or_underreserved_dispatch", {"bad": v})
        for v in ("changed", "count", "reservation", "shrink", "cap")
    ],
    *[
        (
            "test_two_edits_rechecks_finish_and_public_review_precedes_both_assessments",
            {"oracle_pass": v},
        )
        for v in (True, False)
    ],
    ("test_third_edit_is_not_accepted", {}),
    *[
        ("test_deadline_before_request_has_no_model_or_assessment", {"which": v})
        for v in ("solver", "invocation")
    ],
    ("test_inherited_limits_and_time_not_reset", {}),
    ("test_u_semantic_grade_accepts_conditional_linkage_without_keyword_rules", {}),
    ("test_invalid_u_citations_stop_before_oracle_or_evaluator", {}),
    ("test_real_task_guard_denies_target_edits_and_execution", {}),
    ("test_failing_check_triggers_budgeted_automatic_recheck_after_repair", {}),
    ("test_late_return_settles_but_cannot_execute_tools", {}),
    ("test_sixth_generation_finish_is_executed_and_count_cap_blocks_seventh", {}),
    *[
        ("test_terminal_oracle_uncertainty_never_reaches_isolated_evaluator", {"failure": v})
        for v in ("cleanup_failed", "timed_out", "truncated", "missing")
    ],
    ("test_file_review_deadline_never_fabricates_a_grade", {}),
    *[("test_parallel_reads_count_individually_and_reject_fifth", {"number": v}) for v in (4, 5)],
    ("test_discarded_counts_cannot_fund_a_seventh_or_reuse_old_request", {}),
    ("test_terminal_phase_deadlines_are_separate_inside_overall_time", {}),
]


@pytest.mark.parametrize(
    "name,extra", CONTRACTS, ids=[n.removeprefix("test_") + str(e) for n, e in CONTRACTS]
)
def test_inherited_contract(name, extra, source, tmp_path, monkeypatch):
    monkeypatch.setattr(inherited, "execution", execution)
    monkeypatch.setattr(inherited, "prepared", prepared)
    function = getattr(inherited, name)
    available = {"source": source, "tmp_path": tmp_path, **extra}
    function(**{k: available[k] for k in inspect.signature(function).parameters})


@pytest.mark.parametrize(
    "field",
    [
        "working_plan",
        "completion_guidance",
        "working_notes",
        "workflow_gate",
        "current_public_failure",
        "remaining_visible_check_ids",
    ],
)
def test_initial_state_changes_are_denied_before_count(source, tmp_path, field):
    branch, group = prepared(source, tmp_path)
    original = execution.add_feedback

    def changed(items, feedback):
        result = original(items, feedback)
        view = json.loads(result[-1]["content"])
        view["state"][field] = "TAMPERED"
        result[-1]["content"] = canonical_json(view)
        return result

    client = ScriptedClient(stop_steps())
    with (
        patch.object(execution, "add_feedback", changed),
        execution.offline_environment(branch, client),
    ):
        result = execution.run_row(
            branch, group, "UNEXECUTED", reviewer=execution.inert_reviewer, client=client
        )
    assert not client.counted and not client.created and result["stop_remaining"], result


@pytest.mark.parametrize(
    "bad", ["cell", "omitted", "basis", "reordered", "raw", "extra_instruction"]
)
def test_display_or_original_data_drift_is_denied(source, tmp_path, bad):
    branch, group = prepared(source, tmp_path)
    if bad == "cell":
        branch.feedback["case_comparison"]["rows"][1][4] = "item"
    elif bad == "omitted":
        branch.feedback["case_comparison"]["rows"].pop()
    elif bad == "basis":
        branch.feedback["case_comparison"]["rows"][1][1] = "hidden oracle"
    elif bad == "reordered":
        branch.feedback["case_comparison"]["rows"].reverse()
    elif bad == "raw":
        branch.feedback["snapshots"][0]["receipt"]["stdout"] = "{}"
    else:
        branch.feedback["instruction"] = "Revise the hypothesis now."
    client = ScriptedClient(stop_steps())
    with execution.offline_environment(branch, client):
        result = execution.run_row(
            branch, group, "UNEXECUTED", reviewer=execution.inert_reviewer, client=client
        )
    assert not client.counted and not client.created and result["stop_remaining"], result


def test_only_active_time_normalizes_and_full_request_is_bound(source):
    request = copy.deepcopy(source.expected)
    view = json.loads(request["input"][-1]["content"])
    view["state"]["remaining_budget"]["active_wall_time_seconds"] -= 1
    request["input"][-1]["content"] = canonical_json(view)
    assert checkpoint.compare_first_request(request, source.expected)["difference_seconds"] == -1
    for field, value in (("model", "other-model"), ("tools", []), ("max_output_tokens", 100)):
        with pytest.raises(ContractError, match="parity changed"):
            checkpoint.compare_first_request({**request, field: value}, source.expected)
    request["input"][0] = {"role": "system", "content": "different instructions"}
    with pytest.raises(ContractError, match="parity changed"):
        checkpoint.compare_first_request(request, source.expected)


def test_table_is_delivered_only_once_and_receipts_are_lossless(source, tmp_path):
    branch, group = prepared(source, tmp_path)
    read = inherited.call(
        "read_file",
        {"path": "mini_data_utils/csvlite.py", "start_line": 1, "end_line": 90},
        "inspect",
    )
    client = ScriptedClient([[read], *stop_steps()])
    with execution.offline_environment(branch, client):
        result = execution.run_row(
            branch, group, "UNEXECUTED", reviewer=execution.inert_reviewer, client=client
        )
    assert result["first_input_parity"]["status"] == "PASS" and result["row"] == "I2", result
    first = json.loads(client.created[0]["input"][-1]["content"])["state"]
    second = json.loads(client.created[1]["input"][-1]["content"])["state"]
    assert first[checkpoint.FIELD] == source.feedback and checkpoint.FIELD not in second
    assert first[checkpoint.FIELD]["case_comparison"] == checkpoint.comparison_table(
        source.feedback
    )
    assert result["model_uptake"] == "NOT_RUN" and result["provider_calls"] == 0


def test_action_ceiling_preserves_the_existing_completion_reserve(source, tmp_path):
    branch, group = prepared(source, tmp_path)
    steps = []
    for batch, size in enumerate((4, 4, 4, 4, 2, 1)):
        calls = []
        for number in range(size):
            call = inherited.call(
                "read_file",
                {"path": "mini_data_utils/csvlite.py", "start_line": 1, "end_line": 90},
                "inspect",
            )
            call["action_id"] = f"bounded_read_{batch}_{number}"
            calls.append(call)
        steps.append(calls)
    client = ScriptedClient(steps)
    with execution.offline_environment(branch, client):
        result = execution.run_row(
            branch, group, "UNEXECUTED", reviewer=execution.inert_reviewer, client=client
        )
    assert branch.request.limits.max_tool_actions - branch.parent_actions == 18
    # With two slots left, another two-read batch would consume the finish reserve.
    assert result["new_tool_actions"] == 16, result
    assert result["result"]["terminal"] == "PROTOCOL_VIOLATION"
    assert result["new_generations"] <= 6 and result["U"] != "FAIL"
    assert not any(e["event_type"] == "submission_recorded" for e in branch.journal.events())


def test_review_timeout_never_enters_terminal_assessments(source, tmp_path):
    branch, group = prepared(source, tmp_path)
    client = ScriptedClient(inherited.edit_steps())

    def review(ref, packet, deadline):
        group.deadline = execution.ExecutionDeadline(0, lambda: 1)
        return execution.inert_reviewer(ref, packet, deadline)

    with execution.offline_environment(branch, client, fixture_evaluation=True) as probes:
        result = execution.run_row(branch, group, "UNEXECUTED", reviewer=review, client=client)
    assert result["stop_remaining"] and result["U"] == "NOT_RUN"
    assert not any(p.calls for p in probes)
    assert not any(e["event_type"] == "evaluator_finished" for e in branch.journal.events())
