"""Supplied-case lifecycle/replay tests; no provider or candidate code executes."""

from __future__ import annotations

import copy
import json
import socket
import subprocess
from dataclasses import fields, replace
from decimal import Decimal
from types import SimpleNamespace

import pytest
from test_counterexample_review_rollout import Adapter, Checks, action
from test_dev_probes import FakeProbe, probe_call
from test_dev_tools import mutation_call
from test_failure_given_repair_rollout import CaseProbe, dispatch, mock_plan, prepare, reopen
from test_failure_given_repair_rollout import factory as feedback_factory  # noqa: F401

from diagnostics import public_case_lifecycle as lifecycle
from diagnostics import public_case_rollout as rollout
from patchloop.agent.model import ModelTurnError
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.conversation import reconstruct_state
from patchloop.errors import ContractError
from patchloop.sandbox.probes import probe_execution_policy, probe_profile_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json, utc_now

SOURCE = "print(False)\n"


@pytest.fixture
def receipt_fixture():
    case = lifecycle.define_case(
        purpose="Synthetic case",
        inputs={},
        initial_state="empty",
        expected_observables={},
        question="Question",
        python_source=SOURCE,
        provenance={},
        execution_context={
            "probe_image_digest": "test-image",
            "probe_profile_hash": probe_profile_hash(),
        },
    )
    arguments = {"question": "Question", "python_source": SOURCE}
    digest = sha256_json({"tool": "run_probe", "arguments": arguments})
    start = {
        "tool": "run_probe",
        "action_id": "p",
        "arguments": arguments,
        "input_hash": digest,
        "baseline_diff_hash": "diff",
        "execution_identity": {"action_id": "p", "run_id": "run_dev_mock"},
    }
    policy = probe_execution_policy(
        effective_timeout_seconds=30, row_deadline_limited=False, cleanup_status="confirmed"
    )
    result = {
        "tool": "run_probe",
        "action_id": "p",
        "input_hash": digest,
        "workspace_diff_hash": "diff",
        "status": "succeeded",
        "output": {
            "source_hash": case["source_hash"],
            "image_digest": "test-image",
            "profile_hash": probe_profile_hash(),
            "diff_hash": "diff",
            "workspace_diff_hash": "diff",
            "execution_policy": policy,
            "execution_policy_hash": sha256_json(policy),
            "snapshot_hash": "snapshot",
            "status": "passed",
            "exit_code": 0,
            "stdout": "False",
            "stderr": "",
        },
    }
    events = [
        {"event_type": "action_started", "payload": start, "event_hash": "start"},
        {
            "event_type": "action_finished",
            "event_hash": "finished",
            "payload": {"action_id": "p", "input_hash": digest, "result": result},
        },
    ]
    return case, events


def as_branch(branch):
    return rollout.Branch(**{f.name: getattr(branch, f.name) for f in fields(branch)})


def same_case(action_id="case-probe", source=SOURCE, question="Is the result as expected?"):
    return probe_call(action_id).model_copy(
        update={"arguments": {"question": question, "python_source": source}}
    )


class FalseProbe(FakeProbe):
    def __init__(self):
        super().__init__(status="passed")

    def run_probe(self, *args, **kwargs):
        result = super().run_probe(*args, **kwargs)
        result["stdout"] = "False\n"
        return result


@pytest.fixture
def factory(request):
    make = request.getfixturevalue("feedback_factory")

    def create(label="B1", **kwargs):
        branch = as_branch(make(label, **kwargs))
        branch.gateway.probe_sandbox = FalseProbe()
        identity = branch.gateway.probe_sandbox.preflight()
        branch.bind_case(
            lifecycle.define_case(
                purpose="Synthetic public behavior",
                inputs={"value": False},
                initial_state="Empty public fixture",
                expected_observables={"stdout": "True"},
                question="Is the result as expected?",
                python_source=SOURCE,
                provenance={"origin": "synthetic_public_fixture"},
                execution_context={
                    "public_task_hash": sha256_json(
                        branch.gateway.public_task.model_dump(mode="json")
                    ),
                    "probe_image_digest": identity["image_digest"],
                    "probe_profile_hash": identity["profile_hash"],
                },
            )
        )
        return branch

    return create


