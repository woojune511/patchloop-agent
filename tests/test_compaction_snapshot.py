from __future__ import annotations

import copy
import json

import pytest
from test_compaction_episode import (
    SECRET,
    CapturingAdapter,
    initialize,
    ledger,
    no_network_or_credentials,  # noqa: F401 - autouse fixture, no live backends
    state_of,
    tool,
)
from test_compaction_episode import frozen_source_plan as frozen_source_plan
from test_compaction_episode import source_plan as source_plan
from test_dev_tools import mutation_call
from test_model_state_episode import FailOnce

from diagnostics import compaction_episode as episode
from diagnostics import compaction_snapshot as snapshots
from diagnostics.decision_sampler import read_source_artifact
from patchloop.errors import ContractError
from patchloop.sandbox import LocalSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json


def reentry(**state):
    exchanges = state.pop("exchanges", [])
    return {"role": "developer", "content": canonical_json({
        "kind": snapshots.REENTRY, "state": state,
        "referenced_public_exchanges": exchanges,
    })}


def source(*, start=1, content="one\ntwo", digest="raw-hash", path="public.py"):
    return {"path": path, "file_hash": digest, "inline_spans": [{
        "start_line": start, "end_line": start + content.replace("\r\n", "\n").count("\n"),
        "content": content,
    }]}


def exchange(action="read", *, spans=()):
    return [
        {"type": "function_call", "call_id": action, "name": "read_file",
         "arguments": '{"path":"public.py"}'},
        {"type": "function_call_output", "call_id": action, "output": canonical_json({
            "action_id": action, "tool": "read_file", "status": "succeeded",
            "output": {"spans": list(spans)},
        })},
    ]


def compose(saved, latest, *, added=(), seed=None, policy=snapshots.LATEST):
    return snapshots.compose(seed=saved[:1] if seed is None else seed, saved=saved,
                             added=list(added), reentry=latest, policy=policy)


OPAQUE = {"type": "compaction", "id": "cmp", "encrypted_content": "opaque"}


def test_default_append_is_exact_and_mode_is_explicit():
    saved = [OPAQUE, reentry(remaining_budget={"model_calls": 10})]
    newest = reentry(remaining_budget={"model_calls": 9})
    result, meta = compose(saved, newest, policy=snapshots.APPEND)
    assert result == [*saved, newest] and meta["removed_snapshot_count"] == 0
    with pytest.raises(ContractError, match="unknown"):
        compose(saved, newest, policy="automatic")


def test_entire_seed_native_order_and_current_state_are_unchanged():
    # Even a reentry-looking message INSIDE returned compact output is immutable.
    seed = [{"type": "message", "role": "user", "content": [{"text": "original"}]},
            reentry(remaining_budget={"model_calls": 38}), OPAQUE]
    reasoning = {"type": "reasoning", "encrypted_content": "cipher-exact"}
    old = reentry(current_sources=[source()], working_notes={"open_question": "old"},
                  remaining_budget={"model_calls": 3},
                  recent_attempt_result_next_question=[{"correction": "expired"}])
    saved = [*seed, reasoning, *exchange(), old]
    latest = reentry(current_sources=[source()], working_notes={"open_question": None},
                     remaining_budget={"model_calls": 2}, available_tool_names=["finish_task"])
    before = copy.deepcopy(saved)
    result, meta = compose(saved, latest, seed=seed, added=exchange("next"))
    assert saved == before and result == [*seed, reasoning, *exchange(), *exchange("next"), latest]
    assert meta["removed_snapshot_count"] == 1
    assert "expired" not in canonical_json(result)


