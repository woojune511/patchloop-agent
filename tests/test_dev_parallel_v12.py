"""Durable parallel observation order and same-action replay regressions."""

import copy
from threading import Event

import pytest

from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.tools import DevToolGateway


def _call(action_id: str, name: str, arguments: dict) -> RequestedTool:
    return RequestedTool(
        name=name,
        action_id=action_id,
        arguments=arguments,
        turn_decision=PublicTurnDecision(
            mode="inspect", basis=f"Observe {action_id}.", evidence_goal=f"Question {action_id}."
        ),
    )


@pytest.mark.parametrize("first_end", [5, 20])
def test_parallel_finish_order_does_not_change_hydrated_observations(
    gateway_factory, monkeypatch, first_end
) -> None:
    gateway, journal, workspace = gateway_factory()
    decorated_a, decorated_b = Event(), Event()
    finished_b, finished_c = Event(), Event()
    decorate = gateway._decorate_read_output
    append = journal.append

    def ordered_decoration(**kwargs):
        action_id = kwargs["action_id"]
        if action_id == "B":
            assert decorated_a.wait(5)
        elif action_id == "C":
            assert decorated_b.wait(5)
        output = decorate(**kwargs)
        if action_id == "A":
            decorated_a.set()
        elif action_id == "B":
            decorated_b.set()
        return output

    def reversed_finishes(event_type, payload):
        action_id = payload.get("action_id")
        if event_type == "action_finished":
            if action_id == "A":
                assert finished_b.wait(5)
            elif action_id == "B":
                assert finished_c.wait(5)
        result = append(event_type, payload)
        if event_type == "action_finished":
            if action_id == "B":
                finished_b.set()
            elif action_id == "C":
                finished_c.set()
        return result

    monkeypatch.setattr(gateway, "_decorate_read_output", ordered_decoration)
    monkeypatch.setattr(journal, "append", reversed_finishes)
    results = gateway.execute_batch([
        _call("A", "read_file", {
            "path": "mini_data_utils/csvlite.py", "start_line": 1, "end_line": first_end,
        }),
        _call("B", "search_files", {
            "query": "import csv", "path_glob": "mini_data_utils/csvlite.py",
        }),
        _call("C", "search_files", {
            "query": "not-present-zero-match", "path_glob": "mini_data_utils/csvlite.py",
        }),
    ])
    assert all(result.status == "succeeded" for result in results)
    assert [
        event["payload"]["action_id"]
        for event in journal.events() if event["event_type"] == "action_finished"
    ] == ["C", "B", "A"]
    live_spans = copy.deepcopy(gateway.spans)
    live_ledger = gateway.evidence_ledger()
    assert results[1].output["evidence_gain"]["new_covered_line_count"] == 0
    assert live_ledger["latest_inspection_intent"]["evidence_goal"] == "Question C."
    assert [item["tool"] for item in live_ledger["recent_inspections"]] == [
        "search_files", "search_files", "read_file",
    ]
    restored = DevToolGateway(
        workspace=workspace, public_task=gateway.public_task, sandbox=gateway.sandbox,
        journal=journal, limits=gateway.limits,
    )
    assert restored.spans == live_spans
    assert restored.evidence_ledger() == live_ledger
    before = copy.deepcopy(restored.evidence_ledger())
    restored.execute(_call("A", "read_file", {
        "path": "mini_data_utils/csvlite.py", "start_line": 1, "end_line": first_end,
    }))
    assert restored.spans == live_spans
    assert restored.evidence_ledger() == before


def test_same_action_replay_does_not_promote_old_evidence(gateway_factory) -> None:
    gateway, _, _ = gateway_factory()
    first = _call("earlier", "read_file", {
        "path": "mini_data_utils/csvlite.py", "start_line": 1, "end_line": 5,
    })
    gateway.execute(first)
    gateway.execute(_call("later", "read_file", {
        "path": "mini_data_utils/csvlite.py", "start_line": 6, "end_line": 12,
    }))
    spans = copy.deepcopy(gateway.spans)
    ledger = copy.deepcopy(gateway.evidence_ledger())
    repetitions = dict(gateway._evidence_repetitions)
    gateway.execute(first)
    assert gateway.spans == spans
    assert gateway.evidence_ledger() == ledger
    assert gateway._evidence_repetitions == repetitions
    reread = gateway.execute(_call("new-observation", "read_file", first.arguments))
    assert reread.evidence_cache_hit
    assert reread.output["read_observation_seq"] > 2
    assert gateway.evidence_ledger()["latest_inspection_intent"]["evidence_goal"] == (
        "Question new-observation."
    )


def test_reverse_restore_keeps_repeated_search_counts_and_latest_intent(gateway_factory) -> None:
    gateway, _, _ = gateway_factory()
    arguments = {"query": "import csv", "path_glob": "mini_data_utils/csvlite.py"}
    earlier = gateway.execute(_call("first-search", "search_files", arguments))
    later = gateway.execute(_call("second-search", "search_files", arguments))
    restored, _, _ = gateway_factory()
    restored._restore_read_result(later)
    restored._restore_read_result(earlier)
    assert restored.spans == gateway.spans
    assert restored.evidence_ledger(diff_hash=later.workspace_diff_hash) == (
        gateway.evidence_ledger()
    )
    assert restored._evidence_repetitions == gateway._evidence_repetitions
