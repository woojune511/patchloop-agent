from __future__ import annotations

import copy
import json
import socket
from decimal import Decimal
from types import SimpleNamespace

import pytest
from openai.types.responses import Response
from test_compaction_episode import frozen_source_plan as frozen_source_plan
from test_compaction_episode import snapshot, tool
from test_dev_tools import mutation_call
from test_model_state_episode import FailOnce

from diagnostics import compaction_episode as episode
from diagnostics import compaction_episode_collector as collector
from patchloop.dev import runner as loop
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError
from patchloop.sandbox import LocalSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json, utc_now

PLAIN = "SECRET_PLAINTEXT_REASONING_AND_EXCEPTION_SENTINEL"
LIVE_BACKENDS = collector.live_backends


@pytest.fixture(autouse=True)
def no_live(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No actual API, credentials or Docker in collector tests")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(collector, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(collector.transport.DiagnosticClient, "__init__", forbidden)
    monkeypatch.setattr(collector, "live_backends", forbidden)


@pytest.fixture
def ready(frozen_source_plan, tmp_path, monkeypatch):
    source = copy.deepcopy(frozen_source_plan)
    env = tmp_path / ".env"
    env.write_text("fake fixture only", encoding="utf-8")
    source.identity.update(
        credential_file_path_hash=sha256_bytes(str(env.resolve()).encode()),
        evaluator_image_digest="sha256:fixture-evaluator",
        probe_image_digest=None,
        probe_profile_hash=None,
    )
    packet = episode.proposal(source)
    packet_root = tmp_path / "packet"
    packet_root.mkdir()
    values = SimpleNamespace(source=source, packet=packet, branches=[], loaded=[])

    def verify(root, digest):
        assert root == packet_root
        if digest != sha256_json(values.packet):
            raise ContractError("packet mismatch")
        return source, values.packet

    monkeypatch.setattr(episode, "verify", verify)
    monkeypatch.setattr(collector, "source_preflight", lambda *args, **kwargs: None)
    initialize = episode.initialize

    def remember(*args, **kwargs):
        branch = initialize(*args, **kwargs)
        values.branches.append(branch)
        return branch

    monkeypatch.setattr(episode, "initialize", remember)
    values.kwargs = dict(
        packet_root=packet_root,
        packet_hash=sha256_json(packet),
        output=tmp_path / "collected",
        env_file=env,
        max_generation_cost_usd=Decimal("1.20"),
        repeat=1,
        prices_verified_on=utc_now().date().isoformat(),
    )
    return values


def reply(calls, *, index=1, incomplete=False, output_tokens=100, cache_write=0):
    output = [
        {
            "type": "reasoning",
            "id": "rs_" + str(index),
            "encrypted_content": "cipher-" + str(index),
            "summary": [{"type": "summary_text", "text": PLAIN}],
        }
    ]
    output.extend(
        {
            "type": "function_call",
            "id": "fc_" + c.action_id,
            "call_id": c.action_id,
            "status": "completed",
            "name": c.name,
            "arguments": canonical_json(loop._provider_tool_arguments(c)),
        }
        for c in calls
    )
    return Response.model_validate(
        {
            "id": "resp_fixture_" + str(index),
            "object": "response",
            "created_at": 0,
            "status": "incomplete" if incomplete else "completed",
            "model": collector.PRICES["model"],
            "service_tier": "default",
            "parallel_tool_calls": True,
            "tool_choice": "required",
            "tools": [],
            "output": output,
            "incomplete_details": {"reason": "max_output_tokens"} if incomplete else None,
            "usage": {
                "input_tokens": 1000,
                "output_tokens": output_tokens,
                "total_tokens": 1000 + output_tokens,
                "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": cache_write},
                "output_tokens_details": {"reasoning_tokens": 20},
            },
        }
    )


