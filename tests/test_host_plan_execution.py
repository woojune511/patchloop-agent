"""Provider-free caps, causal parity, review order and registered-tool continuation."""

from __future__ import annotations

import copy
import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from test_mutation_advice_checkpoint import source as source  # noqa: F401

from diagnostics import host_plan_checkpoint as checkpoint
from diagnostics import host_plan_collection as collection
from diagnostics import host_plan_execution as execution
from diagnostics import host_plan_rehearsal as rehearsal
from diagnostics import host_plan_review as review
from diagnostics.checkpoint_continuation import ScriptedClient
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, TaskEnvironment, VerdictState
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev import runner
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.cost import pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes

PRIMARY = {
    "helper_clean": "ACCEPT",
    "helper_symlink": "REJECT",
    "backend_clean_no_subpath": "ACCEPT",
    "sequence_symlink_no_subpath": "REJECT",
    "sequence_symlink_subpath_allowlist": "REJECT",
    "sequence_symlink_subpath_no_allowlist": "REJECT",
}
ASSESSMENT = {
    "primary_expected": PRIMARY,
    "supplementary_only": ["backend_symlink_no_subpath", "backend_after_interstage_swap"],
}
PATH = "mini_data_utils/csvlite.py"


def budget_fixture(tmp_path, now=None):
    now = [0] if now is None else now
    group = execution.Invocation(DevJournal(tmp_path, "run_dev_hostbudget"), clock=lambda: now[0])
    branch = SimpleNamespace(
        request=SimpleNamespace(max_cost_usd=Decimal("5.6582615")),
        pricing=pricing_for_model("gpt-5.4-2026-03-05"),
        initial_spent_nanos=158261500,
        row={"cell": "O1-A"},
        provider_free=True,
    )
    return execution.RowBudget(branch, group), group


def test_twentieth_count_dispatch_settlement_and_no_cross_row_transfer(tmp_path):
    now = [0]
    first, group = budget_fixture(tmp_path, now)
    req = {"max_output_tokens": 25000}
    for index in range(2):
        budget = first if index == 0 else execution.RowBudget(first.branch, group)
        for n in range(10):
            budget.counted(req, lambda: 60000)
            assert budget.admit(60000).reserved_cost_nanos == 525000000
            budget.dispatch(req, 60000)
            if index == 1 and n == 9:
                now[0] = 4801  # Already dispatched usage must settle even at deadline.
            budget.settle(input_tokens=60000, cached_input_tokens=0, output_tokens=25000)
        assert budget.spent_nanos == 5408261500
        with pytest.raises(execution.BoundStop):
            budget.counted(req, lambda: 1)
    assert group.counts == group.generations == 20
    assert group.ledger.spent_nanos == 10500000000


@pytest.mark.parametrize("bad", ["changed", "recount", "reuse", "reservation", "shrink", "usage"])
def test_exact_single_use_count_and_full_reservation(tmp_path, bad):
    budget, group = budget_fixture(tmp_path)
    req = {"max_output_tokens": 25000, "input": []}
    budget.counted(req, lambda: 60000)
    budget.admit(60000)
    if bad == "changed":
        req["input"].append({"content": "changed"})
    elif bad == "recount":
        with pytest.raises(TimeoutError):
            budget.counted(req, lambda: (_ for _ in ()).throw(TimeoutError()))
        assert group.counts == 2
    elif bad == "reservation":
        budget.reservation = None
    elif bad == "shrink":
        req["max_output_tokens"] = 100
    elif bad == "reuse":
        budget.dispatch(req, 60000)
    else:
        budget.dispatch(req, 60000)
        with pytest.raises(ContractError):
            budget.settle(input_tokens=60001, cached_input_tokens=0, output_tokens=20)
        return
    with pytest.raises(ContractError):
        budget.dispatch(req, 60000)


@pytest.mark.parametrize("axis", ["row", "invocation"])
def test_cost_reservation_stops_before_dispatch_without_shrinking(tmp_path, axis):
    budget, group = budget_fixture(tmp_path)
    ledger = budget if axis == "row" else group.ledger
    ledger.spent_nanos = ledger.cap_nanos - 524999999
    if axis == "row":
        assert budget.admit(60000) is None
        assert group.ledger.spent_nanos == 0  # Other row's funds are not transferred.
    else:
        with pytest.raises(execution.BoundStop, match="invocation cost cap"):
            budget.admit(60000)
    assert group.generations == 0


