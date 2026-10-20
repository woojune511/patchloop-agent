"""Inert transport/local fixture contracts; never execute isort or a provider."""

from __future__ import annotations

import copy
import json
import shutil
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml
from test_checkpoint_continuation import stop_steps
from test_decision_sampler import FakeClient
from test_dev_probes import FakeProbe
from test_uptake_execution import call

from diagnostics import isort_uptake_checkpoint as checkpoint
from diagnostics import isort_uptake_execution as execution
from diagnostics.checkpoint_continuation import ScriptedClient
from diagnostics.declaration_checkpoint import Source
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, TaskEnvironment
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.cost import pricing_for_model
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.util import canonical_json, sha256_bytes


@pytest.fixture(scope="module")
def source(tmp_path_factory):
    # Like the isort cut: a still-wrong source edit with a current public PASS.
    root = tmp_path_factory.mktemp("isort-fixture")
    task = root / "task"
    shutil.copytree(repository_root() / "tasks/smoke/csv-quoted-newline", task)
    public = task / "public.yaml"
    value = yaml.safe_load(public.read_text(encoding="utf-8"))
    value["split"] = "dev-train"
    public.write_text(yaml.safe_dump(value), encoding="utf-8")

    def response(value):
        value.model = "gpt-5.4-2026-03-05"
        n = len(client.created)
        choices = [
            call(
                "read_file",
                {"path": "mini_data_utils/csvlite.py", "start_line": 1, "end_line": 90},
                "inspect",
            ),
            call(
                "replace_text",
                {
                    "path": "mini_data_utils/csvlite.py",
                    "old_text": "one audited defect",
                    "new_text": "a known defect",
                    "occurrence": 1,
                    "causal_revision": None,
                    "hypothesis": "Synthetic still-wrong seed.",
                    "expected_behavior": "Public tests pass.",
                },
                "mutate",
            ),
            call("run_check", {"check_id": "existing-unit-tests"}, "verify"),
            stop_steps()[0][0],
        ]
        item = choices[n - 1]
        value.output[1].name = item["name"]
        value.output[1].arguments = canonical_json(item["arguments"])

    client = FakeClient(count_value=100, edit_response=response)
    request = DevRunRequest(
        provider="openai",
        model="gpt-5.4-2026-03-05",
        reasoning_effort="xhigh",
        context_policy="segmented-v1",
        planning_policy="brief-v1",
        enable_probes=True,
        repair_recheck=True,
        max_cost_usd=Decimal("3.50"),
        env_file=root / "absent.env",
        task=public,
        state_root=root / "state",
    )
    task_dir, package = runner._resolve_task_file(public)
    package = package.model_copy(
        update={
            "environment": TaskEnvironment(
                evaluator_image="test/image@sha256:" + "a" * 64, image_digest="sha256:" + "a" * 64
            )
        }
    )
    with (
        patch("socket.socket.connect", lambda *a: pytest.fail("network forbidden")),
        patch.object(runner, "_live_task_is_admitted", lambda *a, **k: None),
        patch.object(runner, "_live_source_preflight", lambda *a, **k: None),
        patch.object(runner, "_live_sandbox_preflight", lambda *a, **k: LocalSandbox()),
        patch.object(runner, "DockerProbeSandbox", lambda **k: FakeProbe(status="passed")),
        patch.object(runner, "load_exact_openai_api_key", lambda _: "synthetic"),
        patch.object(runner, "_resolve_task_file", lambda _: (task_dir, package)),
        patch.object(runner, "OpenAIResponsesAdapter", lambda config, **k: client.factory(config)),
    ):
        result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "AGENT_STOPPED", result
    assert len(client.created) == 4
    journal = DevJournal(request.state_root, result["run_id"])
    return Source(
        request.state_root,
        result["run_id"],
        sha256_bytes(journal.path.read_bytes()),
        sha256_bytes(journal.envelope_path.read_bytes()),
        public,
        sha256_bytes(public.read_bytes()),
    )


