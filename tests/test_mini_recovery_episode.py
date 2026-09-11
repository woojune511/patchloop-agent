from __future__ import annotations

import copy
import json
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import pytest
from test_dev_tools import mutation_call, read_calls
from test_model_state_episode import FailOnce, MultiAdapter, call
from test_model_state_episode import episodes as _episodes
from test_model_state_episode_collector import Client, initializer, run
from test_model_state_episode_collector import prepared as _prepared
from test_model_state_episode_collector import smoke_package as _smoke_package
from test_model_state_sampler import factorial as _factorial
from test_model_state_sampler import snapshot

from diagnostics import decision_sampler as shared
from diagnostics import model_state_episode as episode
from diagnostics import model_state_episode_collector as collector
from diagnostics import model_state_sampler as design
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.errors import ContractError
from patchloop.sandbox import LocalSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json, utc_now

factorial, prepared, smoke_package, episodes = _factorial, _prepared, _smoke_package, _episodes


@pytest.fixture
def mini(prepared, tmp_path):
    old, grant = prepared
    parent = tmp_path / "mini-preparation"
    episode.prepare(old.frozen, parent, profile=episode.MINI_RECOVERY)
    root = tmp_path / "mini-execution"
    result = tmp_path / "mini-result"
    packet = collector.prepare(
        old.frozen, parent / "packet.json", sha256_bytes((parent / "packet.json").read_bytes()),
        tmp_path, root, result)
    path = root / "packet.json"
    plan = collector.load_plan(path, sha256_bytes(path.read_bytes()))
    return plan, replace(
        grant, packet_hash=plan.packet_hash, result_root=result,
        sampler_hash=sha256_json(packet["implementation_hashes"]),
        pricing_hash=packet["pricing_hash"],
        pricing_verified_on=utc_now().date().isoformat())


def test_mini_packet_contains_exact_eight_inputs_balanced_order_and_no_fixed_window(mini):
    plan, grant = mini
    packet = plan.packet
    assert packet["episode_profile"] == episode.MINI_RECOVERY.name
    assert packet["max_responses_per_episode"] is None
    assert set(packet["models"]) == set(packet["prices"]) == {"A", "B"}
    assert {v["model_id"] for v in packet["models"].values()} == {shared.MODEL}
    assert packet["active_group_depth_reservation_nanos"] == 633000000
    assert "four_arm_depth_reservation_nanos" not in packet
    assert packet["comparison_groups"] == [
        ["C1", 1, "AB"], ["C2", 1, "BA"], ["C1", 2, "BA"], ["C2", 2, "AB"]]
    cells = episode.MINI_RECOVERY.cells(plan.frozen)
    assert len(cells) == len(packet["first_requests"]) == 8
    assert packet["maximum_generation_calls"] == episode.MINI_RECOVERY.maximum_calls(cells)
    store = design.readonly_store(plan.path.parent.parent / "mini-preparation")
    for cell, row in zip(cells, packet["first_requests"], strict=True):
        value = collector.review.read_json(store, row["request_artifact"])
        assert design.wire(value) == design.wire(
            episode.episode_request(json.loads(cell.request_json)))
        assert value["include"] == ["reasoning.encrypted_content"] and value["store"] is False
        assert value["max_output_tokens"] == 25000
        assert not any(i.get("type") == "reasoning" for i in value["input"])
    before = snapshot(plan.frozen.source_root, plan.path.parent)
    for _ in range(2):
        assert collector.load_plan(plan.path, plan.packet_hash).packet == packet
    assert before == snapshot(plan.frozen.source_root, plan.path.parent)
    assert not grant.result_root.exists()


@pytest.mark.parametrize("field", ["episode_profile", "max_responses_per_episode",
                                    "comparison_groups", "maximum_generation_calls"])
def test_profile_or_window_changes_cannot_use_the_same_execution_contract(mini, field):
    plan, grant = mini
    changed = copy.deepcopy(plan.packet)
    changed[field] = {
        "episode_profile": episode.FACTORIAL.name,
        "max_responses_per_episode": 8,
        "comparison_groups": [["C1", 1, "AC"]],
        "maximum_generation_calls": 999,
    }[field]
    other = plan.path.with_name("changed.json")
    other.write_text(canonical_json(changed), encoding="utf-8")
    with pytest.raises(ContractError, match="execution contract"):
        collector.load_plan(other, sha256_bytes(other.read_bytes()))
    assert not grant.result_root.exists()


def test_mini_collection_uses_only_eight_selected_cells_and_one_cap(mini):
    client = Client()
    result = run(mini, client)
    assert result["terminal"] == "OBSERVATION_WINDOWS_COMPLETED", result
    assert result["provider_calls"] == result["registered_episodes"] == 8
    assert result["unstarted_episodes"] == 0
    assert result["recorded_cost_nanos"] == 8 * 1200000
    assert all(r["model"] == shared.MODEL for r in client.created)
    assert collector.inspect(mini[1].result_root) == result
    journal = collector.DevJournal(mini[1].result_root, result["run_id"])
    registrations = [e["payload"] for e in journal.events()
                     if e["event_type"] == "branch_registered"]
    assert [(r["case_id"], r["repeat"], r["arm"]) for r in registrations] == [
        (case, repeat, arm)
        for case, repeat, arms in episode.MINI_RECOVERY.groups() for arm in arms]
    for r in registrations:
        event = next(e for e in collector._events(mini[1].result_root, r)
                     if e["event_type"] == "diagnostic_episode_started")
        assert event["payload"]["response_limit"] is None


