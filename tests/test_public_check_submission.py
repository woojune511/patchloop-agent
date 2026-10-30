"""Public-check submission keeps original observations advisory and verdicts external."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest
from test_dev_completion_resources import Gateway, counters
from test_dev_probe_cases import TEXT, ExecutingProbe
from test_dev_tools import mutation_call, read_calls
from test_finish_reproduction import checks, finish, finish_call, mutate, request, results_for
from test_finish_reproduction_budget import snapshot
from test_probe_purpose import probe
from test_required_public_checks import PublicSandbox

from patchloop.dev import repair_context, runner, thin_policy
from patchloop.dev import tools as tool_module
from patchloop.dev.contracts import DevLimits, DevModelTurn, RequestedTool
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ResumeContractMismatch

POLICY = "public-checks-v1"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("submission policy tests must not call providers or network")

    monkeypatch.setattr("socket.socket.connect", forbidden)


def gateway_for(gateway_factory, *, sandbox=None):
    old, journal, workspace = gateway_factory(sandbox=sandbox)
    backend = ExecutingProbe()
    gateway = DevToolGateway(
        workspace=workspace, public_task=old.public_task, journal=journal,
        sandbox=old.sandbox, limits=old.limits, probe_sandbox=backend,
        reproduction_acquisition="bounded-v1", verification_policy=POLICY,
    )
    return gateway, journal, backend


def malformed(task):
    call = probe(task, "malformed", source=(
        f"value = observed_target()({TEXT!r}).value\n"
        "record_observation({'actual': value})\n"
    ))
    call.arguments["purpose"]["expected_json"] = '{"expected": true}'
    call.arguments["purpose"]["reported_failure_json"] = '{"expected": false}'
    return call


def test_policy_has_distinct_identity_and_legacy_default_wire(tmp_path):
    legacy = request(tmp_path)
    public = legacy.model_copy(update={"verification_policy": POLICY})
    assert "verification_policy" not in legacy.model_dump(mode="json")
    assert public.model_dump(mode="json")["verification_policy"] == POLICY
    assert runner._model_hash(legacy, None) != runner._model_hash(public, None)
    for mode in ("current", "thin"):
        prompt = thin_policy.system_prompt(mode, verification_policy=POLICY)
        assert prompt != thin_policy.system_prompt(mode)
        assert "No original replay is automatically started" in prompt
    state = {"completion_guidance": {"verification_policy": POLICY}}
    assert "required current-diff public checks determine submission eligibility" in (
        repair_context.system_prompt(state))


@pytest.mark.parametrize("agent_policy", ["current", "thin"])
def test_finish_description_matches_policy_without_changing_action_contract(agent_policy):
    def schema(**kwargs):
        return tool_module.dev_tool_schemas(
            finish_enabled=True, allowed_tools=["finish_task"],
            agent_policy=agent_policy, **kwargs,
        )[0]

    strict = schema(verification_policy="reproduction-gated-v1")
    public = schema(verification_policy=POLICY)
    assert schema() == strict
    assert strict["name"] == public["name"] == "finish_task"
    assert {key: value for key, value in strict.items() if key != "description"} == {
        key: value for key, value in public.items() if key != "description"
    }
    assert "The host replays stale original-case invocations before submission" in (
        strict["description"])
    assert "current mismatch/conflict returns to repair" in strict["description"]
    assert "No original replay is automatically started at submission" in public["description"]
    assert "optional diagnostics, not submission prerequisites" in public["description"]
    assert "The host replays stale original-case" not in public["description"]
    for description in (strict["description"], public["description"]):
        assert "required visible checks pass on the current diff" in description
        assert "Missing/incomplete evidence is labelled unverified" in description


def test_malformed_observation_does_not_poison_later_valid_case_or_finish(gateway_factory):
    gateway, journal, backend = gateway_for(gateway_factory)
    first = gateway.execute(malformed(gateway.public_task))
    assert first.output["reproduction"]["declared_failure_comparison"] == "not_compared"
    assert first.output["reproduction"]["reason"] == "observation_shape_mismatch"
    gateway.execute(probe(gateway.public_task))
    mutate(gateway)
    gateway.execute(probe(gateway.public_task, "bad-current", replay="malformed"))
    gateway.execute(probe(gateway.public_task, "good-current", replay="original"))
    checks(gateway)
    before = gateway.completion_verification(diff_hash=gateway.current_diff_hash)
    assert before["status"] == "unverified"
    assert any(case["status"] == "verified" for case in before["cases"])
    calls = backend.calls
    result, _ = finish(gateway)
    assert result.status == "succeeded", result
    assert result.output["delivery_state"] == "unverified_delivery"
    assert result.output["submission_verification"] == before
    assert backend.calls == calls
    assert not any(e["event_type"] == "completion_reproduction_started" for e in journal.events())


def test_valid_current_failure_is_retained_without_claiming_verification(gateway_factory):
    gateway, _, backend = gateway_for(gateway_factory)
    baseline = gateway.execute(probe(gateway.public_task))
    assert baseline.output["reproduction"]["declared_failure_comparison"] == "matched"
    mutate(gateway, correct=False)
    current = gateway.execute(probe(gateway.public_task, "still-fails", replay="original"))
    assert current.output["reproduction"]["declared_failure_comparison"] == "matched"
    checks(gateway)
    calls = backend.calls
    result, _ = finish(gateway)
    assert result.status == "succeeded", result
    assert result.output["delivery_state"] == "unverified_delivery"
    assert result.output["submission_verification"]["status"] == "refuted"
    assert result.output["original_verification"]["status"] != "verified"
    assert backend.calls == calls


@pytest.mark.parametrize("status", ["NOT_RUN", "FAIL"])
def test_public_checks_remain_required_for_current_candidate(gateway_factory, status):
    sandbox = PublicSandbox()
    gateway, _, _ = gateway_for(gateway_factory, sandbox=sandbox)
    mutate(gateway)
    if status == "FAIL":
        sandbox.passed = False
        result = gateway.execute(RequestedTool(name="run_check", action_id="public-fail",
            arguments={"check_id": gateway.public_task.visible_checks[0].id}))
        assert result.output["passed"] is False
    assert gateway.visible_check_status()[0]["status"] == status
    assert not gateway.ready_to_submit()
    result = gateway.execute(finish_call())
    assert result.status == "failed"
    assert "visible checks" in result.message


def test_a_new_candidate_cannot_reuse_old_public_pass(gateway_factory):
    gateway, _, _ = gateway_for(gateway_factory)
    change = mutate(gateway)
    checks(gateway)
    gateway.execute(read_calls()[1].model_copy(update={"action_id": "read-new-source"}))
    edit = mutation_call(gateway, action_id="new-candidate")
    edit.arguments.update(old_text=change.arguments["new_text"],
                          new_text=change.arguments["new_text"] + "\n# another candidate\n")
    assert gateway.execute(edit).status == "succeeded"
    assert gateway.visible_check_status()[0]["status"] == "NOT_RUN"
    assert gateway.execute(finish_call()).status == "failed"


@pytest.mark.parametrize("status", ["pending", "refuted"])
def test_ready_finish_needs_no_original_replay_or_repair_reservation(status):
    gateway = Gateway(("PASS",), initial=False)
    gateway.verification_policy = POLICY
    state = snapshot(gateway, status=status, case_count=4, pending_count=4)
    selected = runner._tool_policy(
        gateway, counters(model=1, tools=1), DevLimits(), snapshot=state,
        repair_recheck=False, _preview_inspection=False,
    )
    assert "finish_task" in selected.allowed_tools
    assert selected.minimum_completion_calls == selected.minimum_completion_tool_actions == 1
    guidance = runner._completion_guidance(state, selected)
    assert guidance["submission_ready"] is True
    assert guidance["stage"] != "needs_mutation"
    assert guidance["submission_rule"]
    thin = thin_policy.project_state({"completion_guidance": guidance}, "thin")
    assert thin["completion_guidance"]["submission_rule"] == guidance["submission_rule"]
    assert state.completion_verification["status"] == status


def test_blocked_diagnostics_keep_edit_and_finish_without_extra_reserves():
    gateway = Gateway(("PASS",), initial=False)
    gateway.verification_policy = POLICY
    clean = snapshot(gateway, status="pending", case_count=4, pending_count=4)
    blocked = replace(clean, completion_verification={
        **clean.completion_verification,
        "observation_correction": {"blocked": True, "status": "pending"},
        "helper_correction": {"blocked": True, "status": "needs_helper_correction"},
        "repair_path": {"blocked": True, "status": "needs_path_diagnosis"},
        "repair_prediction": {"status": "needs_test_comparison"},
        "first_observation": {"available": True, "blocked": True},
    })
    policies = [runner._tool_policy(
        gateway, counters(model=3, tools=3), DevLimits(), snapshot=state,
        repair_recheck=False, _preview_inspection=False,
    ) for state in (clean, blocked)]
    assert {"replace_text", "finish_task"} <= policies[1].allowed_tools
    for field in ("minimum_completion_calls", "minimum_completion_tool_actions",
                  "completion_budget_calls", "completion_budget_tool_actions",
                  "optional_mutation_completion_calls",
                  "optional_mutation_completion_tool_actions"):
        assert getattr(policies[1], field) == getattr(policies[0], field), field
    assert policies[1].minimum_completion_calls == 1
    assert blocked.completion_verification["observation_correction"]["blocked"]


def test_gateway_edit_and_finish_bypass_diagnostic_validation_only(gateway_factory, monkeypatch):
    gateway, _, backend = gateway_for(gateway_factory, sandbox=PublicSandbox())
    review = gateway.completion_verification
    correction_review = tool_module.observation_correction.review

    def blocked_correction(*args, **kwargs):
        return {**correction_review(*args, **kwargs), "blocked": True, "status": "pending"}

    def blocked_review(*args, **kwargs):
        return {**review(*args, **kwargs), "status": "refuted",
                "repair_path": {"blocked": True, "status": "needs_path_diagnosis"},
                "repair_prediction": {"status": "needs_test_comparison"},
                "helper_correction": {"blocked": True, "status": "needs_helper_correction"}}

    def forbidden(*args, **kwargs):
        pytest.fail("advisory diagnostic validation must not gate edit or finish")

    monkeypatch.setattr(tool_module.observation_correction, "review", blocked_correction)
    monkeypatch.setattr(gateway, "completion_verification", blocked_review)
    monkeypatch.setattr(tool_module.repair_path, "validate", forbidden)
    monkeypatch.setattr(tool_module.repair_prediction, "admit", forbidden)
    monkeypatch.setattr(tool_module.helper_recovery, "validate", forbidden)
    mutate(gateway)
    checks(gateway)
    result = gateway.execute(finish_call())
    assert result.status == "succeeded", result
    assert result.output["delivery_state"] == "unverified_delivery"
    evidence = result.output["submission_verification"]
    assert all(evidence[key]["blocked"] for key in (
        "observation_correction", "repair_path", "helper_correction"))
    assert backend.calls == 0


def test_pending_acquisition_does_not_force_a_probe_before_edit(gateway_factory):
    gateway, _, backend = gateway_for(gateway_factory)
    mutate(gateway)
    checks(gateway)
    result, _ = finish(gateway)
    assert result.status == "succeeded", result
    assert result.output["delivery_state"] == "unverified_delivery"
    assert backend.calls == 0


def test_unknown_physical_dispatch_still_aborts_without_reexecution(gateway_factory):
    gateway, _, _ = gateway_for(gateway_factory)

    class UncertainBackend(ExecutingProbe):
        def run_probe(self, *args, **kwargs):
            super().run_probe(*args, **kwargs)
            raise RuntimeError("local fixture lost its completion receipt")

    backend = gateway.probe_sandbox = UncertainBackend()
    call = probe(gateway.public_task)
    result = gateway.execute(call)
    assert result.error_code == "RECOVERY_ERROR"
    assert runner._batch_execution_abort([result])[0].value == "TASK_FAILED"
    assert gateway.execute(call).replayed
    assert backend.calls == 1


def test_finish_recovery_reuses_receipt_and_keeps_positive_case_evidence(gateway_factory):
    gateway, journal, backend = gateway_for(gateway_factory)
    gateway.execute(probe(gateway.public_task))
    mutate(gateway)
    gateway.execute(probe(gateway.public_task, "fixed", replay="original"))
    checks(gateway)
    result, _ = finish(gateway)
    assert result.status == "succeeded", result
    assert result.output["delivery_state"] == "cases_verified_delivery"
    before = journal.path.read_bytes()
    count = backend.calls
    repeated = gateway.execute(finish_call())
    assert repeated.replayed and repeated.output == result.output
    assert backend.calls == count and journal.path.read_bytes() == before


@pytest.mark.parametrize("correct", [True, False])
def test_advisory_observation_reaches_independent_mock_evaluation(
    tmp_path, monkeypatch, smoke_package, correct,
):
    backend = ExecutingProbe()
    contexts = []
    finish_descriptions = []

    class OriginalThenRepair(MockDevAdapter):
        def __init__(self, task_id):
            super().__init__(task_id)
            self.observed = False
            if not correct:
                self.mutation = replace(self.mutation,
                    new_text=self.mutation.old_text.replace(
                        "    rows: list", "    # fixture-only neutral edit\n    rows: list"))

        def next_turn(self, context, tools):
            contexts.append(context)
            for tool in tools:
                if tool["name"] == "finish_task":
                    finish_descriptions.append(tool["description"])
                    assert "No original replay is automatically started at submission" in (
                        tool["description"])
                    assert "The host replays stale original-case" not in tool["description"]
                    guidance = json.loads(context)["completion_guidance"]
                    assert guidance["verification_policy"] == POLICY
                    assert "No original replay is automatically started at submission" in (
                        guidance["message"])
            if not self.observed:
                self.observed = True
                return DevModelTurn(tool_calls=[malformed(smoke_package.public)])
            return super().next_turn(context, tools)

    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    monkeypatch.setattr(runner, "MockDevAdapter", OriginalThenRepair)
    req = request(tmp_path).model_copy(update={
        "verification_policy": POLICY, "reproduction_acquisition": "bounded-v1",
    })
    run = runner.run_dev(req)["runs"][0]
    expected = "PASS" if correct else "FAIL"
    assert run["terminal"] == f"EVALUATOR_{expected}", run
    assert run["evaluator"]["task_acceptance"] == expected
    assert run["evaluator"]["safety_state"] == "NOT_RUN"
    assert run["delivery_state"] == "unverified_delivery"
    assert backend.calls == 1
    assert finish_descriptions
    assert all("hidden-multiline-csv" not in value for value in contexts)
    assert all("reference_patch" not in value for value in contexts)
    events = DevJournal(tmp_path, run["run_id"]).events()
    assert not any(e["event_type"] == "completion_reproduction_started" for e in events)
    assert len(results_for(DevJournal(tmp_path, run["run_id"]), "finish_task")) == 1
    assert json.loads(contexts[-1])["completion_guidance"]["submission_ready"] is True
    if correct:
        journal = DevJournal(tmp_path, run["run_id"])
        envelope = journal.load_envelope()
        assert envelope.verification_policy == POLICY
        assert envelope.model_dump(mode="json")["verification_policy"] == POLICY
        before = journal.path.read_bytes()
        with pytest.raises(ResumeContractMismatch):
            runner.run_dev(req.model_copy(update={
                "resume_run_id": run["run_id"],
                "verification_policy": "reproduction-gated-v1",
            }))
        assert journal.path.read_bytes() == before