def test_rescues_only_missing_complete_lines_without_filling_gaps_or_rebinding_hashes():
    old = reentry(current_sources=[source(content="one\r\ntwo"), source(start=5, content="five"),
                                    source(start=1, content="old", digest="old-hash")])
    latest = reentry(current_sources=[source(start=1, content="one")])
    result, meta = compose([OPAQUE, old], latest)
    facts, _, _ = snapshots.inventory(result)
    assert set(facts) == {("public.py", "raw-hash", n) for n in (1, 2, 5)} | {
        ("public.py", "old-hash", 1)}
    assert meta["rescued_source_lines"] == 3
    archive = snapshots.payload(result[1])
    assert [s["start_line"] for g in archive["sources"] if g["file_hash"] == "raw-hash"
            for s in g["inline_spans"]] == [2, 5]
    assert "\r" not in canonical_json(archive)
    assert result[-1] == latest


def test_harness_only_check_probe_receipts_survive_without_native_impersonation():
    check = {"action_id": "harness-check", "diff_hash": "old-diff", "status": "PASS",
             "stdout": "exact public output", "execution_policy": {"cleanup": "confirmed"}}
    probe = {"action_id": "harness-probe", "diff_hash": "old-diff", "observation": "exact"}
    receipt = {"action_id": "harness-check", "candidate_diff_hash": "old-diff", "passed": True}
    old = reentry(recent_checks=[check], recent_probes=[probe],
                  repair_recheck={"enabled": True, "last_result": receipt})
    latest = reentry(recent_checks=[], recent_probes=[],
                     visible_check_status=[{"status": "NOT_RUN", "diff_hash": "new-diff"}],
                     repair_recheck={"enabled": True, "last_result": None})
    result, meta = compose([OPAQUE, old], latest)
    data = snapshots.payload(result[1])
    assert meta["rescued_observations"] == 3 and data["referenced_public_exchanges"] == []
    assert data["observations"] == [
        {"field": "recent_checks", "value": check}, {"field": "recent_probes", "value": probe},
        {"field": "repair_recheck.last_result", "value": receipt},
    ]
    assert "not current state" in data["instructions"] and result[-1] == latest


def test_backward_alias_chain_and_distinct_action_versions_are_retained():
    span = {"path": "public.py", "file_hash": "raw-hash", "start_line": 1,
            "end_line": 2, "content": "one\ntwo"}
    read = exchange(spans=[span])
    alias = {**span, "file_hash": "post-hash", "origin": "revalidated_after_mutation",
             "content_hash": sha256_bytes(b"one\ntwo"), "content_delivery": [{
                 "action_id": "read", "field": "output.spans[0]", "file_hash": "raw-hash",
                 "start_line": 1, "end_line": 2, "target_start_line": 1,
             }]}
    alias.pop("content")
    native = exchange("mutation", spans=[alias])
    version = copy.deepcopy(read)
    version[1]["output"] = canonical_json({**json.loads(version[1]["output"]), "version": 2})
    old = reentry(exchanges=read)
    saved = [OPAQUE, old, *native]
    latest = reentry(exchanges=version)
    result, meta = compose(saved, latest)
    facts, public, _ = snapshots.inventory(result)
    assert facts["public.py", "post-hash", 2] == "two"
    assert sha256_json(read[1]) in public and sha256_json(version[1]) in public
    assert meta["rescued_exchange_items"] == 1  # call was identical, output was not
    # Public source facts are retained even if a duplicated newer version changed
    # the position at which the read is available to the native resolver.
    assert snapshots.inventory([*saved, latest]) == snapshots.inventory(result)


def test_unknown_public_field_is_retained_and_repeated_receipt_does_not_grow():
    old = reentry(future_public_observation={"fact": "unique"}, remaining_budget={"x": 1})
    latest = reentry(remaining_budget={"x": 2})
    first, _ = compose([OPAQUE, old], latest)
    second, meta = compose(first, reentry(remaining_budget={"x": 3}))
    assert meta["rescued_observations"] == 0
    assert first[1] == second[1] and len(first) == len(second)


