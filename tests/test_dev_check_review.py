"""Public selection/source navigation must never become semantic check coverage."""

from __future__ import annotations

import copy
import json

import httpx
import pytest
from test_dev_conversation_v23 import _span

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import PublicTask
from patchloop.dev import check_review, runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, load_unique_yaml, sha256_json


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
    source = next(target["current_source_view"] for target in review["declared_targets"]
                  if target["path"] == "tests/test_0.py")
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


@pytest.mark.parametrize("passed", [True, False])
def test_result_and_added_test_source_cannot_certify_requirement_verification(passed):
    state = _state(command=["python", "-B", "-c", "registered_wrapper()", "tests/test_old.py"])
    state["recent_checks"][0]["passed"] = passed
    state["source_spans"] = [_span("def test_new(): assert reported_case()",
                                   path="tests/test_new.py")]
    state["recent_checks"][0]["mutation_expectation"] = {"expected_behavior": "bug fixed"}
    state["current_diff"]["patch"] += "\n+def test_new(): assert reported_case()"
    before = copy.deepcopy(state)
    projected = compact_model_state(state, [])
    review = projected["recent_checks"][0]["evidence_review"]
    assert review["selection_kind"] == "unresolved"
    assert review["coverage_status"] == review["requirement_verification"] == "not_assessed"
    assert "test source/additions and mutation expectations do not establish it" in (
        review["interpretation"])
    assert projected["recent_checks"][0]["passed"] is passed
    assert projected["available_tool_names"] == state["available_tool_names"]
    assert state == before


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
    assert review["requirement_verification"] == "not_assessed"
    assert row["passed"] and row["diff_hash"] == final["current_diff"]["patch_hash"]
    assert "finish_task" in final["available_tool_names"]
    assert first["current_diff"]["patch"] == "" and first["public_task"] == final["public_task"]
    if context_policy == "segmented-v1":
        assert any(event["event_type"] == "context_segment_started" for event in journal.events())


def _registered_state(*, check_target="tests/test_old.py", changed="tests/test_new.py"):
    prefix = ["/env/bin/python", "-B", "-c", "registered_pytest_wrapper()"]
    state = _state(command=[*prefix, check_target])
    state["public_task"]["test_suites"] = [{
        "id": "public-pytest", "runner": "pytest", "test_roots": ["tests"],
        "command": [*prefix, "-m", "not slow"], "working_directory": ".",
    }]
    state["current_diff"]["changed_files"] = [changed]
    state["recent_tests"] = []
    return state


def test_registered_wrapper_uses_exact_program_and_workdir_without_interpreting_python(monkeypatch):
    state = _registered_state()
    before = copy.deepcopy(state)

    def forbidden(*args, **kwargs):
        pytest.fail("selection review must not read source or execute the registered wrapper")

    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    view = compact_model_state(state, [])
    review = view["recent_checks"][0]["evidence_review"]
    assert review["selection_kind"] == "registered_pytest_arguments"
    assert [(t["path"], t["selection"]) for t in review["declared_targets"]] == [
        ("tests/test_old.py", "file"),
    ]
    changed = view["current_diff"]["test_execution_review"]
    assert changed["files"][0]["selection_status"] == "not_confirmed"
    assert changed["files"][0]["optional_run_tests_selection"] == {
        "suite_id": "public-pytest", "targets": ["tests/test_new.py"],
    }
    assert "missing does not mean never executed" in changed["basis"]
    assert view["available_tool_names"] == state["available_tool_names"]
    assert state == before


@pytest.mark.parametrize("changed_field", ["command", "working_directory", "runner"])
def test_unmatched_wrapper_contract_does_not_guess_pytest_arguments(changed_field):
    state = _registered_state()
    suite = state["public_task"]["test_suites"][0]
    if changed_field == "command":
        suite["command"][3] += "different_program()"
    elif changed_field == "working_directory":
        suite[changed_field] = "package"
    else:
        suite[changed_field] = "unknown"
    assert _review(state)["selection_kind"] == "unresolved"
    assert _review(state)["declared_targets"] == []


