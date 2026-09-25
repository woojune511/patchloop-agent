from __future__ import annotations

import json
from pathlib import Path

import pytest

from diagnostics import candidate_review_repair as experiment
from diagnostics import change_review
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import runner
from patchloop.dev.contracts import DevModelTurn, DevRunRequest, PublicTurnDecision, RequestedTool
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.util import sha256_text

REPORT = {field: "Public model claim; unverified." for field in experiment.REVIEW_FIELDS}


def seed(gateway_factory):
    gateway, _, workspace = gateway_factory()
    path = workspace / "mini_data_utils/csvlite.py"
    path.write_bytes(b"# Saved model candidate.\n" + path.read_bytes())
    return gateway.current_diff.patch


def request(root, context_policy="segmented-v1"):
    return DevRunRequest(
        provider="mock", model="mock", state_root=root,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
        context_policy=context_policy, planning_policy="brief-v1", repair_recheck=True,
    )


@pytest.mark.parametrize("review,with_feedback,review_policy,context_policy", [
    pytest.param(None, False, "none", "segmented-v1", id="default"),
    pytest.param(REPORT, False, "none", "segmented-v1", id="report"),
    pytest.param(None, True, "none", "segmented-v1", id="feedback"),
    pytest.param(None, False, change_review.POLICY, "segmented-v1", id="change-review"),
    pytest.param(None, False, change_review.VALUE_ORIGIN_POLICY, "append-v1", id="origin-append"),
    pytest.param(None, False, change_review.VALUE_ORIGIN_POLICY, "segmented-v1",
                 id="origin-segmented"),
])
def test_seed_repair_check_submit_isolated_evaluation(
    tmp_path, monkeypatch, gateway_factory, smoke_package, review, with_feedback, review_policy,
    context_policy,
):
    patch = seed(gateway_factory)
    feedback = ({
        "observed_on_diff_hash": sha256_text(patch),
        "requirement": "Preserve quoted newlines.",
        "python_source": "print('public fixture')",
        "stdout": "public fixture\n",
        "execution_receipt_hash": "sha256:" + "c" * 64,
        "limitations": "Synthetic delivery fixture, not a real counterexample execution.",
    } if with_feedback else None)
    inputs = []
    original_gateway, original_context = runner.DevToolGateway, runner._build_context

    class RepairMock(MockDevAdapter):
        step = 0

        def _next_action(self, context, tools):
            state = json.loads(context)
            inputs.append(state)
            self.step += 1
            if self.step == 1:
                return DevModelTurn(tool_calls=[RequestedTool(
                    name="read_file", action_id="read-current",
                    arguments={"path": self.mutation.path, "start_line": 1, "end_line": 80},
                    turn_decision=PublicTurnDecision(mode="inspect", basis="Inspect candidate.",
                                                    evidence_goal="Locate parser lifetime."),
                )])
            if self.step == 2:
                return DevModelTurn(tool_calls=[RequestedTool(
                    name="replace_text", action_id="repair-current",
                    arguments={"path": self.mutation.path, "old_text": self.mutation.old_text,
                               "new_text": self.mutation.new_text, "occurrence": 1,
                               "hypothesis": self.mutation.hypothesis,
                               "expected_behavior": self.mutation.expected_behavior,
                               "causal_revision": None},
                    turn_decision=PublicTurnDecision(mode="mutate", basis="Keep parser state."),
                )])
            return super()._next_action(context, tools)

    monkeypatch.setattr(runner, "MockDevAdapter", RepairMock)
    root = tmp_path / "branch"
    result = experiment.run_seeded(
        request(root, context_policy), seed_patch=patch, seed_hash=sha256_text(patch),
        base_commit=smoke_package.public.repository.base_commit,
        source_code=[], review=review, experiment_hash="sha256:" + "a" * 64,
        source_run_id="run_dev_saved", branch="A" if review is None else "B",
        public_feedback=feedback,
        change_review_policy=review_policy,
    )["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert result["accepted_mutations"] == 1  # Seed is not a new tool action.
    assert runner.DevToolGateway is original_gateway and runner._build_context is original_context
    assert inputs[0]["remaining_budget"]["accepted_mutations"] == 3
    assert inputs[-1]["remaining_budget"]["accepted_mutations"] == 2
    journal = DevJournal(root, result["run_id"])
    events = journal.events()
    assert len([e for e in events if e["event_type"] == "diagnostic_candidate_seeded"]) == 1
    assert any(e["event_type"] == "evaluator_finished" for e in events)
    store = ArtifactStore(root / "artifacts")
    wires = []
    for event in events:
        if event["event_type"] == "turn_started":
            items = json.loads(store.read_bytes(Artifact.model_validate(
                event["payload"]["model_input_artifact"])))
            wires.append(reconstruct_state(items, context_policy=context_policy))
    assert len(wires) == len(inputs) == 4
    for state in wires:
        assert state["public_task"] and state["current_diff"]["patch"]
        assert "visible_check_status" in state and experiment.FIELD in state
        assert "source_run_id" not in state[experiment.FIELD]
    assert wires[-1]["visible_check_status"][0]["status"] == "PASS"
    if review_policy != "none":
        assert [change_review.FIELD in v for v in wires] == [True, False, True, False]
        assert wires[0][change_review.FIELD]["subject"]["origin"] == "imported_model_candidate"
        assert wires[2][change_review.FIELD]["subject"]["action_id"] == "repair-current"
        assert wires[2][change_review.FIELD]["subject"]["diff_hash"] == (
            wires[2]["current_diff"]["patch_hash"])
        instruction = change_review.INSTRUCTIONS[review_policy]
        assert all(wires[i][change_review.FIELD]["policy"] == review_policy for i in (0, 2))
        assert all(wires[i][change_review.FIELD]["instruction"] == instruction for i in (0, 2))
        receipts = [e["payload"] for e in events
                    if e["event_type"] == "diagnostic_change_review_policy"]
        assert len(receipts) == 1
        assert receipts[0]["policy"] == review_policy
        assert receipts[0]["instruction_hash"] == sha256_text(instruction)
        assert receipts[0]["delivery_is_completed_review"] is False
    else:
        assert all(change_review.FIELD not in v for v in wires)
    if review is not None:
        assert wires[0][experiment.FIELD]["review"]["currency"] == "matches_current_diff"
        assert wires[-1][experiment.FIELD]["review"]["currency"] == "older_candidate"
    else:
        assert all(v[experiment.FIELD]["review"] is None for v in wires)
    if with_feedback:
        assert wires[0][experiment.FEEDBACK_FIELD]["currency"] == "current_candidate"
        assert wires[-1][experiment.FEEDBACK_FIELD]["currency"] == "historical_candidate"
        assert all(v[experiment.FEEDBACK_FIELD]["stdout"] == feedback["stdout"] for v in wires)
        assert all(v[experiment.FEEDBACK_FIELD]["observed_on_diff_hash"] == sha256_text(patch)
                   for v in wires)
        assert len([e for e in events
                    if e["event_type"] == "diagnostic_public_feedback_attached"]) == 1
    else:
        assert all(experiment.FEEDBACK_FIELD not in v for v in wires)


@pytest.mark.parametrize("change", ["hash", "repeat", "resume", "root", "private_field",
                                    "feedback_subject", "feedback_private_field", "review_policy"])
def test_invalid_seed_request_fails_before_runner(tmp_path, monkeypatch, change):
    req = request(tmp_path / "run")
    kwargs = {"seed_patch": "public patch", "seed_hash": sha256_text("public patch"),
              "base_commit": "a" * 40, "source_code": [], "review": None,
              "experiment_hash": "sha256:" + "b" * 64, "source_run_id": "run_dev_saved",
              "branch": "A"}
    if change == "hash":
        kwargs["seed_hash"] = "sha256:" + "0" * 64
    elif change == "repeat":
        req = req.model_copy(update={"repeat": 2})
    elif change == "resume":
        req = req.model_copy(update={"resume_run_id": "run_dev_saved"})
    elif change == "root":
        Path(req.state_root).mkdir()
    elif change == "private_field":
        kwargs["review"] = {**REPORT, "hidden_verdict": "PASS"}
    elif change == "review_policy":
        kwargs["change_review_policy"] = "unknown"
    else:
        feedback = {name: "public" for name in experiment.FEEDBACK_FIELDS}
        feedback["observed_on_diff_hash"] = kwargs["seed_hash"]
        if change == "feedback_subject":
            feedback["observed_on_diff_hash"] = "sha256:" + "0" * 64
        else:
            feedback["hidden_verdict"] = "FAIL"
        kwargs["public_feedback"] = feedback
    monkeypatch.setattr(runner, "run_dev", lambda _: pytest.fail("runner must not start"))
    with pytest.raises(ContractError):
        experiment.run_seeded(req, **kwargs)


def test_only_review_overlay_differs_and_claims_expire():
    common = {"seed_hash": "seed", "base_commit": "base", "source_code": []}
    state = {"current_diff": {"patch_hash": "seed"}}
    a = experiment.overlay(state, **common, review=None)
    b = experiment.overlay(state, **common, review=REPORT)
    assert {k: v for k, v in a.items() if k != "review"} == {
        k: v for k, v in b.items() if k != "review"}
    state["current_diff"]["patch_hash"] = "changed"
    assert experiment.overlay(state, **common, review=REPORT)["review"]["currency"] == (
        "older_candidate")


@pytest.mark.parametrize("failure", ["base", "patch"])
def test_invalid_checkout_seed_never_reaches_model(
    tmp_path, monkeypatch, gateway_factory, smoke_package, failure,
):
    candidate = seed(gateway_factory) if failure == "base" else "not a Git patch\n"
    original_gateway, original_context = runner.DevToolGateway, runner._build_context
    monkeypatch.setattr(runner, "MockDevAdapter", lambda _: pytest.fail("model must not start"))
    with pytest.raises(ContractError):
        experiment.run_seeded(
            request(tmp_path / "invalid"), seed_patch=candidate,
            seed_hash=sha256_text(candidate), base_commit=("a" * 40 if failure == "base"
                else smoke_package.public.repository.base_commit), source_code=[], review=None,
            experiment_hash="sha256:" + "a" * 64, source_run_id="run_dev_saved", branch="A",
        )
    assert runner.DevToolGateway is original_gateway and runner._build_context is original_context
