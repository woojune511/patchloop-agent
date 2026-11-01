"""Small local controls for OFF parity, shared phases and before/after delivery."""

from __future__ import annotations

import json
import subprocess

import pytest
from frozen_stage_support import pin_pre_stage_prompt
from test_dev_probe_action_replay import restore
from test_dev_probe_cases import TEXT, ExecutingProbe, mock_request
from test_dev_tools import mutation_call, read_calls
from test_probe_purpose import original_intent, probe
from test_verification_role import report
from test_verification_state_comparison import frozen_prompt, legacy_function

from diagnostics import probe_invocation_control as control
from diagnostics import probe_invocation_execution as execution
from diagnostics import probe_invocation_panel as panel
from diagnostics import probe_invocation_qualification as qualification
from diagnostics import verification_role as role
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import original_obligation, reproduction, runner, segments
from patchloop.dev.contracts import DevLimits, DevModelTurn, RequestedTool
from patchloop.dev.conversation import SEGMENT_RULES, assemble_model_input, reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes, sha256_json

OFF_SOURCE = (
    f"from mini_data_utils.csvlite import parse_rows\nrecord_observation(parse_rows({TEXT!r}))"
)
ON_REVIEW_COMMIT = "1b7d53c713bb956234834779324c533cfd5a74e1"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    pin_pre_stage_prompt(monkeypatch)
    monkeypatch.setattr("socket.socket.connect", lambda *a, **k: pytest.fail("offline only"))
    # Retain the closed treatment's review prose while current completion is tested separately.
    monkeypatch.setattr(control, "_REVIEW", legacy_function(
        "patchloop/dev/reproduction.py", "review", dict(vars(reproduction)), ref=ON_REVIEW_COMMIT,
    ))
    with frozen_prompt(control.BASE):
        yield


def test_off_executes_legacy_channel_and_restores_scope(gateway_factory):
    source = subprocess.check_output(
        ["git", "show", control.BASE + ":patchloop/dev/reproduction.py"],
        cwd=repository_root(),
        text=True,
    )
    baseline = {}
    exec(compile(source, "pinned-off-baseline", "exec"), baseline)
    original = reproduction.DESCRIPTION, reproduction.selection, reproduction.review
    gateway, journal, _ = gateway_factory()
    gateway.probe_sandbox = ExecutingProbe()
    with control.assigned("A"):
        assert baseline["DESCRIPTION"] == reproduction.DESCRIPTION
        call = probe(gateway.public_task, source=OFF_SOURCE)
        assert reproduction.selection(call.arguments) == baseline["selection"](call.arguments)
        before = gateway.execute(call)
        binding = before.output["reproduction"]["binding"]
        assert binding["definition"]["observation_channel"] == "record-observation-v1"
        wrapped = reproduction.program(OFF_SOURCE, binding)
        assert wrapped == baseline["program"](OFF_SOURCE, binding)
        assert "def call_target" not in wrapped
        assert before.output["reproduction"]["comparison"] == "mismatched"
        gateway.execute_batch(read_calls())
        gateway.execute(mutation_call(gateway))
        after = gateway.execute(probe(gateway.public_task, "after", replay="original"))
        assert after.output["reproduction"]["comparison"] == "matched"
        review = gateway.reproduction_review(diff_hash=gateway.current_diff_hash)
        # The gateway's new completion projection is outside this historical comparison.
        assert {k: v for k, v in review.items() if k != "completion"} == baseline["review"](
            journal.events(), gateway.current_diff_hash, public_task=gateway.public_task
        )
        assert after.output["execution_source_hash"] == sha256_bytes(wrapped.encode())
    assert original == (reproduction.DESCRIPTION, reproduction.selection, reproduction.review)
    with pytest.raises(RuntimeError), control.assigned("A"):
        raise RuntimeError("cleanup")
    assert original == (reproduction.DESCRIPTION, reproduction.selection, reproduction.review)
    assert role._ACTIVE is False


def test_off_old_pending_purpose_preserves_channel_binding_and_once_execution(gateway_factory):
    gateway, journal, workspace = gateway_factory()
    backend = gateway.probe_sandbox = ExecutingProbe()
    call = probe(gateway.public_task, source=OFF_SOURCE)
    call.arguments["purpose"].pop("reported_failure_json")
    call.arguments["purpose"]["requirement_quote"] = gateway.public_task.issue.description
    with control.assigned("A"):
        with pytest.raises(ContractError, match="reported_failure_json"):
            reproduction.selection(call.arguments)
        raw, channel = reproduction.selection(call.arguments, allow_legacy=True)
        assert channel == reproduction.OBSERVATION_CHANNEL
        binding = reproduction.bind(raw, gateway.public_task, OFF_SOURCE, call.action_id,
                                    observation_channel=channel)
        decision = call.turn_decision.model_dump(mode="json")
        input_hash = sha256_json({"tool": call.name, "arguments": call.arguments,
                                  "turn_decision": decision})
        journal.append("action_started", {
            "action_id": call.action_id, "input_hash": input_hash, "tool": call.name,
            "arguments": call.arguments, "turn_decision": decision,
            "baseline_diff_hash": gateway.current_diff_hash, "reproduction_binding": binding,
            "probe_request": {"policy": original_obligation.PROBE_STAGES,
                              "status": "accepted", "kind": "original_requirement"},
        })
        current = restore(gateway, journal, workspace, gateway.public_task, backend)
        result = current.execute(call)
        assert result.status == "succeeded", result
        observed = result.output["reproduction"]
        assert observed["binding"] == binding and observed["comparison"] == "mismatched"
        assert "declared_failure_comparison" not in observed
        assert backend.sources == [reproduction.program(OFF_SOURCE, binding)]
        assert current.execute(call).replayed and backend.calls == 1