class Client:
    max_retries = 0

    def __init__(self, responses=None, *, count=1000, close_error=False):
        self.queue = responses or [reply([tool("finish_task", "finish")])]
        self.count, self.close_error = count, close_error
        self.calls, self.closes = [], []
        self.phase = None
        self.responses = SimpleNamespace(
            input_tokens=SimpleNamespace(count=self.count_input), create=self.create
        )

    def count_input(self, **payload):
        self.calls.append(("count", copy.deepcopy(payload)))
        if isinstance(self.count, BaseException):
            raise self.count
        return SimpleNamespace(object="response.input_tokens", input_tokens=self.count)

    def create(self, **payload):
        self.calls.append(("create", copy.deepcopy(payload)))
        response = self.queue.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response(payload) if callable(response) else response

    def close(self, *, timeout):
        self.closes.append(timeout)
        if self.close_error:
            raise RuntimeError(PLAIN)


def run(ready, client=None, *, sandbox=None, **kwargs):
    client = client or Client()
    admission = collector.inspect(**ready.kwargs)

    def credentials(path):
        ready.loaded.append(path)
        return "fake-key"

    return collector.collect(
        **ready.kwargs,
        execution_plan_hash=admission["execution_plan_hash"],
        accept_unconfirmed_count_billing=True,
        client_factory=lambda **_: client,
        credential_loader=credentials,
        backend_factory=lambda *args, **kw: (sandbox or LocalSandbox(), None),
        **kwargs,
    )


def test_inspect_is_no_call_exact_and_has_shared_cap(ready):
    before = snapshot(ready.source.source_root)
    first = collector.inspect(**ready.kwargs)
    assert collector.inspect(**ready.kwargs) == first
    assert collector.inspect(**{**ready.kwargs, "max_generation_cost_usd": Decimal("1.2")}) == first
    assert first["plan"]["initial_reservation"]["reserved_generation_nanos"] == 316500000
    assert first["plan"]["max_new_responses"] == 8
    assert first["plan"]["count_billing"].startswith("UNCONFIRMED")
    assert first["execution_granted"] is False and ready.loaded == []
    assert snapshot(ready.source.source_root) == before and not ready.kwargs["output"].exists()


@pytest.mark.parametrize(
    "change",
    [
        {"repeat": 2},
        {"packet_hash": "wrong"},
        {"max_generation_cost_usd": Decimal("NaN")},
        {"max_generation_cost_usd": Decimal("0.316499")},
        {"prices_verified_on": "2020-01-01"},
    ],
)
def test_bad_contract_prevents_output_and_clients(ready, change):
    with pytest.raises(ContractError):
        collector.inspect(**{**ready.kwargs, **change})
    assert not ready.kwargs["output"].exists() and ready.loaded == []


def test_exact_acknowledgement_and_plan_are_required(ready):
    for ack, digest in [(False, "wrong"), (True, "wrong")]:
        with pytest.raises(ContractError):
            collector.collect(
                **ready.kwargs, execution_plan_hash=digest, accept_unconfirmed_count_billing=ack
            )
    assert not ready.kwargs["output"].exists() and ready.loaded == []


def test_seed_check_then_public_finish_with_no_resampling_and_readonly_result(ready):
    before = snapshot(ready.source.source_root), snapshot(ready.source.collection_root)
    client = Client()
    result = run(ready, client)
    assert result["result"] == "PUBLIC_CHECKS_SUBMITTED"
    assert result["execution_mode"] == "injected"
    assert [c[0] for c in client.calls] == ["count", "create"]
    assert len(client.closes) == 1 and result["cleanup"]["status"] == "CLOSED"
    assert result["episode"]["admitted_tool_actions"] == 2
    assert result["episode"]["admitted_generations"] == 1
    assert result["known_generation_cost_nanos"] == 1_200_000
    assert result["episode"]["seed_finished"] and result["task_acceptance"] == "NOT_RUN"
    wire = client.calls[1][1]
    assert wire["input"][: len(ready.source.request["input"])] == ready.source.request["input"]
    assert sum(i.get("type") == "compaction" for i in wire["input"]) == 1
    assert "seed-check" in canonical_json(wire)
    assert before == (snapshot(ready.source.source_root), snapshot(ready.source.collection_root))
    old = snapshot(ready.kwargs["output"])
    assert collector.inspect_result(ready.kwargs["output"]) == result
    assert collector.inspect_result(ready.kwargs["output"]) == result
    assert old == snapshot(ready.kwargs["output"])
    assert all(
        PLAIN.encode() not in p.read_bytes()
        for p in ready.kwargs["output"].rglob("*")
        if p.is_file()
    )
    with pytest.raises(ContractError):
        run(ready, client)
    assert len(client.calls) == 2


