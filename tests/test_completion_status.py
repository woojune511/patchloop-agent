from __future__ import annotations

import copy
import json
import socket
from types import SimpleNamespace

import pytest
from test_candidate_review_repair import REPORT, request

from diagnostics import candidate_review_repair as experiment
from diagnostics import change_review, completion_status, paired_observation
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import runner
from patchloop.dev.contracts import DevModelTurn, PublicTurnDecision, RequestedTool
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_json, sha256_text


@pytest.mark.parametrize("stage,allowed,failed", [
    ("needs_visible_checks", ("run_check", "read_file"), False),
    ("ready_to_submit", ("finish_task", "run_probe"), False),
    ("ready_to_submit", ("finish_task",), False),
    ("needs_source_evidence", ("read_file", "run_check"), True),
    ("needs_mutation", ("replace_text", "run_check"), True),
    ("blocked", ("stop_task",), False),
])
def test_only_completion_advice_changes(stage, allowed, failed):
    snapshot = SimpleNamespace(
        diff=SimpleNamespace(patch_hash="current-diff"),
        ready_to_submit=stage == "ready_to_submit",
        visible_check_status=[{"status": "FAIL" if failed else "NOT_RUN"}],
    )
    policy = SimpleNamespace(
        allowed_tools=allowed, workflow_gate="needs_visible_checks", check_ids=("public-check",),
    )
    guidance = runner._completion_guidance(snapshot, policy)
    before = copy.deepcopy(guidance)
    projected = completion_status.project(guidance)
    assert guidance == before and guidance["stage"] == stage
    if stage in {"needs_visible_checks", "ready_to_submit"}:
        assert {key for key in before if before[key] != projected[key]} == {
            "next_action", "message"}
        assert projected["next_action"] is None
        assert "Use " not in projected["message"]
        assert {k: v for k, v in projected.items() if k not in {"next_action", "message"}} == {
            k: v for k, v in before.items() if k not in {"next_action", "message"}}
    else:
        assert projected == before


def arguments():
    return dict(
        seed_patch="patch", seed_hash=sha256_text("patch"), base_commit="a" * 40,
        source_code=[], review=None, experiment_hash="sha256:" + "b" * 64,
        source_run_id="run_dev_saved", branch="status",
    )


@pytest.mark.parametrize("change", ["unknown", "review", "review_policy", "comparison", "feedback"])
def test_incompatible_request_fails_before_runner(tmp_path, monkeypatch, change):
    kwargs = {**arguments(), "completion_guidance_policy": completion_status.POLICY}
    if change == "unknown":
        kwargs["completion_guidance_policy"] = "unknown"
    elif change == "review":
        kwargs["review"] = REPORT
    elif change == "review_policy":
        kwargs["change_review_policy"] = change_review.POLICY
    elif change == "comparison":
        kwargs["comparison_policy"] = paired_observation.POLICY
    else:
        kwargs["public_feedback"] = {k: "public" for k in experiment.FEEDBACK_FIELDS}
        kwargs["public_feedback"]["observed_on_diff_hash"] = kwargs["seed_hash"]
    monkeypatch.setattr(runner, "run_dev", lambda _: pytest.fail("runner must not start"))
    root = tmp_path / "branch"
    with pytest.raises(ContractError, match="completion guidance"):
        experiment.run_seeded(request(root), **kwargs)
    assert not root.exists()