def prepared(source, tmp_path):
    parent = DevJournal(source.root, source.run_id)
    cut = [e for e in parent.events() if e["event_type"] == "model_input_prepared"][-1]
    bundle = json.loads(
        ArtifactStore(source.root / "artifacts").read_bytes(
            Artifact.model_validate(cut["payload"]["artifact"])
        )
    )
    old = parent.load_envelope()
    program = "print('SYNTHETIC_OPERATOR_ONLY')"
    receipt = {
        "source_hash": sha256_bytes(program.encode()),
        "image_digest": old.probe_image_digest,
        "profile_hash": old.probe_profile_hash,
        "status": "passed",
        "stdout": "SYNTHETIC_OPERATOR_ONLY\n",
        "stderr": "",
        "setup_checks": {"status": "passed"},
        "cleanup_failed": False,
        "deadline_exhausted": False,
        "timed_out": False,
        "truncated": False,
    }
    context = json.loads(
        ArtifactStore(source.root / "artifacts").read_bytes(
            Artifact.model_validate(bundle["turn"]["context_artifact"])
        )
    )
    diff = context["current_diff"]["patch_hash"]
    feedback = {
        "origin": "operator_executed_public_diagnostic",
        "model_authored": False,
        "current_snapshot_label": "submitted",
        "python_source": program,
        "program_hash": receipt["source_hash"],
        "observed_on_current_diff_hash": diff,
        "cases": [
            {"case_id": c} for c in ("type_opening", "type_item", "plain_opening", "plain_item")
        ],
        "snapshots": [
            {"label": s, "receipt": copy.deepcopy(receipt), "observed_on_diff_hash": diff}
            for s in ("base", "submitted")
        ],
    }
    task_dir, package = runner._resolve_task_file(source.public_path)
    package = package.model_copy(
        update={
            "environment": TaskEnvironment(
                evaluator_image="test/image@sha256:" + "a" * 64, image_digest="sha256:" + "a" * 64
            )
        }
    )
    group = execution.Invocation(DevJournal(tmp_path / "group", "run_dev_isortfixture"))
    with patch.object(runner, "_resolve_task_file", lambda _: (task_dir, package)):
        branch = checkpoint.restore_branch(
            source,
            cut["sequence"],
            feedback,
            tmp_path / "I1",
            started=group.started,
            deadline=group.deadline,
        )
    return branch, group


def run(
    branch,
    group,
    client,
    *,
    reviewer=execution.inert_reviewer,
    fixture_evaluation=False,
    oracle_pass=True,
):
    with execution.offline_environment(
        branch, client, fixture_evaluation=fixture_evaluation, oracle_pass=oracle_pass
    ) as probes:
        result = execution.run_row(
            branch, group, "print('SYNTHETIC_ORACLE')", reviewer=reviewer, client=client
        )
    return result, probes


def edit_steps(*, two=False, third=False):
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    args = {
        k: getattr(mutation, k)
        for k in ("path", "old_text", "new_text", "hypothesis", "expected_behavior")
    }
    args.update(occurrence=1, causal_revision=None)
    first = call("replace_text", args, "mutate")
    steps = [[first]]
    if two:
        second = call(
            "replace_text", {**args, "old_text": 'newline=""', "new_text": "newline=''"}, "mutate"
        )
        second["action_id"] = "second_edit"
        steps.append([second])
    if third:
        third_call = call(
            "replace_text", {**args, "old_text": "newline=''", "new_text": 'newline=""'}, "mutate"
        )
        third_call["action_id"] = "third_edit"
        steps.append([third_call])
    steps.extend(
        [
            [call("run_check", {"check_id": "existing-unit-tests"}, "verify")],
            [call("finish_task", {}, "finish")],
        ]
    )
    return steps


