from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from patchloop.contracts import (
    Budget,
    EventType,
    ExperimentPurpose,
    ExperimentRunContext,
    ModelConfig,
    RunEvent,
    RunManifest,
)
from patchloop.errors import RecoveryError
from patchloop.trace_view import (
    ReadOnlyTraceStore,
    build_run_detail_view,
    build_run_index_view,
    build_run_list_view,
)
from patchloop.util import canonical_json


def _manifest(run_id: str = "run_trace_view") -> RunManifest:
    return RunManifest(
        run_id=run_id,
        task_id="public-task",
        task_version=1,
        base_commit="a" * 40,
        public_spec_hash="sha256:" + "b" * 64,
        model=ModelConfig(
            provider="openai",
            model_id="gpt-5.4-mini-2026-03-17",
            input_price_per_million_usd=0.75,
            cached_input_price_per_million_usd=0.075,
            cache_write_input_price_per_million_usd=0.75,
            output_price_per_million_usd=4.5,
            max_output_tokens=25_000,
        ),
        budget=Budget(
            max_model_calls=40,
            max_tool_calls=100,
            max_total_tokens=480_000,
            wall_clock_timeout_seconds=1_800,
        ),
        created_at=datetime.now(UTC),
    )


def _event(
    sequence: int,
    event_type: EventType,
    payload: dict,
    *,
    correlation_id: str | None = None,
) -> RunEvent:
    return RunEvent(
        event_id=f"evt_{sequence:032x}",
        run_id="run_trace_view",
        sequence=sequence,
        type=event_type,
        timestamp=datetime.now(UTC),
        actor="test",
        correlation_id=correlation_id,
        payload=payload,
    )


def _artifact(runtime: Path, value: dict) -> Path:
    raw = canonical_json(value).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    path = runtime / "artifacts" / "objects" / "sha256" / digest[:2] / digest[2:]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path


def _row(manifest: RunManifest) -> dict:
    return {
        "run_id": manifest.run_id,
        "status": "failed",
        "created_at": manifest.created_at.isoformat(),
        "manifest": manifest.model_dump(mode="json"),
        "result": {
            "outcome_kind": "agent_failure",
            "scope_compliant_success": False,
            "evaluation_status": "not_run",
            "agent_submission_status": "failed",
            "terminal_error": {
                "type": "ContractError",
                "code": "CONTRACT_ERROR",
                "message": "model response rejected: incomplete_response",
            },
            "verdicts": {
                "hidden_tests": "not_run",
                "regression_tests": "not_run",
                "scope_policy": "not_run",
                "safety_policy": "not_run",
            },
            "verifier_results": {"private_detail": "MUST NOT BE PROJECTED"},
            "usage": {
                "input_tokens": 1_000,
                "cached_input_tokens": 100,
                "cache_write_input_tokens": 0,
                "output_tokens": 500,
                "reasoning_output_tokens": 400,
                "model_calls": 1,
                "tool_calls": 1,
                "wall_clock_ms": 2_000,
                "model_cost_usd": 0.002925,
            },
        },
    }


def _rapid_manifest(run_id: str = "run_rapid_trace_view") -> RunManifest:
    manifest = _manifest(run_id)
    manifest.experiment = ExperimentRunContext(
        experiment_id="rapid-public-development-test",
        purpose=ExperimentPurpose.RAPID_PUBLIC_DEVELOPMENT,
        suite_hash="sha256:" + "c" * 64,
        execution_hash="sha256:" + "d" * 64,
        campaign_cost_control_hash="sha256:" + "e" * 64,
        schedule_seed=7,
        schedule_order=1,
        schedule_row_id="sha256:" + "f" * 64,
        repetition=1,
    )
    return manifest