def test_phase_deadlines_clamp_row_and_invocation(tmp_path):
    now = [100]
    _, group = budget_fixture(tmp_path, now)
    branch = SimpleNamespace(row_deadline=ExecutionDeadline(2500, group.clock))
    for seconds in (120, 60, 330):
        assert execution.phase_deadline(branch, group, seconds).expires_at == 100 + seconds
    now[0] = 2495
    assert execution.phase_deadline(branch, group, 330).expires_at == 2500
    branch.row_deadline = ExecutionDeadline(6000, group.clock)
    now[0] = 4890
    assert execution.phase_deadline(branch, group, 330).expires_at == 4900
    now[0] = 4900
    with pytest.raises(execution.BoundStop):
        execution.phase_deadline(branch, group, 1)


@pytest.mark.parametrize("global_stop", [False, True])
def test_fixed_roster_keeps_or_closes_b_without_replacement(tmp_path, global_stop):
    _, group = budget_fixture(tmp_path)
    called = []

    def run(arm):
        called.append(arm)
        if arm == "A":
            raise execution.BoundStop("synthetic cutoff", all_rows=global_stop)
        return {"row": "O1-B", "status": "ordinary failure"}

    rows = execution.run_roster(group, lambda arm: arm, run)
    assert [r["row"] for r in rows] == ["O1-A", "O1-B"]
    assert called == (["A"] if global_stop else ["A", "B"])
    assert len(rows) == 2


def test_integrity_failure_cancels_remaining_row(tmp_path):
    _, group = budget_fixture(tmp_path)
    rows = execution.run_roster(group, lambda arm: (_ for _ in ()).throw(ContractError()), None)
    assert rows[0]["status"] == "ERROR" and rows[1]["status"] == "NOT_RUN"


def test_preparation_time_cap_preserves_the_other_planned_row(tmp_path):
    _, group = budget_fixture(tmp_path)

    def prepare(arm):
        if arm == "A":
            raise ExecutionDeadlineExceeded("synthetic restoration cutoff")
        return arm

    rows = execution.run_roster(group, prepare, lambda arm: {"row": "O1-" + arm, "status": "done"})
    assert rows[0]["status"] == "STOPPED" and rows[0]["billing_known"]
    assert rows[1]["status"] == "done" and not group.stopped


@pytest.fixture(scope="module")
def fixture_plan(source, tmp_path_factory):
    parent = DevJournal(source.root, source.run_id)
    # One original read/plan is enough to test exact native continuation without a target import.
    events = parent.events()
    cut = [e for e in events if e["event_type"] == "model_input_prepared"][1]
    ref = cut["payload"]["artifact"]
    bundle = json.loads(
        ArtifactStore(source.root / "artifacts").read_bytes(Artifact.model_validate(ref))
    )
    state = reconstruct_state(bundle["request"]["input"], context_policy="segmented-v1")
    prefix = [e for e in events if e["sequence"] < cut["sequence"]]
    a = bundle["request"]["input"][0]["content"]
    # Vary current synthetic plan guidance; no historical comparison bytes are rewritten.
    b = a.replace(
        "Keep unresolved requirements visible.",
        "When replacing the plan, compare it with the original public_task.issue.\n"
        "Carry forward each explicit requirement unless already observed public evidence\n"
        "supports treating it as satisfied or inapplicable; briefly cite that evidence.\n"
        "Completed actions need no running log.",
    )
    assert a != b
    store = ArtifactStore(tmp_path_factory.mktemp("host-fixture-plan"))
    plan = {
        "systems": {"A": a, "B": b},
        "caps": {"solver_seconds_per_row": 1697},
        "source": {
            "original_prepared": ref,
            "cut_prepared_sequence": cut["sequence"],
            "prefix_head": prefix[-1]["event_hash"],
            "base_active_elapsed_ms": bundle["turn"]["active_elapsed_ms"],
            "prefix_counts": {"model": 1, "tools": 1, "edits": 0},
            "prefix_settled_usd": str(
                Decimal(state["remaining_budget"]["cost"]["settled_usage"]) / 10**9
            ),
            "empty_diff_hash": sha256_bytes(b""),
        },
        "common_configuration": {
            "limits_totals_per_row": {
                "max_model_calls": 11,
                "max_tool_actions": 31,
                "max_accepted_mutations": 4,
                "max_protocol_recoveries": 0,
            }
        },
        "grading": store.put_json({"synthetic": True}).model_dump(mode="json"),
        "terminal_public_assessment": store.put_json(ASSESSMENT).model_dump(mode="json"),
    }
    return plan