def test_first_packet_native_order_source_currency_and_normal_second_state(source, tmp_path):
    before = DevJournal(source.root, source.run_id).path.read_bytes()
    branch, group = prepared(source, tmp_path)
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
    assert result["first_input_verified"] and not result["stop_remaining"]
    assert result["new_counts"] == result["new_generations"] == 2
    assert result["new_tool_actions"] == 2  # Operator delivery is not a model tool/probe.
    assert not any(p.calls for p in probes)
    first = reconstruct_state(client.created[0]["input"], context_policy="segmented-v1")
    second = reconstruct_state(client.created[1]["input"], context_policy="segmented-v1")
    assert first[checkpoint.FIELD] == branch.feedback
    assert checkpoint.FIELD not in second
    assert first["remaining_budget"]["accepted_mutations"] == 2
    assert before == DevJournal(source.root, source.run_id).path.read_bytes()
    assert result["provider_calls"] == result["billed_cost_nanos"] == 0
    assert group.ledger.spent_nanos == 2 * (100 * 2500 + 20 * 15000)
    with pytest.raises(ContractError, match="cannot be retried"):
        run(branch, group, ScriptedClient(stop_steps()))


@pytest.mark.parametrize("bad", ["source", "missing", "setup", "truncated", "origin", "native"])
def test_bad_first_exposure_stops_before_dispatch(source, tmp_path, bad):
    branch, group = prepared(source, tmp_path)
    if bad == "source":
        branch.feedback["observed_on_current_diff_hash"] = "wrong"
    elif bad == "missing":
        branch.feedback["snapshots"].pop()
    elif bad == "setup":
        branch.feedback["snapshots"][0]["receipt"]["setup_checks"]["status"] = "failed"
    elif bad == "truncated":
        branch.feedback["snapshots"][1]["receipt"]["truncated"] = True
    elif bad == "origin":
        branch.feedback["model_authored"] = True
    else:
        branch.selected["input"].insert(2, {"type": "reasoning", "encrypted_content": "bad"})
    client = ScriptedClient(stop_steps())
    result, _ = run(branch, group, client)
    assert not client.counted and not client.created
    assert result["stop_remaining"] and not result["first_input_verified"]


@pytest.mark.parametrize("failure", ["count", "transport", "usage"])
def test_uncertainty_stops_without_retry(source, tmp_path, failure):
    branch, group = prepared(source, tmp_path)
    client = ScriptedClient(stop_steps(), failure=failure)
    result, _ = run(branch, group, client)
    assert result["stop_remaining"] and not result["billing_known"]
    assert result["provisional_cost_nanos"] is None
    assert len(client.counted) == 1 and len(client.created) == (failure != "count")
    assert result["U"] != "FAIL"


def test_malformed_settled_without_correction(source, tmp_path):
    branch, group = prepared(source, tmp_path)
    result, _ = run(branch, group, ScriptedClient([[call("nonexistent_tool", {}, "inspect")]]))
    assert result["result"]["terminal"] in {"PROTOCOL_VIOLATION", "INCOMPLETE_RESPONSE"}, result
    assert result["billing_known"] and result["new_generations"] == result["new_counts"] == 1
    assert not any(
        e["event_type"] == "protocol_correction"
        for e in branch.journal.events()[branch.inherited_events :]
    )


def test_first_oversize_is_counted_once_without_pruning(source, tmp_path):
    branch, group = prepared(source, tmp_path)
    client = ScriptedClient(stop_steps(), input_tokens=60001)
    result, _ = run(branch, group, client)
    assert len(client.counted) == 1 and not client.created
    assert "input-token bound" in result["stop_reason"]
    assert result["billing_known"] and result["U"] == "NOT_OBSERVABLE"


