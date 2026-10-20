"""Compact control equivalence, real local execution, transport and isolation checks."""
from __future__ import annotations

import ast
import copy
import json
import multiprocessing
import subprocess

import httpx
import pytest
from test_dev_probe_action_replay import restore
from test_dev_probe_cases import ExecutingProbe
from test_dev_probes import context
from test_dev_tools import mutation_call, read_calls
from test_evidence_recovery import probe
from test_verification_scope_state import observation, unbound

from diagnostics import verification_state_off as off
from diagnostics import verification_state_panel as panel
from patchloop.dev import evidence_focus, model, reproduction, runner
from patchloop.dev.contracts import RequestedTool
from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.tools import dev_tool_schemas
from patchloop.errors import ContractError
from patchloop.util import canonical_json


@pytest.fixture(autouse=True)
def no_provider(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("provider requests forbidden")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
    monkeypatch.setattr(runner, "load_exact_openai_api_key", forbidden)


def legacy_function(path, name, namespace):
    text = subprocess.check_output(["git", "show", off.LEGACY + ":" + path], text=True)
    node = next(n for n in ast.parse(text).body
                if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), path, "exec"), namespace)
    return namespace[name]


def test_off_matches_old_semantics_and_only_renames_concerns():
    old_review = legacy_function("patchloop/dev/reproduction.py", "review",
                                 {"call_identity": reproduction.call_identity})
    old_project = legacy_function("patchloop/dev/evidence_focus.py", "project_interpretations",
                                  dict(evidence_focus.__dict__))
    cases = [
        [], [unbound(), unbound("suite", "run_check")], [observation()],
        [observation(), observation("again", matched=True)],
        [observation(), observation("changed", matched=True, value=2)],
        [observation(), observation("fixed", diff="D2", matched=True)],
        [observation(case=f"case-{n}", matched=True) for n in range(4)] + [observation()],
    ]
    for events in cases:
        for diff in ("D1", "D2", "unseen"):
            assert off.legacy_review(events, diff) == old_review(events, diff)
    for verification in ({}, {"unresolved_ids": [], "items": [{
        "concern_id": "v", "status": "dismissed",
        "decision": {"outcome": "dismissed", "reason": "failure remains"},
    }]}):
        before = {"current_diff": {"patch_hash": "D1"}, "working_notes": {
            "verification": verification}, "working_plan": {"text": "unchanged"}}
        left, right = copy.deepcopy(before), copy.deepcopy(before)
        old_project(left, [])
        off.legacy_interpretations(right, [])
        assert left == right
        off.legacy_interpretations(right, [])
        assert left == right


@pytest.mark.parametrize("arm", ["A", "B"])
def test_fixed_local_probe_restart_handoff_and_finish_are_executable(
    gateway_factory, smoke_package, arm,
):
    original_prompt = model.DEV_SYSTEM_PROMPT
    schemas = dev_tool_schemas(finish_enabled=True, allowed_tools=["run_probe", "finish_task"])
    with off.assigned(arm):
        gateway, journal, workspace = gateway_factory()
        backend = ExecutingProbe()
        gateway.probe_sandbox = backend
        first = gateway.execute(probe(gateway.public_task))
        assert first.output["reproduction"]["comparison"] == "mismatched"
        invalid = probe(gateway.public_task, "invalid")
        invalid.arguments["reproduction"]["entrypoint"] = "not a qualified entrypoint"
        assert gateway.execute(invalid).status == "failed" and backend.calls == 1
        gateway.execute_batch(read_calls())
        assert gateway.execute(mutation_call(gateway)).status == "succeeded"
        gateway = restore(gateway, journal, workspace, gateway.public_task, backend)
        replay_call = probe(gateway.public_task, "recheck", replay="original")
        replay = gateway.execute(replay_call)
        assert replay.output["reproduction"]["comparison"] == "matched"
        assert gateway.execute(replay_call).replayed and backend.calls == 2
        view = compact_model_state(context(gateway, smoke_package), [])
        review = view["reproduction_review"]
        assert review["items"][0]["comparison_status"] == "mismatch_to_match"
        assert ("required" in review) is (arm == "B")
        if arm == "B":
            assert review["required"]["status"] == "UNKNOWN"
            assert review["items"][0]["evidence"]["status"] == "SUPPORTED"
        view["working_notes"]["verification"] = {
            "unresolved_ids": [], "items": [{"concern_id": "v", "status": "dismissed"}]}
        project = off.legacy_interpretations if arm == "A" else off._ON_PROJECT
        project(view, [])
        concern = view["working_notes"]["verification"]["items"][0]
        assert ("model_position" in concern) is (arm == "B")
        assert ("status" in concern) is (arm == "A")
        wire = assemble_model_input(system_prompt=off.prompt(arm), state=view, history=[],
                                    context_policy="segmented-v1")
        changed = copy.deepcopy(view)
        changed["working_plan"] = {"text": "changed model plan"}
        for previous in (wire, None):  # Native update and fresh result/size entry.
            next_wire = assemble_model_input(
                system_prompt=off.prompt(arm), state=changed, history=[],
                previous_input=previous, context_policy="segmented-v1")
            hydrated = reconstruct_state(next_wire, context_policy="segmented-v1")
            assert hydrated["reproduction_review"] == review
            assert hydrated["working_notes"]["verification"]["items"][0] == concern
        finish = RequestedTool(name="finish_task", action_id="finish", arguments={
            "assessment": "Current parser reproduction and public regression pass."})
        assert gateway.execute(finish).status == "failed"  # Existing check gate retained.
        for check in gateway.public_task.visible_checks:
            result = gateway.execute(RequestedTool(name="run_check", action_id="check-" + check.id,
                                                   arguments={"check_id": check.id}))
            assert result.status == "succeeded"
        done = gateway.execute(finish.model_copy(update={"action_id": "finish-checked"}))
        assert done.status == "succeeded", done
        assert done.output["reproduction_review"] == gateway.reproduction_review(
            diff_hash=gateway.current_diff_hash)
        assert dev_tool_schemas(
            finish_enabled=True, allowed_tools=["run_probe", "finish_task"]) == schemas
    assert original_prompt == model.DEV_SYSTEM_PROMPT