def test_detail_projects_only_requested_agent_visible_surfaces(tmp_path: Path) -> None:
    runtime = tmp_path / ".patchloop"
    request_path = _artifact(
        runtime,
        {
            "request_body": {
                "input": [
                    {"role": "system", "content": "public system prompt"},
                    {"role": "user", "content": "public task context"},
                ],
                "max_output_tokens": 5_000,
            }
        },
    )
    response_path = _artifact(
        runtime,
        {
            "text": "",
            "tool_calls": [{"name": "read_file", "arguments": {"path": "src/public.py"}}],
            "response_status": "incomplete",
            "response_incomplete_reason": "max_output_tokens",
            "response_error": {"code": "incomplete_response"},
        },
    )
    input_path = _artifact(
        runtime,
        {"tool": "read_file", "input": {"path": "src/public.py"}},
    )
    output_path = _artifact(
        runtime,
        {
            "actual_start_line": 20,
            "content": "def public_value():\n    return 'public source text'",
        },
    )
    events = [
        _event(
            1,
            EventType.MODEL_CALLED,
            {
                "request_artifact_path": str(request_path),
                "artifact_path": str(response_path),
                "input_tokens": 1_000,
                "cached_input_tokens": 100,
                "cache_write_input_tokens": 0,
                "output_tokens": 500,
                "reasoning_output_tokens": 400,
                "response_model": "gpt-5.4-mini-2026-03-17",
            },
        ),
        _event(
            2,
            EventType.TOOL_CALLED,
            {
                "tool": "read_file",
                "input_artifact": {"path": str(input_path)},
            },
            correlation_id="call_public",
        ),
        _event(
            3,
            EventType.TOOL_SUCCEEDED,
            {
                "tool": "read_file",
                "status": "succeeded",
                "duration_ms": 12,
                "result_artifact": {"path": str(output_path)},
            },
            correlation_id="call_public",
        ),
    ]
    manifest = _manifest()
    detail = build_run_detail_view(
        row=_row(manifest),
        manifest=manifest,
        events=events,
        runtime=runtime,
    )

    assert detail["raw_render_schema_version"] == "raw-render-v1"
    assert [(item["role"], item["content"]) for item in detail["turns"][0]["messages"]] == [
        ("system", "public system prompt"),
        ("user", "public task context"),
    ]
    assert [
        {"name": call["name"], "arguments": call["arguments"]}
        for call in detail["turns"][0]["response"]["tool_calls"]
    ] == [{"name": "read_file", "arguments": '{\n  "path": "src/public.py"\n}'}]
    assert detail["turns"][0]["messages"][0]["view"]["kind"] == "text"
    assert detail["turns"][0]["response"]["tool_calls"][0]["arguments_view"]["kind"] == "json"
    assert detail["tools"][0]["name"] == "read_file"
    assert "public source text" in detail["tools"][0]["output"]
    assert detail["tools"][0]["input_view"]["kind"] == "json"
    output_children = {
        child["key"]: child["node"]
        for child in detail["tools"][0]["output_view"]["node"]["children"]
    }
    source_view = output_children["content"]["rendered"]
    assert source_view["kind"] == "code"
    assert source_view["path"] == "src/public.py"
    assert source_view["language"] == "python"
    assert [line["number"] for line in source_view["lines"]] == [20, 21]
    assert detail["result"]["terminal_error"]["code"] == "CONTRACT_ERROR"
    serialized = json.dumps(detail, default=str)
    assert "MUST NOT BE PROJECTED" not in serialized
    assert "private_spec_hash" not in serialized