def test_directory_receipt_keeps_collection_unknown_for_changed_file():
    state = _registered_state(check_target="tests", changed="tests/new_combo.py")
    view = compact_model_state(state, [])
    target = view["recent_checks"][0]["evidence_review"]["declared_targets"][0]
    assert (target["path"], target["selection"]) == ("tests", "discovery")
    row = view["current_diff"]["test_execution_review"]["files"][0]
    assert row["selection_status"] == "directory_selected"
    assert row["collection_status"] == "not_reported"
    assert row["optional_run_tests_selection"]["targets"] == ["tests/new_combo.py"]
    assert row["visible_receipts"] == [{
        "action_id": "checked", "tool": "run_check", "selection": "directory_selected",
        "node_selector": None, "command_passed": True,
    }]
    assert "Missing collection telemetry alone does not require rerunning" in (
        view["current_diff"]["test_execution_review"]["basis"])


@pytest.mark.parametrize("tool", ["run_check", "run_tests"])
def test_current_passing_file_selection_does_not_recommend_the_same_selection(tool):
    state = _registered_state(check_target="tests/test_new.py" if tool == "run_check" else "tests")
    if tool == "run_tests":
        state["public_task"]["test_suites"][0]["command"] = ["python", "-m", "pytest", "-q"]
        state["recent_tests"] = [{
            "action_id": "selected", "suite_id": "public-pytest", "targets": ["tests/test_new.py"],
            "diff_hash": "candidate", "evidence_currency": "current", "passed": True,
            "test_status": "PASS",
        }]
    row = compact_model_state(state, [])["current_diff"]["test_execution_review"]["files"][0]
    assert row["selection_status"] == "explicit_file"
    assert row["collection_status"] == "not_reported"
    assert "optional_run_tests_selection" not in row
    assert "run_tests_selection" not in row


@pytest.mark.parametrize("tool,options,filters", [
    ("run_check", ["-k", "existing"], ["-k"]),
    ("run_check", ["-m", "not slow"], ["-m"]),
    ("run_check", ["--deselect=tests/test_new.py::test_added"], ["--deselect"]),
    ("run_tests", ["-m", "not slow"], ["-m"]),
])
def test_filtered_file_pass_retains_optional_selection_without_implying_collection(
    tool, options, filters,
):
    state = _registered_state(check_target="tests/test_new.py" if tool == "run_check" else "tests")
    if tool == "run_check":
        state["public_task"]["visible_checks"][0]["command"].extend(options)
    else:
        state["public_task"]["test_suites"][0]["command"] = ["python", "-m", "pytest", *options]
        state["recent_tests"] = [{
            "action_id": "filtered", "suite_id": "public-pytest", "targets": ["tests/test_new.py"],
            "diff_hash": "candidate", "evidence_currency": "current", "passed": True,
            "test_status": "PASS",
        }]
    row = compact_model_state(state, [])["current_diff"]["test_execution_review"]["files"][0]
    assert row["selection_status"] == "explicit_file"
    assert row["optional_run_tests_selection"]["targets"] == ["tests/test_new.py"]
    assert row["visible_receipts"][-1]["command_filters"] == filters
    assert row["collection_status"] == "not_reported"


@pytest.mark.parametrize("passed", [False, None])
def test_failed_or_unknown_file_result_retains_optional_selection(passed):
    state = _registered_state(check_target="tests/test_new.py")
    state["recent_checks"][0]["passed"] = passed
    row = compact_model_state(state, [])["current_diff"]["test_execution_review"]["files"][0]
    assert row["selection_status"] == "explicit_file"
    assert row["optional_run_tests_selection"]["targets"] == ["tests/test_new.py"]


def test_a_passing_file_receipt_does_not_hide_a_conflicting_failure():
    state = _registered_state(check_target="tests/test_new.py")
    state["recent_checks"].append({
        **state["recent_checks"][0], "action_id": "failed", "passed": False,
    })
    row = compact_model_state(state, [])["current_diff"]["test_execution_review"]["files"][0]
    assert row["optional_run_tests_selection"]["targets"] == ["tests/test_new.py"]
    assert [receipt["command_passed"] for receipt in row["visible_receipts"]] == [True, False]


@pytest.mark.parametrize("tool, node, expected", [
    ("run_check", None, "explicit_file"),
    ("run_check", "test_existing", "partial_nodes"),
    ("run_tests", None, "explicit_file"),
    ("run_tests", "test_existing", "partial_nodes"),
])
def test_explicit_file_and_node_receipts_are_separate_from_case_coverage(tool, node, expected):
    target = "tests/test_new.py" + ("::" + node if node is not None else "")
    state = _registered_state(check_target=target if tool == "run_check" else "tests/test_old.py")
    if tool == "run_tests":
        state["recent_tests"] = [{
            "action_id": "selected", "suite_id": "public-pytest", "targets": [target],
            "diff_hash": "candidate", "evidence_currency": "current", "passed": False,
            "test_status": "FAIL",
        }]
    view = compact_model_state(state, [])
    review = view["current_diff"]["test_execution_review"]
    row = review["files"][0]
    assert row["selection_status"] == expected
    assert row["visible_receipts"][0]["node_selector"] == node
    assert "do not prove collected test cases" in review["basis"]
    if tool == "run_tests":
        assert row["visible_receipts"][0]["test_status"] == "FAIL"
        assert row["visible_receipts"][0]["command_passed"] is False
    if node is not None or tool == "run_tests":
        assert row["optional_run_tests_selection"]["targets"] == ["tests/test_new.py"]
    assert view["recent_checks"][0]["evidence_review"]["coverage_status"] == "not_assessed"