def test_projection_rehydration_uses_saved_wire_not_process_cache():
    old = reentry(current_sources=[source()], recent_checks=[{"action_id": "check", "v": 1}])
    saved, _ = compose([OPAQUE, old], reentry(remaining_budget={"model_calls": 5}))
    newest = reentry(remaining_budget={"model_calls": 4})
    direct = compose(saved, newest, added=exchange("parallel-a") + exchange("parallel-b"))
    restored = compose(json.loads(canonical_json(saved)), copy.deepcopy(newest),
                       added=exchange("parallel-a") + exchange("parallel-b"))
    assert direct == restored
    assert direct[0][1] == saved[1]


@pytest.mark.parametrize("error", ["prefix", "conflict", "incomplete"])
def test_invalid_inputs_fail_without_silent_evidence_loss(error):
    older = source()
    newer = source()
    seed = [OPAQUE]
    if error == "prefix":
        seed = [{**OPAQUE, "encrypted_content": "changed"}]
    elif error == "conflict":
        newer["inline_spans"][0]["content"] = "different\ntwo"
    else:
        older["inline_spans"][0]["end_line"] = 99
    with pytest.raises(ContractError):
        compose([OPAQUE, reentry(current_sources=[older])],
                reentry(current_sources=[newer]), seed=seed)


def opt_in(source_plan):
    plan, _, root = source_plan
    return plan, episode.proposal(plan, context_policy=snapshots.LATEST), root


def test_live_path_uses_projected_input_for_count_dispatch_and_durable_recovery(source_plan):
    e = initialize(opt_in(source_plan), clock=lambda: 0)
    episode.execute_seed(e)
    read = CapturingAdapter([tool("read_file", "read-again", path="mini_data_utils/csvlite.py",
                                  start_line=1, end_line=10)], tag="read")
    package = source_plan[0].package
    episode.step(e, package, read, ledger())
    finish = CapturingAdapter([tool("finish_task", "finish")], tag="finish")
    counted = []
    count = finish.count_input_tokens_v2

    def record_count(request, **kwargs):
        counted.append(copy.deepcopy(request))
        return count(request, **kwargs)

    finish.count_input_tokens_v2 = record_count
    episode.step(e, package, finish, ledger())
    assert e.terminal["terminal"] == "PUBLIC_CHECKS_SUBMITTED"
    request = finish.requests[0]
    assert counted == [request]
    started = [x["payload"] for x in e.journal.events() if x["event_type"] == "turn_started"]
    latest = started[-1]
    raw = read_source_artifact(e.journal.root, latest["model_input_artifact"])
    assert json.loads(raw) == request["input"]
    assert sha256_bytes(raw) == latest["model_input_hash"]
    assert latest["state_lifecycle"]["projected_input_hash"] == sha256_json(request["input"])
    assert latest["state_lifecycle"]["removed_snapshot_count"] == 1
    assert state_of(request)["current_diff"] == state_of(read.requests[0])["current_diff"]
    assert [i for i in request["input"] if i.get("type") == "reasoning"][-1][
        "encrypted_content"] == "cipher_read"
    # Reconstructing the exact projection from the prior durable input is deterministic.
    assert snapshots.inventory(json.loads(raw)) == snapshots.inventory(request["input"])


def test_incomplete_reasoning_and_correction_are_not_reset_or_repeated(source_plan):
    e = initialize(opt_in(source_plan), clock=lambda: 0)
    episode.execute_seed(e)
    incomplete = CapturingAdapter([], incomplete=True, tag="incomplete")
    episode.step(e, source_plan[0].package, incomplete, ledger())
    read = CapturingAdapter([tool("read_file", "read", path="mini_data_utils/csvlite.py",
                                  start_line=1, end_line=10)], tag="read")
    episode.step(e, source_plan[0].package, read, ledger())
    cards = state_of(read.requests[0])["recent_attempt_result_next_question"]
    assert cards and any(c["attempt"] == "protocol" for c in cards)
    assert sum(i.get("encrypted_content") == "cipher_incomplete"
               for i in read.requests[0]["input"]) == 1
    finish = CapturingAdapter([tool("finish_task", "finish")])
    episode.step(e, source_plan[0].package, finish, ledger())
    assert state_of(finish.requests[0])["recent_attempt_result_next_question"] == []
    archives = [snapshots.payload(i) for i in finish.requests[0]["input"]
                if snapshots.payload(i) is not None
                and snapshots.payload(i)["kind"] == snapshots.ARCHIVE]
    assert all(r["field"] != "recent_attempt_result_next_question"
               for archive in archives for r in archive["observations"])
    for path in e.journal.root.rglob("*"):
        if path.is_file():
            assert SECRET.encode() not in path.read_bytes()


