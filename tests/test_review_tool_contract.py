"""Exercise reviewer projection and admission together, without executing a sandbox."""
import copy
import json
from types import SimpleNamespace

import pytest

from diagnostics import review_context_rehearsal as review
from diagnostics.checkpoint_continuation import ScriptedClient
from patchloop.dev.contracts import DevLimits
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.errors import ContractError


@pytest.fixture
def context(smoke_package, monkeypatch):
    loaded = SimpleNamespace(package=smoke_package, diff={"patch_hash": "candidate"}, checks=[],
        envelope=SimpleNamespace(model="gpt-5.4-2026-03-05", reasoning_effort="xhigh",
            max_output_tokens=25000, limits=DevLimits(), probe_policy="none"),
        bundle={"request": {"model": "gpt-5.4-2026-03-05", "input": [
            {"role": "system", "content": "original system"},
            {"role": "user", "content": "original trajectory"}],
            "tools": dev_tool_schemas(finish_enabled=True, planning_policy="brief-v1",
                allowed_tools=["read_file", "search_files", "run_probe", "replace_text"]),
            "parallel_tool_calls": True, "tool_choice": "required", "max_output_tokens": 25000}})
    executed = []

    class Gateway:
        def __init__(self, **kwargs):
            pass

        def execute(self, call):
            executed.append(call.name)
            return SimpleNamespace(model_dump=lambda **kw: {"observed": "scripted"})

    monkeypatch.setattr(review, "DevToolGateway", Gateway)
    monkeypatch.setattr(review, "admitted_probe", lambda *args: SimpleNamespace(identity={}))
    monkeypatch.setattr(review.runner, "_batch_execution_abort", lambda results: (None, None))
    return loaded, executed


def tool(name, index):
    if name == "finish_review":
        args = dict.fromkeys(("suspected_behavior", "evidence", "observation", "limitations"),
                             "No execution claim")
        args["candidate_hash"] = "candidate"
    else:
        mode = "verify" if name == "run_probe" else "inspect"
        args = {"turn_decision": {"mode": mode, "basis": "Contract test",
            "evidence_goal": "Inspect public source" if mode == "inspect" else None,
            "memory_update": None, "plan_update": None}}
    return {"name": name, "action_id": f"call_{index}", "arguments": args}


CASES = [
    (["read_file"], None, True),
    (["read_file", "search_files", "read_file", "search_files"], None, True),
    (["run_probe"], None, True), (["finish_review"], None, True),
    (["read_file", "run_probe"], None, False),
    (["run_probe", "read_file"], None, False),
    (["run_probe", "run_probe"], None, False),
    (["read_file"] * 5, None, False),
    (["read_file", "finish_review"], None, False),
    (["finish_review", "finish_review"], None, False),
    (["replace_text"], None, False), (["run_check"], None, False),
    (["stop_task"], None, False), (["shell"], None, False),
    (["read_file", "search_files"], "missing_decision", False),
    (["read_file", "search_files"], "wrong_mode", False),
    (["read_file", "search_files"], "missing_goal", False),
    (["read_file", "search_files"], "memory_update", False),
    (["read_file", "search_files"], "plan_update", False),
    (["read_file", "search_files"], "duplicate_id", False),
    (["finish_review"], "wrong_candidate", False),
    ([], None, False),
]


