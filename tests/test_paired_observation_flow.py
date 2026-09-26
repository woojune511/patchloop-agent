from __future__ import annotations

import json
import subprocess
import sys

import pytest
from test_candidate_review_repair import request, seed
from test_paired_observation import JSONProbe, design

from diagnostics import candidate_review_repair as experiment
from diagnostics import paired_observation as paired
from diagnostics.segmented_input_audit import reconstruct_state
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import runner
from patchloop.dev.contracts import DevModelTurn, PublicTurnDecision, RequestedTool
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import sha256_text

PROGRAM = (
    "import json\nfrom mini_data_utils.csvlite import parse_rows\n"
    "print(json.dumps({'a': parse_rows('\"x\\ny\"'), 'b': parse_rows('x')}))\n"
)


class FixtureProbe(JSONProbe):
    """Trusted test-only program on the local smoke workspace; no Docker or provider."""

    def run_probe(self, workspace, question, python_source, **kwargs):
        assert python_source == PROGRAM
        result = super().run_probe(workspace, question, python_source, **kwargs)
        completed = subprocess.run(
            [sys.executable, "-B", "-c", python_source], cwd=workspace,
            capture_output=True, text=True, encoding="utf-8", check=True,
        )
        result["stdout"] = completed.stdout
        return result


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
def test_compare_repair_check_submit_and_actual_input_delivery(
    tmp_path, monkeypatch, gateway_factory, smoke_package, context_policy,
):
    patch_text = seed(gateway_factory)
    backend = FixtureProbe()
    inputs, schemas = [], []
    hooks = {name: getattr(runner, name) for name in (
        "DevToolGateway", "_build_context", "_tool_policy", "dev_tool_schemas", "DEV_SYSTEM_PROMPT",
    )}

    class RepairMock(MockDevAdapter):
        step = 0

        def _next_action(self, context, tools):
            state = json.loads(context)
            inputs.append(state)
            schemas.append(tools)
            self.step += 1
            if self.step == 1:
                call = RequestedTool(
                    name="read_file", action_id="read-current",
                    arguments={"path": self.mutation.path, "start_line": 1, "end_line": 80},
                    turn_decision=PublicTurnDecision(
                        mode="inspect", basis="Locate parser lifetime.",
                        evidence_goal="Construct public CSV inputs."),
                )
            elif self.step == 2:
                invalid = design()
                invalid["cases"][0]["expected_json"] = "NaN"
                call = RequestedTool(
                    name="run_probe", action_id="invalid-comparison",
                    arguments={"question": "Compare multiline and ordinary CSV records.",
                               "python_source": PROGRAM, "comparison": invalid},
                    turn_decision=PublicTurnDecision(mode="verify", basis="Declare expectations."),
                )
            elif self.step == 3:
                phase = state[paired.FIELD]
                assert phase["phase"] == "observe" and phase["result"] is None
                assert phase["rejected_declarations"] == 1 and backend.calls == 0
                assert phase["last_declaration_error"]["action_id"] == "invalid-comparison"
                assert "read:read-current" in {r["id"] for r in phase["evidence_catalog"]["reads"]}
                corrected = design()
                corrected["requirement_ids"] = [phase["evidence_catalog"]["requirements"][1]["id"]]
                call = RequestedTool(
                    name="run_probe", action_id="compare-current",
                    arguments={"question": "Compare multiline and ordinary CSV records.",
                               "python_source": PROGRAM, "comparison": corrected},
                    turn_decision=PublicTurnDecision(mode="verify", basis=(
                        "The declaration rejected NaN before execution; use literal JSON values.")),
                )
            elif self.step == 4:
                observation = state[paired.FIELD]["result"]["comparison"]["observation"]
                assert observation["status"] == "mismatched"
                assert json.loads(observation["observed_json"])["b"] == [["x"]]
                assert "replace_text" in {t["name"] for t in tools}
                call = RequestedTool(
                    name="replace_text", action_id="repair-current",
                    arguments={"path": self.mutation.path, "old_text": self.mutation.old_text,
                               "new_text": self.mutation.new_text, "occurrence": 1,
                               "hypothesis": self.mutation.hypothesis,
                               "expected_behavior": self.mutation.expected_behavior,
                               "causal_revision": None},
                    turn_decision=PublicTurnDecision(mode="mutate", basis=(
                        "The multiline observation splits while the ordinary case is preserved; "
                        "keep one parser alive across the complete text.")),
                )
            else:
                return super()._next_action(context, tools)
            return DevModelTurn(tool_calls=[call])

    monkeypatch.setattr(runner, "MockDevAdapter", RepairMock)
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    root = tmp_path / "branch"
    req = request(root, context_policy).model_copy(update={"enable_probes": True})
    result = experiment.run_seeded(
        req, seed_patch=patch_text, seed_hash=sha256_text(patch_text),
        base_commit=smoke_package.public.repository.base_commit,
        source_code=[], review=None, experiment_hash="sha256:" + "a" * 64,
        source_run_id="run_dev_saved", branch="comparison", comparison_policy=paired.POLICY,
    )["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert result["accepted_mutations"] == 1 and backend.calls == 1
    assert all(getattr(runner, name) is original for name, original in hooks.items())
    assert [s[paired.FIELD]["phase"] for s in inputs] == [
        "observe", "observe", "observe",
        "returned_to_repair", "returned_to_repair", "returned_to_repair",
    ]
    for index, tools in enumerate(schemas):
        names = {t["name"] for t in tools}
        assert names == set(inputs[index]["available_tool_names"])
        if index < 3:
            assert not names & {"replace_text", "finish_task"}
        for tool in tools:
            if tool["name"] in {"run_check", "run_probe"}:
                assert ("comparison" in tool["parameters"]["required"]) is (index < 3)
                if index < 3:
                    schema = tool["parameters"]["properties"]["comparison"]
                    assert schema["properties"]["requirement_ids"]["items"]["enum"] == [
                        "issue-title", "issue-1"]
                    refs = schema["properties"]["cases"]["items"]["properties"]["evidence_ref"]
                    catalog = inputs[index][paired.FIELD]["evidence_catalog"]
                    assert refs["enum"] == (
                        [r["id"] for r in catalog["checks"] + catalog["reads"]]
                        if tool["name"] == "run_check" else [None])
    journal = DevJournal(root, result["run_id"])
    events = journal.events()
    assert len([e for e in events if e["event_type"] == paired.EVENT]) == 1
    assert any(e["event_type"] == "evaluator_finished" for e in events)
    store = ArtifactStore(root / "artifacts")
    wires = [reconstruct_state(json.loads(store.read_bytes(Artifact.model_validate(
        e["payload"]["model_input_artifact"]))), context_policy=context_policy)
        for e in events if e["event_type"] == "turn_started"]
    assert len(wires) == 6
    for state, original in zip(wires, inputs, strict=True):
        assert state["public_task"] and state["current_diff"]["patch"]
        assert "visible_check_status" in state
        assert state[paired.FIELD] == original[paired.FIELD]
    assert wires[3][paired.FIELD]["result"]["currency"] == "current"
    assert wires[-1][paired.FIELD]["result"]["currency"] == "historical"
    assert wires[-1]["visible_check_status"][0]["status"] == "PASS"
    last = wires[-1][paired.FIELD]["result"]["comparison"]["observation"]
    assert last["semantic_verdict"] is None
    assert wires[-1][paired.FIELD]["last_declaration_error"]["currency"] == "historical"


@pytest.mark.parametrize("change", ["unknown", "disabled", "case_policy", "review", "feedback"])
def test_incompatible_option_fails_before_runner(tmp_path, monkeypatch, change):
    req = request(tmp_path / "run").model_copy(update={"enable_probes": True})
    kwargs = dict(seed_patch="patch", seed_hash=sha256_text("patch"), base_commit="a" * 40,
                  source_code=[], review=None, experiment_hash="sha256:" + "b" * 64,
                  source_run_id="run_dev_saved", branch="B", comparison_policy=paired.POLICY)
    if change == "unknown":
        kwargs["comparison_policy"] = "unknown"
    elif change == "disabled":
        req = req.model_copy(update={"enable_probes": False})
    elif change == "case_policy":
        req = req.model_copy(update={"probe_policy": "cases-v1"})
    elif change == "review":
        kwargs["change_review_policy"] = "change-review-v1"
    else:
        kwargs["public_feedback"] = {k: "public" for k in experiment.FEEDBACK_FIELDS}
        kwargs["public_feedback"]["observed_on_diff_hash"] = kwargs["seed_hash"]
    monkeypatch.setattr(runner, "run_dev", lambda _: pytest.fail("runner must not start"))
    with pytest.raises(ContractError):
        experiment.run_seeded(req, **kwargs)


def test_missing_option_preserves_every_runner_hook():
    before = dict(vars(runner))
    with paired.install(runner, enabled=False):
        assert before == vars(runner)
    assert before == vars(runner)


def test_hooks_restore_after_exception():
    before = {key: getattr(runner, key) for key in (
        "_tool_policy", "_build_context", "dev_tool_schemas", "DEV_SYSTEM_PROMPT",
    )}
    with pytest.raises(RuntimeError, match="fixture"), paired.install(runner, enabled=True):
        assert runner.DEV_SYSTEM_PROMPT.endswith(paired.SYSTEM_SUFFIX)
        raise RuntimeError("fixture")
    assert all(getattr(runner, key) is value for key, value in before.items())