@pytest.mark.parametrize("policy", [None, "none", completion_status.POLICY])
def test_context_isolated_and_hooks_restored_after_failure(tmp_path, monkeypatch, policy):
    state = {
        "current_diff": {"patch_hash": "seed"},
        "completion_guidance": {
            "stage": "ready_to_submit", "diff_hash": "seed", "submission_ready": True,
            "next_action": {"tool": "finish_task"}, "message": "Use finish_task to submit.",
        },
        "public_task": {"issue": "public"}, "available_tool_names": ["finish_task"],
    }
    monkeypatch.setattr(runner, "_build_context", lambda **_: canonical_json(state))
    hooks = {key: getattr(runner, key) for key in (
        "DevToolGateway", "_build_context", "_tool_policy", "dev_tool_schemas", "DEV_SYSTEM_PROMPT",
    )}

    def fail_after_context(_):
        actual = json.loads(runner._build_context())
        actual.pop(experiment.FIELD)
        expected = copy.deepcopy(state)
        if policy == completion_status.POLICY:
            expected["completion_guidance"] = completion_status.project(
                state["completion_guidance"])
        assert actual == expected
        assert all(getattr(runner, key) is hooks[key] for key in (
            "_tool_policy", "dev_tool_schemas", "DEV_SYSTEM_PROMPT"))
        raise RuntimeError("fixture failure")

    monkeypatch.setattr(runner, "run_dev", fail_after_context)
    kwargs = arguments()
    if policy is not None:
        kwargs["completion_guidance_policy"] = policy
    with pytest.raises(RuntimeError, match="fixture failure"):
        experiment.run_seeded(request(tmp_path / "branch"), **kwargs)
    assert all(getattr(runner, key) is value for key, value in hooks.items())


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
def test_failed_check_repair_submit_and_native_input_delivery(
    tmp_path, monkeypatch, gateway_factory, smoke_package, context_policy,
):
    monkeypatch.setattr(socket.socket, "connect", lambda *_: pytest.fail("network is forbidden"))
    gateway, _, workspace = gateway_factory()
    path = workspace / "mini_data_utils/csvlite.py"
    path.write_bytes(path.read_bytes().replace(b"return rows", b"return rows[:-1]"))
    patch_text = gateway.current_diff.patch
    inputs, raw_states = [], []
    original_context = runner._build_context

    def capture_context(**kwargs):
        context = original_context(**kwargs)
        raw_states.append(json.loads(context))
        return context

    monkeypatch.setattr(runner, "_build_context", capture_context)
    hooks = {key: getattr(runner, key) for key in (
        "DevToolGateway", "_build_context", "_tool_policy", "dev_tool_schemas", "DEV_SYSTEM_PROMPT",
    )}

    class RepairMock(MockDevAdapter):
        step = 0

        def _next_action(self, context, tools):
            state = json.loads(context)
            inputs.append(state)
            assert {t["name"] for t in tools} == set(state["available_tool_names"])
            expected = copy.deepcopy(raw_states[-1])
            expected["completion_guidance"] = completion_status.project(
                expected["completion_guidance"])
            actual = copy.deepcopy(state)
            actual.pop(experiment.FIELD)
            if context_policy == "segmented-v1":
                # The common runner adds cost metadata after the diagnostic overlay.
                assert actual["remaining_budget"].pop("cost")["provider"] == "mock"
            assert actual == expected
            self.step += 1
            if self.step == 1:
                call = RequestedTool(
                    name="run_check", action_id=f"check-{self.step}",
                    arguments={"check_id": smoke_package.public.visible_checks[0].id},
                    turn_decision=PublicTurnDecision(
                        mode="verify", basis="Check current CSV parser."),
                )
            elif self.step == 2:
                call = RequestedTool(
                    name="read_file", action_id="read-current",
                    arguments={"path": self.mutation.path, "start_line": 1, "end_line": 80},
                    turn_decision=PublicTurnDecision(
                        mode="inspect", basis="The public check failed.",
                        evidence_goal="Locate the parser lifetime in current code."),
                )
            elif self.step == 3:
                call = RequestedTool(
                    name="replace_text", action_id="repair-current",
                    arguments={"path": self.mutation.path,
                               "old_text": self.mutation.old_text.replace(
                                   "return rows", "return rows[:-1]"),
                               "new_text": self.mutation.new_text, "occurrence": 1,
                               "hypothesis": self.mutation.hypothesis,
                               "expected_behavior": self.mutation.expected_behavior,
                               "causal_revision": None},
                    turn_decision=PublicTurnDecision(mode="mutate", basis="Keep parser state."),
                )
            else:
                assert self.step == 4
                call = RequestedTool(
                    name="finish_task", action_id="submit", arguments={},
                    turn_decision=PublicTurnDecision(mode="finish", basis="Current check passed."),
                )
            return DevModelTurn(tool_calls=[call])

    monkeypatch.setattr(runner, "MockDevAdapter", RepairMock)
    root = tmp_path / "branch"
    result = experiment.run_seeded(
        request(root, context_policy), **{
            **arguments(), "seed_patch": patch_text, "seed_hash": sha256_text(patch_text),
            "base_commit": smoke_package.public.repository.base_commit,
            "completion_guidance_policy": completion_status.POLICY,
        },
    )["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert result["accepted_mutations"] == 1 and result["official"] is False
    assert result["call_counts"] == {"model": 4, "input_count": 0, "tool": 5}
    assert result["cost_nanos"] == 0
    assert all(getattr(runner, key) is value for key, value in hooks.items())
    assert [s["completion_guidance"]["stage"] for s in inputs] == [
        "needs_visible_checks", "needs_source_evidence", "needs_mutation",
        "ready_to_submit",
    ]
    assert inputs[0]["remaining_budget"]["accepted_mutations"] == 3
    assert inputs[-1]["remaining_budget"]["accepted_mutations"] == 2
    events = DevJournal(root, result["run_id"]).events()
    receipt = next(e for e in events if e["event_type"] == completion_status.EVENT)
    assert receipt["payload"] == {
        **completion_status.identity(), "experiment_hash": arguments()["experiment_hash"],
    }
    assert receipt["payload"]["message_hash"] == sha256_json(completion_status.MESSAGES)
    assert len([e for e in events if e["event_type"] == completion_status.EVENT]) == 1
    assert events.index(receipt) < next(i for i, e in enumerate(events)
                                       if e["event_type"] == "turn_started")
    assert any(e["event_type"] == "evaluator_finished" for e in events)
    assert len([e for e in events if e["event_type"] == "repair_recheck_finished"]) == 1
    assert not any(e["event_type"].startswith(("provider_call", "input_count")) for e in events)
    store = ArtifactStore(root / "artifacts")
    wires = [reconstruct_state(json.loads(store.read_bytes(Artifact.model_validate(
        e["payload"]["model_input_artifact"]))), context_policy=context_policy)
        for e in events if e["event_type"] == "turn_started"]
    assert len(wires) == len(inputs) == 4
    for wire, expected in zip(wires, inputs, strict=True):
        for key in ("public_task", "current_diff", "visible_check_status", "completion_guidance",
                    "available_tool_names", experiment.FIELD):
            assert wire[key] == expected[key]
        # Native delivery may reference update receipts and add a segment handoff
        # reason. The plan's content and identity must still survive unchanged.
        assert wire["working_plan"]["policy"] == expected["working_plan"]["policy"]
        native_plan, canonical_plan = wire["working_plan"]["plan"], expected["working_plan"]["plan"]
        if canonical_plan is None:
            assert native_plan is None
        else:
            for key in ("text", "text_hash", "revision", "diff_hash", "diff_currency", "turn_id"):
                assert native_plan[key] == canonical_plan[key]
        assert completion_status.POLICY not in canonical_json(wire)
    assert wires[1]["visible_check_status"][0]["status"] == "FAIL"
    assert wires[-1]["visible_check_status"][0]["status"] == "PASS"