@pytest.mark.parametrize("arm", ["A", "B"])
@pytest.mark.parametrize("names,fault,accepted", CASES)
def test_projected_contract_and_whole_batch_admission(
    context, tmp_path, arm, names, fault, accepted,
):
    loaded, executed = context
    original = copy.deepcopy(loaded.bundle)
    batch = [tool(name, i) for i, name in enumerate(names)]
    if fault == "duplicate_id":
        batch[-1]["action_id"] = batch[0]["action_id"]
    elif fault == "wrong_candidate":
        batch[-1]["arguments"]["candidate_hash"] = "old candidate"
    elif fault == "missing_decision":
        batch[-1]["arguments"].pop("turn_decision")
    elif fault:
        decision = batch[-1]["arguments"]["turn_decision"]
        if fault == "wrong_mode":
            decision.update(mode="verify", evidence_goal=None)
        elif fault == "missing_goal":
            decision["evidence_goal"] = None
        else:
            decision[fault] = "unsupported annotation"
    client = ScriptedClient([batch, [tool("finish_review", "end")]])
    args = (loaded, arm, tmp_path / "review", tmp_path, client,
            review.offline.SharedBudget(), DevJournal(tmp_path / "panel", "run_dev_matrix"))
    if accepted:
        result = review.scripted_review(*args, execute_probes=True)
        assert result["subject_candidate_hash"] == "candidate"
        assert executed == [n for n in names if n != "finish_review"]
    else:
        with pytest.raises(review.offline.ReviewStopped) as error:
            review.scripted_review(*args, execute_probes=True)
        assert not executed  # Even an invalid second call prevents the first execution.
        assert error.value.billing_known and error.value.settled_cost_nanos > 0
        assert len(client.created) == 1
    request = client.created[0]
    assert "Never mix these shapes" in request["input"][0]["content"]
    assert {t["name"] for t in request["tools"]} == {
        "read_file", "search_files", "run_probe", "finish_review"}
    for definition in request["tools"]:
        if definition["name"] == "finish_review":
            continue
        fields = definition["parameters"]["properties"]["turn_decision"]["properties"]
        assert fields["memory_update"] == fields["plan_update"] == {"type": "null"}
    assert loaded.bundle == original
    assert "review_budget" in json.loads(request["input"][-1]["content"])


def test_disabled_probe_is_not_offered_or_executed(context, tmp_path):
    loaded, executed = context
    client = ScriptedClient([[tool("run_probe", 0)]])
    with pytest.raises(review.offline.ReviewStopped):
        review.scripted_review(loaded, "B", tmp_path / "review", tmp_path, client,
            review.offline.SharedBudget(), DevJournal(tmp_path / "panel", "run_dev_no_probe"))
    assert not executed
    assert "run_probe" not in {t["name"] for t in client.created[0]["tools"]}


@pytest.mark.parametrize("arm", ["A", "B"])
def test_separate_inspection_probe_and_report(context, tmp_path, arm):
    loaded, executed = context
    client = ScriptedClient([[tool("read_file", 0)], [tool("run_probe", 1)],
                             [tool("finish_review", 2)]])
    report = review.scripted_review(loaded, arm, tmp_path / "review", tmp_path, client,
        review.offline.SharedBudget(), DevJournal(tmp_path / "panel", "run_dev_sequence"),
        execute_probes=True)
    assert executed == ["read_file", "run_probe"]
    assert report["subject_candidate_hash"] == "candidate"
    outputs = [i for i in client.created[-1]["input"] if i.get("type") == "function_call_output"]
    assert [i["call_id"] for i in outputs] == ["call_0", "call_1"]
    assert len(client.created) == len(client.counted) == 3


@pytest.mark.parametrize("seconds", [180, 360])
def test_review_time_allowance_controls_horizon_and_execution(context, tmp_path, seconds):
    loaded, executed = context
    now = [0.0]
    budget = review.offline.SharedBudget(review_seconds=seconds, clock=lambda: now[0])
    client = ScriptedClient([[tool("read_file", 0)], [tool("finish_review", 1)]])
    original = client.responses.create

    def delayed(**kwargs):
        assert kwargs["timeout"] == seconds - now[0]
        response = original(**kwargs)
        now[0] += 200 if len(client.created) == 1 else 30
        return response

    client.responses.create = delayed
    args = (loaded, "B", tmp_path / "review", tmp_path, client, budget,
            DevJournal(tmp_path / "panel", "run_dev_reviewtime"))
    if seconds == 180:
        with pytest.raises(review.offline.ReviewStopped, match="review time exhausted"):
            review.scripted_review(*args)
        assert executed == [] and len(client.created) == 1
    else:
        report = review.scripted_review(*args)
        assert report["subject_candidate_hash"] == "candidate"
        assert executed == ["read_file"] and len(client.created) == 2
        assert json.loads(client.created[-1]["input"][-1]["content"])[
            "review_budget"]["remaining_seconds"] == 160
    assert json.loads(client.created[0]["input"][-1]["content"])[
        "review_budget"]["remaining_seconds"] == seconds
    now[0] = seconds
    with pytest.raises(ContractError, match="episode stopped" if seconds == 180
                       else "review time exhausted"):
        budget._ready()
