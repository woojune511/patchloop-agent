from __future__ import annotations

import copy
import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
from test_dev_tools import mutation_call, read_calls

from diagnostics import fresh_state_rollout as rollout
from patchloop.agent.model import (
    EncryptedReasoningContinuationItem,
    FunctionCallContinuationRef,
    ModelTurn,
)
from patchloop.agent.model import (
    RequestedTool as RawTool,
)
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner as loop
from patchloop.dev.contracts import DevModelTurn, PublicTurnDecision, RequestedTool
from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_json, utc_now


@pytest.fixture
def branch(gateway_factory):
    gateway, journal, _ = gateway_factory()
    active = rollout.ActiveClock()
    gateway.deadline = ExecutionDeadline.from_remaining(1477, clock=active)
    return rollout.Branch(
        "B1",
        journal,
        ArtifactStore(journal.root / "artifacts"),
        gateway,
        loop._RunCounters(),
        active,
        0,
    )


def start(branch, label, calls):
    context = loop._build_context(
        package=SimpleNamespace(public=branch.gateway.public_task),
        gateway=branch.gateway,
        journal=branch.journal,
        correction=None,
        latest_tool_results=branch.latest,
        counters=branch.counters,
        elapsed_seconds=0,
        limits=branch.gateway.limits,
    )
    policy = loop._tool_policy(branch.gateway, branch.counters, branch.gateway.limits)
    items = assemble_model_input(
        system_prompt=loop.DEV_SYSTEM_PROMPT, state=json.loads(context), history=[]
    )
    ref = branch.store.put_text(canonical_json(items), "application/json")
    branch.journal.append(
        "turn_started",
        {
            "turn_id": label,
            "model_input_artifact": ref.model_dump(mode="json"),
            "model_input_hash": ref.content_hash,
            "native_history": loop.history_metadata(items),
            "available_tool_names": sorted(policy.allowed_tools),
            "workflow_gate": policy.workflow_gate,
        },
    )
    branch.counters.model_calls += 1
    branch.accept(label, DevModelTurn(tool_calls=calls), policy)


class Adapter:
    def __init__(self, calls, *, count=1000, failure=None, mutate=False, mismatch=False):
        self.config = rollout.shared.model_config("medium")
        self.client = SimpleNamespace(max_retries=0)
        self.calls, self.count = calls, count
        self.failure, self.mutate, self.mismatch = failure, mutate, mismatch
        self.sequence = []

    def request_payload(self, items, schemas, **_):
        return {
            "model": rollout.shared.MODEL,
            "input": items,
            "tools": schemas,
            "store": False,
            "reasoning": {"effort": "medium"},
            "include": ["reasoning.encrypted_content"],
            "max_output_tokens": 25000,
        }

    def count_input_tokens_v2(self, request, **_):
        self.sequence.append("count")
        if self.failure == "count":
            raise TimeoutError("SECRET_SDK_ERROR_SENTINEL")
        if self.mutate:
            request["tools"].reverse()
        return self.count

    def execute_request(self, request, **_):
        self.sequence.append("create")
        if self.failure == "create":
            raise TimeoutError("SECRET_SDK_ERROR_SENTINEL")
        raw_calls = [
            RawTool(c.name, c.action_id, loop._provider_tool_arguments(c)) for c in self.calls
        ]
        return ModelTurn(
            tool_calls=raw_calls,
            input_tokens=self.count + int(self.mismatch),
            cached_input_tokens=0,
            output_tokens=100,
            reasoning_output_tokens=20,
            response_model=rollout.shared.MODEL,
            response_id="response-test",
            response_status="completed",
            output_item_types=("reasoning", "function_call"),
            provider_continuation=(
                EncryptedReasoningContinuationItem("r-new", "cipher-new"),
                *(FunctionCallContinuationRef(c.action_id) for c in self.calls),
            ),
        )


def ledger(cap="1.20"):
    return DevCostLedger(Decimal(cap), pricing_for_model(rollout.shared.MODEL))


def test_active_clock_excludes_other_branches_and_preserves_deadline():
    now = [100.0]
    active = rollout.ActiveClock(lambda: now[0])
    deadline = ExecutionDeadline.from_remaining(10, clock=active)
    with active.active():
        now[0] += 3
        assert deadline.check() == 7
    now[0] += 1000
    assert deadline.check() == 7
    with active.active():
        now[0] += 2
    assert deadline.check() == 5