def test_mini_uncertainty_stops_the_second_arm_and_all_later_groups(mini):
    client = Client(failure="transport")
    result = run(mini, client)
    assert result["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert result["provider_calls"] == len(client.created) == 2
    assert result["registered_episodes"] == 2 and result["unstarted_episodes"] == 6
    assert result["recorded_cost_nanos"] == 1200000
    assert result["request_failures"][-1]["effective_timeout_seconds"] == 300


def test_mini_depth_requires_full_pair_reserve_before_count():
    completed = []
    branches = [SimpleNamespace(
        arm=a, terminal=None, new_provider_calls=0, max_responses=None,
        finish=lambda *args: completed.append(args)) for a in "AB"]
    episode.run_round(branches, None, {}, shared.SharedCostLedger(Decimal("0.632")),
                      profile=episode.MINI_RECOVERY)
    assert len(completed) == 2 and all(c[0] == "DIAGNOSTIC_COST_LIMIT" for c in completed)
    with pytest.raises(ContractError, match="complete comparison group"):
        episode.run_round(branches[:1], None, {}, shared.SharedCostLedger(Decimal("5")),
                          profile=episode.MINI_RECOVERY)


def test_public_failure_at_eighth_response_can_mutate_recheck_and_finish(episodes):
    pair = [e for e in episodes if e.arm in "AB"]
    for e in pair:
        e.max_responses = None
    ledger = shared.SharedCostLedger(Decimal("5"))

    def step(calls, tag):
        adapters = {e.arm: MultiAdapter(e.arm, calls(e), tag=tag) for e in pair}
        episode.run_round(pair, SimpleNamespace(public=pair[0].gateway.public_task), adapters,
                          ledger, profile=episode.MINI_RECOVERY)
        return adapters

    for index in range(6):
        step(lambda _, i=index: [c.model_copy(update={"action_id": f"read-{i}-{c.action_id}"})
                                for c in read_calls()], str(index))
    step(lambda e: [mutation_call(e.gateway)], "first-mutation")
    for e in pair:
        e.gateway.sandbox = FailOnce(e.gateway.sandbox)
    step(lambda _: [call("run_check", "failed", check_id="existing-unit-tests")], "failed")
    assert all(e.new_provider_calls == 8 and e.terminal is None for e in pair)

    def repair(e):
        c = mutation_call(e.gateway, action_id="repair")
        source = MOCK_MUTATIONS["csv-quoted-newline"]
        c.arguments["old_text"] = source.new_text
        c.arguments["new_text"] = source.new_text + "\n# mock recovery candidate\n"
        return [c]

    after = step(repair, "repair")
    for e in pair:
        assert e.gateway.accepted_mutations == 2 and e.terminal is None
        assert "PUBLIC_CHECK_FAILURE_SENTINEL" in canonical_json(after[e.arm].requests[0])
    step(lambda _: [call("run_check", "recheck", check_id="existing-unit-tests")], "recheck")
    step(lambda _: [call("finish_task", "finish")], "finish")
    for e in pair:
        assert e.new_provider_calls == 11
        assert e.terminal["terminal"] == "PUBLIC_CHECKS_SUBMITTED"
        assert e.gateway.limits.max_model_calls == 40
        assert e.gateway.limits.max_tool_actions == 100
        assert e.gateway.limits.max_accepted_mutations == 4


def test_remaining_global_budget_still_stops_before_new_count(episodes):
    pair = [e for e in episodes if e.arm in "AB"]
    adapters = {e.arm: MultiAdapter(e.arm, read_calls()) for e in pair}
    package = SimpleNamespace(public=pair[0].gateway.public_task)
    for e in pair:
        e.max_responses = None
    episode.run_round(pair, package, adapters, shared.SharedCostLedger(Decimal("5")),
                      profile=episode.MINI_RECOVERY)
    for e in pair:
        e.new_provider_calls = 8
        e.counters.model_calls = 39
        adapter = MultiAdapter(e.arm, [])
        assert e.prepare_request(package, adapter) is None
        assert e.terminal["terminal"] == "LIMIT_REACHED"
        assert adapter.sequence == []


def test_mini_hydration_still_uses_native_budget_and_never_old_provider_state(mini, tmp_path):
    plan, _ = mini
    cell = episode.MINI_RECOVERY.cells(plan.frozen)[0]
    branch = initializer(
        plan.frozen, cell, tmp_path / "branch", tmp_path / "copy", plan.package,
        LocalSandbox(), profile=episode.MINI_RECOVERY)
    assert branch.max_responses is None
    # This synthetic prefix has no durable provider dispatches; real checkpoints
    # are independently restored in the external no-call rehearsal.
    assert branch.counters.model_calls == 0
    assert branch.new_provider_calls == 0
    assert not any(e["event_type"] == "turn_started" for e in branch.journal.events())
    assert not any(i.get("type") == "reasoning" for i in branch.seed_request["input"])
    assert branch.gateway.limits.max_model_calls == 40
    state = reconstruct_state(branch.seed_request["input"])
    assert state["remaining_budget"]["model_calls"] == 40 - branch.counters.model_calls