@pytest.mark.parametrize("arm", ["A", "B"])
def test_shared_phase_before_after_and_two_reference_return(
    tmp_path, monkeypatch, smoke_package, arm
):
    # The model chooses the baseline; neither the controller nor the harness adds it.
    source = (OFF_SOURCE if arm == "A" else
              f"record_observation(observed_target()({TEXT!r}).value)")

    class Script(MockDevAdapter):
        baseline = False
        verification = 0

        def next_turn(self, context, tools):
            state = json.loads(context)
            if not self.baseline:
                self.baseline = True
                return DevModelTurn(tool_calls=[probe(smoke_package.public, source=source)])
            if state["verification_phase"]["phase"] != "verify":
                return super().next_turn(context, tools)
            self.verification += 1
            if self.verification == 1:
                return DevModelTurn(
                    tool_calls=[probe(smoke_package.public, "after", replay="original")]
                )
            if self.verification == 2:
                return DevModelTurn(
                    tool_calls=[
                        RequestedTool(
                            name="read_file",
                            action_id="select",
                            arguments={"path": self.mutation.path, "start_line": 1, "end_line": 80},
                            turn_decision={
                                "mode": "inspect",
                                "basis": "Compare before and after.",
                                "evidence_goal": "Preserve both observations and their scope.",
                                "memory_update": {
                                    "findings": [],
                                    "open_question": {
                                        "text": "Does the same input satisfy the expectation?",
                                        "evidence": [
                                            {
                                                "kind": "tool_result",
                                                "action_id": "original",
                                                "role": "primary",
                                            },
                                            {
                                                "kind": "tool_result",
                                                "action_id": "after",
                                                "role": "countercheck",
                                            },
                                        ],
                                    },
                                },
                            },
                        )
                    ]
                )
            return DevModelTurn(tool_calls=[report()])

    backend = ExecutingProbe()
    monkeypatch.setattr(runner, "MockDevAdapter", Script)
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    request = mock_request(tmp_path, policy="none").model_copy(
        update={
            "enable_probes": True,
            "context_policy": "segmented-v1",
            "planning_policy": "brief-v1",
            "history_search_policy": "public-v1",
            "limits": DevLimits(max_accepted_mutations=4),
        }
    )
    with control.assigned(arm):
        result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS", result
    # The current original-reproduction policy also replays the invocation-bound
    # case after editing in B. It is a registered host action, not a model call.
    assert backend.calls == (3 if arm == "B" else 2)
    assert all(source == backend.sources[0] for source in backend.sources)
    (path,) = (request.state_root / "runs").glob("*.jsonl")
    journal, store = (
        DevJournal(request.state_root, path.stem),
        ArtifactStore(request.state_root / "artifacts"),
    )
    events = journal.events()
    phases = [e["payload"] for e in events if e["event_type"] == role.PHASE_EVENT]
    assert [p["phase"] for p in phases] == ["initial", "verify", "final"]
    assert all(p["stream"] == "repair" and p["arm"] == "A" for p in phases)
    receipts = [
        e["payload"]["result"]
        for e in events
        if e["event_type"] == "action_finished" and e["payload"]["result"]["tool"] == "run_probe"
    ]
    assert [r["output"]["reproduction"]["comparison"] for r in receipts] == (
        ["mismatched", "matched", "matched"] if arm == "B" else ["mismatched", "matched"])
    assert [r["action_id"] for r in receipts if not r["action_id"].startswith(
        "completion-reproduction-")] == ["original", "after"]
    rows = []
    for event, phase, _ in role.phased_events(events):
        if event["event_type"] != "turn_started":
            continue
        items = json.loads(
            store.read_bytes(Artifact.model_validate(event["payload"]["model_input_artifact"]))
        )
        state = reconstruct_state(items, context_policy="segmented-v1")
        _, exchanges, _ = SEGMENT_RULES.inventory(items)
        ids = sorted(
            {v["call_id"] for v in exchanges.values() if v["type"] == "function_call_output"}
        )
        assert not segments.size_reasons(event["payload"]["context_request_sizes"])
        rows.append(
            {
                "sequence": event["sequence"],
                "phase": phase,
                "input": event["payload"]["model_input_artifact"],
                "delivered_receipts": ids,
                "source_lines": qualification.phase.ranges(
                    qualification.phase.exposed({"input": items})[0]
                ),
                "review": state["reproduction_review"],
                "question": state["working_notes"]["open_question"],
                "sizes": event["payload"]["context_request_sizes"],
            }
        )
    final = rows[-1]
    assert {"original", "after"} <= set(final["delivered_receipts"])
    assert len(final["question"]["evidence"]) == 2
    assert all(v["evidence_delivery"] == "complete" for v in final["question"]["evidence"])
    review = final["review"]["items"][0]
    assert review["comparison_status"] == "mismatch_to_match"
    assert ("execution_link" in review["latest"]) is (arm == "B")
    qualification.save(
        tmp_path,
        "invocation-local.json",
        {
            "arm": arm,
            "passed": True,
            "terminal": result["terminal"],
            "phases": phases,
            "inputs": rows,
            "model_calls": runner._restore_counters(journal).model_calls,
            "source_chars": len(source),
            "wrapped_chars": len(backend.sources[0]),
            "probe_calls": backend.calls,
            "provider_calls": 0,
            "input_count_calls": 0,
        },
    )