def budget_fixture(tmp_path, clock=lambda: 0):
    group = execution.Invocation(DevJournal(tmp_path, "run_dev_isortbudget"), clock=clock)
    branch = SimpleNamespace(
        request=SimpleNamespace(max_cost_usd=Decimal("5.50")),
        pricing=pricing_for_model("gpt-5.4-2026-03-05"),
        initial_spent_nanos=2_000_000_000,
        row={"cell": "I1"},
        provider_free=True,
    )
    return execution.RowBudget(branch, group), group


def test_sixth_full_reservation_settles_at_deadline_then_stops(tmp_path):
    now = [0]
    budget, group = budget_fixture(tmp_path, lambda: now[0])
    req = {"max_output_tokens": 25000}
    for n in range(6):
        budget.counted(req, lambda: 60000)
        assert budget.admit(60000).reserved_cost_nanos == 525_000_000
        budget.dispatch(req, 60000)
        if n == 5:
            now[0] = 721
        budget.settle(input_tokens=60000, cached_input_tokens=0, output_tokens=25000)
    assert group.ledger.spent_nanos == 3_150_000_000
    assert budget.spent_nanos == 5_150_000_000
    assert group.counts == group.generations == 6
    with pytest.raises(execution.BoundStop):
        budget.counted(req, lambda: 1)
    with pytest.raises(execution.BoundStop):
        budget.dispatch(req, 60000)


@pytest.mark.parametrize("bad", ["changed", "count", "reservation", "shrink", "cap"])
def test_no_uncounted_changed_or_underreserved_dispatch(tmp_path, bad):
    budget, group = budget_fixture(tmp_path)
    req = {"max_output_tokens": 25000}
    budget.counted(req, lambda: 60000)
    budget.admit(60000)
    if bad == "changed":
        req["input"] = ["different"]
    elif bad == "count":
        budget.pending = None
    elif bad == "reservation":
        budget.reservation = None
    elif bad == "shrink":
        req["max_output_tokens"] = 100
    else:
        group.ledger.spent_nanos = 3_499_999_999
        with pytest.raises(execution.BoundStop, match="cost cap"):
            budget.admit(60000)
        return
    with pytest.raises(ContractError):
        budget.dispatch(req, 60000)
    assert group.generations == 0


@pytest.mark.parametrize("oracle_pass", [True, False])
def test_two_edits_rechecks_finish_and_public_review_precedes_both_assessments(
    source, tmp_path, oracle_pass
):
    branch, group = prepared(source, tmp_path)
    client = ScriptedClient(edit_steps(two=True))
    observed = []

    def review(ref, packet, deadline):
        assert not any(
            e["event_type"] in {"isort_uptake_terminal_oracle", "evaluator_finished"}
            for e in branch.journal.events()
        )
        assert "SYNTHETIC_ORACLE" not in canonical_json(packet)
        observed.append(ref.content_hash)
        return execution.inert_reviewer(ref, packet, deadline)

    result, probes = run(
        branch, group, client, fixture_evaluation=True, reviewer=review, oracle_pass=oracle_pass
    )
    assert result["result"]["terminal"] == "EVALUATOR_PASS", result
    assert result["accepted_new_edits"] == 2
    assert result["new_generations"] == result["new_counts"] == 4
    assert result["new_tool_actions"] == 4  # Recheck runs only after repair of a failing check.
    events = branch.journal.events()[branch.inherited_events :]
    kinds = [e["event_type"] for e in events]
    assert (
        kinds.index("isort_uptake_U_sealed")
        < kinds.index("isort_uptake_terminal_oracle")
        < kinds.index("evaluator_finished")
    )
    assert kinds.count("submission_recorded") == kinds.count("evaluator_finished") == 1
    oracle = next(e["payload"] for e in events if e["event_type"] == "isort_uptake_terminal_oracle")
    assert oracle["public_behavior"] == ("PASS" if oracle_pass else "FAIL")
    assert oracle["fresh_final_diff_regression"] and oracle["new_accepted_source_change"]
    assert result["public_repair"] == ("PASS" if oracle_pass else "FAIL")
    assert len(observed) == 1
    assert [p.calls for p in probes] == [[], ["uptake_final_public_oracle"]]
    assert "SYNTHETIC_ORACLE" not in json.dumps(client.created)
    assert result["U"] == "NOT_OBSERVABLE"  # A correct inert patch is not semantic linkage.
    assert not result["stop_remaining"]