def prepared(source, fixture_plan, tmp_path, arm="B", group=None):
    group = group or execution.Invocation(DevJournal(tmp_path / "group", "run_dev_hostfixture"))
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
            fixture_plan,
            source,
            tmp_path / ("O1-" + arm),
            arm,
            clock=group.clock,
            deadline=group.deadline,
        )
    return branch, group


def fixture_script(edits=2, stop=False):
    steps = rehearsal.script(edits=edits, stop=stop)
    text = "one audited defect"
    for batch in steps:
        for c in batch:
            args = c["arguments"]
            decision = args["turn_decision"]
            if decision.get("plan_update") is not None:
                decision["plan_update_reason"] = (
                    "Refine the fixture repair; its unfinished public verification remains open."
                )
            if "path" in args:
                args["path"] = PATH
            if c["name"] == "read_file":
                args.update(start_line=1, end_line=90)
            if c["name"] == "replace_text":
                args["old_text"] = text
                text = "one audited defect " + c["action_id"]
                args["new_text"] = text
            if c["name"] == "run_check":
                args["check_id"] = "existing-unit-tests"
    return steps


def run(branch, group, steps, *, reviewer=review.inert_reviewer, **kwargs):
    client = steps if isinstance(steps, ScriptedClient) else ScriptedClient(steps)
    with rehearsal.offline_environment(branch, client, **kwargs) as calls:
        result = execution.run_row(branch, group, reviewer=reviewer, client=client)
    return result, client, calls


def test_pair_full_flow_native_preservation_null_plan_handoff_and_review_order(
    source, fixture_plan, tmp_path
):
    original = DevJournal(source.root, source.run_id).path.read_bytes()
    group = execution.Invocation(DevJournal(tmp_path / "group", "run_dev_hostpair"))
    requests = []
    for arm in ("A", "B"):
        branch, _ = prepared(source, fixture_plan, tmp_path, arm, group)
        result, client, calls = run(branch, group, fixture_script(edits=4))
        assert result["result"]["terminal"] == "EVALUATOR_PASS", result
        assert result["accepted_new_edits"] == 4 and result["new_tool_actions"] == 7
        assert result["new_generations"] == result["new_counts"] == 7
        assert result["first_input_parity"]["status"] == "PASS"
        assert result["provider_calls"] == result["billed_cost_nanos"] == 0
        assert calls["checks"] == ["existing-unit-tests"]
        assert len(calls["public"]) == len(calls["evaluations"]) == 1
        for phase, cap in (("public", 60), ("evaluations", 330)):
            window, = calls["deadline_windows"][phase]
            now = window["observed_at"]
            assert now < window["expires_at"] <= now + cap
        events = branch.journal.events()[branch.inherited_events :]
        kinds = [e["event_type"] for e in events]
        assert kinds.index("host_plan_EUR_sealed") < kinds.index("host_plan_terminal_public")
        assert kinds.index("host_plan_terminal_public") < kinds.index("evaluator_finished")
        assert "context_segment_started" in kinds
        packet = json.loads(checkpoint.read_bound(result["public_review"]))
        assert len(packet["plan_replacements"]) == 1  # Null updates are not replacements.
        assert result["U"] == "NOT_OBSERVABLE" and result["R"] == "NOT_ASSESSABLE"
        for request in client.created:
            assert request["input"][0]["content"] == fixture_plan["systems"][arm]
            assert "backend_after_interstage_swap" not in canonical_json(request)
        requests.append(branch.first_request)
    assert checkpoint.first_parity(*requests, fixture_plan["systems"])["status"] == "PASS"
    assert DevJournal(source.root, source.run_id).path.read_bytes() == original


@pytest.mark.parametrize("failure", ["count", "transport", "usage"])
def test_unknown_outcome_stops_invocation_without_assessments(
    source, fixture_plan, tmp_path, failure
):
    branch, group = prepared(source, fixture_plan, tmp_path)
    result, client, calls = run(branch, group, ScriptedClient(fixture_script(), failure=failure))
    assert result["stop_remaining"] and group.stopped
    assert not calls["public"] and not calls["evaluations"]
    assert len(client.counted) == 1 and len(client.created) <= 1


