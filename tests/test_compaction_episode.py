from __future__ import annotations

import copy
import json
import socket
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import pytest
from test_dev_tools import mutation_call, read_calls
from test_fresh_state_rollout import Adapter, start
from test_model_state_episode import FailOnce

from diagnostics import compaction_episode as episode
from diagnostics import compaction_replay as compact
from diagnostics import fresh_state_rollout as engine
from patchloop.agent.model import ModelTurnError
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev import runner as loop
from patchloop.dev.contracts import DevLimits, DevToolResult, RequestedTool
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas
from patchloop.errors import ContractError, RecoveryError
from patchloop.repository import WorkspaceManager, run_git
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SECRET = "PRIVATE_HIDDEN_REFERENCE_PLAINTEXT_SENTINEL"


@pytest.fixture(autouse=True)
def no_network_or_credentials(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("provider-free episode used network/credential/client")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(episode.followup, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(engine.requests.DiagnosticClient, "__init__", forbidden)


def tool(name, action_id, **arguments):
    mode = {
        "run_check": "verify",
        "replace_text": "mutate",
        "finish_task": "finish",
        "read_file": "inspect",
        "stop_task": "stop",
    }[name]
    return RequestedTool(
        name=name,
        action_id=action_id,
        arguments=arguments,
        turn_decision={
            "mode": mode,
            "basis": "Use the public result",
            "evidence_goal": "Inspect the public source" if mode == "inspect" else None,
        },
    )


@pytest.fixture(scope="module")
def frozen_source_plan(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("compact-episode-source")
    package = load_task_package(repository_root() / "tasks/smoke/csv-quoted-newline")
    journal = DevJournal(tmp_path / "source", "run_dev_fixture")
    manager = WorkspaceManager(
        repository_root() / "fixtures/repositories", journal.root / "workspaces"
    )
    workspace = manager.create(
        journal.run_id, package.public.repository.url, package.public.repository.base_commit
    )
    # Smoke packages use a content identity; this diagnostic clones an actual Git cutoff.
    public = package.public.model_copy(
        update={
            "repository": package.public.repository.model_copy(
                update={"base_commit": run_git(workspace, "rev-parse", "HEAD").stdout.strip()}
            )
        }
    )
    gateway = DevToolGateway(
        workspace=workspace,
        journal=journal,
        public_task=public,
        sandbox=LocalSandbox(),
        limits=DevLimits(),
    )
    active = engine.ActiveClock(lambda: 0)
    old = engine.Branch(
        "old",
        journal,
        ArtifactStore(journal.root / "artifacts"),
        gateway,
        loop._RunCounters(),
        active,
        0,
    )
    start(old, "read", read_calls())
    journal.append("model_call_finished", {"turn_id": "read"})
    start(old, "mutation", [mutation_call(gateway)])
    journal.append("model_call_finished", {"turn_id": "mutation"})
    package = SimpleNamespace(public=gateway.public_task)
    context = loop._build_context(
        package=package,
        gateway=gateway,
        journal=journal,
        correction=None,
        latest_tool_results=old.latest,
        counters=old.counters,
        elapsed_seconds=0,
        limits=gateway.limits,
    )
    native = loop._build_model_input(
        journal=journal, artifact_store=old.store, context=context, latest_tool_results=old.latest
    )
    reentry, _ = compact.public_reentry(native)
    state = json.loads(reentry[-1]["content"])["state"]
    policy = loop._tool_policy(gateway, old.counters, gateway.limits)
    # The entire synthetic compact return is kept, including retained message items.
    window = [
        {
            "type": "message",
            "role": item["role"],
            "content": [{"type": "input_text", "text": item["content"]}],
        }
        for item in native[:3]
    ]
    window.append(
        {"type": "compaction", "id": "cmp_fixture", "encrypted_content": "opaque-compact"}
    )
    request = {
        **engine.shared.SETTINGS,
        "reasoning": {"effort": "medium"},
        "input": [*window, *reentry],
        "tools": dev_tool_schemas(
            finish_enabled=False, check_ids=policy.check_ids, allowed_tools=policy.allowed_tools
        ),
    }
    collection = tmp_path / "seed"
    store = ArtifactStore(collection / "artifacts")
    call = tool("run_check", "seed-check", check_id="existing-unit-tests")
    raw = Adapter([call]).execute_request(request)
    seed = loop._turn_from_openai(raw)
    ref = loop._store_provider_continuation(store, seed.provider_continuation)
    seed = seed.model_copy(update={"continuation_ref": ref})
    identity = {
        "source_run_id": journal.run_id,
        "request_hash": sha256_json(request),
        "seed_turn_hash": sha256_json(seed.model_dump(mode="json")),
        "seed_active_seconds": 7.5,
        "repair_recheck": False,
        "probe_image_digest": None,
        "original_input_hash": sha256_json(native),
        "collection_root": str(collection),
        "result_hash": "fixture-hash",
        "task_dir": str(tmp_path / "task"),
    }
    plan = episode.Plan(
        identity,
        journal.root,
        collection,
        journal.events(),
        {"limits": gateway.limits.model_dump(mode="json")},
        request,
        native,
        state,
        seed,
        package,
    )
    return plan


@pytest.fixture
def source_plan(frozen_source_plan, tmp_path):
    plan = copy.deepcopy(frozen_source_plan)
    return plan, episode.proposal(plan), tmp_path / "continued"


def initialize(source_plan, **kwargs):
    plan, packet, root = source_plan
    return episode.initialize(plan, packet, root, kwargs.pop("sandbox", LocalSandbox()), **kwargs)


def ledger(cap="1.20"):
    return DevCostLedger(Decimal(cap), pricing_for_model(engine.shared.MODEL))


def snapshot(root):
    return {str(p): sha256_bytes(p.read_bytes()) for p in root.rglob("*") if p.is_file()}


class CapturingAdapter(Adapter):
    def __init__(self, calls, *, tag="next", incomplete=False, no_cipher=False, **kwargs):
        super().__init__(calls, **kwargs)
        self.tag, self.incomplete, self.no_cipher = tag, incomplete, no_cipher
        self.requests = []

    def execute_request(self, request, **kwargs):
        self.requests.append(copy.deepcopy(request))
        raw = super().execute_request(request, **kwargs)
        cipher = raw.provider_continuation[0]
        continuation = (
            replace(cipher, id="rs_" + self.tag, encrypted_content="cipher_" + self.tag),
            *raw.provider_continuation[1:],
        )
        if self.no_cipher:
            continuation = ()
        if self.incomplete:
            return replace(
                raw,
                provider_continuation=continuation[:1],
                tool_calls=[],
                response_status="incomplete",
                output_item_types=("reasoning",),
                error=ModelTurnError(code="incomplete_response", message=SECRET),
                response_incomplete_reason="max_output_tokens",
            )
        return replace(raw, provider_continuation=continuation)


def state_of(request):
    return json.loads(request["input"][-1]["content"])["state"]


def test_restore_seed_check_once_then_finish_without_resampling(source_plan):
    plan, _, root = source_plan
    before = snapshot(plan.source_root), snapshot(plan.collection_root)
    e = initialize(source_plan, clock=lambda: 0)
    assert e.gateway.accepted_mutations == 1 and e.new_tools == e.new_provider_calls == 0
    assert e.base_elapsed == 7.5 and e.gateway.deadline.remaining_seconds() == 1792.5
    episode.execute_seed(e)
    assert e.new_tools == 1 and e.new_provider_calls == 0
    assert e.gateway.visible_check_status()[0]["status"] == "PASS"
    old = snapshot(root)
    episode.execute_seed(e)
    assert old == snapshot(root)
    adapter = CapturingAdapter([tool("finish_task", "finish")])
    episode.step(e, plan.package, adapter, ledger())
    request = adapter.requests[0]
    assert request["input"][: len(plan.request["input"])] == plan.request["input"]
    assert {k: v for k, v in request.items() if k not in {"tools", "input"}} == {
        k: v for k, v in plan.request.items() if k not in {"tools", "input"}
    }
    assert sum(i.get("encrypted_content") == "cipher-new" for i in request["input"]) == 1
    assert [i["call_id"] for i in request["input"] if i.get("type") == "function_call"] == [
        "seed-check"
    ]
    assert state_of(request)["workflow_gate"] == "ready_to_submit"
    assert e.terminal["terminal"] == "PUBLIC_CHECKS_SUBMITTED"
    assert e.terminal["submitted_artifact"]["content_hash"] == e.gateway.current_diff_hash
    assert e.terminal["accepted_mutations_since_checkpoint"] == 0
    assert e.terminal["task_acceptance"] == e.terminal["hidden_evaluator"] == "NOT_RUN"
    assert before == (snapshot(plan.source_root), snapshot(plan.collection_root))
    assert loop._restore_counters(e.journal).model_calls == e.counters.model_calls == 4
    for p in root.rglob("*"):
        if p.is_file():
            assert SECRET.encode() not in p.read_bytes()


def test_failed_seed_repair_recheck_finish_with_native_feedback(source_plan):
    plan, packet, _ = source_plan
    plan.identity["repair_recheck"] = True
    packet.update(episode.proposal(plan))
    e = initialize(source_plan, sandbox=FailOnce(LocalSandbox()), clock=lambda: 0)
    episode.execute_seed(e)
    assert e.gateway.visible_check_status()[0]["status"] == "FAIL"
    mutation = mutation_call(e.gateway, action_id="repair")
    new = mutation.arguments["new_text"]
    mutation = mutation.model_copy(
        update={
            "arguments": {
                **mutation.arguments,
                "old_text": new,
                "new_text": new + "\n# public fixture repair\n",
            }
        }
    )
    repair = CapturingAdapter([mutation], tag="repair")
    episode.step(e, plan.package, repair, ledger())
    assert "PUBLIC_CHECK_FAILURE_SENTINEL" in canonical_json(repair.requests[0])
    assert e.gateway.accepted_mutations == 2
    assert e.gateway.visible_check_status()[0]["status"] == "PASS"
    assert e.new_tools == 3  # Seed check + model repair + original opt-in harness recheck.
    finish = CapturingAdapter([tool("finish_task", "finish")], tag="finish")
    episode.step(e, plan.package, finish, ledger())
    request = finish.requests[0]
    assert request["input"][: len(repair.requests[0]["input"])] == repair.requests[0]["input"]
    assert sum(i.get("encrypted_content") == "cipher_repair" for i in request["input"]) == 1
    assert state_of(request)["repair_recheck"]["last_result"]["passed"] is True
    assert e.terminal["terminal"] == "PUBLIC_CHECKS_SUBMITTED"
    assert e.terminal["accepted_mutations_since_checkpoint"] == 1


def test_parallel_reads_memory_feedback_and_rejected_mutation_do_not_break_history(source_plan):
    plan, _, _ = source_plan
    e = initialize(source_plan, sandbox=FailOnce(LocalSandbox()))
    episode.execute_seed(e)
    reads = [c.model_copy(update={"action_id": "next-" + c.action_id}) for c in read_calls()]
    reads[0] = reads[0].model_copy(
        update={
            "turn_decision": reads[0].turn_decision.model_copy(
                update={
                    "memory_update": {
                        "findings": [
                            {
                                "note_id": None,
                                "statement": "Observed public check failed",
                                "evidence": [{"kind": "tool_result", "action_id": "seed-check"}],
                            }
                        ],
                        "open_question": "Which public behavior needs repair?",
                    }
                }
            )
        }
    )
    adapter = CapturingAdapter(reads, tag="reads")
    episode.step(e, plan.package, adapter, ledger())
    rejected = CapturingAdapter([mutation_call(e.gateway, action_id="stale")], tag="bad-edit")
    episode.step(e, plan.package, rejected, ledger())
    request = rejected.requests[0]
    outputs = [i for i in request["input"] if i.get("type") == "function_call_output"]
    assert [i["call_id"] for i in outputs] == [
        "seed-check",
        "next-search-source",
        "next-read-source",
    ]
    assert "Observed public check failed" in canonical_json(state_of(request))
    assert e.gateway.accepted_mutations == 1 and e.gateway.last_failed_mutation is not None
    stop = CapturingAdapter(
        [
            tool(
                "stop_task",
                "stop",
                reason_code="insufficient_public_evidence",
                summary="fixture stop",
            )
        ],
        tag="stop",
    )
    episode.step(e, plan.package, stop, ledger())
    assert state_of(stop.requests[0])["last_failed_mutation"]
    assert e.terminal["terminal"] == "AGENT_STOPPED"


@pytest.mark.parametrize("failure", ["count", "create"])
def test_uncertainty_is_terminal_and_cannot_retry(source_plan, failure):
    e = initialize(source_plan)
    episode.execute_seed(e)
    a = CapturingAdapter([], failure=failure)
    with pytest.raises(engine.AbortExperiment):
        episode.step(e, source_plan[0].package, a, ledger())
    sequence = list(a.sequence)
    episode.step(e, source_plan[0].package, a, ledger())
    assert a.sequence == sequence and e.new_tools == 1
    assert e.terminal["terminal"] in {"COUNT_TIMEOUT_OR_UNKNOWN", "PROVIDER_TIMEOUT_OR_UNKNOWN"}
    assert SECRET not in canonical_json(e.terminal)


@pytest.mark.parametrize(
    "fault",
    [
        "dispatch_recorded",
        "provider_returned",
        "usage_recorded",
        "decision_recorded",
        "actions_finished",
        "batch_finished",
    ],
)
def test_crashes_do_not_replay_provider_or_action(source_plan, fault):
    e = initialize(source_plan)
    episode.execute_seed(e)
    calls = [
        tool("read_file", "new-read", path="mini_data_utils/csvlite.py", start_line=1, end_line=3)
    ]
    a = CapturingAdapter(calls)

    def crash(point):
        if point == fault:
            raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        episode.step(e, source_plan[0].package, a, ledger(), checkpoint=crash)
    before = snapshot(e.journal.root)
    episode.step(e, source_plan[0].package, a, ledger())
    assert before == snapshot(e.journal.root)
    assert a.sequence.count("create") <= 1


@pytest.mark.parametrize("fault", ["decision_recorded", "actions_finished", "batch_finished"])
def test_seed_crash_never_reexecutes_check(source_plan, fault):
    e = initialize(source_plan)

    def crash(point):
        if point == fault:
            raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        episode.execute_seed(e, checkpoint=crash)
    before = snapshot(e.journal.root)
    episode.execute_seed(e)
    assert before == snapshot(e.journal.root) and e.new_provider_calls == 0


def test_incomplete_carries_reasoning_to_one_correction(source_plan):
    e = initialize(source_plan)
    episode.execute_seed(e)
    a = CapturingAdapter([], incomplete=True, tag="incomplete")
    episode.step(e, source_plan[0].package, a, ledger())
    assert e.correction is not None
    b = CapturingAdapter([tool("finish_task", "finish")])
    episode.step(e, source_plan[0].package, b, ledger())
    assert (
        sum(i.get("encrypted_content") == "cipher_incomplete" for i in b.requests[0]["input"]) == 1
    )
    assert "max_output_tokens" in canonical_json(state_of(b.requests[0]))
    assert SECRET not in canonical_json(b.requests[0])


@pytest.mark.parametrize("mode", ["missing", "tampered"])
def test_seed_cipher_failure_prevents_tools(source_plan, mode):
    e = initialize(source_plan)
    path = e.seed.continuation_ref.artifact.path
    from pathlib import Path

    if mode == "missing":
        Path(path).unlink()
    else:
        Path(path).write_bytes(b"corrupted")
    with pytest.raises(RecoveryError):
        episode.execute_seed(e)
    assert e.new_tools == 0 and e.terminal["terminal"] == "PROVIDER_CONTINUATION_ERROR"


def test_corrupt_new_continuation_stops_before_actions(source_plan):
    e = initialize(source_plan)
    episode.execute_seed(e)
    a = CapturingAdapter([tool("finish_task", "finish")], no_cipher=True)
    with pytest.raises(engine.AbortExperiment):
        episode.step(e, source_plan[0].package, a, ledger())
    assert e.new_tools == 1 and e.terminal["terminal"] == "PROVIDER_CONTINUATION_ERROR"


def test_horizon_prevents_count(source_plan):
    e = initialize(source_plan, clock=lambda: 0)
    episode.execute_seed(e)
    e.counters.model_calls = 40
    a = CapturingAdapter([])
    episode.step(e, source_plan[0].package, a, ledger())
    assert e.terminal["terminal"] == "LIMIT_REACHED" and a.sequence == []


def test_external_observation_limit_does_not_change_action_mask(source_plan):
    e = initialize(source_plan)
    episode.execute_seed(e)
    e.max_responses = 0
    a = CapturingAdapter([])
    episode.step(e, source_plan[0].package, a, ledger())
    assert e.terminal["terminal"] == "DIAGNOSTIC_STEP_LIMIT" and e.terminal["censored"]
    assert e.gateway.limits.max_model_calls == 40 and a.sequence == []


def test_expired_deadline_keeps_terminal_without_new_task_execution(source_plan):
    tick = [0.0]
    e = initialize(source_plan, clock=lambda: tick[0])
    episode.execute_seed(e)
    e.gateway.deadline = ExecutionDeadline.from_remaining(0)
    a = CapturingAdapter([])
    with pytest.raises(ExecutionDeadlineExceeded):
        episode.step(e, source_plan[0].package, a, ledger())
    assert e.terminal["terminal"] == "LIMIT_REACHED" and a.sequence == []


def test_full_output_reservation_stops_without_tool(source_plan):
    e = initialize(source_plan)
    episode.execute_seed(e)
    a = CapturingAdapter([tool("finish_task", "finish")])
    with pytest.raises(engine.AbortExperiment, match="COST_CAP_REACHED"):
        episode.step(e, source_plan[0].package, a, ledger("0.01"))
    assert a.sequence == ["count"] and e.new_tools == 1


@pytest.mark.parametrize("mismatch", ["usage", "request"])
def test_dispatch_identity_mismatch_stops_without_tool(source_plan, mismatch):
    e = initialize(source_plan)
    episode.execute_seed(e)
    a = CapturingAdapter(
        [tool("finish_task", "finish")],
        mismatch=mismatch == "usage",
        mutate=mismatch == "request",
    )
    with pytest.raises((engine.AbortExperiment, ContractError)):
        episode.step(e, source_plan[0].package, a, ledger())
    assert a.sequence == (["count", "create"] if mismatch == "usage" else ["count"])
    assert e.new_tools == 1 and e.terminal is not None
    episode.step(e, source_plan[0].package, a, ledger())
    assert e.new_tools == 1


@pytest.mark.parametrize(
    ("field", "terminal"),
    [("deadline_exhausted", "LIMIT_REACHED"), ("cleanup_failed", "TASK_FAILED")],
)
def test_tool_abort_keeps_native_terminal_class(source_plan, monkeypatch, field, terminal):
    e = initialize(source_plan)

    def aborted(calls):
        return [
            DevToolResult(
                action_id=calls[0].action_id,
                input_hash=sha256_json(calls[0].arguments),
                tool="run_check",
                status="failed",
                output={field: True},
                workspace_diff_hash=e.gateway.current_diff_hash,
            )
        ]

    monkeypatch.setattr(e.gateway, "execute_batch", aborted)
    with pytest.raises(engine.AbortExperiment):
        episode.execute_seed(e)
    assert e.terminal["terminal"] == terminal
    assert e.new_provider_calls == 0 and e.new_tools == 1
    episode.execute_seed(e)
    assert e.new_tools == 1


def test_source_and_packet_changes_fail_before_workspace(source_plan):
    plan, packet, root = source_plan
    packet["max_new_responses"] = 0
    with pytest.raises(ContractError):
        initialize(source_plan)
    assert not root.exists()
    packet.update(episode.proposal(plan))
    plan.request["tools"].reverse()
    with pytest.raises(ContractError, match="in-memory"):
        initialize(source_plan)
    assert not root.exists()


def test_cannot_initialize_same_directory_or_dispatch_before_seed(source_plan):
    e = initialize(source_plan)
    with pytest.raises(ContractError, match="must be new"):
        initialize(source_plan)
    a = CapturingAdapter([])
    with pytest.raises(ContractError, match="collected seed"):
        episode.step(e, source_plan[0].package, a, ledger())
    assert a.sequence == [] and e.new_tools == 0


def test_prepare_verify_are_identical_and_do_not_clone_or_execute(
    source_plan, tmp_path, monkeypatch
):
    plan, _, _ = source_plan
    monkeypatch.setattr(episode, "load_source", lambda *args: plan)
    output = tmp_path / "prepared"
    prepared = episode.prepare(plan.collection_root, "hash", tmp_path / "task", output)
    before = snapshot(output)
    _, packet = episode.verify(output, prepared["packet_hash"])
    assert episode.verify(output, prepared["packet_hash"])[1] == packet
    assert snapshot(output) == before and packet["paid_execution_authorized"] is False
    assert packet["generation_cap_usd"] is None and "UNCONFIRMED" in packet["count_billing"]
    assert packet["max_new_responses"] == 8 and prepared["api_requests"] == 0