def test_third_edit_is_not_accepted(source, tmp_path):
    branch, group = prepared(source, tmp_path)
    client = ScriptedClient(edit_steps(two=True, third=True))
    result, _ = run(branch, group, client, fixture_evaluation=True)
    assert result["accepted_new_edits"] == 2
    assert result["result"]["terminal"] != "EVALUATOR_PASS"
    assert result["new_generations"] <= 4


@pytest.mark.parametrize("which", ["solver", "invocation"])
def test_deadline_before_request_has_no_model_or_assessment(source, tmp_path, which):
    branch, group = prepared(source, tmp_path)
    if which == "solver":
        branch.solver_deadline = execution.ExecutionDeadline(group.clock() - 1)
    else:
        group.deadline = execution.ExecutionDeadline(group.clock() - 1)
    client = ScriptedClient(stop_steps())
    result, probes = run(branch, group, client)
    assert not client.counted and not client.created
    assert not any(p.calls for p in probes)
    assert result["U"] != "FAIL"


def test_inherited_limits_and_time_not_reset(source, tmp_path):
    branch, group = prepared(source, tmp_path)
    old = DevJournal(source.root, source.run_id).load_envelope()
    counters = runner._restore_counters(branch.journal)
    assert branch.request.limits.max_model_calls - counters.model_calls == 6
    assert branch.request.limits.max_tool_actions - counters.tool_actions == 18
    assert branch.request.limits.max_accepted_mutations - branch.parent_edits == 2
    assert branch.request.limits.max_protocol_recoveries == 0
    assert branch.request.limits.wall_time_seconds == old.limits.wall_time_seconds
    assert branch.request.evaluation_reserve_seconds == 0
    assert 0 < branch.solver_deadline.remaining_seconds() <= 281
    assert group.deadline.expires_at == group.started + 720
    assert branch.request.repair_recheck == old.repair_recheck is True


def test_u_semantic_grade_accepts_conditional_linkage_without_keyword_rules(source, tmp_path):
    branch, group = prepared(source, tmp_path)

    def review(ref, packet, deadline):
        events = [e for e in packet["public_events"] if e["sequence"] > branch.inherited_events]
        edits = [e for e in events if checkpoint.accepted_edits([e])]
        explanation = next(
            e
            for e in events
            if e["event_type"] == "action_started" and e["payload"]["tool"] == "replace_text"
        )
        return {
            "review_hash": ref.content_hash,
            "U": "PASS",
            "reason": "Fixture reviewer accepts a conditional qualification, not a reversion.",
            "public_event_sequences": [explanation["sequence"], edits[0]["sequence"]],
            "observation_case_ids": ["type_item"],
        }

    result, _ = run(
        branch, group, ScriptedClient(edit_steps()), fixture_evaluation=True, reviewer=review
    )
    assert result["U"] == "PASS" and result["model_uptake"] == "NOT_RUN", result


def test_invalid_u_citations_stop_before_oracle_or_evaluator(source, tmp_path):
    branch, group = prepared(source, tmp_path)

    def review(ref, packet, deadline):
        return {
            "review_hash": ref.content_hash,
            "U": "PASS",
            "reason": "Patch passed.",
            "public_event_sequences": [],
            "observation_case_ids": [],
        }

    result, probes = run(
        branch, group, ScriptedClient(edit_steps()), fixture_evaluation=True, reviewer=review
    )
    assert result["stop_remaining"] and not any(p.calls for p in probes)
    assert not any(e["event_type"] == "evaluator_finished" for e in branch.journal.events())