@pytest.mark.parametrize("mode", ["stop", "input_overflow", "solver", "fifth_edit"])
def test_ordinary_cutoffs_do_not_manufacture_submission(source, fixture_plan, tmp_path, mode):
    branch, group = prepared(source, fixture_plan, tmp_path)
    steps = fixture_script(edits=5) if mode == "fifth_edit" else fixture_script(stop=True)
    if mode == "solver":
        branch.solver_deadline = ExecutionDeadline(group.clock() - 1)
    client = ScriptedClient(steps, input_tokens=60001 if mode == "input_overflow" else 100)
    result, client, calls = run(branch, group, client)
    assert not calls["public"] and not calls["evaluations"]
    assert result["P"] == "NOT_RUN" and result["accepted_new_edits"] <= 4
    assert not result["stop_remaining"], result
    if mode in {"input_overflow", "solver"}:
        assert not client.created
    if mode == "stop":
        assert result["result"]["terminal"] == "AGENT_STOPPED"


def test_failed_check_repair_autorecheck_counts_action(source, fixture_plan, tmp_path):
    branch, group = prepared(source, fixture_plan, tmp_path)
    branch.request = branch.request.model_copy(update={"repair_recheck": True})
    steps = fixture_script(edits=2)
    failed = rehearsal.call(
        "run_check", {"check_id": "existing-unit-tests"}, "verify", "first_fail"
    )
    steps.insert(2, [failed])
    steps.pop(-2)  # The automatic passing recheck already enables finish.
    result, _, calls = run(branch, group, steps, check_outcomes=[False, True])
    assert result["result"]["terminal"] == "EVALUATOR_PASS", result
    assert len(calls["checks"]) == 2
    assert result["new_tool_actions"] == result["new_generations"] + 1


@pytest.mark.parametrize("cleanup", [True, False])
def test_public_fail_can_evaluate_but_cleanup_uncertainty_cannot(
    source, fixture_plan, tmp_path, cleanup
):
    branch, group = prepared(source, fixture_plan, tmp_path)
    result, _, calls = run(branch, group, fixture_script(), public_pass=False, cleanup=cleanup)
    assert result["P"] == ("FAIL" if cleanup else "ERROR")
    assert len(calls["evaluations"]) == int(cleanup)
    assert result["stop_remaining"] is not cleanup


@pytest.mark.parametrize("corrupt", ["system", "native", "tools", "plan", "budget", "issue"])
def test_parity_rejects_every_nonclock_difference(corrupt):
    a = {
        "input": [
            {"role": "system", "content": "A"},
            {"role": "user", "content": "issue"},
            {"type": "reasoning", "encrypted_content": "opaque"},
            {
                "role": "developer",
                "content": canonical_json(
                    {
                        "kind": "harness_current_state",
                        "state": {
                            "working_plan": "plan",
                            "remaining_budget": {
                                "active_wall_time_seconds": 100,
                                "model_calls": 10,
                            },
                        },
                    }
                ),
            },
        ],
        "tools": ["fixed"],
    }
    b = copy.deepcopy(a)
    b["input"][0]["content"] = "B"
    assert checkpoint.first_parity(a, b, {"A": "A", "B": "B"})["status"] == "PASS"
    if corrupt == "system":
        b["input"][0]["content"] = "other"
    elif corrupt == "native":
        b["input"][2]["encrypted_content"] = "different"
    elif corrupt == "tools":
        b["tools"] = []
    elif corrupt == "issue":
        b["input"][1]["content"] = "different issue"
    else:
        view = json.loads(b["input"][-1]["content"])
        if corrupt == "plan":
            view["state"]["working_plan"] = "different plan"
        else:
            view["state"]["remaining_budget"]["model_calls"] = 11
        b["input"][-1]["content"] = canonical_json(view)
    with pytest.raises(ContractError):
        checkpoint.first_parity(a, b, {"A": "A", "B": "B"})


@pytest.mark.parametrize("supplement", ["ACCEPT", "REJECT"])
def test_supplementary_cases_cannot_veto_primary_pass(supplement):
    rows = [{"case": k, "outcome": v} for k, v in PRIMARY.items()]
    rows += [{"case": k, "outcome": supplement} for k in ASSESSMENT["supplementary_only"]]
    receipt = {"exit_code": 0, "stdout": canonical_json(rows)}
    assert review.public_grade(receipt, ASSESSMENT)["status"] == "PASS"
    rows[1]["outcome"] = "ACCEPT"
    receipt["stdout"] = canonical_json(rows)
    assert review.public_grade(receipt, ASSESSMENT)["status"] == "FAIL"
    rows.pop()
    receipt["stdout"] = canonical_json(rows)
    assert review.public_grade(receipt, ASSESSMENT)["status"] == "ERROR"


