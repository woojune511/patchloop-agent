"""Small, provider-free controls for evidence-preserving finalization context."""

import copy
import json

import pytest

from patchloop.dev import completion_context
from patchloop.util import canonical_json

DIFF = "sha256:" + "a" * 64
FILE = "sha256:" + "b" * 64
SOURCE_BODY = "source-body-must-not-repeat\n" * 500
BULK_OUTPUT = "old-probe-bulk-must-not-repeat\n" * 2_000


def state():
    exception = {
        "kind": "original_target_exception", "action_id": "original-after-edit",
        "case_id": "original", "diff_hash": DIFF, "call_id": "target-1",
        "exception": {"type": "builtins.FileNotFoundError", "message": "missing initializer"},
        "capture": {"stdout": "", "stderr": "target diagnostic"}, "condition_match": "same",
    }
    return {
        "public_task": {"task_id": "fixture", "issue": "Resolve the original failure."},
        "workflow_gate": "ready_to_submit",
        "completion_guidance": {"next_action": {"tool": "finish_task"}},
        "available_tool_names": ["finish_task", "stop_task", "read_file", "search_files"],
        "remaining_budget": {"model_calls": 2, "tool_actions": 4, "cost": {"remaining": 90}},
        "action_horizon": {"minimum_completion_calls": 1, "completion_possible": True},
        "current_diff": {"patch_hash": DIFF, "patch": "-return old\n+return new\n",
                         "changed_files": ["source.py"], "added_lines": 1, "deleted_lines": 1},
        "visible_check_status": [{"check_id": "required", "status": "PASS", "diff_hash": DIFF}],
        "remaining_visible_check_ids": [],
        "current_public_failure": exception,
        "reproduction_review": {
            "required": {"status": "UNKNOWN", "reason": "requirement_mapping_unverified"},
            "original_task_verification": "mapping_unverified", "current_diff_hash": DIFF,
            "completion": {"status": "unverified", "target_failure_count": 1,
                "case_count": 2, "omitted_count": 1, "cases": [{
                    "case_id": "original", "status": "unverified", "target_failure": exception,
                    "current": {"action_id": "original-after-edit", "diff_hash": DIFF,
                                "comparison": "not_compared", "observed_json": None},
                    "comparability": {"status": "same", "differences": []},
                    "evidence": {"status": "UNKNOWN"}}]},
        },
        "working_notes": {
            "findings": [{"note_id": "n1", "statement": "The original is still unverified."}],
            "open_question": {"question": "Was the original exception resolved?"},
            "verification": {"unresolved_ids": ["v1"], "items": [
                {"concern_id": "v1", "status": "unresolved", "statement": "Retain the exception"},
                {"concern_id": "v2", "status": "resolved", "statement": "Retain its history"}],
                "observations": {"items": [{"action_id": "failed-probe", "currency": "historical"}],
                                 "omitted_count": 2}},
        },
        "working_plan": {"plan": {"text": "Check the original; report unresolved behavior.",
                                    "diff_hash": DIFF, "revision": 2},
                         "review_request": {"requested": True,
                                            "reasons": ["first_ready_to_submit"]}},
        "source_spans": [{"path": "source.py", "file_hash": FILE, "start_line": 10,
                          "end_line": 20, "content": SOURCE_BODY}],
        "observed_source_index": {"entries": [{"path": "source.py", "file_hash": FILE,
                                               "kind": "function", "name": "parse",
                                               "start_line": 10}], "omitted_count": 0},
        "recent_checks": [
            {"action_id": "old-check", "check_id": "required", "diff_hash": "old",
             "passed": False, "stdout": BULK_OUTPUT},
            {"action_id": "check", "check_id": "required", "diff_hash": DIFF,
             "passed": True, "exit_code": 0, "stdout": BULK_OUTPUT}],
        "recent_tests": [{"action_id": "tests", "diff_hash": DIFF, "test_status": "PASS",
                          "comparison": {"status": "PASSED_BOTH",
                                         "original_requirement_credit": False},
                          "stdout": BULK_OUTPUT}],
        "recent_probes": [{"action_id": "old-probe", "diff_hash": "old", "stdout": BULK_OUTPUT}],
        "latest_tool_results": [{"tool": "run_probe", "action_id": "original-after-edit",
                                 "status": "failed", "error_code": "TARGET_ERROR",
                                 "message": "Unexpected target exception",
                                 "workspace_diff_hash": DIFF,
                                 "output": {"target_failure": exception, "exit_code": 1,
                                            "stdout": "latest target diagnostic",
                                            "python_source": SOURCE_BODY}}],
        "last_successful_mutation": {"postimage_evidence": {"content": SOURCE_BODY}},
        "operator_private_material": "must-not-enter-finalization",
    }


