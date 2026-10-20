"""Manual action-ID replay preserves a public program, not a correctness verdict."""

from __future__ import annotations

import copy

import httpx
import pytest
from test_dev_probe_cases import REPRODUCER, ExecutingProbe
from test_dev_probes import FakeProbe
from test_dev_runner import _crash_journal_once, _SimulatedCrash
from test_dev_tools import mutation_call, read_calls

from patchloop.dev import probe_cases as cases
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas
from patchloop.errors import ActionConflict

POLICIES = ("none", cases.POLICY, cases.REFERENCE_POLICY)
QUESTION = "Does the public parser preserve a quoted newline?"


@pytest.fixture(autouse=True)
def no_provider_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("action replay tests must not send real provider requests")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def probe(action_id="original", *, replay=None, source=REPRODUCER, policy="none"):
    arguments = {
        "question": None if replay is not None else QUESTION,
        "python_source": None if replay is not None else source,
        "replay_action_id": replay,
    }
    if policy in cases.POLICIES:
        arguments.update(case_id=None, reference_action_id=None)
        if policy == cases.POLICY:
            arguments["save_program"] = False
    return RequestedTool(
        name="run_probe", action_id=action_id, arguments=arguments,
        turn_decision=PublicTurnDecision(mode="verify", basis="Recheck the public example."),
    )


def restore(gateway, journal, workspace, public_task, backend):
    return DevToolGateway(
        workspace=workspace, public_task=public_task, journal=journal,
        sandbox=gateway.sandbox, probe_sandbox=backend, limits=gateway.limits,
        probe_policy=gateway.probe_policy,
    )


@pytest.mark.parametrize("policy", POLICIES)
def test_action_replay_is_available_in_every_probe_schema(policy):
    schema = dev_tool_schemas(
        finish_enabled=True, allowed_tools={"run_probe"}, probe_policy=policy,
    )[0]
    parameters = schema["parameters"]
    assert set(parameters["required"]) == set(parameters["properties"])
    assert not parameters["additionalProperties"]
    for name in ("question", "python_source", "replay_action_id"):
        assert parameters["properties"][name]["type"] == ["string", "null"]


def test_ordinary_failing_probe_replays_exact_program_after_edit_and_restart(
    gateway_factory, smoke_package,
):
    gateway, journal, workspace = gateway_factory()
    backend = ExecutingProbe()
    gateway.probe_sandbox = backend
    original_call = probe()
    original = gateway.execute(original_call)
    assert original.status == "succeeded" and original.output["exit_code"] == 1
    assert "AssertionError" in original.output["stderr"]
    assert "case_comparison" not in original.output
    assert not cases.saved_cases(journal.events())
    gateway.execute_batch(read_calls())
    assert gateway.execute(mutation_call(gateway)).status == "succeeded"
    current = restore(gateway, journal, workspace, smoke_package.public, backend)
    replay_call = probe("recheck", replay="original")
    replay = current.execute(replay_call)
    assert replay.status == "succeeded" and replay.output["exit_code"] == 0
    assert replay.output["question"] == QUESTION
    assert replay.output["source_hash"] == original.output["source_hash"]
    assert replay.workspace_diff_hash == current.current_diff_hash
    assert replay.workspace_diff_hash != original.workspace_diff_hash
    assert replay.output["replayed_from"] == {
        "action_id": "original", "input_hash": original.input_hash,
        "diff_hash": original.workspace_diff_hash, "source_hash": original.output["source_hash"],
    }
    assert "case_comparison" not in replay.output
    assert backend.sources == [REPRODUCER, REPRODUCER]
    assert not current.checks_by_diff and not cases.saved_cases(journal.events())
    restarted = restore(current, journal, workspace, smoke_package.public, backend)
    assert restarted.execute(replay_call).replayed and backend.calls == 2
    changed = probe("recheck", replay="recheck")
    with pytest.raises(ActionConflict):
        restarted.execute(changed)
    # A different action ID is a new execution, even on the same diff.
    chained = restarted.execute(probe("third", replay="recheck"))
    assert chained.output["replayed_from"]["action_id"] == "recheck"
    assert chained.output["source_hash"] == original.output["source_hash"]
    assert backend.sources == [REPRODUCER] * 3


