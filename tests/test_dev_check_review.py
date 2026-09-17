"""Public selection/source navigation must never become semantic check coverage."""

from __future__ import annotations

import copy
import json

import httpx
import pytest
from test_dev_conversation_v23 import _span

from patchloop.artifacts import ArtifactStore
from patchloop.dev import check_review, runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_json


def _state(*, command=None, directory="."):
    command = command or [
        "/project/.venv/bin/python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
        "-o", "addopts=", "tests/test_rule.py::test_changed", "tests/test_rule.py::test_preserved",
    ]
    return {
        "public_task": {"visible_checks": [{"id": "behavior", "command": command,
                                           "working_directory": directory}]},
        "current_diff": {"patch_hash": "candidate", "patch": "public patch"},
        "recent_checks": [{"action_id": "checked", "check_id": "behavior", "passed": True,
                           "diff_hash": "candidate", "evidence_currency": "current",
                           "counts_toward_completion": True, "stdout": "2 passed", "stderr": ""}],
        "source_spans": [], "available_tool_names": ["read_file", "finish_task"],
    }


def _review(state):
    return compact_model_state(state, [])["recent_checks"][0]["evidence_review"]


def test_pytest_selection_links_partial_current_source_without_coverage_or_new_reads(monkeypatch):
    state = _state()
    # These are already admitted source ranges, with a gap and an unseen test body.
    state["source_spans"] = [
        _span("def test_changed():\n    assert changed()", path="tests/test_rule.py", start=10),
        _span("    assert changed()", path="tests/test_rule.py", start=11),
        _span("def test_preserved():", path="tests/test_rule.py", start=20),
    ]
    before = copy.deepcopy(state)

    def forbidden(*args, **kwargs):
        pytest.fail("check linkage must not read a file or dispatch a request")

    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    review = _review(state)
    assert state == before
    assert review["definition_ref"] == "public_task.visible_checks[0]"
    command = state["public_task"]["visible_checks"][0]["command"]
    assert review["command_hash"] == sha256_json(command)
    assert review["selection_kind"] == "pytest_literals"
    assert review["coverage_status"] == "not_assessed"
    first, second = review["declared_targets"]
    assert (first["path"], first["node_selector"], first["command_argument_index"]) == (
        "tests/test_rule.py", "test_changed", 8,
    )
    assert second["node_selector"] == "test_preserved"
    assert first["current_source_view"] == {
        "ranges": [{"file_hash": "raw-hash", "start_line": 10, "end_line": 11},
                   {"file_hash": "raw-hash", "start_line": 20, "end_line": 20}],
        "omitted_range_count": 0,
    }
    assert "assert changed" not in canonical_json(review)


@pytest.mark.parametrize("command, kind, targets", [
    (["python3.13.exe", "-c", "assert public_example()"], "inline_python", []),
    (["pytest", "-k", "tests/looks_like_a_target.py", "tests/real.py::test_case"],
     "pytest_literals", ["tests/real.py"]),
    (["pytest", "--custom-plugin-option", "tests/ambiguous.py"], "unresolved", []),
    (["sh", "-c", "pytest tests/not_parsed.py"], "unresolved", []),
    (["python", "-m", "unittest", "tests.test_public"], "unresolved", []),
    (["pytest", "-p"], "unresolved", []),
    (["pytest", "--", "tests/real.py"], "pytest_literals", ["tests/real.py"]),
])
def test_literal_selection_and_definition_fallback(command, kind, targets):
    review = _review(_state(command=command))
    assert review["selection_kind"] == kind
    assert [target["path"] for target in review["declared_targets"]] == targets
    assert review["coverage_status"] == "not_assessed"
    assert review["definition_ref"] == "public_task.visible_checks[0]"


def test_relative_workdir_and_literal_parameter_selector_are_preserved():
    state = _state(command=["pytest.exe", r"tests\test_rule.py::test_case[path\value]"],
                   directory="package")
    target = _review(state)["declared_targets"][0]
    assert target["path"] == "package/tests/test_rule.py"
    assert target["node_selector"] == r"test_case[path\value]"
    assert target["current_source_view"]["ranges"] == []


def test_unresolved_paths_and_bounds_are_reported_without_guessing_or_cutting_selectors():
    arguments = ["/outside/test.py", "../test.py", "tests/test_*.py", "tests",
                 "tests/" + "x" * 300 + ".py", *[f"tests/test_{n}.py::test_case" for n in range(9)]]
    state = _state(command=["pytest", *arguments])
    state["source_spans"] = [_span("line", start=number, path="tests/test_0.py")
                             for number in range(1, 20, 2)]
    review = _review(state)
    assert len(review["declared_targets"]) <= check_review.MAX_TARGETS
    assert len(canonical_json(review)) <= check_review.MAX_REVIEW_CHARS
    assert review["omitted_target_count"] + len(review["declared_targets"]) == len(arguments)
    source = review["declared_targets"][0]["current_source_view"]
    assert len(source["ranges"]) == 3 and source["omitted_range_count"] == 7
    assert "/outside" not in canonical_json(review)