def test_raw_render_projection_structures_json_diff_and_check_output(tmp_path: Path) -> None:
    runtime = tmp_path / ".patchloop"
    request_path = _artifact(
        runtime,
        {
            "request_body": {
                "input": [
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "public_task": {
                                    "issue": {"title": "Render public JSON"},
                                    "allowed_paths": ["src/public.py"],
                                }
                            }
                        ),
                    }
                ]
            }
        },
    )
    response_path = _artifact(
        runtime,
        {
            "text": "## Result\n\n- inspected source\n- ran check\n\n```python\nvalue = 1\n```",
            "tool_calls": [],
            "response_status": "completed",
        },
    )
    diff_input = _artifact(runtime, {"tool": "get_diff", "input": {}})
    diff_output = _artifact(
        runtime,
        {
            "patch": (
                "diff --git a/src/public.py b/src/public.py\n"
                "--- a/src/public.py\n"
                "+++ b/src/public.py\n"
                "@@ -1 +1 @@\n"
                "-old = 1\n"
                "+new = 2"
            )
        },
    )
    check_input = _artifact(
        runtime,
        {"tool": "run_check", "input": {"check_id": "targeted"}},
    )
    check_output = _artifact(
        runtime,
        {
            "stdout": "collected 1 item\nFAILED test_public.py::test_value\nAssertionError: 1 != 2",
            "stderr": "",
        },
    )
    events = [
        _event(
            1,
            EventType.MODEL_CALLED,
            {
                "request_artifact_path": str(request_path),
                "artifact_path": str(response_path),
            },
        ),
        _event(
            2,
            EventType.TOOL_CALLED,
            {"tool": "get_diff", "input_artifact": {"path": str(diff_input)}},
            correlation_id="diff",
        ),
        _event(
            3,
            EventType.TOOL_SUCCEEDED,
            {"tool": "get_diff", "result_artifact": {"path": str(diff_output)}},
            correlation_id="diff",
        ),
        _event(
            4,
            EventType.TOOL_CALLED,
            {"tool": "run_check", "input_artifact": {"path": str(check_input)}},
            correlation_id="check",
        ),
        _event(
            5,
            EventType.TOOL_SUCCEEDED,
            {
                "tool": "run_check",
                "check_id": "targeted",
                "passed": False,
                "result_artifact": {"path": str(check_output)},
            },
            correlation_id="check",
        ),
    ]
    manifest = _manifest()
    detail = build_run_detail_view(
        row=_row(manifest),
        manifest=manifest,
        events=events,
        runtime=runtime,
    )

    assert detail["turns"][0]["messages"][0]["view"]["kind"] == "json"
    response_blocks = detail["turns"][0]["response"]["text_view"]["blocks"]
    assert [block["kind"] for block in response_blocks] == ["heading", "list", "code"]
    diff_children = {
        child["key"]: child["node"]
        for child in detail["tools"][0]["output_view"]["node"]["children"]
    }
    diff_lines = diff_children["patch"]["rendered"]["lines"]
    assert {line["tone"] for line in diff_lines} >= {"meta", "hunk", "add", "delete"}
    check_children = {
        child["key"]: child["node"]
        for child in detail["tools"][1]["output_view"]["node"]["children"]
    }
    assert check_children["stdout"]["rendered"]["kind"] == "terminal"
    assert [line["tone"] for line in check_children["stdout"]["rendered"]["lines"]] == [
        "neutral",
        "bad",
        "bad",
    ]
    serialized = json.dumps(detail, default=str)
    assert "private evaluator output" not in serialized


def test_artifact_path_outside_runtime_is_not_rendered(tmp_path: Path) -> None:
    runtime = tmp_path / ".patchloop"
    outside = tmp_path / "outside.json"
    outside.write_text(
        canonical_json({"request_body": {"input": [{"role": "user", "content": "secret"}]}}),
        encoding="utf-8",
    )
    manifest = _manifest()
    detail = build_run_detail_view(
        row=_row(manifest),
        manifest=manifest,
        events=[
            _event(
                1,
                EventType.MODEL_CALLED,
                {
                    "request_artifact_path": str(outside),
                    "artifact_path": str(outside),
                    "input_tokens": 0,
                    "output_tokens": 0,
                },
            )
        ],
        runtime=runtime,
    )

    assert detail["turns"][0]["messages"] == []
    assert detail["turns"][0]["response"]["available"] is False
    assert "secret" not in json.dumps(detail, default=str)