def test_capacity_supports_original_and_countercondition(gateway_factory):
    # A meaningful original input and a normal-input control fit together.
    source = (
        f"a=observed_target()({TEXT!r}).value\n"
        "b=observed_target()('h,v\\na,b\\n').value\nrecord_observation([a,b])"
    )
    gateway, _, _ = gateway_factory()
    gateway.probe_sandbox = ExecutingProbe()
    definition, channel = reproduction.selection(
        {"purpose": {"kind": "original_requirement", **original_intent(gateway.public_task)}}
    )
    binding = reproduction.bind(
        definition, gateway.public_task, source, "capacity", observation_channel=channel
    )
    assert len(reproduction.program(source, binding)) < 8000
    result = gateway.execute(probe(gateway.public_task, "capacity", source=source))
    trace = result.output["reproduction"]["call_observation"]
    assert result.status == "succeeded" and len(trace["calls"]) == 2
    assert trace["incomplete"] is False
    assert result.output["reproduction"]["observed_json"] is not None


def test_new_packet_initializer_and_qualification_are_mandatory(monkeypatch, tmp_path):
    from diagnostics import parallel_dev_batch

    calls = []
    monkeypatch.setattr(parallel_dev_batch, "initialize_worker", lambda *args: calls.append(args))
    for arm in "AB":
        execution.initializer(arm)("stop", "admission")
        try:
            assert role._ACTIVE
            assert (reproduction.DESCRIPTION == control.DESCRIPTION) is (arm == "A")
        finally:
            control._WORKER_SCOPE.__exit__(None, None, None)
    assert calls == [("stop", "admission")] * 2
    assert panel.SCHEMA != panel.common.SCHEMA
    missing = tmp_path / "validation.json"
    missing.write_text("{}", encoding="utf-8")
    with pytest.raises(ContractError, match="qualification"):
        panel.freeze(tmp_path, tmp_path / "live", missing)
    assert panel.allocation(3)["total_cap_usd"] == "5.28"
    assert control.contract()["role_mode"] == {"A": "A", "B": "A"}
    monkeypatch.setattr(panel, "validate", lambda *a: {"rows": [{"public_id": "p", "arm": "B"}]})
    missing.write_text(json.dumps({"rows": [{"public_id": "p", "invocation": {"arm": "A"}}]}))
    with execution.configured(), pytest.raises(ContractError, match="assignment"):
        execution.common.seal(tmp_path, "digest", missing)


def test_input_comparison_rejects_schema_budget_and_prompt_confounders():
    import copy

    state = {
        "public_task": {"issue": {"title": "Shared public task"}},
        "current_diff": {"patch": ""},
        "reproduction_review": {"items": []},
    }
    wires = {
        a: {
            "input": assemble_model_input(
                system_prompt="shared", state=state, history=[], context_policy="segmented-v1"
            ),
            "max_output_tokens": 25000,
            "tools": [{"name": "run_probe", "description": d, "parameters": {"type": "object"}}],
        }
        for a, d in (("A", control.DESCRIPTION), ("B", reproduction.DESCRIPTION))
    }
    assert panel.initial_pair(wires)["common_state_and_schemas_equal"]
    for field in ("schema", "budget", "prompt"):
        changed = copy.deepcopy(wires)
        if field == "schema":
            changed["B"]["tools"][0]["parameters"]["type"] = "string"
        elif field == "budget":
            changed["B"]["max_output_tokens"] = 25001
        else:
            changed["B"]["input"][0]["content"] = "different instruction"
        with pytest.raises(ContractError, match="difference"):
            panel.initial_pair(changed)