def test_history_currency_and_native_output_dedup_keep_review_without_rewriting():
    state = _state()
    state["recent_checks"][0].update(evidence_currency="historical", counts_toward_completion=False,
                                      diff_hash="old-candidate")
    output = {"action_id": "checked", "tool": "run_check", "status": "succeeded",
              "output": {"check_id": "behavior", "diff_hash": "old-candidate",
                         "passed": True, "stdout": "2 passed", "stderr": ""}}
    history = [{"type": "function_call_output", "call_id": "checked",
                "output": canonical_json(output)}]
    before = copy.deepcopy((state, history))
    view = compact_model_state(state, history)
    row = view["recent_checks"][0]
    assert row["delivery"] == "preceding_function_call_output" and "stdout" not in row
    assert row["evidence_currency"] == "historical" and not row["counts_toward_completion"]
    assert row["evidence_review"]["coverage_status"] == "not_assessed"
    assert (state, history) == before
    assert view["available_tool_names"] == state["available_tool_names"]


def test_source_updates_are_current_navigation_and_old_model_input_remains_exact():
    state = _state()
    first = assemble_model_input(
        system_prompt="public", state=compact_model_state(state, []), history=[],
    )
    saved = canonical_json(first)
    state["source_spans"] = [_span("assert preserved()", path="tests/test_rule.py", start=31,
                                   file_hash="current-file")]
    # Current coordinates remain authoritative even if content references earlier lines.
    state["source_spans"][0]["content_delivery"] = [{
        "action_id": "prior-read", "field": "output.spans[0]", "start_line": 10, "end_line": 10,
    }]
    view = compact_model_state(state, [])
    second = assemble_model_input(
        system_prompt="public", state=view, history=[], previous_input=first,
    )
    restored = reconstruct_state(json.loads(canonical_json(second)))
    ranges = restored["recent_checks"][0]["evidence_review"]["declared_targets"][0][
        "current_source_view"]["ranges"]
    assert ranges == [{"file_hash": "current-file", "start_line": 31, "end_line": 31}]
    assert canonical_json(first) == saved and second[:len(first)] == first
    state["source_spans"] = []
    assert _review(state)["declared_targets"][0]["current_source_view"]["ranges"] == []


def test_unknown_check_and_legacy_inputs_do_not_gain_an_invented_definition():
    state = _state()
    state["recent_checks"][0]["check_id"] = "unregistered"
    assert "evidence_review" not in compact_model_state(state, [])["recent_checks"][0]
    del state["public_task"]
    assert "evidence_review" not in compact_model_state(state, [])["recent_checks"][0]


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
def test_actual_mock_inputs_link_registered_check_and_keep_submission_eligible(
    tmp_path, monkeypatch, context_policy,
):
    def forbidden(*args, **kwargs):
        pytest.fail("mock check review must not dispatch a provider request")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
    request = DevRunRequest(
        provider="mock", model="mock-dev", state_root=tmp_path,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
        context_policy=context_policy, planning_policy="brief-v1",
    )
    run = runner.run_dev(request)["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS"
    assert run["call_counts"] == {"model": 4, "input_count": 0, "tool": 5}
    journal = DevJournal(tmp_path, run["run_id"])
    store = ArtifactStore(tmp_path / "artifacts")
    turns = [event["payload"] for event in journal.events()
             if event["event_type"] == "turn_started"]
    states = [reconstruct_state(
        runner._load_active_model_input(turn, store, context_policy=context_policy),
        context_policy=context_policy,
    ) for turn in turns]
    first, final = states[0], states[-1]
    row = final["recent_checks"][0]
    review = row["evidence_review"]
    # The smoke task uses unittest discovery, whose dynamic selection is not guessed.
    assert review["selection_kind"] == "unresolved"
    command = final["public_task"]["visible_checks"][0]["command"]
    assert review["command_hash"] == sha256_json(command)
    assert review["coverage_status"] == "not_assessed" and review["declared_targets"] == []
    assert row["passed"] and row["diff_hash"] == final["current_diff"]["patch_hash"]
    assert "finish_task" in final["available_tool_names"]
    assert first["current_diff"]["patch"] == "" and first["public_task"] == final["public_task"]
    if context_policy == "segmented-v1":
        assert any(event["event_type"] == "context_segment_started" for event in journal.events())