def test_real_task_guard_denies_target_edits_and_execution(source, tmp_path):
    branch, _ = prepared(source, tmp_path)
    branch.package = branch.package.model_copy(
        update={
            "public": branch.package.public.model_copy(
                update={
                    "repository": branch.package.public.repository.model_copy(
                        update={"url": "https://example.invalid/repo"}
                    )
                }
            )
        }
    )
    with (
        pytest.raises(ContractError, match="outside a provider-free rehearsal"),
        execution.offline_environment(branch, ScriptedClient(edit_steps())),
    ):
        pytest.fail("real target mutation was admitted")


def test_failing_check_triggers_budgeted_automatic_recheck_after_repair(source, tmp_path):
    branch, group = prepared(source, tmp_path)
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    bad = call(
        "replace_text",
        {
            "path": mutation.path,
            "old_text": "csv.reader",
            "new_text": "csv.readerx",
            "occurrence": 1,
            "causal_revision": None,
            "hypothesis": "Inert intentional failure.",
            "expected_behavior": "Fixture check fails.",
        },
        "mutate",
    )
    good = edit_steps()[0][0]
    good["action_id"] = "repair_after_failure"
    good["arguments"]["old_text"] = mutation.old_text.replace("csv.reader", "csv.readerx")
    client = ScriptedClient(
        [
            [bad],
            [call("run_check", {"check_id": "existing-unit-tests"}, "verify")],
            [good],
            [call("finish_task", {}, "finish")],
        ]
    )
    result, _ = run(branch, group, client, fixture_evaluation=True)
    assert result["result"]["terminal"] == "EVALUATOR_PASS", result
    assert result["accepted_new_edits"] == 2
    assert result["new_tool_actions"] == 5 and result["new_generations"] == 4
    events = branch.journal.events()[branch.inherited_events :]
    rechecks = [e for e in events if e["event_type"] == "repair_recheck_finished"]
    assert len(rechecks) == 1 and rechecks[0]["payload"]["passed"]


def test_late_return_settles_but_cannot_execute_tools(source, tmp_path):
    branch, group = prepared(source, tmp_path)
    now = [group.clock()]
    group.clock = lambda: now[0]
    group.deadline = execution.ExecutionDeadline(now[0] + 720, group.clock)
    branch.solver_deadline = execution.ExecutionDeadline(now[0] + 281, group.clock)

    class LateClient(ScriptedClient):
        def create(self, **kwargs):
            value = super().create(**kwargs)
            now[0] += 282
            return value

    client = LateClient(stop_steps())
    result, _ = run(branch, group, client)
    assert result["billing_known"] and result["provisional_cost_nanos"] == 550000
    assert result["new_generations"] == 1 and result["new_tool_actions"] <= 1
    assert not any(
        e["event_type"] == "action_started"
        for e in branch.journal.events()[branch.inherited_events :]
    )


def test_sixth_generation_finish_is_executed_and_count_cap_blocks_seventh(source, tmp_path):
    branch, group = prepared(source, tmp_path)
    # Two reads, two edits using their current postimages, one check, then finish.
    reads = []
    for n in range(2):
        item = call(
            "read_file",
            {"path": "mini_data_utils/csvlite.py", "start_line": 1, "end_line": 90},
            "inspect",
        )
        item["action_id"] = f"fresh_read_{n}"
        reads.append([item])
    result, _ = run(
        branch, group, ScriptedClient([*reads, *edit_steps(two=True)]), fixture_evaluation=True
    )
    assert result["new_counts"] == result["new_generations"] == 6
    assert result["result"]["terminal"] == "EVALUATOR_PASS", result