@pytest.mark.parametrize("boundary", ["provider_returned", "decision_recorded", "batch_finished"])
def test_projection_crash_cannot_retry_provider_or_tools(source_plan, boundary):
    e = initialize(opt_in(source_plan), clock=lambda: 0)
    episode.execute_seed(e)
    adapter = CapturingAdapter([tool("read_file", "read", path="mini_data_utils/csvlite.py",
                                     start_line=1, end_line=10)])

    def crash(point):
        if point == boundary:
            raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        episode.step(e, source_plan[0].package, adapter, ledger(), checkpoint=crash)
    counts = (e.new_provider_calls, e.new_tools, e.gateway.accepted_mutations)
    terminal = copy.deepcopy(e.terminal)
    assert episode.step(e, source_plan[0].package, adapter, ledger()) == terminal
    assert counts == (e.new_provider_calls, e.new_tools, e.gateway.accepted_mutations)
    assert adapter.sequence == ["count", "create"]
    for row in e.journal.events():
        if row["event_type"] == "turn_started":
            payload = row["payload"]
            raw = read_source_artifact(e.journal.root, payload["model_input_artifact"])
            assert sha256_bytes(raw) == payload["model_input_hash"]


def test_opt_in_failed_check_repair_recheck_and_finish(source_plan):
    plan, _, root = opt_in(source_plan)
    plan.identity["repair_recheck"] = True
    packet = episode.proposal(plan, context_policy=snapshots.LATEST)
    e = initialize((plan, packet, root), sandbox=FailOnce(LocalSandbox()), clock=lambda: 0)
    episode.execute_seed(e)
    call = mutation_call(e.gateway, action_id="repair")
    new = call.arguments["new_text"]
    call = call.model_copy(update={"arguments": {
        **call.arguments, "old_text": new, "new_text": new + "\n# public fixture repair\n",
    }})
    adapter = CapturingAdapter([call], tag="repair")
    episode.step(e, plan.package, adapter, ledger())
    finish = CapturingAdapter([tool("finish_task", "finish")])
    episode.step(e, plan.package, finish, ledger())
    state = state_of(finish.requests[0])
    assert state["repair_recheck"]["last_result"]["passed"] is True
    assert e.terminal["terminal"] == "PUBLIC_CHECKS_SUBMITTED"


def test_policy_packet_binding_changes_and_pending_turn_never_dispatches(source_plan):
    plan, packet, root = opt_in(source_plan)
    assert packet != episode.proposal(plan)
    assert "compaction_snapshot.py" in packet["implementation"]["modules"]
    changed = {**packet, "context_policy": "invalid"}
    with pytest.raises(ContractError):
        initialize((plan, changed, root))
    assert not root.exists()
    e = initialize((plan, packet, root), clock=lambda: 0)
    episode.execute_seed(e)
    adapter = CapturingAdapter([tool("finish_task", "finish")])
    e.prepare_request(plan.package, adapter)  # crash after admission/turn_started
    before = e.new_tools
    with pytest.raises(ContractError, match="pending request"):
        episode.step(e, plan.package, adapter, ledger())
    assert not adapter.requests and e.new_provider_calls == 0 and e.new_tools == before