def test_story_projection_groups_turns_and_reports_only_observed_failure_chain(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / ".patchloop"
    request_path = _artifact(
        runtime,
        {
            "request_body": {
                "input": [
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "public_task": {
                                    "issue": {
                                        "title": "Public failure story",
                                        "description": (
                                            "Fix the public behavior without changing tests."
                                        ),
                                    },
                                    "constraints": {
                                        "allowed_paths": ["src/public.py"],
                                        "max_changed_files": 1,
                                    },
                                    "visible_checks": [{"id": "public-check"}],
                                },
                                "evaluator_private": "MUST NOT BE PROJECTED",
                            }
                        ),
                    }
                ],
                "max_output_tokens": 5_000,
            }
        },
    )
    search_response = _artifact(
        runtime,
        {
            "text": "",
            "tool_calls": [{"name": "search_files", "arguments": {"query": "needle"}}],
            "response_status": "completed",
        },
    )
    patch_response = _artifact(
        runtime,
        {
            "text": "",
            "tool_calls": [{"name": "apply_patch", "arguments": {}}],
            "response_status": "completed",
        },
    )
    incomplete_response = _artifact(
        runtime,
        {
            "text": "",
            "tool_calls": [],
            "response_status": "incomplete",
            "response_incomplete_reason": "max_output_tokens",
            "response_error": {"code": "incomplete_response"},
        },
    )
    search_input = _artifact(runtime, {"input": {"query": "needle"}})
    search_output = _artifact(runtime, {"matches": ["src/public.py:1"]})
    patch_input = _artifact(runtime, {"input": {"patch": "public diff"}})
    patch_output = _artifact(runtime, {"status": "rejected"})
    events = [
        _event(
            1,
            EventType.PHASE_CHANGED,
            {"from": "INTAKE", "to": "REPRODUCE"},
        ),
        _event(
            2,
            EventType.MODEL_CALLED,
            {
                "request_artifact_path": str(request_path),
                "artifact_path": str(search_response),
                "input_tokens": 100,
                "output_tokens": 20,
            },
        ),
        _event(
            3,
            EventType.TOOL_CALLED,
            {"tool": "search_files", "input_artifact": {"path": str(search_input)}},
            correlation_id="search_1",
        ),
        _event(
            4,
            EventType.TOOL_SUCCEEDED,
            {
                "tool": "search_files",
                "duration_ms": 2,
                "result_artifact": {"path": str(search_output)},
            },
            correlation_id="search_1",
        ),
        _event(
            5,
            EventType.PHASE_CHANGED,
            {"from": "REPRODUCE", "to": "PLAN"},
        ),
        _event(
            6,
            EventType.PHASE_CHANGED,
            {"from": "PLAN", "to": "IMPLEMENT"},
        ),
        _event(
            7,
            EventType.MODEL_CALLED,
            {
                "request_artifact_path": str(request_path),
                "artifact_path": str(patch_response),
                "input_tokens": 200,
                "output_tokens": 40,
            },
        ),
        _event(
            8,
            EventType.TOOL_CALLED,
            {"tool": "apply_patch", "input_artifact": {"path": str(patch_input)}},
            correlation_id="patch_1",
        ),
        _event(
            9,
            EventType.TOOL_FAILED,
            {
                "tool": "apply_patch",
                "duration_ms": 3,
                "error_code": "CONTRACT_ERROR",
                "error_message": "public patch did not apply",
                "result_artifact": {"path": str(patch_output)},
            },
            correlation_id="patch_1",
        ),
        _event(
            10,
            EventType.MODEL_CALLED,
            {
                "request_artifact_path": str(request_path),
                "artifact_path": str(incomplete_response),
                "input_tokens": 300,
                "output_tokens": 50,
                "reasoning_output_tokens": 50,
            },
        ),
        _event(11, EventType.RUN_FAILED, {"code": "CONTRACT_ERROR"}),
    ]
    manifest = _manifest()

    detail = build_run_detail_view(
        row=_row(manifest),
        manifest=manifest,
        events=events,
        runtime=runtime,
    )

    assert detail["task"]["title"] == "Public failure story"
    assert detail["task"]["visible_check_count"] == 1
    assert detail["story"]["schema_version"] == "trace-story-v1"
    assert [stage["calls"] for stage in detail["story"]["workflow"]] == [1, 1, 0, 0, 0]
    assert [episode["kind"] for episode in detail["story"]["episodes"]] == [
        "inspect",
        "edit",
        "terminal",
    ]
    assert detail["story"]["timeline"][1]["phase"] == "IMPLEMENT"
    assert detail["story"]["timeline"][1]["tools"][0]["status"] == "failed"
    assert [item["kind"] for item in detail["story"]["failure_chain"]] == [
        "tool_failure",
        "model_incomplete",
        "run_terminal",
    ]
    assert "evaluator" in detail["story"]["summary"]
    serialized = json.dumps(detail["story"], default=str)
    assert "public patch did not apply" in serialized
    assert "MUST NOT BE PROJECTED" not in serialized