def current(branch):
    request = prepare(branch)[1]
    return reconstruct_state(request["input"]), request


def state_from_events(branch, events, diff=None):
    return lifecycle.status(
        branch.case(),
        lifecycle.observations(branch.case(), events),
        diff or branch.gateway.current_diff_hash,
    )


def test_control_and_treatment_share_definition_only_declared_paths_differ(factory):
    branch = factory("A1", checked=True)
    state, control = current(branch)
    treated, overlay, _ = lifecycle.add_case(control, branch.case(), [], treatment=True)
    new = reconstruct_state(treated["input"])
    assert treated["input"][:-1] == control["input"][:-1]
    assert {k for k in new if new[k] != state.get(k)} == {lifecycle.STATUS, "completion_guidance"}
    assert new[lifecycle.DEFINITION] == state[lifecycle.DEFINITION] == branch.case()
    assert new[lifecycle.STATUS]["state"] == "no_current_result"
    assert new["completion_guidance"]["next_action"] == {"tool": "run_probe"}
    assert new["current_public_failure"] is None
    assert new["working_notes"] == state["working_notes"]
    assert branch.new_provider_calls == branch.new_tools == branch.new_cost_nanos == 0
    assert overlay[lifecycle.STATUS]["behavior_verdict"] == "NOT_ASSESSED"
    assert "current_candidate_feedback" not in canonical_json(treated)


def test_false_output_is_completed_not_pass_and_body_delivered_only_once(factory):
    branch = factory(checked=True)
    first = dispatch(branch, [same_case()])
    state, second = current(as_branch(reopen(branch)))
    issue = state[lifecycle.STATUS]
    assert (
        issue["state"] == "current_result_available" and issue["behavior_verdict"] == "NOT_ASSESSED"
    )
    assert issue["current_result"]["delivery"]["kind"] == "native_function_call_output"
    assert "run_probe" not in state["completion_guidance"]["message"]
    assert state["completion_guidance"]["next_action"] == {"tool": "finish_task"}
    assert "python_source" not in state[lifecycle.DEFINITION]
    delivery = state[lifecycle.DEFINITION]["delivery"]
    delivered = second["input"][delivery["input_item_index"]]
    assert sha256_json(delivered) == delivery["item_hash"]
    assert json.loads(delivered["content"])["state"][lifecycle.DEFINITION] == branch.case()
    assert second["input"][: len(first["input"])] == first["input"]
    assert sum(i.get("encrypted_content") == "cipher-case-probe" for i in second["input"]) == 1
    assert len(branch._new_events("public_case_result_bound")) == 1
    assert branch.gateway.probe_sandbox.calls == 1
    assert "False" not in canonical_json(issue)  # No duplicated stdout/source in status.
    ref = Artifact.model_validate(branch._new_events("turn_started")[-1]["context_artifact"])
    assert json.loads(branch.store.read_bytes(ref))[lifecycle.STATUS] == issue


def test_source_fallback_never_fabricates_delivery_reference(factory):
    branch = factory()
    state, request = current(branch)
    delivered, diagnostic = lifecycle.definition_delivery(
        branch.case(), request["input"], previously_projected=True
    )
    assert delivered == branch.case() and diagnostic == "definition_delivery_not_restored"
    # A damaged old inline definition cannot be used as a backward reference.
    request["input"].append(copy.deepcopy(request["input"][-1]))
    view = json.loads(request["input"][-2]["content"])
    view["state"][lifecycle.DEFINITION]["python_source"] = "print('different')"
    request["input"][-2]["content"] = canonical_json(view)
    delivered, diagnostic = lifecycle.definition_delivery(
        branch.case(), request["input"], previously_projected=True
    )
    assert delivered == branch.case() and diagnostic is not None
    assert state[lifecycle.STATUS]["current_result"] is None