@pytest.mark.parametrize("diff_hash,currency", [("old", "historical"), ("candidate", "unknown")])
def test_old_or_unknown_receipts_do_not_confirm_current_selection(diff_hash, currency):
    state = _registered_state(check_target="tests")
    state["recent_checks"][0].update(diff_hash=diff_hash, evidence_currency=currency)
    state["recent_tests"] = [{
        "action_id": "old-selection", "targets": ["tests/test_new.py"],
        "diff_hash": diff_hash, "evidence_currency": currency, "passed": True,
    }]
    row = compact_model_state(state, [])["current_diff"]["test_execution_review"]["files"][0]
    assert row["selection_status"] == "not_confirmed"
    assert row["visible_receipts"] == []
    assert row["optional_run_tests_selection"]["targets"] == ["tests/test_new.py"]


def test_changed_test_review_is_bounded_and_ignores_non_test_roots():
    state = _registered_state()
    state["current_diff"]["changed_files"] = ["src/feature.py", *[
        "tests/" + "long" * 30 + str(n) + ".py" for n in range(12)
    ]]
    view = compact_model_state(state, [])
    review = view["current_diff"]["test_execution_review"]
    assert len(review["files"]) <= check_review.MAX_TARGETS
    assert len(canonical_json(review)) <= check_review.MAX_REVIEW_CHARS
    assert len(review["files"]) + review["omitted_file_count"] == 12
    assert "src/feature.py" not in canonical_json(review)


@pytest.mark.parametrize("changed,directory", [
    ("tests/test_new.py", "package"),
    ("tests/.hidden.py", "."),
    ("tests/-option.py", "."),
])
def test_changed_test_review_does_not_recommend_invalid_registered_selectors(changed, directory):
    state = _registered_state(changed=changed)
    state["public_task"]["test_suites"][0]["working_directory"] = directory
    assert "test_execution_review" not in compact_model_state(state, [])["current_diff"]


def test_changed_test_review_survives_completion_projection():
    from patchloop.dev import completion_context

    state = _registered_state()
    state["workflow_gate"] = "ready_to_submit"
    state["available_tool_names"] = ["finish_task", "stop_task"]
    compact = compact_model_state(state, [])
    final = completion_context.project(compact)
    assert final["current_diff"]["test_execution_review"] == (
        compact["current_diff"]["test_execution_review"])
    assert final["available_tool_names"] == state["available_tool_names"]


@pytest.mark.parametrize("index, changed, declared, status", [
    (3, "pvlib/tests/test_irradiance_reindl.py", "pvlib/tests/test_irradiance.py", "not_confirmed"),
    (13, "tests/unittest_modutils.py", "tests", "directory_selected"),
    (18, "test/rules/std_L003_L036_combo.py", "test/rules", "directory_selected"),
])
def test_current_public_wrappers_expose_the_observed_selection_gaps(
    index, changed, declared, status,
):
    path = repository_root() / "tasks/dev-train/current-dev20" / str(index) / "public.yaml"
    public = PublicTask.model_validate(load_unique_yaml(path.read_text(encoding="utf-8")))
    state = _state()
    state["public_task"] = public.model_dump(mode="json")
    state["current_diff"]["changed_files"] = [changed]
    state["recent_checks"][0]["check_id"] = "base-regression"
    view = compact_model_state(state, [])
    review = view["recent_checks"][0]["evidence_review"]
    assert review["selection_kind"] == "registered_pytest_arguments"
    assert [target["path"] for target in review["declared_targets"]] == [declared]
    file_review = view["current_diff"]["test_execution_review"]["files"][0]
    assert file_review["selection_status"] == status
    assert file_review["collection_status"] == "not_reported"
    assert file_review["optional_run_tests_selection"] == {
        "suite_id": "public-pytest", "targets": [changed],
    }
