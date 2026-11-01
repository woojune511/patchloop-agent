"""Explicit verification purpose and a separate observation channel, offline only."""
from __future__ import annotations

import copy
import json

import pytest
from test_dev_probe_action_replay import restore
from test_dev_probe_cases import TEXT, ExecutingProbe, mock_request
from test_dev_tools import mutation_call, read_calls
from test_evidence_recovery import context, intent

from patchloop.dev import probe_invocation, reproduction, runner
from patchloop.dev.contracts import DevModelTurn, RequestedTool
from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.dev.history_evidence import separate
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.state import DevJournal
from patchloop.util import canonical_json, sha256_bytes

SOURCE = (
    "print('progress before: not a JSON document', flush=True)\n"
    f"record_observation(observed_target()({TEXT!r}).value)\n"
    "print('progress after', flush=True)\n"
)
REPORTED_FAILURE = [["h", "v"], ["first"], ['second"', "x"]]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("probe-purpose tests are local and must not use the network")
    monkeypatch.setattr("socket.socket.connect", forbidden)


def original_intent(task, **changes):
    fields = {key: value for key, value in intent(task).items() if key != "requirement_quote"}
    return {**fields, "reported_failure_json": json.dumps(REPORTED_FAILURE), **changes}


def probe(task, action="original", *, source=SOURCE, replay=None):
    return RequestedTool(name="run_probe", action_id=action, arguments={
        "question": None if replay else "Does the public parser preserve quoted newlines?",
        "python_source": None if replay else source, "replay_action_id": replay,
        "purpose": None if replay else {"kind": "original_requirement", **original_intent(task)},
    }, turn_decision={"mode": "verify", "basis": "Check the original public requirement."})


def test_same_action_binds_purpose_observation_and_replay_across_handoff(
    gateway_factory, smoke_package,
):
    gateway, journal, workspace = gateway_factory()
    backend = gateway.probe_sandbox = ExecutingProbe()
    source = SOURCE + "\n#" + "x" * (8_000 - len(SOURCE) - 2)
    first = gateway.execute(probe(gateway.public_task, source=source))
    assert first.status == "succeeded", first
    evidence = first.output["reproduction"]
    assert evidence["comparison"] == "mismatched"
    assert evidence["comparison_feedback"]["declared_failure"]["differences"] == []
    assert all(text in first.output["stdout"] for text in ("progress before", "progress after"))
    assert evidence["observed_json"] is not None
    assert evidence["binding"]["definition"]["observation_channel"] == (
        probe_invocation.CHANNEL)
    actual = evidence["call_observation"]["calls"][0]
    assert actual["entrypoint"] == intent(gateway.public_task)["entrypoint"]
    assert actual["arguments"] == {"args": [TEXT], "kwargs": {}}
    assert gateway.reproduction_review(diff_hash=gateway.current_diff_hash)[
        "items"][0]["evidence"]["status"] == "REFUTED"
    gateway.execute_batch(read_calls())
    assert gateway.execute(mutation_call(gateway)).status == "succeeded"
    current = restore(gateway, journal, workspace, gateway.public_task, backend)
    call = probe(gateway.public_task, "recheck", replay="original")
    after = current.execute(call)
    assert after.output["reproduction"]["comparison"] == "matched"
    assert after.output["reproduction"]["comparison_feedback"]["desired"]["differences"] == []
    assert after.output["reproduction"]["binding"] == evidence["binding"]
    assert after.output["source_hash"] == sha256_bytes(source.encode())
    assert backend.sources[0] == backend.sources[1]
    assert len(backend.sources[0]) > 8_000
    assert current.execute(call).replayed and backend.calls == 2
    assert current.execute(call).output == after.output
    review = current.reproduction_review(diff_hash=current.current_diff_hash)
    assert review["items"][0]["evidence"]["status"] == "SUPPORTED"
    assert review["items"][0]["comparison_status"] == "mismatch_to_match"
    assert review["items"][0]["replay_action_id"] == "original"
    for phase in ("baseline", "latest"):
        assert review["items"][0][phase]["execution_link"]["status"] == "called"
        assert "args" in review["items"][0][phase]["execution_link"]["actual_conditions"]
    assert review["required"]["status"] == "UNKNOWN"
    assert review["items"][0]["repair_success"] == "not_assessed"
    state = compact_model_state(context(current, smoke_package), [])
    handoff = assemble_model_input(system_prompt="fixed", state=state, history=[],
                                   context_policy="segmented-v1")
    assert reconstruct_state(handoff)["reproduction_review"] == review
    original_arguments = probe(gateway.public_task, source=source).arguments
    split = separate({"call": {"tool": "run_probe", "arguments": original_arguments},
                      "result": first.model_dump(mode="json")})
    assert "/call/arguments/purpose" in split["annotations"]
    assert "expected_json" not in canonical_json(split["observed"])