@pytest.mark.parametrize(
    "change",
    [
        {"status": "failed", "exit_code": 1},
        {"status": "timeout", "timed_out": True},
        {"status": "output_limit", "truncated": True},
        {"truncated": True},
        {"snapshot_hash": None},
    ],
)
def test_incomplete_execution_never_becomes_case_success(receipt_fixture, change):
    case, events = receipt_fixture
    event = next(e for e in reversed(events) if e["event_type"] == "action_finished")
    event["payload"]["result"]["output"].update(change)
    issue = lifecycle.status(case, lifecycle.observations(case, events), "diff")
    assert issue["state"] == "execution_incomplete" and issue["behavior_verdict"] == "NOT_ASSESSED"


def test_exact_source_not_question_and_unrelated_newer_probe_does_not_evict(factory):
    branch = factory(checked=True)
    dispatch(branch, [same_case("other", source=SOURCE + "\n")])
    assert current(branch)[0][lifecycle.STATUS]["state"] == "no_current_result"
    dispatch(branch, [same_case("matching", question="Different wording, identical code.")])
    dispatch(branch, [same_case("unrelated", source="print(True)\n")])
    state, _ = current(branch)
    assert state[lifecycle.STATUS]["current_result"]["action_id"] == "matching"
    assert len(branch.case_rows()) == 1 and branch.gateway.probe_sandbox.calls == 3


def test_edit_historical_rollback_currency_and_replay_are_deterministic(factory):
    branch = factory()
    dispatch(branch, [same_case("before")])
    old_diff = branch.gateway.current_diff_hash
    dispatch(branch, [mutation_call(branch.gateway)])
    state, _ = current(as_branch(reopen(branch)))
    assert state[lifecycle.STATUS]["state"] == "no_current_result"
    assert state[lifecycle.STATUS]["last_historical_result"]["diff_hash"] == old_diff
    dispatch(branch, [same_case("after")])
    baseline = branch.gateway.current_diff_hash
    edit = mutation_call(branch.gateway, action_id="rejected")
    rejected = edit.model_copy(
        update={
            "arguments": {
                **edit.arguments,
                "old_text": edit.arguments["new_text"],
                "new_text": "# too big\n" * 100,
            }
        }
    )
    dispatch(branch, [rejected])
    state, _ = current(as_branch(reopen(branch)))
    assert branch.gateway.current_diff_hash == baseline
    assert state[lifecycle.STATUS]["current_result"]["action_id"] == "after"
    assert len(branch._new_events("public_case_result_bound")) == 2
    assert (
        state_from_events(branch, branch.journal.events(), old_diff)["current_result"]["action_id"]
        == "before"
    )  # Returning to exact baseline restores that result's currency.


@pytest.mark.parametrize("bad", ["input", "receipt_source", "diff", "environment", "policy"])
def test_receipt_integrity_errors_are_not_unobserved_or_pass(receipt_fixture, bad):
    case, events = receipt_fixture
    start = next(
        e["payload"]
        for e in events
        if e["event_type"] == "action_started" and e["payload"]["tool"] == "run_probe"
    )
    result = next(
        e["payload"]["result"]
        for e in events
        if e["event_type"] == "action_finished" and e["payload"]["result"]["tool"] == "run_probe"
    )
    if bad == "input":
        start["arguments"]["python_source"] = "other"
    else:
        key = {
            "receipt_source": "source_hash",
            "diff": "diff_hash",
            "environment": "image_digest",
            "policy": "execution_policy_hash",
        }[bad]
        result["output"][key] = "bad"
    with pytest.raises(ContractError):
        lifecycle.observations(case, events)