def test_finalization_preserves_verification_uncertainty_failure_and_unresolved_plan_exactly():
    original = state()
    before = copy.deepcopy(original)
    projected = completion_context.project(original)
    for key in ("public_task", "current_diff", "visible_check_status", "current_public_failure",
                "reproduction_review", "working_notes", "working_plan", "remaining_budget"):
        assert projected[key] == original[key]
    assert original == before
    projected["current_public_failure"]["exception"]["message"] = "changed derived view"
    assert original == before


def test_source_and_old_bulk_are_removed_but_current_outcomes_and_retrieval_ids_remain():
    original = state()
    projected = completion_context.project(original)
    serialized = canonical_json(projected)
    assert "source-body-must-not-repeat" not in serialized
    assert "old-probe-bulk-must-not-repeat" not in serialized
    assert "must-not-enter-finalization" not in serialized
    assert len(serialized) < len(canonical_json(original)) // 8
    assert not projected.get("recent_probes") and "source_spans" not in projected
    assert projected["recent_checks"] == [{"action_id": "check", "diff_hash": DIFF,
                                           "check_id": "required", "passed": True, "exit_code": 0}]
    assert projected["recent_tests"][0]["comparison"]["status"] == "PASSED_BOTH"
    result = projected["latest_tool_results"][0]
    assert result["status"] == "failed" and result["message"] == "Unexpected target exception"
    assert result["output"]["target_failure"] == original["current_public_failure"]
    source = projected["completion_stage"]["source_retrieval"]
    assert source["available_tools"] == ["read_file", "search_files"]
    assert source["source_bodies_delivered"] is False
    assert source["sources"] == [{"path": "source.py", "file_hash": FILE,
                                  "observed_ranges": [[10, 20]], "symbols": [{
                                      "kind": "function", "name": "parse", "start_line": 10}]}]