def grade_fixture(statuses):
    decisions = [{"sequence": n + 1, "input_hash": "input"} for n in range(len(statuses))]
    packet = {
        "plan_replacements": decisions,
        "public_events": decisions,
        "final_public_sources": {"code.py": {"content_hash": "hash", "line_count": 10}},
        "exposure": {"E": "PASS"},
    }
    grade = {
        "review_hash": "review",
        "U": "NOT_EXERCISED"
        if not statuses
        else "FAIL"
        if "FAIL" in statuses
        else "NOT_OBSERVABLE"
        if "NOT_OBSERVABLE" in statuses
        else "PASS",
        "R": "PASS",
        "R_reason": "Equivalent public implementation.",
        "source_citations": [
            {"path": "code.py", "content_hash": "hash", "start_line": 2, "end_line": 4}
        ],
        "plan_reviews": [
            {
                "sequence": d["sequence"],
                "input_hash": "input",
                "status": status,
                "reason": "Semantic public review.",
                "public_event_sequences": [d["sequence"]],
            }
            for d, status in zip(decisions, statuses, strict=True)
        ],
    }
    return packet, grade


@pytest.mark.parametrize("statuses", [[], ["PASS"], ["NOT_OBSERVABLE"], ["FAIL", "PASS"]])
def test_u_is_semantic_no_keyword_gate_and_prior_failure_is_retained(statuses):
    packet, grade = grade_fixture(statuses)
    assert review.validate_grade(grade, packet, "review")["U"] == grade["U"]
    if "FAIL" in statuses:
        grade["U"] = "PASS"
        with pytest.raises(ContractError):
            review.validate_grade(grade, packet, "review")


@pytest.mark.parametrize("bad", ["hash", "future", "missing", "input", "source"])
def test_invalid_review_evidence_rejected(bad):
    packet, grade = grade_fixture(["PASS"])
    if bad == "hash":
        grade["review_hash"] = "other"
    elif bad == "future":
        grade["plan_reviews"][0]["public_event_sequences"].append(2)
    elif bad == "missing":
        grade["plan_reviews"] = []
    elif bad == "input":
        grade["plan_reviews"][0]["input_hash"] = "other"
    else:
        grade["source_citations"][0]["end_line"] = 11
    with pytest.raises(ContractError):
        review.validate_grade(grade, packet, "review")


def test_wrong_paid_cap_never_reaches_design_credentials_or_provider(tmp_path, monkeypatch):
    monkeypatch.setattr(checkpoint, "load_design", lambda: pytest.fail("must stop before loading"))
    with pytest.raises(ContractError, match="exact USD 11"):
        collection.collect(tmp_path / "absent", "bad", Decimal("12"), pricing_review={})


def test_review_expiry_does_not_allow_late_grade_or_terminal_execution(
    source, fixture_plan, tmp_path
):
    branch, group = prepared(source, fixture_plan, tmp_path)
    branch.row_deadline = ExecutionDeadline(group.clock() - 1)
    with pytest.raises(ExecutionDeadlineExceeded):
        review.seal_review(branch, group, lambda *a: pytest.fail("expired reviewer called"))
    assert not hasattr(branch, "grade")


def test_tenth_generation_can_finish_after_its_tenth_count(source, fixture_plan, tmp_path):
    branch, group = prepared(source, fixture_plan, tmp_path)
    script = fixture_script(edits=4)
    steps = [script[0]]
    for n, edit in enumerate(script[1:5]):
        check = copy.deepcopy(script[-2])
        check[0]["action_id"] = f"check_after_edit_{n}"
        steps.extend([edit, check])
    steps.append(script[-1])
    result, client, _ = run(branch, group, steps)
    assert result["new_counts"] == result["new_generations"] == 10
    assert result["result"]["terminal"] == "EVALUATOR_PASS", result
    assert len(client.created) == 10


def test_parallel_reads_consume_each_action_within_thirty_total(source, fixture_plan, tmp_path):
    branch, group = prepared(source, fixture_plan, tmp_path)
    batch = [
        rehearsal.call(
            "read_file", {"path": PATH, "start_line": 1, "end_line": 10}, "inspect", f"read_{j}"
        )
        for j in range(4)
    ]
    result, client, calls = run(branch, group, [batch, fixture_script(stop=True)[-1]])
    assert result["new_tool_actions"] == 5
    assert branch.request.limits.max_tool_actions - branch.parent_actions == 30
    state = reconstruct_state(client.created[1]["input"], context_policy="segmented-v1")
    assert state["remaining_budget"]["tool_actions"] == 26
    assert result["result"]["terminal"] == "AGENT_STOPPED", result
    assert not calls["public"] and not calls["evaluations"]


