from __future__ import annotations

import copy
import json
import socket
import uuid
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import pytest
from test_decision_sampler import ProcessKilled
from test_dev_tools import mutation_call, read_calls
from test_model_state_episode import MultiAdapter, call
from test_model_state_sampler import factorial as _factorial
from test_model_state_sampler import snapshot

from diagnostics import decision_sampler as shared
from diagnostics import model_state_episode as episode
from diagnostics import model_state_episode_collector as collector
from diagnostics import model_state_sampler as design
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner as loop
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.conversation import reconstruct_state
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_json, utc_now

factorial = _factorial


@pytest.fixture
def smoke_package():
    raw = load_task_package(repository_root() / "tasks/smoke/csv-quoted-newline")
    return raw.model_copy(
        update={
            "public": raw.public.model_copy(update={"split": "dev-train"}),
            "environment": SimpleNamespace(
                evaluator_image="test@sha256:fixture", image_digest="sha256:fixture"
            ),
        }
    )


@pytest.fixture
def prepared(factorial, tmp_path, monkeypatch):
    frozen, _, package = factorial
    monkeypatch.setattr(collector, "load_task_package", lambda _: package)
    parent = tmp_path / "episode-preparation"
    episode.prepare(frozen, parent)
    execution = tmp_path / "execution"
    result = tmp_path / "collection"
    data = collector.prepare(
        frozen,
        parent / "packet.json",
        sha256_bytes((parent / "packet.json").read_bytes()),
        tmp_path,
        execution,
        result,
    )
    path = execution / "packet.json"
    plan = collector.load_plan(path, sha256_bytes(path.read_bytes()))
    grant = shared.Approval(
        plan.packet_hash,
        sha256_json(data["implementation_hashes"]),
        result,
        repository_root() / ".env",
        Decimal("5.00"),
        data["pricing_hash"],
        utc_now().date().isoformat(),
    )

    def forbidden(*args, **kwargs):
        pytest.fail("provider-free test reached credential, network or real Docker")

    monkeypatch.setattr(shared, "create_openai_client", forbidden)
    monkeypatch.setattr(shared, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(loop, "_live_sandbox_preflight", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    return plan, grant


def initializer(plan, cell, root, workspace, package, sandbox, **kwargs):
    # The reusable synthetic sampler fixture has illustrative counters, not runtime budgets.
    # Adjust those in this injected initializer only; production exact hydration is unchanged.
    events, _ = design.source_events(plan.source_root)
    cutoff = plan.packet["cases"][cell.case_id]["cutoff_event_hash"]
    prefix = events[: next(i for i, e in enumerate(events) if e["event_hash"] == cutoff)]
    counters = loop._restore_counters(SimpleNamespace(events=lambda: prefix))
    request = json.loads(cell.request_json)
    payload = json.loads(request["input"][1]["content"])
    payload["remaining_budget"].update(
        model_calls=40 - counters.model_calls,
        tool_actions=100 - counters.tool_actions,
        accepted_mutations=4,
        active_wall_time_seconds=1800,
    )
    request["input"][1]["content"] = canonical_json(payload)
    cell = replace(cell, request_json=canonical_json(request), request_hash=sha256_json(request))
    kwargs["probe_sandbox"] = None  # This public fixture, unlike row43, has no probe tool.
    return episode.initialize(
        replace(plan, cells=(cell,)), cell, root, workspace, package, sandbox, **kwargs
    )


class Client:
    def __init__(self, *, failure=None, workflow=False, full_usage=False):
        self.failure, self.workflow, self.full_usage = failure, workflow, full_usage
        self.created, self.counted = [], []

    def factory(self, config):
        owner = self
        arm = "A" if config.model_id == design.MINI.model_id else "C"

        class Adapter(MultiAdapter):
            def count_input_tokens_v2(self, request, **kwargs):
                owner.counted.append(copy.deepcopy(request))
                if owner.failure == "count":
                    raise TimeoutError("SECRET_SDK_SENTINEL")
                return 272000 if owner.full_usage else 1000

            def execute_request(self, request, **kwargs):
                owner.created.append(copy.deepcopy(request))
                if owner.failure == "transport" and len(owner.created) == 2:
                    raise TimeoutError("SECRET_SDK_SENTINEL")
                label = "action_" + uuid.uuid4().hex
                state = reconstruct_state(request["input"])
                if not owner.workflow:
                    self.calls = [
                        RequestedTool(
                            name="stop_task",
                            action_id=label,
                            arguments={
                                "reason_code": "no_safe_scoped_mutation",
                                "summary": "Mock observation",
                            },
                            turn_decision=PublicTurnDecision(mode="stop", basis="Mock observation"),
                        )
                    ]
                elif len(request["input"]) == 3:
                    self.calls = [
                        c.model_copy(update={"action_id": label + str(i)})
                        for i, c in enumerate(read_calls())
                    ]
                elif not state["current_diff"]["patch"]:
                    self.calls = [mutation_call(None, action_id=label)]
                elif any(c["status"] != "PASS" for c in state["visible_check_status"]):
                    check_id = next(
                        c["check_id"]
                        for c in state["visible_check_status"]
                        if c["status"] != "PASS"
                    )
                    self.calls = [call("run_check", label, check_id=check_id)]
                else:
                    self.calls = [call("finish_task", label)]
                self.count = 272000 if owner.full_usage else 1000
                raw = super().execute_request(request, **kwargs)
                if owner.full_usage:
                    raw = replace(raw, output_tokens=25000)
                if owner.failure == "billing":
                    raw = replace(raw, response_model="WRONG_MODEL")
                if owner.failure == "cipher":
                    raw = replace(raw, provider_continuation=())
                return raw

        adapter = Adapter(arm, [], tag=uuid.uuid4().hex)
        adapter.config = config
        return adapter


def run(prepared, client, **kwargs):
    plan, grant = prepared
    return collector.collect(
        plan,
        grant,
        adapter_factory=client.factory,
        sandbox=LocalSandbox(),
        probe=SimpleNamespace(),
        initializer=initializer,
        **kwargs,
    )


def test_exact_packet_validates_twice_without_execution_or_source_changes(prepared):
    plan, _ = prepared
    before = snapshot(plan.frozen.source_root, plan.path.parent)
    for _ in range(2):
        checked = collector.load_plan(plan.path, plan.packet_hash)
        assert checked.packet == plan.packet
    assert before == snapshot(plan.frozen.source_root, plan.path.parent)
    assert plan.packet["four_arm_depth_reservation_nanos"] == 2743000000
    assert plan.packet["maximum_generation_calls"] == 128
    assert plan.packet["paid_execution_authorized"] is False
    assert "OLD_OPAQUE" not in canonical_json(plan.packet)


def test_all_sixteen_fresh_windows_share_one_cap_and_have_blind_receipts(prepared):
    plan, grant = prepared
    client = Client()
    result = run(prepared, client)
    assert result["terminal"] == "OBSERVATION_WINDOWS_COMPLETED", result
    assert result["provider_calls"] == result["completed_episode_records"] == 16
    assert result["tool_actions_finished"] == 16
    assert result["recorded_cost_nanos"] == 8 * (1200000 + 4000000)
    assert result["task_acceptance"] == result["hidden_evaluator"] == "NOT_RUN"
    assert [r["model"] for r in client.created] == [
        design.PROFILES[c.arm].model_id for c in plan.frozen.cells
    ]
    before = snapshot(grant.result_root)
    assert collector.inspect(grant.result_root) == result
    assert before == snapshot(grant.result_root)
    review = collector.review.read_json(
        design.readonly_store(grant.result_root), result["review_artifact"]
    )
    assert len(review["episodes"]) == 16
    assert all("arm" not in e and "model" not in e for e in review["episodes"])
    store = design.readonly_store(grant.result_root)
    for record in review["episodes"]:
        batches = collector.review.read_json(store, record["decision_batches"])
        results = collector.review.read_json(store, record["actions"])
        assert len(batches) == len(results) == 1
        intent = batches[0]["tool_calls"][0]
        assert intent["name"] == "stop_task"
        assert intent["arguments"]["reason_code"] == "no_safe_scoped_mutation"
        assert intent["action_id"] == results[0]["action_id"]
    with pytest.raises(ContractError):
        run(prepared, Client())


def test_whole_invocation_stops_when_next_complete_depth_cannot_be_reserved(prepared):
    client = Client(full_usage=True)
    result = run(prepared, client)
    assert result["terminal"] == "DIAGNOSTIC_COST_LIMIT"
    assert len(client.created) == result["provider_calls"] == 4
    assert result["unstarted_episodes"] == 12
    assert result["recorded_cost_nanos"] == 2743000000
    assert all(r["max_output_tokens"] == 25000 for r in client.created)


@pytest.mark.parametrize(
    "failure,terminal",
    [
        ("count", "COUNT_TIMEOUT_OR_UNKNOWN"),
        ("transport", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("billing", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("cipher", "PROVIDER_CONTINUATION_ERROR"),
    ],
)
def test_uncertainty_stops_every_group_and_preserves_known_evidence(prepared, failure, terminal):
    client = Client(failure=failure)
    result = run(prepared, client)
    assert result["terminal"] == terminal, result
    assert len(client.created) <= 2 and len(client.counted) <= 2
    assert result["unstarted_episodes"] == 12
    assert collector.inspect(prepared[1].result_root) == result
    for data in snapshot(prepared[1].result_root).values():
        assert b"SECRET_SDK_SENTINEL" not in data
        assert b"PRIVATE_SPEC_SENTINEL" not in data and b"FUTURE_RESULT_SENTINEL" not in data


@pytest.mark.parametrize(
    "point,terminal",
    [
        ("dispatch_recorded", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("usage_recorded", "INTERRUPTED"),
        ("actions_finished", "INTERRUPTED"),
    ],
)
def test_crash_inspection_is_read_only_and_never_replays(prepared, point, terminal):
    def killed(at):
        if at == point:
            raise ProcessKilled()

    with pytest.raises(ProcessKilled):
        run(prepared, Client(), checkpoint=killed)
    before = snapshot(prepared[1].result_root)
    result = collector.inspect(prepared[1].result_root)
    assert result["terminal"] == terminal
    assert result["resume_allowed"] is False
    assert before == snapshot(prepared[1].result_root)
    with pytest.raises(ContractError):
        run(prepared, Client())


@pytest.mark.parametrize("field", ["cap", "credential", "root", "price", "implementation"])
def test_changed_grant_is_rejected_before_root_creation(prepared, field):
    plan, grant = prepared
    changed = {
        "cap": {"max_cost_usd": Decimal("6")},
        "credential": {"credential_file": grant.credential_file.with_name("other.env")},
        "root": {"result_root": grant.result_root.with_name("other-result")},
        "price": {"pricing_hash": "wrong"},
        "implementation": {"sampler_hash": "wrong"},
    }
    with pytest.raises(ContractError):
        collector.collect(plan, replace(grant, **changed[field]), adapter_factory=Client().factory)
    assert not grant.result_root.exists()


def test_changed_disk_packet_is_rejected_before_credentials(prepared):
    plan, grant = prepared
    plan.path.write_bytes(plan.path.read_bytes() + b" ")
    with pytest.raises(ContractError, match="packet hash"):
        run(prepared, Client())
    assert not grant.result_root.exists()


def test_shared_deadline_after_response_prevents_tool_and_future_dispatch(prepared):
    now = [0.0]

    def expire(at):
        if at == "usage_recorded":
            now[0] = 1801

    client = Client(workflow=True)
    result = run(prepared, client, clock=lambda: now[0], checkpoint=expire)
    assert result["terminal"] == "LIMIT_REACHED", result
    assert len(client.created) == 1
    assert result["recorded_cost_nanos"] == 1200000
    assert result["task_acceptance"] == "NOT_RUN"
    assert result["tool_actions_started"] == 0
    assert result["candidate_snapshots_unavailable"] == 0
    assert collector.inspect(prepared[1].result_root) == result


def test_deadline_is_already_bound_during_initialization(prepared):
    now = [0.0]

    def expired_initializer(*args, execution_deadline, **kwargs):
        now[0] = 1801
        execution_deadline.check()

    client = Client()
    result = collector.collect(
        *prepared,
        adapter_factory=client.factory,
        sandbox=LocalSandbox(),
        probe=SimpleNamespace(),
        initializer=expired_initializer,
        clock=lambda: now[0],
    )
    assert result["terminal"] == "LIMIT_REACHED"
    assert not client.counted and not client.created
    assert result["registered_episodes"] == 1
    assert result["completed_episode_records"] == 0
    assert collector.inspect(prepared[1].result_root) == result


def test_unavailable_final_snapshot_preserves_durable_results(prepared, monkeypatch):
    original = collector.public_receipt

    def unavailable(*args):
        with monkeypatch.context() as scoped:

            def fail_snapshot(*args, **kwargs):
                raise OSError("SECRET_METADATA_SENTINEL")

            scoped.setattr(collector.WorkspaceManager, "diff_summary", fail_snapshot)
            return original(*args)

    monkeypatch.setattr(collector, "public_receipt", unavailable)
    result = run(prepared, Client(failure="count"))
    assert result["terminal"] == "COUNT_TIMEOUT_OR_UNKNOWN"
    assert result["candidate_snapshots_unavailable"] == 4
    assert collector.inspect(prepared[1].result_root) == result
    public = collector.review.read_json(
        design.readonly_store(prepared[1].result_root), result["review_artifact"]
    )
    assert all(
        e["candidate"] is None and e["snapshot_error"] == "OSError" for e in public["episodes"]
    )
    assert "SECRET_METADATA_SENTINEL" not in canonical_json(public)


def test_concurrent_entry_is_rejected_before_count_or_provider(prepared):
    client = Client()
    observed = []

    def concurrent(at):
        if at == "dispatch_recorded":
            contender = Client()
            with pytest.raises(ContractError):
                run(prepared, contender)
            assert not contender.counted and not contender.created
            observed.append(at)

    result = run(prepared, client, checkpoint=concurrent)
    assert result["provider_calls"] == len(observed) == 16


def test_final_candidate_drift_is_not_bound_to_old_check_result(tmp_path, monkeypatch):
    branch = SimpleNamespace(
        gateway=SimpleNamespace(workspace=tmp_path),
        terminal={
            "terminal": "PUBLIC_CHECKS_SUBMITTED",
            "censored": False,
            "current_diff_hash": "old",
            "visible_checks": [{"status": "PASS"}],
        },
        journal=SimpleNamespace(events=lambda: []),
    )
    monkeypatch.setattr(
        collector.WorkspaceManager,
        "diff_summary",
        lambda *_, **kw: SimpleNamespace(patch_hash="drift", patch="changed"),
    )
    receipt = collector.public_receipt(
        {"anonymous_id": "e1", "case_id": "C1"},
        branch,
        ArtifactStore(tmp_path),
        "done",
        ExecutionDeadline.from_remaining(10),
    )
    assert receipt["candidate"] is None
    assert receipt["snapshot_error"] == "TerminalCandidateMismatch"
    assert receipt["outcome"]["current_diff_hash"] == "old"


def test_mock_multi_turn_public_check_finish_smoke(prepared, monkeypatch):
    # One four-arm group tests actual gateway work; the sixteen-window test covers the schedule.
    monkeypatch.setattr(design, "BLOCKS", design.BLOCKS[:1])
    plan, grant = prepared
    monkeypatch.setattr(collector, "load_plan", lambda *_: plan)
    client = Client(workflow=True)
    result = run((plan, grant), client)
    assert result["terminal"] == "OBSERVATION_WINDOWS_COMPLETED", result
    assert result["provider_calls"] == 20
    review = collector.review.read_json(
        design.readonly_store(grant.result_root), result["review_artifact"]
    )
    assert all(e["outcome"]["terminal"] == "PUBLIC_CHECKS_SUBMITTED" for e in review["episodes"])
    assert all(
        i["status"] == "PASS" for e in review["episodes"] for i in e["outcome"]["visible_checks"]
    )
    assert all(r["store"] is False and r["max_output_tokens"] == 25000 for r in client.created)
    assert any(any(i.get("type") == "reasoning" for i in r["input"]) for r in client.created)