@pytest.mark.parametrize(
    "fault,code",
    [
        ("dispatch_recorded", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("provider_returned", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("usage_recorded", "PROVIDER_CONTINUATION_ERROR"),
        ("decision_recorded", None),
        ("actions_finished", None),
        ("batch_finished", None),
    ],
)
def test_crash_replay_never_duplicates_provider_or_probe(factory, fault, code):
    branch = factory(checked=True)
    adapter = Adapter([same_case()])

    def crash(point):
        if point == fault:
            raise RuntimeError("crash")

    with pytest.raises(RuntimeError, match="crash"):
        dispatch(branch, adapter=adapter, checkpoint=crash)
    restored = as_branch(reopen(branch))
    calls_before = list(adapter.sequence)
    if code:
        with pytest.raises(rollout.native.engine.AbortExperiment) as error:
            current(restored)
        assert error.value.code == code and branch.gateway.probe_sandbox.calls == 0
    else:
        state, _ = current(restored)
        assert state[lifecycle.STATUS]["state"] == "current_result_available"
        assert restored.new_provider_calls == restored.new_tools == 1
        again, _ = current(as_branch(reopen(restored)))
        assert again[lifecycle.STATUS] == state[lifecycle.STATUS]
        assert branch.gateway.probe_sandbox.calls == 1
        assert len(branch._new_events("public_case_result_bound")) == 1
    assert adapter.sequence == calls_before


@pytest.mark.parametrize("corrupt", ["definition", "result"])
def test_corrupt_case_artifact_blocks_pending_mutation(factory, corrupt):
    branch = factory()
    if corrupt == "result":
        dispatch(branch, [same_case()])

    def crash(point):
        if point == "decision_recorded":
            raise RuntimeError("crash")

    with pytest.raises(RuntimeError):
        dispatch(branch, [mutation_call(branch.gateway)], checkpoint=crash)
    binding = branch._new_events(
        "public_case_bound" if corrupt == "definition" else "public_case_result_bound"
    )[0]
    ref = Artifact.model_validate(binding[f"{corrupt}_artifact"])
    with open(ref.path, "wb") as stream:
        stream.write(b"tampered")
    with pytest.raises(rollout.native.engine.AbortExperiment) as error:
        current(as_branch(reopen(branch)))
    assert error.value.code == "PUBLIC_CASE_EVIDENCE_ERROR"
    assert branch.gateway.accepted_mutations == 0


def test_correction_replays_cipher_without_plaintext_or_new_case_execution(factory):
    class Incomplete(Adapter):
        def execute_request(self, *args, **kwargs):
            return replace(
                super().execute_request(*args, **kwargs),
                output_item_types=("reasoning",),
                response_status="incomplete",
                response_incomplete_reason="max_output_tokens",
                error=ModelTurnError("incomplete_response", "RAW_REASONING_SENTINEL"),
            )

    branch = factory()
    dispatch(branch, adapter=Incomplete([]))
    state, request = current(as_branch(reopen(branch)))
    assert "max_output_tokens" in request["input"][-1]["content"]
    assert state[lifecycle.STATUS]["state"] == "no_current_result"
    assert sum(i.get("encrypted_content") == "cipher-incomplete" for i in request["input"]) == 1
    assert "RAW_REASONING_SENTINEL" not in canonical_json(request) + branch.journal.path.read_text()


@pytest.mark.parametrize(
    "ready,tools,next_tool",
    [
        (False, ["replace_text", "run_probe"], "replace_text"),
        (False, ["run_check", "run_probe"], "run_check"),
        (True, ["finish_task", "run_probe"], "run_probe"),
        (True, ["finish_task"], "finish_task"),
    ],
)
def test_guidance_keeps_required_priorities_and_actual_tools(ready, tools, next_tool):
    state = {
        "available_tool_names": tools,
        "completion_guidance": {
            "submission_ready": ready,
            "next_action": {"tool": tools[0]},
            "message": "original",
        },
    }
    value = lifecycle.completion_guidance(state, {"state": "no_current_result"})
    assert value["next_action"]["tool"] == next_tool
    if not ready:
        assert value == state["completion_guidance"]
    if "run_probe" not in tools:
        assert "run_probe" not in value["message"]


def test_check_pass_and_resolved_concern_do_not_observe_case_or_require_probe(factory):
    branch = factory(checked=True)
    state, request = current(branch)
    state["working_notes"]["verification"] = {"concerns": [{"status": "resolved"}]}
    view = json.loads(request["input"][-1]["content"])
    view["state"]["working_notes"] = state["working_notes"]
    request["input"][-1]["content"] = canonical_json(view)
    changed = lifecycle.add_case(request, branch.case(), [], treatment=True)[0]
    assert reconstruct_state(changed["input"])[lifecycle.STATUS]["state"] == "no_current_result"
    dispatch(branch, [action("finish_task", "finish")])
    assert branch.terminal["terminal"] == "PUBLIC_CHECKS_SUBMITTED"
    before = branch.journal.path.read_bytes()
    assert prepare(as_branch(reopen(branch))) is None
    assert before == branch.journal.path.read_bytes() and branch.gateway.probe_sandbox.calls == 0


def test_cli_summary_does_not_reveal_labeled_candidate_or_case_verdicts():
    result = {
        "terminal": "ROLLOUTS_COMPLETED",
        "official": False,
        "branches": [{"branch": "B2", "submitted_artifact": "secret-until-review"}],
        "operator_case_audits": [{"branch": "B2", "case_outcome": "PASS"}],
    }
    assert rollout.public_execution_summary(result) == {
        "terminal": "ROLLOUTS_COMPLETED",
        "official": False,
    }


def test_four_arm_mock_repair_check_optional_case_finish_and_separate_audit(
    factory,
    tmp_path,
    monkeypatch,
):
    packet = tmp_path / "packet"
    packet.mkdir()
    (packet / "plan.json").write_bytes(b"{}")
    branches = {label: factory(label, checked=True) for label in rollout.ORDER}
    plan = mock_plan(branches["A1"])
    plan.verification_source = SOURCE
    monkeypatch.setattr(rollout, "validate", lambda _: (plan, {}))
    monkeypatch.setattr(rollout, "initialize_branch", lambda p, label, *a: branches[label])

    def forbidden(*args, **kwargs):
        pytest.fail("live access during mock")

    monkeypatch.setattr(rollout.feedback, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(rollout.native.loop, "_live_source_preflight", forbidden)
    monkeypatch.setattr(rollout.native.loop, "_live_sandbox_preflight", forbidden)
    repair = mutation_call(branches["B1"].gateway, action_id="repair")
    repair = repair.model_copy(
        update={
            "arguments": {
                **repair.arguments,
                "old_text": repair.arguments["new_text"],
                "new_text": repair.arguments["new_text"] + "  # revised",
            }
        }
    )
    calls = iter(
        [
            action("finish_task", "a-finish"),
            repair,
            same_case("b2-probe"),
            action("finish_task", "a2-finish"),
            action("run_check", "repair-check", check_id="existing-unit-tests"),
            action("finish_task", "b2-finish"),
            same_case("b1-probe"),
            action("finish_task", "b1-finish"),
        ]
    )
    args = dict(
        approval_packet_hash=sha256_bytes(b"{}"),
        credential_file=rollout.repository_root() / ".env",
        cap=rollout.TOTAL_CAP,
        pricing_verified_on=utc_now().date().isoformat(),
        sandbox=Checks(),
        probe=CaseProbe(plan.report),
        adapter_factory=lambda _: Adapter([next(calls)]),
    )
    destination = tmp_path / "result"
    result = rollout.run(packet, destination, **args)
    assert result["terminal"] == "ROLLOUTS_COMPLETED" and result["provider_free"]
    assert result["new_provider_calls"] == result["new_tool_actions"] == 8
    assert args["probe"].calls == 2 and len(result["operator_case_audits"]) == 4
    assert branches["B1"].terminal["accepted_mutations_since_checkpoint"] == 1
    assert all(
        r["case_outcome"] == "FAIL" and not r["agent_credit"]
        for r in result["operator_case_audits"]
    )
    assert [b.gateway.probe_sandbox.calls for b in branches.values()] == [0, 1, 1, 0]
    assert all(
        lifecycle.status(b.case(), b.case_rows(), b.gateway.current_diff_hash)["behavior_verdict"]
        == "NOT_ASSESSED"
        for b in branches.values()
    )
    assert result["task_acceptance"] == "NOT_RUN" and not result["official"]
    with pytest.raises(ContractError, match="fresh disjoint"):
        rollout.run(packet, destination, **args)


@pytest.mark.parametrize(
    "failure,expected",
    [
        ("count", "COUNT_TIMEOUT_OR_UNKNOWN"),
        ("create", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("billing", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
    ],
)
def test_uncertainty_precedes_case_corruption_and_stops_other_conditions(
    factory, failure, expected
):
    branches = [factory(label, checked=True) for label in ("A1", "B1")]
    adapters = []

    def make(_):
        adapter = Adapter(
            [action("finish_task", "finish")], failure=failure, mismatch=failure == "billing"
        )
        adapters.append(adapter)
        return adapter

    result = rollout.native.drive(
        mock_plan(branches[0]),
        branches,
        make,
        branch_cap=rollout.BRANCH_CAP,
        total_cap=rollout.TOTAL_CAP,
    )
    assert result["terminal"] == expected and len(adapters) == 1
    assert branches[1].new_provider_calls == 0
    assert all(b.gateway.probe_sandbox.calls == 0 for b in branches)
    # Explicitly leave the same uncertainty in a nonterminal diagnostic, then corrupt
    # its definition: integrity handling must not hide the billing/count unknown.
    damaged = as_branch(reopen(branches[0]))
    ref = Artifact.model_validate(
        damaged._new_events("public_case_bound")[0]["definition_artifact"]
    )
    with open(ref.path, "wb") as stream:
        stream.write(b"tampered")
    assert rollout.native.uncertainty([damaged]) == expected


def test_nontransferable_caps_reserve_full_25000_output(factory):
    class Costly(Adapter):
        def count_input_tokens_v2(self, request, **kwargs):
            self.count = 200000
            return super().count_input_tokens_v2(request, **kwargs)

        def execute_request(self, *args, **kwargs):
            return replace(super().execute_request(*args, **kwargs), output_tokens=25000)

    branches = [factory(label, checked=True) for label in rollout.ORDER]
    requests = []
    order = iter(["A1", "B1", "B2", "A2", "A1", "A1", "A1"])

    def make(_):
        label = next(order)
        adapter = Costly(
            [
                same_case("p" + str(len(requests)))
                if label == "A1"
                else action("finish_task", "finish")
            ]
        )
        requests.append(adapter)
        return adapter

    result = rollout.native.drive(
        mock_plan(branches[0]),
        branches,
        make,
        branch_cap=rollout.BRANCH_CAP,
        total_cap=rollout.TOTAL_CAP,
    )
    assert result["terminal"] == "ROLLOUTS_COMPLETED"
    assert branches[0].terminal["terminal"] == "COST_CAP_REACHED"
    assert branches[0].new_provider_calls == 3
    assert branches[0].new_cost_nanos == 787500000
    assert result["new_provider_calls"] == 6 and result["new_input_count_calls"] == 7
    assert all(
        e["output_ceiling"] == 25000
        for b in branches
        for e in b._new_events("provider_call_started")
    )


@pytest.mark.parametrize("bad", ["packet", "cap", "credential", "date"])
def test_bad_execution_inputs_never_load_keys_or_create_result(tmp_path, monkeypatch, bad):
    packet = tmp_path / "packet"
    packet.mkdir()
    (packet / "plan.json").write_bytes(b"{}")
    monkeypatch.setattr(rollout, "validate", lambda _: (SimpleNamespace(), {}))
    args = dict(
        approval_packet_hash=sha256_bytes(b"{}"),
        cap=rollout.TOTAL_CAP,
        credential_file=rollout.repository_root() / ".env",
        pricing_verified_on=utc_now().date().isoformat(),
    )
    key, value = {
        "packet": ("approval_packet_hash", "bad"),
        "cap": ("cap", Decimal("2")),
        "credential": ("credential_file", tmp_path / ".env"),
        "date": ("pricing_verified_on", "2000-01-01"),
    }[bad]
    args[key] = value
    with pytest.raises(ContractError):
        rollout.run(
            packet,
            tmp_path / "result",
            **args,
            adapter_factory=lambda _: pytest.fail("provider admitted"),
        )
    assert not (tmp_path / "result").exists()


def test_result_cannot_be_created_inside_frozen_source_experiment(tmp_path, monkeypatch):
    monkeypatch.setattr(rollout.checkpoint.design, "SOURCE", tmp_path)
    monkeypatch.setattr(rollout.feedback, "execute_packet", lambda *a, **k: pytest.fail("admitted"))
    with pytest.raises(ContractError, match="fresh disjoint"):
        rollout.run(tmp_path / "packet", tmp_path / "sibling")


@pytest.mark.parametrize("source", ["", "x" * 8001])
def test_case_source_bound_does_not_expand_probe_schema(source):
    with pytest.raises(ContractError, match="source exceeds"):
        lifecycle.define_case(
            purpose="case",
            inputs={},
            initial_state="",
            expected_observables={},
            question="question",
            python_source=source,
            provenance={},
            execution_context={},
        )


@pytest.mark.skipif(not rollout.DESIGN.exists(), reason="local frozen design unavailable")
def test_real_checkpoint_frozen_inputs_and_no_call_reconstruction(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("provider/key/network/candidate execution during preparation")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(rollout.feedback, "load_exact_openai_api_key", forbidden)
    saved = json.loads((rollout.checkpoint.DESIGN / "packet.json").read_bytes())
    if saved["runtime_hash"] != rollout.checkpoint.design.seed.runtime_content_hash():
        with monkeypatch.context() as scoped:
            scoped.setattr(subprocess, "Popen", forbidden)
            with pytest.raises(ValueError, match="source runtime/config mismatch"):
                rollout.load_plan()
        return
    with monkeypatch.context() as scoped:
        scoped.setattr(subprocess, "Popen", forbidden)
        plan = rollout.load_plan()
        envelope = rollout.prepare(tmp_path / "packet")
        assert rollout.validate(tmp_path / "packet")[1] == envelope
    assert envelope["cap_usd_each"] == "1.00" and envelope["cap_usd_total"] == "4.00"
    assert not envelope["paid_execution_authorized"]
    for label in ("A1", "B1"):
        checks, probe = Checks(), FakeProbe()
        branch = rollout.initialize_branch(
            plan, label, tmp_path / "branches", checks, probe, ExecutionDeadline.from_remaining(90)
        )
        state, request = current(branch)
        assert request == plan.arms[label[0]]
        assert branch.counters.model_calls == 24 and branch.counters.tool_actions == 25
        assert branch.gateway.accepted_mutations == branch.inherited_accepted_mutations == 3
        assert branch.new_provider_calls == branch.new_tools == branch.new_cost_nanos == 0
        assert checks.calls == [] and probe.calls == 0
        assert state["working_notes"] == plan.state["working_notes"]
        assert state["visible_check_status"] == plan.state["visible_check_status"]
        assert state[lifecycle.DEFINITION] == plan.case
        assert len(plan.case["python_source"]) == 3222
        assert request["input"][:-1] == plan.seed_request["input"][:-1]
        assert rollout.checkpoint.design.FIELD not in state
        assert "private_spec" not in canonical_json(plan.case)
        assert (
            lifecycle.STATUS not in state
            if label[0] == "A"
            else (state[lifecycle.STATUS]["state"] == "no_current_result")
        )