def test_full_gateway_read_mutation_check_finish(branch):
    start(branch, "r", read_calls())
    start(branch, "m", [mutation_call(branch.gateway)])
    start(
        branch,
        "c",
        [
            RequestedTool(
                name="run_check",
                action_id="c",
                arguments={"check_id": "existing-unit-tests"},
                turn_decision=PublicTurnDecision(mode="verify", basis="Check repaired source"),
            )
        ],
    )
    start(
        branch,
        "f",
        [
            RequestedTool(
                name="finish_task",
                action_id="f",
                arguments={},
                turn_decision=PublicTurnDecision(mode="finish", basis="Public check passed"),
            )
        ],
    )
    assert branch.terminal["terminal"] == "PUBLIC_CHECKS_SUBMITTED"
    assert branch.terminal["task_acceptance"] == "NOT_RUN"
    assert branch.terminal["safety_state"] == "NOT_RUN"
    assert branch.terminal["submitted_artifact"]["content_hash"] == branch.gateway.current_diff_hash
    assert branch.new_tools == 5


def test_native_seed_prefix_unchanged_and_new_reasoning_once(branch):
    start(branch, "r", read_calls())
    adapter = Adapter([mutation_call(branch.gateway)])
    package = SimpleNamespace(public=branch.gateway.public_task)
    prepared = branch.prepare_request(package, adapter)
    before = copy.deepcopy(prepared[1]["input"])
    rollout.dispatch(branch, adapter, ledger(), prepared)
    after = branch.prepare_request(package, Adapter([]))[1]["input"]
    assert after[: len(before)] == before
    assert sum(i.get("encrypted_content") == "cipher-new" for i in after) == 1
    call_ids = [i["call_id"] for i in after if i.get("type") == "function_call"]
    output_ids = [i["call_id"] for i in after if i.get("type") == "function_call_output"]
    assert call_ids == output_ids
    state = reconstruct_state(after)
    assert state["current_diff"]["patch_hash"] == branch.gateway.current_diff_hash
    assert state["followup_state_contract"] == rollout.STATE_NOTICE
    assert adapter.sequence == ["count", "create"]


@pytest.mark.parametrize("failure", ["count", "create"])
def test_transport_failure_never_retries_or_executes_tools(branch, failure):
    start(branch, "r", read_calls())
    calls = branch.new_tools
    adapter = Adapter([mutation_call(branch.gateway)], failure=failure)
    prepared = branch.prepare_request(SimpleNamespace(public=branch.gateway.public_task), adapter)
    with pytest.raises(rollout.AbortExperiment) as error:
        rollout.dispatch(branch, adapter, ledger(), prepared)
    assert error.value.code == (
        "COUNT_TIMEOUT_OR_UNKNOWN" if failure == "count" else "PROVIDER_TIMEOUT_OR_UNKNOWN"
    )
    assert branch.new_tools == calls
    assert "SECRET_SDK_ERROR_SENTINEL" not in branch.journal.path.read_text()


@pytest.mark.parametrize(
    "cap,count,expected",
    [
        ("0.01", 1000, "COST_CAP_REACHED"),
        ("1.20", 272001, "INPUT_LIMIT_EXCEEDED"),
    ],
)
def test_full_output_ceiling_never_lowered_to_fit(branch, cap, count, expected):
    start(branch, "r", read_calls())
    adapter = Adapter([], count=count)
    prepared = branch.prepare_request(SimpleNamespace(public=branch.gateway.public_task), adapter)
    with pytest.raises(rollout.AbortExperiment) as error:
        rollout.dispatch(branch, adapter, ledger(cap), prepared)
    assert error.value.code == expected
    assert adapter.sequence == ["count"]
    assert prepared[1]["max_output_tokens"] == 25000


def test_count_request_mutation_rejected_before_dispatch(branch):
    start(branch, "r", read_calls())
    adapter = Adapter([], mutate=True)
    prepared = branch.prepare_request(SimpleNamespace(public=branch.gateway.public_task), adapter)
    with pytest.raises(ContractError, match="altered"):
        rollout.dispatch(branch, adapter, ledger(), prepared)
    assert adapter.sequence == ["count"]


def test_usage_mismatch_cannot_execute_mutation(branch):
    start(branch, "r", read_calls())
    before = branch.gateway.current_diff_hash
    adapter = Adapter([mutation_call(branch.gateway)], mismatch=True)
    prepared = branch.prepare_request(SimpleNamespace(public=branch.gateway.public_task), adapter)
    with pytest.raises(rollout.AbortExperiment):
        rollout.dispatch(branch, adapter, ledger(), prepared)
    assert branch.gateway.current_diff_hash == before
    assert branch.journal.events()[-1]["payload"]["billing_known"] is False