def test_failed_seed_repair_native_recheck_then_finish(ready):
    ready.source.identity["repair_recheck"] = True
    ready.packet = episode.proposal(ready.source)
    ready.kwargs["packet_hash"] = sha256_json(ready.packet)

    def repair(_):
        call = mutation_call(ready.branches[0].gateway, action_id="repair")
        body = call.arguments["new_text"]
        call = call.model_copy(
            update={
                "arguments": {
                    **call.arguments,
                    "old_text": body,
                    "new_text": body + "\n# repaired\n",
                }
            }
        )
        return reply([call])

    client = Client([repair, reply([tool("finish_task", "finish")], index=2)])
    result = run(ready, client, sandbox=FailOnce(LocalSandbox()))
    assert result["result"] == "PUBLIC_CHECKS_SUBMITTED"
    assert result["episode"]["admitted_generations"] == 2
    assert result["episode"]["admitted_tool_actions"] == 4
    state = json.loads(client.calls[-1][1]["input"][-1]["content"])["state"]
    assert state["repair_recheck"]["last_result"]["passed"]
    assert result["episode"]["terminal"]["accepted_mutations_since_checkpoint"] == 1


def test_latest_state_packet_binds_collector_and_exact_counted_projected_input(ready):
    old_admission = collector.inspect(**ready.kwargs)
    ready.packet = episode.proposal(ready.source, context_policy=episode.snapshots.LATEST)
    ready.kwargs["packet_hash"] = sha256_json(ready.packet)
    current = collector.inspect(**ready.kwargs)
    assert current["plan"]["context_policy"] == "latest-state-v1"
    assert current["execution_plan_hash"] != old_admission["execution_plan_hash"]
    with pytest.raises(ContractError):
        collector.collect(**ready.kwargs,
                          execution_plan_hash=old_admission["execution_plan_hash"],
                          accept_unconfirmed_count_billing=True)
    assert not ready.kwargs["output"].exists() and ready.loaded == []
    client = Client([
        reply([tool("read_file", "read", path="mini_data_utils/csvlite.py",
                    start_line=1, end_line=10)]),
        reply([tool("finish_task", "finish")], index=2),
    ])
    result = run(ready, client)
    assert result["result"] == "PUBLIC_CHECKS_SUBMITTED"
    assert result["episode"]["terminal"]["context_policy"] == "latest-state-v1"
    assert [call[0] for call in client.calls] == ["count", "create", "count", "create"]
    assert client.calls[2][1]["input"] == client.calls[3][1]["input"]
    branch = ready.branches[0]
    last = [e["payload"] for e in branch.journal.events()
            if e["event_type"] == "turn_started"][-1]
    assert last["state_lifecycle"]["removed_snapshot_count"] == 1
    assert last["state_lifecycle"]["projected_input_hash"] == sha256_json(
        client.calls[3][1]["input"]
    )
    before = snapshot(ready.kwargs["output"])
    assert collector.inspect_result(ready.kwargs["output"]) == result
    assert snapshot(ready.kwargs["output"]) == before


def test_incomplete_correction_keeps_encrypted_state_without_plain_reasoning(ready):
    client = Client([reply([], incomplete=True), reply([tool("finish_task", "finish")], index=2)])
    result = run(ready, client)
    assert result["result"] == "PUBLIC_CHECKS_SUBMITTED"
    assert result["episode"]["admitted_generations"] == 2
    last = client.calls[-1][1]
    assert sum(i.get("encrypted_content") == "cipher-1" for i in last["input"]) == 1
    state = json.loads(last["input"][-1]["content"])["state"]
    assert "max_output_tokens" in canonical_json(state)
    assert PLAIN not in canonical_json(last)


@pytest.mark.parametrize("bad_count", [True, 0, 272001, TimeoutError(PLAIN)])
def test_count_failure_never_generates_or_retries(ready, bad_count):
    client = Client(count=bad_count)
    result = run(ready, client)
    assert [c[0] for c in client.calls] == ["count"]
    assert result["result"] in {"COUNT_TIMEOUT_OR_UNKNOWN", "INPUT_LIMIT_EXCEEDED"}
    assert result["episode"]["admitted_tool_actions"] == 1
    assert len(client.closes) == 1 and PLAIN not in canonical_json(result)