@pytest.mark.parametrize("mutation_tool", ["replace_text", "edit_files"])
def test_offered_repair_keeps_selected_current_source_without_reopening_reads(mutation_tool):
    original = state()
    original["available_tool_names"] = [mutation_tool, "run_check", "finish_task", "stop_task"]
    original["context_projection"] = {
        "retained_content_chars": len(SOURCE_BODY), "retained_content_limit": 24_000,
        "omitted_observed_line_count": 3,
    }
    before = copy.deepcopy(original)
    projected = completion_context.project(original)
    for field in ("source_spans", "observed_source_index", "context_projection",
                  "available_tool_names", "remaining_budget"):
        assert projected[field] == original[field]
    source = projected["completion_stage"]["source_retrieval"]
    assert source["source_bodies_delivered"] is True
    assert source["available_tools"] == []
    assert "old-probe-bulk-must-not-repeat" not in canonical_json(projected)
    assert "must-not-enter-finalization" not in canonical_json(projected)
    assert completion_context.project(projected) == projected
    projected["source_spans"][0]["content"] = "changed derived view"
    assert original == before


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
@pytest.mark.parametrize("mutation_tool", ["replace_text", "edit_files"])
def test_actual_completion_request_retains_selected_anchor_when_repair_is_offered(
    tmp_path, context_policy, mutation_tool,
):
    from patchloop.artifacts import ArtifactStore
    from patchloop.dev import runner
    from patchloop.dev.conversation import reconstruct_state
    from patchloop.dev.state import DevJournal

    original = state()
    original["available_tool_names"] = [mutation_tool, "run_check", "finish_task", "stop_task"]
    original["latest_tool_results"] = []
    original["working_notes"] = {"findings": [], "verification": {"items": []}}
    original["source_spans"][0]["content"] = "CURRENT_REPAIR_ANCHOR"
    original["source_spans"][0]["end_line"] = 10
    journal = DevJournal(tmp_path, "run_dev_completionanchor")
    store = ArtifactStore(tmp_path / "artifacts")
    with journal.execution_lock():
        request_input = runner._build_model_input(
            journal=journal, artifact_store=store, context=canonical_json(original),
            latest_tool_results=[], context_policy=context_policy,
            planning_policy="none", agent_policy="thin",
        )
    actual = reconstruct_state(request_input, context_policy=context_policy)
    assert canonical_json(request_input).count("CURRENT_REPAIR_ANCHOR") == 1
    assert actual["current_sources"][0]["inline_spans"][0]["content"] == "CURRENT_REPAIR_ANCHOR"
    assert actual["available_tool_names"] == original["available_tool_names"]
    assert "read_file" not in actual["available_tool_names"]


def test_repair_source_reuses_exact_native_body_and_closes_with_mutation_tools():
    from patchloop.dev import runner, segments
    from patchloop.dev.conversation import assemble_model_input, reconstruct_state

    original = state()
    result = source_result()
    original["available_tool_names"] = ["replace_text", "finish_task", "stop_task"]
    original["working_notes"] = {"findings": [], "verification": {"items": []}}
    original["latest_tool_results"] = []
    original["source_spans"] = copy.deepcopy(result["output"]["spans"])
    original["observed_source_index"] = {"entries": [], "omitted_count": 0}
    history = [
        {"type": "function_call", "call_id": result["action_id"], "name": "read_file",
         "arguments": "{}"},
        {"type": "function_call_output", "call_id": result["action_id"],
         "output": canonical_json(result)},
    ]
    before = copy.deepcopy(history)
    projected = completion_context.project(original)
    view = runner._segment_current_view(projected, history, [])
    request_input = assemble_model_input(
        system_prompt=completion_context.SYSTEM_PROMPT, state=view, history=history,
        context_policy=segments.POLICY,
    )
    actual = reconstruct_state(request_input, context_policy=segments.POLICY)
    assert canonical_json(request_input).count("LATEST_SOURCE_BODY") == 1
    assert actual["current_sources"][0]["content_delivery"] == {
        result["action_id"]: {"output.spans[0]": [[1, 2]]},
    }
    assert history == before
    projected["available_tool_names"] = ["finish_task", "stop_task"]
    closed = completion_context.project(projected)
    assert "LATEST_SOURCE_BODY" not in canonical_json(closed)
    assert closed["completion_stage"]["source_retrieval"]["source_bodies_delivered"] is False


@pytest.mark.parametrize("gate", [
    None, "needs_mutation", "needs_visible_checks", "verification_incomplete",
])
def test_host_gate_is_the_only_activation_authority_and_nonfinal_states_are_unchanged(gate):
    original = state()
    original["workflow_gate"] = gate
    original["completion_stage"] = {"policy": completion_context.POLICY, "active": True}
    assert not completion_context.active(original)
    assert completion_context.project(original) == original