@pytest.mark.parametrize("policy", (cases.POLICY, cases.REFERENCE_POLICY))
def test_action_replay_does_not_register_or_compare_a_case(gateway_factory, policy):
    gateway, journal, _ = gateway_factory()
    gateway.probe_policy = policy
    backend = FakeProbe(status="passed")
    gateway.probe_sandbox = backend
    original = gateway.execute(probe(source="print('not JSON')", policy=policy))
    replay = gateway.execute(probe("recheck", replay="original", policy=policy))
    assert original.status == replay.status == "succeeded"
    assert replay.output["source_hash"] == original.output["source_hash"]
    assert "case_comparison" not in replay.output
    assert not cases.saved_cases(journal.events()) and not gateway.checks_by_diff
    assert backend.calls == 2


def test_action_replay_resolves_prior_case_replay_without_updating_case_catalog(gateway_factory):
    gateway, journal, _ = gateway_factory()
    gateway.probe_policy = cases.POLICY
    backend = FakeProbe(status="passed")
    gateway.probe_sandbox = backend
    save = probe(source="print(1)", policy=cases.POLICY)
    save.arguments["save_program"] = True
    original = gateway.execute(save)
    case_id = original.output["case_comparison"]["case_id"]
    case_replay = probe("case-recheck", replay="unused", policy=cases.POLICY)
    case_replay.arguments.update(replay_action_id=None, case_id=case_id)
    case_result = gateway.execute(case_replay)
    assert case_result.status == "succeeded"
    assert case_replay.arguments["python_source"] is None
    catalog = cases.saved_cases(journal.events())
    direct = gateway.execute(probe("direct-recheck", replay="case-recheck", policy=cases.POLICY))
    assert direct.status == "succeeded"
    assert direct.output["source_hash"] == original.output["source_hash"]
    assert direct.output["question"] == QUESTION
    assert direct.output["replayed_from"]["action_id"] == "case-recheck"
    assert "case_comparison" not in direct.output
    assert cases.saved_cases(journal.events()) == catalog
    assert not gateway.checks_by_diff and backend.calls == 3


@pytest.mark.parametrize("source", [
    "assert False, 'public expected value'",
    "import missing_public_probe_dependency",
    "print('a non-JSON public observation')",
])
def test_completed_assertion_import_error_and_non_json_programs_remain_replayable(
    gateway_factory, source,
):
    gateway, _, _ = gateway_factory()
    backend = ExecutingProbe()
    gateway.probe_sandbox = backend
    original = gateway.execute(probe(source=source))
    replay = gateway.execute(probe("recheck", replay="original"))
    assert original.status == replay.status == "succeeded"
    assert original.output["exit_code"] == replay.output["exit_code"]
    assert backend.sources == [source, source]


@pytest.mark.parametrize("cleanup", ["flag", "policy", "missing"])
def test_uncertain_original_execution_is_not_replayed(gateway_factory, cleanup):
    gateway, _, _ = gateway_factory()

    class UncertainProbe(FakeProbe):
        def run_probe(self, *args, **kwargs):
            result = super().run_probe(*args, **kwargs)
            if cleanup == "flag":
                result["cleanup_failed"] = True
            elif cleanup == "policy":
                result["execution_policy"]["cleanup_status"] = "failed"
            else:
                result.pop("execution_policy")
            return result

    backend = UncertainProbe(status="failed")
    gateway.probe_sandbox = backend
    gateway.execute(probe())
    result = gateway.execute(probe("recheck", replay="original"))
    assert result.status == "failed" and backend.calls == 1


@pytest.mark.parametrize("status", ["timeout", "output_limit"])
def test_cleanly_terminated_program_can_be_replayed_after_edit(gateway_factory, status):
    gateway, _, _ = gateway_factory()

    class LimitedProbe(FakeProbe):
        def run_probe(self, *args, **kwargs):
            result = super().run_probe(*args, **kwargs)
            if self.calls == 1:
                result.update(status=status, exit_code=None, timed_out=status == "timeout",
                              truncated=status == "output_limit", deadline_exhausted=True)
            return result

    backend = LimitedProbe(status="passed")
    gateway.probe_sandbox = backend
    original = gateway.execute(probe())
    gateway.execute_batch(read_calls())
    assert gateway.execute(mutation_call(gateway)).status == "succeeded"
    replay = gateway.execute(probe("recheck", replay="original"))
    assert replay.status == "succeeded" and backend.calls == 2
    assert replay.workspace_diff_hash != original.workspace_diff_hash
    assert replay.output["source_hash"] == original.output["source_hash"]
    assert replay.output["status"] == "passed"