def test_purpose_requires_complete_public_mapping_before_execution(gateway_factory):
    gateway, _, _ = gateway_factory()
    backend = gateway.probe_sandbox = ExecutingProbe()
    purposes = [
        None, {"kind": "original_requirement"}, {"kind": "helper", "expected_json": "true"},
        {"kind": "original_requirement",
         **original_intent(gateway.public_task, entrypoint="not qualified")},
        {"kind": "original_requirement",
         **original_intent(gateway.public_task, requirement_quote="invented")},
        {"kind": "original_requirement",
         **original_intent(gateway.public_task, expected_json='{"x":NaN}')},
    ]
    for n, purpose in enumerate(purposes):
        call = probe(gateway.public_task, f"bad-{n}")
        call.arguments["purpose"] = purpose
        assert gateway.execute(call).status == "failed"
    mixed = probe(gateway.public_task, "mixed")
    mixed.arguments["reproduction"] = None
    assert gateway.execute(mixed).status == "failed"
    assert backend.calls == 0
    assert gateway.reproduction_review(diff_hash=gateway.current_diff_hash)["items"] == []


@pytest.mark.parametrize(("tail", "reason", "retained"), [
    ("print(value)", "missing_observation", False),
    ("record_observation(value)\ntry:\n record_observation(value)\nexcept ValueError:\n pass",
     "invalid_or_multiple_observations", False),
    ("record_observation(float('nan'))", "invalid_or_multiple_observations", False),
    ("record_observation('a'*2049)", "invalid_or_multiple_observations", False),
    ("record_observation(value)\nraise AssertionError('later failure')",
     "execution_not_healthy", True),
])
def test_logs_invalid_values_and_crashes_never_acquire_comparison_credit(
    gateway_factory, tail, reason, retained,
):
    gateway, _, _ = gateway_factory()
    gateway.probe_sandbox = ExecutingProbe()
    source = f"value=observed_target()({TEXT!r}).value\n{tail}"
    result = gateway.execute(probe(gateway.public_task, source=source))
    assert result.status == "succeeded", result
    observation = result.output["reproduction"]
    assert observation["comparison"] == "not_compared"
    assert observation["reason"] == reason
    assert (observation["observed_json"] is not None) == retained
    assert gateway.reproduction_review(diff_hash=gateway.current_diff_hash)[
        "items"][0]["evidence"]["status"] == "UNKNOWN"


def test_helper_and_missing_call_stay_unverified_and_output_limits_stay_in_force(gateway_factory):
    gateway, _, _ = gateway_factory()
    backend = gateway.probe_sandbox = ExecutingProbe()
    helper = probe(gateway.public_task, "helper", source="print('original task passed')")
    helper.arguments["purpose"] = {"kind": "helper"}
    assert "reproduction" not in gateway.execute(helper).output
    missing = gateway.execute(probe(
        gateway.public_task, "missing", source="record_observation(True)"))
    assert missing.output["reproduction"]["reason"] == "declared_call_unobserved_or_incomplete"
    valid = gateway.execute(probe(gateway.public_task))
    for flag in ("truncated", "timed_out", "cleanup_failed", "deadline_exhausted"):
        damaged = copy.deepcopy(valid.output)
        # Reattach the channel as it arrived from the sandbox, before host stripping.
        prefix = reproduction.marker(valid.output["reproduction"]["binding"])
        observed = valid.output["reproduction"]["call_observation"]
        trace = {key: observed[key] for key in ("calls", "incomplete", "request_phase")
                 if key in observed}
        trace["observation"] = {
            "count": 1, "json": valid.output["reproduction"]["observed_json"], "error": None,
            "call_count": len(observed["calls"])}
        damaged["stderr"] = prefix + json.dumps(trace)
        damaged[flag] = True
        judged = reproduction.compare(
            copy.deepcopy(damaged), valid.output["reproduction"]["binding"],
        )
        assert judged["reproduction"]["comparison"] == "not_compared"
    damaged["deadline_exhausted"] = False
    damaged["setup_checks"] = {"status": "failed"}
    judged = reproduction.compare(damaged, valid.output["reproduction"]["binding"])
    assert judged["reproduction"]["comparison"] == "not_compared"
    assert judged["reproduction"]["reason"] == "setup_check_failed"
    huge = gateway.execute(probe(gateway.public_task, "huge", source="#" + "x" * 8_000))
    assert huge.status == "failed" and "1-8000 characters" in huge.message
    assert backend.calls == 3


def test_selected_requirement_reaches_isolated_mock_evaluation(
    tmp_path, monkeypatch, smoke_package,
):
    backend = ExecutingProbe()

    class ReproduceThenMock(MockDevAdapter):
        def next_turn(self, context, tools):
            state = json.loads(context)
            review = state["reproduction_review"]
            if not review["items"]:
                return DevModelTurn(tool_calls=[probe(smoke_package.public)])
            if review["items"][0]["comparison_status"] == "current_diff_not_observed":
                return DevModelTurn(tool_calls=[
                    probe(smoke_package.public, "recheck", replay="original")])
            return super().next_turn(context, tools)

    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    monkeypatch.setattr(runner, "MockDevAdapter", ReproduceThenMock)
    request = mock_request(tmp_path, policy="none").model_copy(update={
        "enable_probes": True, "context_policy": "segmented-v1",
        "history_search_policy": "public-v1",
    })
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert backend.calls == 2
    events = DevJournal(tmp_path, result["run_id"]).events()
    finish = next(e["payload"]["result"] for e in events if e["event_type"] == "action_finished"
                  and e["payload"]["result"]["tool"] == "finish_task")
    scope = finish["output"]["reproduction_review"]
    assert scope["items"][0]["evidence"]["status"] == "SUPPORTED"
    assert scope["required"]["status"] == "UNKNOWN"
    assert result["evaluator"]["claim_eligible"] is False