@pytest.mark.parametrize(
    "boundary",
    [
        "provider_returned",
        "usage_recorded",
        "decision_recorded",
        "actions_finished",
        "batch_finished",
    ],
)
def test_crash_points_preserve_prior_usage_without_reexecuting(branch, boundary):
    start(branch, "r", read_calls())
    adapter = Adapter([mutation_call(branch.gateway)])
    prepared = branch.prepare_request(SimpleNamespace(public=branch.gateway.public_task), adapter)

    def crash(point):
        if point == boundary:
            raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        rollout.dispatch(branch, adapter, ledger(), prepared, checkpoint=crash)
    rows = branch.journal.events()
    finished = [r for r in rows if r["event_type"] == "provider_call_finished"]
    assert len(finished) == int(boundary != "provider_returned")
    assert adapter.sequence == ["count", "create"]
    restarted = DevToolGateway(
        workspace=branch.gateway.workspace,
        public_task=branch.gateway.public_task,
        sandbox=branch.gateway.sandbox,
        journal=branch.journal,
        limits=branch.gateway.limits,
    )
    assert restarted.accepted_mutations == int(boundary in {"actions_finished", "batch_finished"})


def test_horizon_blocks_before_counting(branch):
    start(branch, "r", read_calls())
    branch.counters.model_calls = 39
    adapter = Adapter([])
    prepared = branch.prepare_request(SimpleNamespace(public=branch.gateway.public_task), adapter)
    assert prepared is None
    assert branch.terminal["terminal"] == "LIMIT_REACHED"
    assert "model_calls" in branch.terminal["completion_horizon"]["blocking_resources"]
    assert adapter.sequence == []


def test_rejected_mutation_gets_exact_failure_then_next_current_context(branch):
    start(branch, "r", read_calls())
    call = mutation_call(branch.gateway)
    call.arguments["old_text"] = "not an observed anchor"
    start(branch, "m", [call])
    assert branch.latest[0].status == "failed"
    assert branch.gateway.accepted_mutations == 0
    prepared = branch.prepare_request(
        SimpleNamespace(public=branch.gateway.public_task), Adapter([])
    )
    state = reconstruct_state(prepared[1]["input"])
    assert state["last_failed_mutation"] is not None
    assert state["current_diff"]["patch_hash"] == branch.gateway.current_diff_hash


def test_imported_artifacts_preserve_bytes_and_source_but_rebind_paths(tmp_path):
    source, target = ArtifactStore(tmp_path / "source"), ArtifactStore(tmp_path / "target")
    ref = source.put_json({"encrypted_content": "cipher", "summary": []})
    raw = source.read_bytes(ref)
    imported = rollout.import_artifacts({"a": ref.model_dump(mode="json")}, target, [source])
    new_ref = ref.model_validate(imported["a"])
    assert target.read_bytes(new_ref) == source.read_bytes(ref) == raw
    assert new_ref.content_hash == ref.content_hash and new_ref.path != ref.path
    assert sha256_json(ref.model_dump(mode="json")) != sha256_json(imported["a"])
    with pytest.raises(ContractError, match="unregistered"):
        rollout.import_artifacts(ref.model_dump(mode="json"), target, [])


def test_missing_or_corrupt_cipher_fails_before_followup_provider(branch):
    start(branch, "r", read_calls())
    adapter = Adapter([mutation_call(branch.gateway)])
    package = SimpleNamespace(public=branch.gateway.public_task)
    rollout.dispatch(branch, adapter, ledger(), branch.prepare_request(package, adapter))
    record = next(
        e
        for e in branch.journal.events()
        if e["event_type"] == "turn_decision_recorded" and e["payload"].get("continuation_ref")
    )
    from pathlib import Path

    Path(record["payload"]["continuation_ref"]["artifact"]["path"]).write_bytes(b"bad")
    with pytest.raises(RecoveryError):
        branch.prepare_request(package, Adapter([]))


def test_reused_output_directory_rejected_before_initialization(branch, tmp_path):
    root = tmp_path / "already-used"
    root.mkdir()
    with pytest.raises(ContractError, match="external"):
        rollout.run(
            None,
            root,
            credential_file=rollout.repository_root() / ".env",
            cap=Decimal("1.20"),
            pricing_verified_on=utc_now().date().isoformat(),
            approved_hash=rollout.implementation_hash(),
            adapter_factory=lambda _: None,
        )