@pytest.mark.parametrize("fault", ["unknown", "pending", "other_tool", "outer_failed"])
def test_only_completed_successful_outer_probe_receipts_can_be_selected(
    gateway_factory, monkeypatch, fault,
):
    gateway, journal, _ = gateway_factory()
    backend = FakeProbe(status="passed")
    gateway.probe_sandbox = backend
    if fault == "pending":
        _crash_journal_once(
            monkeypatch, event_type="action_started",
            predicate=lambda payload: payload["action_id"] == "original", when="after",
        )
        with pytest.raises(_SimulatedCrash):
            gateway.execute(probe())
    elif fault == "other_tool":
        read = read_calls()[0].model_copy(update={"action_id": "original"})
        assert gateway.execute(read).status == "succeeded"
    elif fault == "outer_failed":
        invalid = probe(source="")
        assert gateway.execute(invalid).status == "failed"
    result = gateway.execute(probe("recheck", replay="original"))
    assert result.status == "failed" and backend.calls == 0
    assert not cases.saved_cases(journal.events())


def test_action_replay_rejects_mixed_modes_before_execution(gateway_factory):
    gateway, _, _ = gateway_factory()
    gateway.probe_policy = cases.POLICY
    backend = FakeProbe(status="passed")
    gateway.probe_sandbox = backend
    assert gateway.execute(probe(policy=cases.POLICY)).status == "succeeded"
    alternatives = [
        {"question": QUESTION}, {"python_source": REPRODUCER},
        {"case_id": "pc_unknown"}, {"reference_action_id": "original"},
        {"save_program": True}, {"replay_action_id": ""},
    ]
    for index, replacement in enumerate(alternatives):
        mixed = probe(f"mixed-{index}", replay="original", policy=cases.POLICY)
        mixed.arguments.update(replacement)
        assert gateway.execute(mixed).status == "failed", replacement
    assert backend.calls == 1


def test_reference_policy_still_rejects_unexposed_save_field(gateway_factory):
    gateway, _, _ = gateway_factory()
    gateway.probe_policy = cases.REFERENCE_POLICY
    backend = FakeProbe(status="passed")
    gateway.probe_sandbox = backend
    assert gateway.execute(probe(policy=cases.REFERENCE_POLICY)).status == "succeeded"
    replay = probe("recheck", replay="original", policy=cases.REFERENCE_POLICY)
    replay.arguments["save_program"] = False
    assert gateway.execute(replay).status == "failed"
    assert backend.calls == 1


@pytest.mark.parametrize("drift", ["none", "workspace", "program"])
def test_interrupted_action_replay_binds_program_and_diff_before_restart(
    gateway_factory, smoke_package, monkeypatch, drift,
):
    gateway, journal, workspace = gateway_factory()
    backend = FakeProbe(status="passed")
    gateway.probe_sandbox = backend
    original = gateway.execute(probe())
    replay_call = probe("recheck", replay="original")
    _crash_journal_once(
        monkeypatch, event_type="action_started",
        predicate=lambda payload: payload["action_id"] == "recheck", when="after",
    )
    with pytest.raises(_SimulatedCrash):
        gateway.execute(replay_call)
    admission = journal.events()[-1]["payload"]["probe_replay_request"]
    assert admission["python_source"] == REPRODUCER
    assert admission["question"] == QUESTION and admission["case"] is None
    assert admission["replayed_from"]["input_hash"] == original.input_hash
    if drift == "workspace":
        source = workspace / "mini_data_utils/csvlite.py"
        source.write_bytes(source.read_bytes() + b"\n# external drift\n")
    elif drift == "program":
        original_events = journal.events

        def changed_program():
            events = copy.deepcopy(original_events())
            for event in events:
                payload = event["payload"]
                if event["event_type"] == "action_started" and payload.get(
                    "action_id"
                ) == "recheck":
                    payload["probe_replay_request"]["python_source"] += "\nprint('drift')"
            return events

        monkeypatch.setattr(journal, "events", changed_program)
    restored = restore(gateway, journal, workspace, smoke_package.public, backend)
    result = restored.execute(replay_call)
    if drift == "none":
        assert result.status == "succeeded" and backend.calls == 2
        assert restored.execute(replay_call).replayed and backend.calls == 2
    else:
        assert result.error_code == "RECOVERY_ERROR" and backend.calls == 1