def test_off_no_probe_inclusion_and_exception_restore(gateway_factory, smoke_package):
    gateway, _, _ = gateway_factory()
    baseline = context(gateway, smoke_package)
    assert "reproduction_review" in baseline
    with pytest.raises(RuntimeError), off.assigned("A"):
        off_view = context(gateway, smoke_package)
        assert {k: v for k, v in baseline.items() if k != "reproduction_review"} == off_view
        raise RuntimeError("exercise cleanup")
    assert context(gateway, smoke_package) == baseline
    with pytest.raises(ContractError), off.assigned("C"):
        pass


def _child_arm(queue, arm):
    with off.assigned(arm):
        queue.put({"prompt": model.DEV_SYSTEM_PROMPT,
                   "review": reproduction.review([], "D1")})


def test_spawned_off_cannot_contaminate_on():
    ctx = multiprocessing.get_context("spawn")
    for arm in "AB":
        queue = ctx.Queue()
        process = ctx.Process(target=_child_arm, args=(queue, arm))
        process.start()
        value = queue.get(timeout=20)
        process.join(20)
        assert process.exitcode == 0
        assert value["prompt"] == off.prompt(arm)
        assert ("required" in value["review"]) is (arm == "B")
        queue.close()
    assert off.prompt("B") == model.DEV_SYSTEM_PROMPT


def test_initial_pair_rejects_unassigned_schema_time_and_budget_changes():
    from patchloop.dev import thin_policy
    from patchloop.task_loader import load_public_task

    public = load_public_task(panel.repository_root() / panel.TASK)
    wires = {}
    for arm in "AB":
        with off.assigned(arm):
            state = {
                "public_task": public.model_dump(mode="json"),
                "current_diff": {"patch": "", "patch_hash": "D1"},
                "segment_handoff": {"segment_id": "derived-" + arm},
                "remaining_budget": {"wall_time_seconds": 1800},
                "reproduction_review": reproduction.review(
                    [], "D1", public_task=public),
                "working_notes": {"verification": {
                    "items": [], "unresolved_ids" if arm == "A" else "model_open_concern_ids": []}},
            }
            wires[arm] = {"input": assemble_model_input(
                system_prompt=thin_policy.system_prompt(
                    "current", "brief-v1", history_search_policy="public-v1"),
                state=state, history=[], context_policy="segmented-v1"),
                "tools": [{"name": "unchanged", "strict": True}], "max_output_tokens": 25000}
    assert panel.initial_pair(wires)["tools_equal"]
    for mutate in ("schema", "time"):
        bad = copy.deepcopy(wires)
        if mutate == "schema":
            bad["A"]["tools"][0]["strict"] = False
        else:
            frame = json.loads(bad["A"]["input"][-1]["content"])
            frame["state"]["remaining_budget"]["wall_time_seconds"] -= 1
            bad["A"]["input"][-1]["content"] = canonical_json(frame)
        with pytest.raises(ContractError):
            panel.initial_pair(bad)