@pytest.mark.parametrize("failure", [None, "count", "create", "billing"])
def test_whole_driver_stops_all_branches_on_uncertainty(
    gateway_factory,
    tmp_path,
    monkeypatch,
    failure,
):
    branches = []
    for label in ("A1", "B1", "B2", "A2"):
        gateway, journal, _ = gateway_factory()
        clock = rollout.ActiveClock()
        gateway.deadline = ExecutionDeadline.from_remaining(1477, clock=clock)
        gateway.accepted_mutations = 3
        branch = rollout.Branch(
            label,
            journal,
            ArtifactStore(journal.root / label),
            gateway,
            loop._RunCounters(model_calls=31),
            clock,
            323,
        )
        initial = loop._build_context(
            package=SimpleNamespace(public=gateway.public_task),
            gateway=gateway,
            journal=journal,
            correction=None,
            latest_tool_results=[],
            counters=branch.counters,
            elapsed_seconds=323,
            limits=gateway.limits,
        )
        items = assemble_model_input(
            system_prompt=loop.DEV_SYSTEM_PROMPT, state=json.loads(initial), history=[]
        )
        ref = branch.store.put_text(canonical_json(items), "application/json")
        policy = loop._tool_policy(gateway, branch.counters, gateway.limits)
        journal.append(
            "turn_started",
            {
                "turn_id": "seed",
                "model_input_artifact": ref.model_dump(mode="json"),
                "model_input_hash": ref.content_hash,
                "native_history": loop.history_metadata(items),
                "available_tool_names": sorted(policy.allowed_tools),
                "workflow_gate": policy.workflow_gate,
            },
        )
        branch._seed = ("seed", DevModelTurn(tool_calls=read_calls()), policy)
        branches.append(branch)
    monkeypatch.setattr(rollout, "initialize", lambda *args: branches)
    sequence = []

    class AutoAdapter(Adapter):
        def execute_request(self, request, **kwargs):
            index = (len(sequence) - 1) % 4
            branch = branches[index]
            state = reconstruct_state(request["input"])
            if not state["current_diff"]["patch"]:
                self.calls = [mutation_call(branch.gateway, action_id=f"m-{len(sequence)}")]
            elif state["remaining_visible_check_ids"]:
                self.calls = [
                    RequestedTool(
                        name="run_check",
                        action_id=f"c-{len(sequence)}",
                        arguments={"check_id": state["remaining_visible_check_ids"][0]},
                        turn_decision=PublicTurnDecision(mode="verify", basis="test public check"),
                    )
                ]
            else:
                self.calls = [
                    RequestedTool(
                        name="finish_task",
                        action_id=f"f-{len(sequence)}",
                        arguments={},
                        turn_decision=PublicTurnDecision(
                            mode="finish", basis="test checked submission"
                        ),
                    )
                ]
            return super().execute_request(request, **kwargs)

    def factory(config):
        sequence.append(config)
        return AutoAdapter(
            [], failure=failure if failure != "billing" else None, mismatch=failure == "billing"
        )

    package = SimpleNamespace(public=branches[0].gateway.public_task, task_content_hash="test-hash")
    result = rollout.run(
        SimpleNamespace(package=package, public_state={"remaining_budget": {}}),
        tmp_path / "driver",
        credential_file=rollout.repository_root() / ".env",
        cap=Decimal("1.20"),
        pricing_verified_on=utc_now().date().isoformat(),
        approved_hash=rollout.implementation_hash(),
        sandbox=branches[0].gateway.sandbox,
        adapter_factory=factory,
    )
    if failure is None:
        assert result["terminal"] == "ROLLOUTS_COMPLETED"
        assert result["new_provider_calls"] == 12
        assert all(b["terminal"] == "PUBLIC_CHECKS_SUBMITTED" for b in result["branches"])
    else:
        assert result["terminal"] == (
            "COUNT_TIMEOUT_OR_UNKNOWN" if failure == "count" else "PROVIDER_TIMEOUT_OR_UNKNOWN"
        )
        assert len(sequence) == 1
        assert all(b.get("censored") for b in result["branches"])
        assert result["total_cost_known"] == (failure == "count")


def test_shared_deadline_uses_tighter_remaining_clock():
    now = [0.0]
    a = ExecutionDeadline.from_remaining(100, clock=lambda: now[0])
    b = ExecutionDeadline.from_remaining(10, clock=lambda: now[0])
    combined = rollout.SharedDeadline(a, b)
    assert combined.bounded_timeout(50, reserve_seconds=5) == 5
    now[0] = 9
    from patchloop.deadline import ExecutionDeadlineExceeded

    with pytest.raises(ExecutionDeadlineExceeded):
        combined.check(reserve_seconds=5)