@pytest.mark.parametrize("code,fresh", [
    ("incomplete_response", True), ("MISSING_REQUIRED_TOOL", True), ("INVALID_TOOL_BATCH", False),
])
def test_correction_keeps_finalization_evidence_budget_and_request_failure(code, fresh):
    original = state()
    failure = {"violations": [{"field_path": "assessment", "message": "required"}]}
    correction = completion_context.correction(code, "Fix the assessment", failure)
    original["protocol_correction"] = {"code": code, "completion_correction": correction}
    projected = completion_context.project(original)
    assert completion_context.active(projected)
    assert projected["protocol_correction"] == original["protocol_correction"]
    assert projected["remaining_budget"] == original["remaining_budget"]
    assert correction["fresh_segment"] is fresh
    assert correction["tool_contract_failure"] == failure
    assert projected["working_notes"] == original["working_notes"]
    if fresh:
        assert "unverified" in correction["message"] and "same" in correction["message"]


def test_missing_original_evidence_is_not_created_or_promoted_and_no_tools_are_granted():
    original = state()
    del original["reproduction_review"]
    del original["current_public_failure"]
    original["available_tool_names"] = ["stop_task"]
    projected = completion_context.project(original)
    assert "reproduction_review" not in projected and "current_public_failure" not in projected
    assert projected["available_tool_names"] == ["stop_task"]
    assert projected["completion_stage"]["source_retrieval"]["available_tools"] == []
    original["visible_check_status"][0]["status"] = "FAIL"
    assert completion_context.project(original)["visible_check_status"][0]["status"] == "FAIL"


def test_projection_is_idempotent_and_can_accept_already_compact_source_catalogs():
    original = state()
    del original["source_spans"]
    del original["observed_source_index"]
    original["current_sources"] = [{
        "path": "source.py", "file_hash": FILE,
        "inline_spans": [{"start_line": 1, "end_line": 2, "content": SOURCE_BODY}],
        "content_delivery": {"read": {"output.spans.0.content": [[4, 6]]}},
        "headers": [{"kind": "function", "name": "parse", "start_line": 1}],
    }]
    projected = completion_context.project(original)
    assert completion_context.project(projected) == projected
    source = projected["completion_stage"]["source_retrieval"]["sources"][0]
    assert source["observed_ranges"] == [[1, 2], [4, 6]]
    assert "source-body-must-not-repeat" not in canonical_json(projected)
    assert projected["completion_stage"]["omitted_historical_records"]["recent_checks"] == 1


def test_context_contract_is_explicit_and_each_call_is_independent():
    declared = completion_context.contract()
    assert declared["policy"] == completion_context.POLICY
    assert declared["authority"] == "public-context-projection-only"
    assert declared["unknown_evidence"] == "remains-unverified-no-success-inference"
    declared["preserved"].clear()
    assert completion_context.contract()["preserved"]
    assert "unverified_delivery" in completion_context.SYSTEM_PROMPT


def source_result(tool="read_file", scope="repository"):
    span = {"path": "source.py", "file_hash": FILE, "start_line": 1, "end_line": 2,
            "content": "LATEST_SOURCE_BODY\nreturn value"}
    key = "spans" if scope == "repository" else "dependency_spans"
    output = {"source_scope": scope, key: [span], "truncated": False}
    if tool == "read_file":
        output.update(path="source.py", start_line=1, end_line=2, line_count=2,
                      eof=False, next_start_line=None, diagnostic=None)
    else:
        output.update(query="value", path_glob="**/*.py", searched_file_count=1)
    if scope != "repository":
        output.update(read_only=True, dependency_source_identity="registered-identity")
        span.update(source_scope=scope, read_only=True, provenance={"scope": scope,
                    "path": "source.py", "file_hash": FILE})
    return {"tool": tool, "action_id": "latest-source", "input_hash": FILE,
            "status": "succeeded", "workspace_diff_hash": DIFF, "output": output}


