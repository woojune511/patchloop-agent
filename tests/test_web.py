from __future__ import annotations

import asyncio
from types import SimpleNamespace

import httpx

from patchloop.contracts import EventType, RunEvent
from patchloop.util import utc_now
from patchloop.web import _build_trace_view, app


def _event(
    sequence: int,
    event_type: EventType,
    payload: dict | None = None,
) -> RunEvent:
    return RunEvent(
        event_id=f"event-{sequence}",
        run_id="run_viewer_test",
        sequence=sequence,
        type=event_type,
        timestamp=utc_now(),
        actor="test",
        payload=payload or {},
    )


def _trace_events() -> list[RunEvent]:
    return [
        _event(1, EventType.RUN_STARTED, {"task_id": "viewer-test"}),
        _event(
            2,
            EventType.CONTEXT_BUILT,
            {
                "context_characters": 1200,
                "omitted_event_count": 3,
                "truncated_tool_result_count": 0,
            },
        ),
        _event(
            3,
            EventType.MODEL_CALLED,
            {
                "prompt_telemetry_version": "prompt-token-integrity-v1",
                "requested_input_tokens": 100,
                "input_tokens": 100,
                "output_tokens": 20,
                "input_token_count_match": True,
                "response_status": "completed",
                "response_truncation": "disabled",
                "response_incomplete_reason": None,
                "request_artifact_id": "art_request",
                "request_body_hash": "sha256:" + ("a" * 64),
            },
        ),
        _event(4, EventType.TOOL_CALLED, {"tool": "run_check"}),
        _event(
            5,
            EventType.TOOL_SUCCEEDED,
            {
                "tool": "run_check",
                "check_id": "visible",
                "passed": True,
            },
        ),
        _event(
            6,
            EventType.RUN_FAILED,
            {"message": "invalid phase transition: VERIFY -> DONE"},
        ),
    ]


def test_health_route() -> None:
    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/healthz")

    response = asyncio.run(request())
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_trace_view_prioritizes_critical_path_and_collapses_turns() -> None:
    trace = _build_trace_view(_trace_events())

    assert trace["event_count"] == 6
    assert trace["model_turn_count"] == 1
    assert trace["telemetry"] == {
        "available": True,
        "turn_count": 1,
        "matched_turns": 1,
        "completed_turns": 1,
        "provider_truncations": 0,
        "request_artifacts": 1,
        "omitted_events_total": 3,
        "max_omitted_events": 3,
        "truncated_tool_results": 0,
    }
    assert [item["event"].sequence for item in trace["critical"]] == [1, 5, 6]
    assert trace["turns"][0]["tool_label"] == "run_check"
    assert trace["turns"][0]["tone"] == "bad"
    assert trace["turns"][0]["open"] is True


def test_run_route_renders_summary_before_collapsible_raw_trace(
    tmp_path,
    monkeypatch,
) -> None:
    result = {
        "scope_compliant_success": False,
        "official": False,
        "outcome_kind": "agent_failure",
        "evaluation_status": "not_run",
        "terminal_error": {
            "message": "invalid phase transition: VERIFY -> DONE",
        },
        "usage": {
            "model_calls": 1,
            "tool_calls": 1,
            "input_tokens": 100,
            "output_tokens": 20,
            "model_cost_usd": 0.01,
        },
    }
    manifest = SimpleNamespace(
        run_id="run_viewer_test",
        task_id="viewer-test",
        memory=SimpleNamespace(condition=SimpleNamespace(value="no_memory")),
        model=SimpleNamespace(
            model_id="gpt-test",
            reasoning_effort="medium",
        ),
    )

    class FakeState:
        @staticmethod
        def get_manifest(_run_id):
            return manifest

        @staticmethod
        def list_runs():
            return [
                {
                    "run_id": "run_viewer_test",
                    "status": "failed",
                    "result": result,
                }
            ]

        @staticmethod
        def list_events(_run_id):
            return _trace_events()

        @staticmethod
        def latest_checkpoint(_run_id):
            return None

        @staticmethod
        def list_checkpoints(_run_id):
            return []

        @staticmethod
        def has_run(_run_id):
            return True

    monkeypatch.setattr("patchloop.web._state", lambda: FakeState())
    monkeypatch.setattr("patchloop.web.runtime_root", lambda: tmp_path)

    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.get("/runs/run_viewer_test")

    response = asyncio.run(request())

    assert response.status_code == 200
    assert "Agent stopped before evaluation" in response.text
    assert "Prompt count" in response.text
    assert "Critical path" in response.text
    assert "Model turns" in response.text
    assert "All 6 raw events" in response.text
    assert response.text.index("Critical path") < response.text.index(
        "All 6 raw events"
    )