@pytest.mark.parametrize("response", [TimeoutError(PLAIN), "cache_write", "mismatch"])
def test_usage_and_transport_uncertainty_stop_with_numeric_evidence(ready, response):
    if response == "cache_write":
        response = reply([tool("finish_task", "finish")], cache_write=1)
    elif response == "mismatch":
        response = reply([tool("finish_task", "finish")])
        response.usage.input_tokens = 1001
    client = Client([response])
    result = run(ready, client)
    assert result["result"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert result["episode"]["admitted_tool_actions"] == 1
    assert result["generation_billing_complete"] is False
    assert result["total_invoice_cost_usd"] is None and len(client.closes) == 1
    if not isinstance(response, BaseException):
        assert result["episode"]["usage"][0]["usage"]["input_tokens"] >= 1000
    assert PLAIN not in canonical_json(result)
    assert collector.inspect_result(ready.kwargs["output"]) == result


def test_shared_cap_stops_tail_without_lowering_25k(ready):
    ready.kwargs["max_generation_cost_usd"] = Decimal("0.3165")
    responses = [
        reply(
            [
                tool(
                    "read_file",
                    f"read-{n}",
                    path="mini_data_utils/csvlite.py",
                    start_line=1,
                    end_line=3,
                )
            ],
            index=n,
            output_tokens=25000,
        )
        for n in range(1, 3)
    ]
    client = Client(responses)
    result = run(ready, client)
    assert [c[0] for c in client.calls] == ["count", "create", "count", "create", "count"]
    assert result["result"] == "COST_CAP_REACHED"
    assert result["known_generation_cost_nanos"] == 226500000
    assert all(p["max_output_tokens"] == 25000 for kind, p in client.calls if kind == "create")


def test_cleanup_failure_preserves_submitted_patch(ready):
    result = run(ready, Client(close_error=True))
    assert result["result"] == "STOP_CLEANUP_UNKNOWN"
    assert result["episode"]["terminal"]["terminal"] == "PUBLIC_CHECKS_SUBMITTED"
    assert result["episode"]["terminal"]["submitted_artifact"]
    assert result["cleanup"]["status"] == "UNKNOWN" and PLAIN not in canonical_json(result)


def test_source_preflight_failure_stops_before_backends_credentials(ready, monkeypatch):
    def broken(*args, **kwargs):
        raise ContractError(PLAIN)

    monkeypatch.setattr(collector, "source_preflight", broken)
    result = run(ready)
    assert result["result"] == "EXECUTION_ERROR" and not result["episode"]["created"]
    assert ready.loaded == [] and result["cleanup"]["status"] == "NOT_CREATED"


@pytest.mark.parametrize("wrong", [None, "evaluator", "probe"])
def test_preflight_requires_original_image_and_probe_identities(ready, monkeypatch, wrong):
    source = ready.source
    source.identity.update(probe_image_digest="probe", probe_profile_hash="profile")
    source.package = SimpleNamespace(
        environment=SimpleNamespace(
            image_digest="wrong"
            if wrong == "evaluator"
            else source.identity["evaluator_image_digest"]
        )
    )
    monkeypatch.setattr(loop, "_live_sandbox_preflight", lambda *a, **kw: "sandbox")
    seen = []

    class Probe:
        def preflight(self, *, deadline):
            seen.append(deadline)
            return {
                "image_digest": "wrong" if wrong == "probe" else "probe",
                "profile_hash": "profile",
            }

    monkeypatch.setattr(collector, "DockerProbeSandbox", Probe)
    if wrong:
        with pytest.raises(ContractError):
            LIVE_BACKENDS(source, deadline="deadline")
    else:
        assert LIVE_BACKENDS(source, deadline="deadline")[0] == "sandbox"
        assert seen == ["deadline"]
    assert ready.loaded == [] and not ready.kwargs["output"].exists()


def test_initialization_failure_preserves_partial_child_without_client(ready, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError(PLAIN)

    monkeypatch.setattr(episode.review, "clone_checkpoint", broken)
    result = run(ready)
    assert result["result"] == "EXECUTION_ERROR" and result["episode"]["created"]
    assert result["episode"]["terminal"] is None and ready.loaded == []
    assert collector.inspect_result(ready.kwargs["output"]) == result


def test_horizon_and_cleanup_reserve_before_new_client(ready):
    def horizon(point):
        if point == "seed_finished":
            ready.branches[0].counters.model_calls = 40

    result = run(ready, checkpoint=horizon)
    assert result["result"] == "LIMIT_REACHED" and ready.loaded == []
    assert result["episode"]["admitted_counts"] == 0


def test_cleanup_has_five_seconds_inside_inherited_deadline(ready):
    now = [0.0]
    client = Client(
        [
            reply(
                [
                    tool(
                        "read_file",
                        "read",
                        path="mini_data_utils/csvlite.py",
                        start_line=1,
                        end_line=3,
                    )
                ]
            )
        ]
    )
    remaining = (
        ready.source.state["remaining_budget"]["active_wall_time_seconds"]
        - ready.source.identity["seed_active_seconds"]
    )

    def elapsed(point):
        if point == "step_finished":
            now[0] = remaining - 5

    result = run(ready, client, clock=lambda: now[0], checkpoint=elapsed)
    assert result["result"] == "LIMIT_REACHED" and client.closes == [5]
    assert [c[0] for c in client.calls] == ["count", "create"]


def test_outer_lock_remains_held_until_client_cleanup(ready):
    observed = []

    def locked(point):
        if point not in {"client_created", "step_finished"}:
            return
        binding = json.loads((ready.kwargs["output"] / "execution.json").read_bytes())
        other = DevJournal(ready.kwargs["output"], binding["run_id"])
        with pytest.raises(RecoveryError, match="active"), other.execution_lock():
            pytest.fail("collector execution lock was released")
        observed.append(point)

    assert run(ready, checkpoint=locked)["result"] == "PUBLIC_CHECKS_SUBMITTED"
    assert observed == ["client_created", "step_finished"]


def test_observation_bound_does_not_dispatch_an_extra_request(ready):
    ready.packet = episode.proposal(ready.source, max_new_responses=1)
    ready.kwargs["packet_hash"] = sha256_json(ready.packet)
    client = Client(
        [
            reply(
                [
                    tool(
                        "read_file",
                        "read",
                        path="mini_data_utils/csvlite.py",
                        start_line=1,
                        end_line=3,
                    )
                ]
            )
        ]
    )
    result = run(ready, client)
    assert result["result"] == "DIAGNOSTIC_STEP_LIMIT"
    assert result["episode"]["terminal"]["censored"]
    assert [kind for kind, _ in client.calls] == ["count", "create"]


@pytest.mark.parametrize("point", ["dispatch_recorded", "usage_recorded", "batch_finished"])
def test_interrupted_child_has_readonly_partial_receipt_and_no_retry(ready, point):
    class Interrupted(BaseException):
        pass

    def crash(phase):
        if phase == point:
            raise Interrupted()

    client = Client()
    with pytest.raises(Interrupted):
        run(ready, client, checkpoint=crash)
    before = snapshot(ready.kwargs["output"])
    first = collector.inspect_result(ready.kwargs["output"])
    assert first["result"] == "INCOMPLETE_NO_RETRY"
    assert first["execution_mode"] == "injected"
    assert collector.inspect_result(ready.kwargs["output"]) == first
    assert snapshot(ready.kwargs["output"]) == before
    assert sum(k == "create" for k, _ in client.calls) <= 1


def test_terminal_receipt_survives_missing_result_file_and_detects_tamper(ready):
    def crash(point):
        if point == "terminal_recorded":
            raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        run(ready, checkpoint=crash)
    assert not (ready.kwargs["output"] / "result.json").exists()
    result = collector.inspect_result(ready.kwargs["output"])
    assert result["result"] == "PUBLIC_CHECKS_SUBMITTED"
    ref = result["episode"]["terminal"]["submitted_artifact"]
    from pathlib import Path

    Path(ref["path"]).write_bytes(b"tampered")
    with pytest.raises(ContractError):
        collector.inspect_result(ready.kwargs["output"])