def test_agent_work_log_explains_task_reads_edits_and_public_check_failure(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / ".patchloop"
    request_path = _artifact(
        runtime,
        {
            "request_body": {
                "input": [
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "public_task": {
                                    "issue": {
                                        "title": "Stop resumed work",
                                        "description": "The public coroutine must not resume.",
                                    },
                                    "repository": {
                                        "url": "https://example.test/public.git",
                                        "language": "python",
                                    },
                                    "constraints": {
                                        "allowed_paths": ["src/**"],
                                        "forbidden_paths": ["tests/**"],
                                        "max_changed_files": 1,
                                        "max_diff_lines": 20,
                                        "dependency_changes_allowed": False,
                                        "public_api_changes_allowed": False,
                                    },
                                    "visible_checks": [{"id": "public-lifecycle"}],
                                },
                                "evaluator_private": "MUST NOT BE PROJECTED",
                            }
                        ),
                    }
                ],
                "max_output_tokens": 5_000,
            }
        },
    )
    response_path = _artifact(
        runtime,
        {"text": "", "tool_calls": [], "response_status": "completed"},
    )
    read_input = _artifact(
        runtime,
        {"input": {"path": "src/public.py", "start_line": 1, "end_line": 2}},
    )
    read_output = _artifact(
        runtime,
        {
            "actual_start_line": 1,
            "actual_end_line": 2,
            "content": 'def public():\n    return "old"\n',
        },
    )
    plan_input = _artifact(
        runtime,
        {
            "input": {
                "hypothesis": "The public function returns the stale value.",
                "intended_change": "Return the current value.",
                "expected_behavior": "The visible lifecycle check should pass.",
                "candidate_files": [{"path": "src/public.py"}],
                "unknowns": ["Whether another caller caches the value."],
            }
        },
    )
    edit_input = _artifact(
        runtime,
        {
            "input": {
                "files": [
                    {
                        "path": "src/public.py",
                        "replacements": [
                            {
                                "expected_text": 'def public():\n    return "old"\n',
                                "replacement_text": 'def public():\n    return "new"\n',
                            }
                        ],
                    }
                ]
            }
        },
    )
    check_input = _artifact(runtime, {"input": {"check_id": "public-lifecycle"}})
    check_output = _artifact(
        runtime,
        {
            "public_visible_only": True,
            "check_id": "public-lifecycle",
            "passed": False,
            "timed_out": False,
            "failure_summary": (
                "Traceback (most recent call last):\nAssertionError: PUBLIC_CASE:test-resumed"
            ),
        },
    )
    edit_output = _artifact(runtime, {"status": "applied"})
    plan_output = _artifact(runtime, {"status": "recorded"})
    events = [
        _event(
            1,
            EventType.MODEL_CALLED,
            {
                "request_artifact_path": str(request_path),
                "artifact_path": str(response_path),
                "input_tokens": 100,
                "output_tokens": 20,
            },
        ),
        _event(
            2,
            EventType.TOOL_CALLED,
            {"tool": "read_file", "input_artifact": {"path": str(read_input)}},
            correlation_id="read",
        ),
        _event(
            3,
            EventType.TOOL_SUCCEEDED,
            {"tool": "read_file", "result_artifact": {"path": str(read_output)}},
            correlation_id="read",
        ),
        _event(
            4,
            EventType.TOOL_CALLED,
            {"tool": "record_work_plan", "input_artifact": {"path": str(plan_input)}},
            correlation_id="plan",
        ),
        _event(
            5,
            EventType.TOOL_SUCCEEDED,
            {"tool": "record_work_plan", "result_artifact": {"path": str(plan_output)}},
            correlation_id="plan",
        ),
        _event(
            6,
            EventType.TOOL_CALLED,
            {"tool": "apply_structured_edit", "input_artifact": {"path": str(edit_input)}},
            correlation_id="edit",
        ),
        _event(
            7,
            EventType.TOOL_SUCCEEDED,
            {"tool": "apply_structured_edit", "result_artifact": {"path": str(edit_output)}},
            correlation_id="edit",
        ),
        _event(
            8,
            EventType.TOOL_CALLED,
            {"tool": "run_check", "input_artifact": {"path": str(check_input)}},
            correlation_id="check",
        ),
        _event(
            9,
            EventType.TOOL_SUCCEEDED,
            {
                "tool": "run_check",
                "check_id": "public-lifecycle",
                "passed": False,
                "timed_out": False,
                "result_artifact": {"path": str(check_output)},
            },
            correlation_id="check",
        ),
    ]
    manifest = _manifest()

    detail = build_run_detail_view(
        row=_row(manifest),
        manifest=manifest,
        events=events,
        runtime=runtime,
    )

    assert detail["task"]["visible_check_ids"] == ["public-lifecycle"]
    assert detail["task"]["forbidden_paths"] == ["tests/**"]
    assert detail["task"]["max_diff_lines"] == 20
    work_log = detail["work_log"]
    assert work_log["schema_version"] == "agent-work-log-v1"
    assert (work_log["read_count"], work_log["edit_attempts"], work_log["checks_failed"]) == (
        1,
        1,
        1,
    )
    actions = work_log["cycles"][0]["actions"]
    assert [action["summary"]["kind"] for action in actions] == [
        "read",
        "plan",
        "edit",
        "check",
    ]
    assert actions[0]["summary"]["title"] == "src/public.py"
    change = actions[2]["summary"]["changes"][0]
    assert (change["line_start"], change["line_end"], change["anchor"]) == (
        2,
        2,
        "def public():",
    )
    assert change["preview"] == [
        "@@ -1,2 +1,2 @@",
        " def public():",
        '-    return "old"',
        '+    return "new"',
    ]
    assert actions[3]["summary"]["detail"] == "AssertionError: PUBLIC_CASE:test-resumed"
    serialized = json.dumps(
        {"task": detail["task"], "work_log": detail["work_log"]},
        default=str,
    )
    assert "MUST NOT BE PROJECTED" not in serialized