@pytest.mark.parametrize("tool", ["read_file", "search_files"])
@pytest.mark.parametrize("scope", ["repository", "dependency:caller"])
def test_latest_successful_current_source_output_survives_completion_projection(tool, scope):
    original = state()
    result = source_result(tool, scope)
    original["latest_tool_results"] = [result]
    before = copy.deepcopy(original)
    projected = completion_context.project(original)
    assert projected["latest_tool_results"] == [result]
    assert projected["completion_stage"]["source_retrieval"]["source_bodies_delivered"] is True
    assert completion_context.project(projected) == projected
    assert original == before
    assert SOURCE_BODY not in canonical_json(projected)
    for key in ("workflow_gate", "available_tool_names", "remaining_budget", "current_diff",
                "visible_check_status", "reproduction_review"):
        assert projected[key] == original[key]
    projected["latest_tool_results"][0]["output"]["truncated"] = True
    assert original == before


@pytest.mark.parametrize("change", [
    {"status": "failed"}, {"workspace_diff_hash": "old"},
    {"workspace_diff_hash": None}, {"historical": True}, {"tool": "run_probe"},
])
def test_latest_source_exception_does_not_retain_failed_stale_unbound_or_other_bulk(change):
    original = state()
    original["latest_tool_results"] = [{**source_result(), **change}]
    projected = completion_context.project(original)
    assert "LATEST_SOURCE_BODY" not in canonical_json(projected)
    assert projected["latest_tool_results"][0]["output"] == {"truncated": False}
    assert projected["completion_stage"]["source_retrieval"]["source_bodies_delivered"] is False


def test_no_current_diff_cannot_retain_source_body_and_later_batch_does_not_reuse_it():
    original = state()
    original["latest_tool_results"] = [source_result()]
    projected = completion_context.project(original)
    projected["latest_tool_results"] = [{"tool": "run_check", "status": "succeeded",
                                        "workspace_diff_hash": DIFF, "output": {"passed": True}}]
    assert "LATEST_SOURCE_BODY" not in canonical_json(completion_context.project(projected))
    original["current_diff"].pop("patch_hash")
    assert "LATEST_SOURCE_BODY" not in canonical_json(completion_context.project(original))


@pytest.mark.parametrize("native", [False, True])
@pytest.mark.parametrize("tool", ["read_file", "run_probe"])
def test_actual_segment_view_delivers_latest_observation_once_with_or_without_native(native, tool):
    from patchloop.dev import runner, segments
    from patchloop.dev.contracts import DevToolResult
    from patchloop.dev.conversation import assemble_model_input, reconstruct_state
    from patchloop.dev.probe_observation import project_probe_result

    original = state()
    original["working_notes"] = {"findings": [], "verification": {"items": []}}
    raw = source_result() if tool == "read_file" else probe_result()
    result = project_probe_result(raw)
    original["latest_tool_results"] = [result]
    history = ([{"type": "function_call", "call_id": result["action_id"], "name": tool,
                 "arguments": "{}"},
                {"type": "function_call_output", "call_id": result["action_id"],
                 "output": canonical_json(result)}] if native else [])
    before = copy.deepcopy(history)
    view = runner._segment_current_view(completion_context.project(original), history,
                                        [DevToolResult.model_validate(raw)])
    request_input = assemble_model_input(system_prompt=completion_context.SYSTEM_PROMPT,
                                        state=view, history=history, context_policy=segments.POLICY)
    actual = reconstruct_state(request_input, context_policy=segments.POLICY)
    marker = "LATEST_SOURCE_BODY" if tool == "read_file" else "LATEST_PROBE_STDOUT"
    assert canonical_json(request_input).count(marker) == 1
    assert "source-body-must-not-repeat" not in canonical_json(request_input)
    assert history == before
    if native:
        assert actual["latest_tool_results"] == []
        assert actual["latest_tool_results_delivery"]["action_ids"] == [result["action_id"]]
        delivered = [json.loads(row["output"]) for row in request_input
                     if row.get("type") == "function_call_output"]
    else:
        delivered = actual["latest_tool_results"]
    fields = ("spans",) if tool == "read_file" else ("stdout", "stderr", "setup_checks")
    for field in fields:
        assert delivered[0]["output"][field] == result["output"][field]
    if tool == "run_probe":
        assert delivered[0]["observation"] == result["observation"]