@pytest.mark.parametrize("failure", ["cleanup_failed", "timed_out", "truncated", "missing"])
def test_terminal_oracle_uncertainty_never_reaches_isolated_evaluator(source, tmp_path, failure):
    branch, group = prepared(source, tmp_path)
    client = ScriptedClient(edit_steps())
    with execution.offline_environment(branch, client, fixture_evaluation=True):
        original = runner.DockerProbeSandbox.run_probe

        def probe(instance, *a, **k):
            receipt = original(instance, *a, **k)
            receipt.update({failure: True} if failure != "missing" else {"stdout": "{}"})
            return receipt

        with patch.object(runner.DockerProbeSandbox, "run_probe", probe):
            result = execution.run_row(
                branch, group, "SYNTHETIC_ORACLE", reviewer=execution.inert_reviewer, client=client
            )
    assert result["stop_remaining"]
    assert not any(e["event_type"] == "evaluator_finished" for e in branch.journal.events())


def test_file_review_deadline_never_fabricates_a_grade(tmp_path):
    ref = ArtifactStore(tmp_path).put_json({"public": True})
    with pytest.raises(execution.BoundStop, match="review exceeded"):
        execution.file_reviewer(tmp_path)(ref, {}, execution.ExecutionDeadline(0, lambda: 1))
    assert (tmp_path / "public-review-ready.json").is_file()
    assert not (tmp_path / "public-grade.json").exists()


@pytest.mark.parametrize("number", [4, 5])
def test_parallel_reads_count_individually_and_reject_fifth(source, tmp_path, number):
    branch, group = prepared(source, tmp_path)
    reads = []
    for n in range(number):
        item = call(
            "read_file",
            {"path": "mini_data_utils/csvlite.py", "start_line": 1, "end_line": 90},
            "inspect",
        )
        item["action_id"] = f"parallel_{n}"
        reads.append(item)
    result, _ = run(branch, group, ScriptedClient([reads, *stop_steps()]))
    assert result["new_tool_actions"] == (5 if number == 4 else 0)
    assert result["result"]["terminal"] == (
        "AGENT_STOPPED" if number == 4 else "PROTOCOL_VIOLATION"
    )


def test_discarded_counts_cannot_fund_a_seventh_or_reuse_old_request(tmp_path):
    budget, group = budget_fixture(tmp_path)
    for _ in range(6):
        budget.counted({"max_output_tokens": 25000}, lambda: 60001)
        assert budget.admit(60001) is None
    assert group.counts == 6 and group.generations == 0
    with pytest.raises(execution.BoundStop, match="call cap"):
        budget.before_count()


def test_terminal_phase_deadlines_are_separate_inside_overall_time(source, tmp_path):
    branch, group = prepared(source, tmp_path)
    client = ScriptedClient(edit_steps())
    evaluation = runner.EvaluationEngine.evaluate
    seen = []

    def evaluate(engine, *a, **k):
        deadline = k["deadline"]
        # Coarse clocks may repeat a tick: (1900.001 + 330) - 1900.001
        # is 330.0000000000002. Compare absolute bounds without subtraction.
        now = deadline.clock()
        assert now < deadline.expires_at <= now + 330
        assert deadline.expires_at <= group.deadline.expires_at
        seen.append("evaluate")
        return evaluation(engine, *a, **k)

    with execution.offline_environment(branch, client, fixture_evaluation=True):
        probe_run = runner.DockerProbeSandbox.run_probe

        def probe(instance, *a, **k):
            deadline = k["deadline"]
            now = deadline.clock()
            assert now < deadline.expires_at <= now + 30
            assert deadline.expires_at <= group.deadline.expires_at
            seen.append("oracle")
            return probe_run(instance, *a, **k)

        with (
            patch.object(runner.EvaluationEngine, "evaluate", evaluate),
            patch.object(runner.DockerProbeSandbox, "run_probe", probe),
        ):
            result = execution.run_row(
                branch, group, "SYNTHETIC_ORACLE", reviewer=execution.inert_reviewer, client=client
            )
    assert seen == ["oracle", "evaluate"], result
    assert result["result"]["terminal"] == "EVALUATOR_PASS", result