def test_agent_work_log_hides_check_output_without_public_marker(tmp_path: Path) -> None:
    runtime = tmp_path / ".patchloop"
    check_input = _artifact(runtime, {"input": {"check_id": "visible"}})
    check_output = _artifact(
        runtime,
        {
            "passed": False,
            "failure_summary": "MUST NOT BE PROJECTED",
        },
    )
    events = [
        _event(
            1,
            EventType.TOOL_CALLED,
            {"tool": "run_check", "input_artifact": {"path": str(check_input)}},
            correlation_id="check",
        ),
        _event(
            2,
            EventType.TOOL_SUCCEEDED,
            {
                "tool": "run_check",
                "check_id": "visible",
                "passed": False,
                "result_artifact": {"path": str(check_output)},
            },
            correlation_id="check",
        ),
    ]
    manifest = _manifest()

    detail = build_run_detail_view(
        row=_row(manifest),
        manifest=manifest,
        events=events,
        runtime=runtime,
    )

    check = detail["work_log"]["cycles"][0]["actions"][0]["summary"]
    assert check["detail"] == "registered visible check did not pass"
    assert "MUST NOT BE PROJECTED" not in json.dumps(detail["work_log"], default=str)


def test_run_index_defaults_to_latest_rapid_experiment() -> None:
    rapid = _rapid_manifest()
    legacy = _manifest("run_legacy_trace_view")

    index = build_run_index_view([_row(rapid), _row(legacy)])

    assert index["default_experiment_id"] == "rapid-public-development-test"
    assert index["schema_version"] == "trace-index-v2"
    assert index["default_count"] == 1
    assert index["total_count"] == 2
    assert index["runs"][0]["purpose"] == "rapid-public-development"
    assert [run["default_visible"] for run in index["runs"]] == [True, False]


def test_in_progress_story_does_not_label_unreached_stages_as_failures(
    tmp_path: Path,
) -> None:
    manifest = _manifest()
    row = {
        "run_id": manifest.run_id,
        "status": "running",
        "created_at": manifest.created_at.isoformat(),
        "manifest": manifest.model_dump(mode="json"),
        "result": None,
    }

    detail = build_run_detail_view(
        row=row,
        manifest=manifest,
        events=[],
        runtime=tmp_path / ".patchloop",
    )

    assert detail["result"]["outcome"] is None
    assert detail["story"]["observations"] == []
    assert detail["story"]["failure_chain"] == []


def test_story_treats_failed_check_and_rejected_submission_as_tool_failures(
    tmp_path: Path,
) -> None:
    manifest = _manifest()
    events = [
        _event(
            1,
            EventType.MODEL_CALLED,
            {"input_tokens": 10, "output_tokens": 2},
        ),
        _event(
            2,
            EventType.TOOL_CALLED,
            {"tool": "run_check"},
            correlation_id="check_1",
        ),
        _event(
            3,
            EventType.TOOL_SUCCEEDED,
            {"tool": "run_check", "passed": False, "timed_out": False},
            correlation_id="check_1",
        ),
        _event(
            4,
            EventType.MODEL_CALLED,
            {"input_tokens": 10, "output_tokens": 2},
        ),
        _event(
            5,
            EventType.TOOL_CALLED,
            {"tool": "finish_task"},
            correlation_id="submit_1",
        ),
        _event(
            6,
            EventType.SUBMISSION_REJECTED,
            {"tool": "finish_task"},
            correlation_id="submit_1",
        ),
        _event(7, EventType.RUN_FAILED, {}),
    ]

    detail = build_run_detail_view(
        row=_row(manifest),
        manifest=manifest,
        events=events,
        runtime=tmp_path / ".patchloop",
    )

    stages = {stage["key"]: stage for stage in detail["story"]["workflow"]}
    assert (stages["verify"]["calls"], stages["verify"]["failed"]) == (1, 1)
    assert (stages["submit"]["calls"], stages["submit"]["failed"]) == (1, 1)
    error_codes = [
        tool["error_code"] for turn in detail["story"]["timeline"] for tool in turn["tools"]
    ]
    assert error_codes == [
        "CHECK_FAILED",
        "SUBMISSION_REJECTED",
    ]
    assert [item["kind"] for item in detail["story"]["failure_chain"]] == [
        "tool_failure",
        "tool_failure",
        "run_terminal",
    ]