def probe_result(outcome="passed"):
    return {
        "tool": "run_probe", "action_id": "latest-probe", "input_hash": FILE,
        "status": "succeeded", "workspace_diff_hash": DIFF,
        "output": {
            "status": outcome, "question": "Which caller arguments reach the fallback?",
            "stdout": "LATEST_PROBE_STDOUT: {'fallback_calls': [{'path': ['root/leaf']}]}",
            "stderr": "LATEST_PROBE_STDERR: reported warning",
            "exit_code": 0 if outcome == "passed" else None if outcome == "timeout" else 1,
            "probe_stage": "execution_returned", "timed_out": outcome == "timeout",
            "deadline_exhausted": outcome == "timeout", "truncated": outcome == "output_limit",
            "cleanup_failed": outcome == "cleanup_failed", "captured_output_bytes": 99,
            "observed_output_bytes": 120 if outcome == "output_limit" else 99,
            "verification_scope": "helper_or_unbound_diagnostic",
            "source_hash": FILE, "snapshot_hash": DIFF, "execution_policy_hash": FILE,
            "setup_checks": {"status": "passed", "checks": [{"matched": True}]},
            "exception_diagnostics": {"status": "unknown", "reason": "report_unavailable"},
            "public_execution": {"status": "unknown", "files": [], "omitted_file_count": 0},
            "call_path": {"status": "incomplete", "collection_limit_reached": True},
        },
    }


@pytest.mark.parametrize("outcome", [
    "passed", "failed", "timeout", "output_limit", "cleanup_failed",
])
def test_current_probe_keeps_bounded_observations_without_promoting_execution_or_failure(outcome):
    from patchloop.dev.probe_observation import project_probe_result

    original = state()
    result = project_probe_result(probe_result(outcome))
    result["output"].update(python_source=SOURCE_BODY, execution_policy={"large": BULK_OUTPUT})
    original["latest_tool_results"] = [result]
    before = copy.deepcopy(original)
    projected = completion_context.project(original)
    retained = projected["latest_tool_results"][0]
    expected = copy.deepcopy(result)
    del expected["output"]["python_source"], expected["output"]["execution_policy"]
    assert retained == expected
    assert retained["observation"]["behavior_verdict"] == "not_assessed"
    assert retained["observation"]["execution_status"] == (
        "completed" if outcome == "passed" else outcome)
    assert completion_context.project(projected) == projected
    assert original == before
    assert SOURCE_BODY not in canonical_json(projected)
    assert BULK_OUTPUT not in canonical_json(projected)
    for field in ("workflow_gate", "remaining_budget", "available_tool_names",
                  "reproduction_review"):
        assert projected[field] == original[field]


def test_failed_partial_probe_retains_observed_json_with_its_incomplete_call_and_no_credit():
    from patchloop.dev.probe_observation import project_probe_result

    raw = probe_result("failed")
    raw.update(status="failed", error_code="PROBE_ERROR", message="partial observation")
    raw["output"]["reproduction"] = {
        "binding": {"program_hash": FILE}, "observed_json": {"has_f0010": False},
        "comparison": "not_compared", "reason": "declared_call_unobserved_or_incomplete",
        "call_observation": {"incomplete": True, "calls": [{"target_started": True,
            "capture": {"status": "incomplete", "stdout": "partial", "stderr": ""}}]},
        "requirement_mapping": "model_authored_unverified", "repair_success": "not_assessed",
    }
    original = state()
    original["latest_tool_results"] = [project_probe_result(raw)]
    retained = completion_context.project(original)["latest_tool_results"][0]
    assert retained == original["latest_tool_results"][0]
    assert retained["status"] == "failed"
    assert retained["output"]["reproduction"]["comparison"] == "not_compared"