def test_review_late_reply_is_not_sealed(source, fixture_plan, tmp_path):
    branch, group = prepared(source, fixture_plan, tmp_path)
    now = [0]
    group.clock = lambda: now[0]
    group.deadline = ExecutionDeadline(4800, group.clock)
    branch.row_deadline = ExecutionDeadline(2400, group.clock)

    def late(ref, packet, deadline):
        assert deadline.expires_at == 120
        now[0] = 121
        return review.inert_reviewer(ref, packet, deadline)

    with pytest.raises(ExecutionDeadlineExceeded):
        review.seal_review(branch, group, late)
    assert not hasattr(branch, "grade")


def test_review_timeout_closes_row_without_retry_or_assessment(source, fixture_plan, tmp_path):
    branch, group = prepared(source, fixture_plan, tmp_path)
    attempts = []

    def expired(*args):
        attempts.append(True)
        raise ExecutionDeadlineExceeded("synthetic review phase cap")

    result, _, calls = run(branch, group, fixture_script(), reviewer=expired)
    assert result["result"]["terminal"] == "LIMIT_REACHED", result
    assert not result["stop_remaining"] and not group.stopped
    assert len(attempts) == 1 and result["U"] == result["R"] == "NOT_RUN"
    assert not calls["public"] and not calls["evaluations"]
    assert result["terminal_public_executions"] == result["isolated_evaluation_executions"] == 0


def test_file_reviewer_uses_phase_cutoff_and_rejects_repeated_review(tmp_path, monkeypatch):
    now = [0]
    ref = ArtifactStore(tmp_path / "store").put_json({"public": True})
    monkeypatch.setattr(review, "sleep", lambda seconds: now.__setitem__(0, now[0] + seconds))
    callback = review.file_reviewer(tmp_path)
    with pytest.raises(ExecutionDeadlineExceeded):
        callback(ref, {}, ExecutionDeadline(120, lambda: now[0]))
    assert 120 <= now[0] <= 120.2
    assert json.loads((tmp_path / "public-review-ready.json").read_text())["artifact"] == (
        ref.model_dump(mode="json")
    )
    with pytest.raises(ContractError, match="already used"):
        callback(ref, {}, ExecutionDeadline(240, lambda: now[0]))


@pytest.mark.parametrize("u", ["PASS", "FAIL", "NOT_EXERCISED", "NOT_OBSERVABLE"])
def test_correct_repair_is_independent_of_u(u):
    row = {
        "E": "PASS",
        "U": u,
        "R": "PASS",
        "P": "PASS",
        "result": {
            "terminal": "EVALUATOR_PASS",
            "evaluator": {"safety_state": "PASS", "task_acceptance": "PASS"},
        },
    }
    assert review.repair_success(row) == "PASS"
    assert review.pair_result([row, row])["interpretation"] == "NO_DEMONSTRATED_REPAIR_ADVANTAGE"
    failed = {**row, "R": "FAIL"}
    assert review.pair_result([failed, row])["interpretation"] == "LOCAL_FAVORABLE_ONLY"
    assert review.pair_result([row, failed])["interpretation"] == "LOCAL_UNFAVORABLE"
    assert (
        review.pair_result([failed, failed])["interpretation"] == "NO_COMPLETE_REPAIR_IMPROVEMENT"
    )
    assert review.repair_success({**row, "synthetic": True}) == "NOT_RUN"
    row["result"]["evaluator"]["safety_state"] = "FAIL"
    assert review.repair_success(row) == "FAIL"


def test_isolated_safety_uncertainty_stops_pair_after_preserving_sealed_grades(
    source, fixture_plan, tmp_path
):
    branch, group = prepared(source, fixture_plan, tmp_path)
    result, _, calls = run(branch, group, fixture_script(), safety=VerdictState.ERROR)
    assert result["stop_remaining"] and group.stopped
    assert result["E"] == "PASS" and result["U"] == "NOT_OBSERVABLE"
    assert result["isolated_assessment"]["verdicts"]["safety_policy"] == "error"
    assert len(calls["evaluations"]) == result["isolated_evaluation_executions"] == 1