def test_task_failure_story_names_failed_verdict_without_private_detail(
    tmp_path: Path,
) -> None:
    manifest = _manifest()
    row = _row(manifest)
    row["result"].update(
        {
            "outcome_kind": "task_failure",
            "agent_submission_status": "completed",
            "evaluation_status": "completed",
            "terminal_error": None,
            "verdicts": {
                "hidden_tests": "fail",
                "regression_tests": "pass",
                "scope_policy": "pass",
                "safety_policy": "pass",
            },
        }
    )

    detail = build_run_detail_view(
        row=row,
        manifest=manifest,
        events=[_event(1, EventType.RUN_COMPLETED, {})],
        runtime=tmp_path / ".patchloop",
    )

    terminal = detail["story"]["failure_chain"][-1]
    assert terminal["detail"] == "evaluator fail · hidden tests"
    assert "private_detail" not in json.dumps(detail["story"], default=str)


def test_read_only_store_preserves_sqlite_bytes_and_has_no_initializer(tmp_path: Path) -> None:
    path = tmp_path / "state.sqlite3"
    manifest = _manifest()
    event = _event(1, EventType.RUN_STARTED, {"task_id": manifest.task_id})
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE runs (
                run_id TEXT PRIMARY KEY,
                manifest_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                result_json TEXT
            );
            CREATE TABLE events (
                run_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                event_id TEXT NOT NULL UNIQUE,
                event_json TEXT NOT NULL,
                PRIMARY KEY (run_id, sequence)
            );
            """
        )
        connection.execute(
            "INSERT INTO runs VALUES (?, ?, ?, ?, ?)",
            (
                manifest.run_id,
                canonical_json(manifest.model_dump(mode="json")),
                "running",
                manifest.created_at.isoformat(),
                None,
            ),
        )
        connection.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?)",
            (
                event.run_id,
                event.sequence,
                event.event_id,
                canonical_json(event.model_dump(mode="json")),
            ),
        )
    before = (
        path.read_bytes(),
        path.stat().st_mtime_ns,
        sorted(item.name for item in tmp_path.iterdir()),
    )

    store = ReadOnlyTraceStore(path)
    assert store.has_run(manifest.run_id) is True
    assert store.get_manifest(manifest.run_id) == manifest
    assert store.list_events(manifest.run_id) == [event]
    assert build_run_list_view(store.list_runs())[0]["task_id"] == manifest.task_id

    after = (
        path.read_bytes(),
        path.stat().st_mtime_ns,
        sorted(item.name for item in tmp_path.iterdir()),
    )
    assert after == before


def test_read_only_store_rejects_live_sqlite_sidecar(tmp_path: Path) -> None:
    path = tmp_path / "state.sqlite3"
    path.write_bytes(b"not-opened")
    Path(str(path) + "-wal").write_bytes(b"active")

    with pytest.raises(RecoveryError, match="sidecars"):
        ReadOnlyTraceStore(path).list_runs()


def test_read_only_store_closes_wal_mode_connections_between_reads(tmp_path: Path) -> None:
    path = tmp_path / "state.sqlite3"
    connection = sqlite3.connect(path)
    try:
        assert connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        connection.execute(
            """
            CREATE TABLE runs (
                run_id TEXT PRIMARY KEY,
                manifest_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                result_json TEXT
            )
            """
        )
        connection.commit()
    finally:
        connection.close()

    store = ReadOnlyTraceStore(path)
    assert store.list_runs() == []
    assert store.list_runs() == []
    assert not any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-shm", "-journal"))