@pytest.mark.parametrize("change", [
    {"workspace_diff_hash": "old"}, {"workspace_diff_hash": None}, {"historical": True},
])
def test_stale_or_unbound_probe_body_is_not_reintroduced_as_current_evidence(change):
    from patchloop.dev.probe_observation import project_probe_result

    original = state()
    original["latest_tool_results"] = [{**project_probe_result(probe_result()), **change}]
    projected = completion_context.project(original)
    assert "LATEST_PROBE_STDOUT" not in canonical_json(projected)
    assert "observation" not in projected["latest_tool_results"][0]


def test_missing_current_diff_or_absent_recent_record_does_not_invent_previous_probe_body():
    from patchloop.dev.probe_observation import project_probe_result

    original = state()
    original.pop("recent_probes")
    original["latest_tool_results"] = [project_probe_result(probe_result())]
    projected = completion_context.project(original)
    projected["latest_tool_results"] = [{"tool": "run_check", "status": "succeeded",
                                        "workspace_diff_hash": DIFF, "output": {"passed": True}}]
    assert "LATEST_PROBE_STDOUT" not in canonical_json(completion_context.project(projected))
    original["current_diff"].pop("patch_hash")
    assert "LATEST_PROBE_STDOUT" not in canonical_json(completion_context.project(original))


def recent_probe_record(outcome="passed"):
    """Match the bounded public row produced by runner._build_context."""
    from patchloop.dev.probe_observation import probe_observation

    result = probe_result(outcome)
    return {
        "action_id": result["action_id"], "diff_hash": DIFF, "historical": False,
        "diagnostic_only": True, "observation": probe_observation(result),
        "question": result["output"]["question"],
        "exit_code": result["output"]["exit_code"],
        "stdout": result["output"]["stdout"][-2_000:],
        "stderr": result["output"]["stderr"][-2_000:], "message": None,
    }


@pytest.mark.parametrize("outcome", [
    "passed", "failed", "timeout", "output_limit", "cleanup_failed",
])
def test_recent_current_probe_survives_later_test_without_promoting_its_outcome(outcome):
    original = state()
    recent = recent_probe_record(outcome)
    original["recent_probes"] = [recent]
    original["latest_tool_results"] = [{
        "tool": "run_tests", "action_id": "later-test", "status": "succeeded",
        "workspace_diff_hash": DIFF, "output": {"test_status": "PASS", "exit_code": 0},
    }]
    # Neither a program nor bulk tracing belongs in the retained observation.
    recent.update(python_source=SOURCE_BODY, call_path={"events": BULK_OUTPUT})
    before = copy.deepcopy(original)
    projected = completion_context.project(original)
    retained = projected["recent_probes"][0]
    for key in ("action_id", "diff_hash", "question", "stdout", "stderr", "exit_code",
                "observation", "diagnostic_only"):
        assert retained[key] == recent[key]
    assert retained["observation"]["behavior_verdict"] == "not_assessed"
    assert retained["observation"]["execution_status"] == (
        "completed" if outcome == "passed" else outcome)
    assert "python_source" not in retained and "call_path" not in retained
    assert SOURCE_BODY not in canonical_json(projected)
    assert BULK_OUTPUT not in canonical_json(projected)
    assert completion_context.project(projected) == projected
    assert original == before
    for field in ("workflow_gate", "remaining_budget", "available_tool_names",
                  "visible_check_status", "reproduction_review"):
        assert projected[field] == original[field]
    retained["observation"]["behavior_verdict"] = "changed-derived-view"
    assert original == before


@pytest.mark.parametrize("change", [
    {"diff_hash": "old"}, {"diff_hash": None}, {"historical": True},
])
def test_recent_probe_with_stale_or_unknown_identity_is_not_current_evidence(change):
    original = state()
    original["latest_tool_results"] = []
    original["recent_probes"] = [{**recent_probe_record(), **change}]
    projected = completion_context.project(original)
    assert not projected.get("recent_probes")
    assert "LATEST_PROBE_STDOUT" not in canonical_json(projected)


@pytest.mark.parametrize("patch_hash", [None, "new-diff"])
def test_retained_probe_is_dropped_when_current_diff_becomes_unknown_or_changes(patch_hash):
    original = state()
    original["latest_tool_results"] = []
    original["recent_probes"] = [recent_probe_record()]
    projected = completion_context.project(original)
    assert projected["recent_probes"][0]["stdout"].startswith("LATEST_PROBE_STDOUT")
    projected["current_diff"]["patch_hash"] = patch_hash
    updated = completion_context.project(projected)
    assert not updated.get("recent_probes")
    assert "LATEST_PROBE_STDOUT" not in canonical_json(updated)


@pytest.mark.parametrize("later_tool", ["run_tests", "read_file"])
@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
def test_fresh_completion_request_keeps_recent_probe_after_an_intervening_action(
    tmp_path, later_tool, context_policy,
):
    from patchloop.artifacts import ArtifactStore
    from patchloop.dev import runner
    from patchloop.dev.conversation import reconstruct_state
    from patchloop.dev.state import DevJournal

    original = state()
    original["working_notes"] = {"findings": [], "verification": {"items": []}}
    original["recent_probes"] = [recent_probe_record()]
    original["latest_tool_results"] = [{
        "tool": later_tool, "action_id": "intervening-action", "status": "succeeded",
        "workspace_diff_hash": DIFF, "output": {"exit_code": 0},
    }]
    journal = DevJournal(tmp_path, "run_dev_completionrecentprobe")
    store = ArtifactStore(tmp_path / "artifacts")
    # This is the fresh segment/snapshot after probe -> intervening action. No old
    # native exchange can substitute for the bounded current public observation.
    with journal.execution_lock():
        request_input = runner._build_model_input(
            journal=journal, artifact_store=store, context=canonical_json(original),
            latest_tool_results=[], context_policy=context_policy,
            planning_policy="none", agent_policy="thin",
        )
    actual = reconstruct_state(request_input, context_policy=context_policy)
    assert canonical_json(request_input).count("LATEST_PROBE_STDOUT") == 1
    assert actual["recent_probes"][0]["question"] == original["recent_probes"][0]["question"]
    assert actual["recent_probes"][0]["observation"]["behavior_verdict"] == "not_assessed"
    assert actual["available_tool_names"] == original["available_tool_names"]


def test_recent_probe_output_is_not_repeated_when_exact_native_result_is_visible():
    from patchloop.dev import runner, segments
    from patchloop.dev.conversation import assemble_model_input, reconstruct_state
    from patchloop.dev.probe_observation import project_probe_result

    original = state()
    original["working_notes"] = {"findings": [], "verification": {"items": []}}
    original["latest_tool_results"] = [{
        "tool": "run_tests", "action_id": "later-test", "status": "succeeded",
        "workspace_diff_hash": DIFF, "output": {"passed": True},
    }]
    original["recent_probes"] = [recent_probe_record()]
    raw = probe_result()
    raw["output"]["diff_hash"] = DIFF
    result = project_probe_result(raw)
    history = [
        {"type": "function_call", "call_id": result["action_id"], "name": "run_probe",
         "arguments": "{}"},
        {"type": "function_call_output", "call_id": result["action_id"],
         "output": canonical_json(result)},
    ]
    before = copy.deepcopy(history)
    view = runner._segment_current_view(completion_context.project(original), history, [])
    request_input = assemble_model_input(
        system_prompt=completion_context.SYSTEM_PROMPT, state=view, history=history,
        context_policy=segments.POLICY,
    )
    actual = reconstruct_state(request_input, context_policy=segments.POLICY)
    assert canonical_json(request_input).count("LATEST_PROBE_STDOUT") == 1
    assert "stdout" not in actual["recent_probes"][0]
    assert actual["recent_probes"][0]["delivery"] == "preceding_function_call_output"
    assert history == before
