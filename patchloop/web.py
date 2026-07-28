"""Read-only FastAPI/Jinja trace viewer."""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from patchloop.contracts import EventType, RunEvent
from patchloop.errors import ContractError
from patchloop.evals.qualification import load_trace_qualification
from patchloop.runtime import repository_root, runtime_root
from patchloop.state import StateStore

app = FastAPI(title="PatchLoop Trace Viewer", docs_url=None, redoc_url=None)
web_root = repository_root() / "patchloop" / "web_assets"
templates = Jinja2Templates(directory=web_root / "templates")
app.mount("/static", StaticFiles(directory=web_root / "static"), name="static")


def _state() -> StateStore:
    return StateStore(runtime_root() / "state.sqlite3")


def _event_summary(event: RunEvent) -> str:
    payload = event.payload
    if event.type == EventType.RUN_STARTED:
        return f"Run started for {payload.get('task_id', 'task')}"
    if event.type == EventType.PHASE_CHANGED:
        return f"{payload.get('from', '?')} → {payload.get('to', '?')}"
    if event.type == EventType.CONTEXT_BUILT:
        omitted = int(payload.get("omitted_event_count", 0) or 0)
        truncated = int(payload.get("truncated_tool_result_count", 0) or 0)
        return (
            f"{payload.get('context_characters', 0):,} chars · "
            f"{omitted} older events omitted · {truncated} tool results truncated"
        )
    if event.type == EventType.MODEL_CALLED:
        input_tokens = int(payload.get("input_tokens", 0) or 0)
        output_tokens = int(payload.get("output_tokens", 0) or 0)
        matched = payload.get("input_token_count_match")
        count_label = (
            "input count matched"
            if matched is True
            else "input count mismatch"
            if matched is False
            else "input count unavailable"
        )
        return (
            f"{input_tokens:,} input / {output_tokens:,} output · "
            f"{count_label}"
        )
    if event.type == EventType.TOOL_CALLED:
        return f"{payload.get('tool', 'tool')} requested"
    if event.type in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}:
        tool = payload.get("tool", "tool")
        check = payload.get("check_id")
        suffix = f" · {check}" if check else ""
        if payload.get("passed") is not None:
            suffix += f" · passed={str(payload['passed']).lower()}"
        return f"{tool} {event.type.value.removeprefix('Tool').lower()}{suffix}"
    if event.type == EventType.PATCH_APPLIED:
        return f"Patch applied · {payload.get('patch_hash', 'hash unavailable')}"
    if event.type == EventType.CHECKPOINT_SAVED:
        return f"Checkpoint through sequence {payload.get('through_sequence', '?')}"
    if event.type == EventType.RUN_COMPLETED:
        return (
            "Evaluator completed · "
            f"scope-compliant success={payload.get('scope_compliant_success')}"
        )
    if event.type == EventType.RUN_FAILED:
        return payload.get("message", "Run failed")
    return event.type.value


def _event_tone(event: RunEvent) -> str:
    if event.type in {EventType.RUN_FAILED, EventType.TOOL_FAILED}:
        return "bad"
    if event.type in {
        EventType.RUN_COMPLETED,
        EventType.PATCH_APPLIED,
        EventType.TOOL_SUCCEEDED,
    }:
        return "good"
    if event.type == EventType.PHASE_CHANGED:
        return "accent"
    return "neutral"


def _event_view(event: RunEvent) -> dict[str, Any]:
    return {
        "event": event,
        "summary": _event_summary(event),
        "tone": _event_tone(event),
    }


def _turn_view(number: int, events: list[RunEvent]) -> dict[str, Any]:
    model_event = next(
        (event for event in events if event.type == EventType.MODEL_CALLED),
        None,
    )
    tool_events = [
        event for event in events if event.type == EventType.TOOL_CALLED
    ]
    tool_names = [str(event.payload.get("tool", "tool")) for event in tool_events]
    failed = any(
        event.type in {EventType.TOOL_FAILED, EventType.RUN_FAILED}
        for event in events
    )
    completed = any(event.type == EventType.RUN_COMPLETED for event in events)
    if model_event is None:
        token_label = "no model response"
        prompt_match = None
    else:
        token_label = (
            f"{int(model_event.payload.get('input_tokens', 0) or 0):,} in / "
            f"{int(model_event.payload.get('output_tokens', 0) or 0):,} out"
        )
        prompt_match = model_event.payload.get("input_token_count_match")
    return {
        "number": number,
        "events": [_event_view(event) for event in events],
        "tools": tool_names,
        "tool_label": ", ".join(tool_names) if tool_names else "no tool",
        "token_label": token_label,
        "prompt_match": prompt_match,
        "tone": "bad" if failed else "good" if completed else "neutral",
        "open": failed or completed,
    }


def _build_trace_view(events: list[RunEvent]) -> dict[str, Any]:
    model_events = [
        event for event in events if event.type == EventType.MODEL_CALLED
    ]
    context_events = [
        event for event in events if event.type == EventType.CONTEXT_BUILT
    ]
    telemetry_events = [
        event
        for event in model_events
        if event.payload.get("prompt_telemetry_version")
    ]
    matched_turns = sum(
        event.payload.get("input_token_count_match") is True
        and event.payload.get("requested_input_tokens")
        == event.payload.get("input_tokens")
        for event in telemetry_events
    )
    completed_turns = sum(
        event.payload.get("response_status") == "completed"
        and event.payload.get("response_incomplete_reason") is None
        for event in telemetry_events
    )
    provider_truncations = sum(
        event.payload.get("response_truncation") not in {None, "disabled"}
        for event in telemetry_events
    )
    request_artifacts = sum(
        bool(
            event.payload.get("request_artifact_id")
            and event.payload.get("request_body_hash")
        )
        for event in telemetry_events
    )

    turns: list[dict[str, Any]] = []
    prelude: list[RunEvent] = []
    current_turn: list[RunEvent] | None = None
    for event in events:
        if event.type == EventType.CONTEXT_BUILT:
            if current_turn:
                turns.append(_turn_view(len(turns) + 1, current_turn))
            current_turn = [event]
        elif current_turn is None:
            prelude.append(event)
        else:
            current_turn.append(event)
    if current_turn:
        turns.append(_turn_view(len(turns) + 1, current_turn))

    critical_types = {
        EventType.RUN_STARTED,
        EventType.PHASE_CHANGED,
        EventType.TOOL_FAILED,
        EventType.PATCH_APPLIED,
        EventType.RUN_COMPLETED,
        EventType.RUN_FAILED,
    }
    critical = [
        _event_view(event)
        for event in events
        if event.type in critical_types
        or (
            event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool") in {"run_check", "get_diff"}
        )
    ]
    return {
        "event_count": len(events),
        "model_turn_count": len(model_events),
        "turns": turns,
        "prelude": [_event_view(event) for event in prelude],
        "critical": critical,
        "raw_events": [_event_view(event) for event in events],
        "telemetry": {
            "available": bool(telemetry_events),
            "turn_count": len(telemetry_events),
            "matched_turns": matched_turns,
            "completed_turns": completed_turns,
            "provider_truncations": provider_truncations,
            "request_artifacts": request_artifacts,
            "omitted_events_total": sum(
                int(event.payload.get("omitted_event_count", 0) or 0)
                for event in context_events
            ),
            "max_omitted_events": max(
                (
                    int(event.payload.get("omitted_event_count", 0) or 0)
                    for event in context_events
                ),
                default=0,
            ),
            "truncated_tool_results": sum(
                int(event.payload.get("truncated_tool_result_count", 0) or 0)
                for event in context_events
            ),
        },
    }


def _outcome_view(result: dict[str, Any] | None) -> dict[str, str]:
    if result is None:
        return {
            "tone": "neutral",
            "label": "Run pending",
            "description": "No terminal result has been recorded.",
        }
    outcome = result.get("outcome_kind", "unknown")
    labels = {
        "resolved": ("good", "Resolved"),
        "task_failure": ("bad", "Patch failed evaluation"),
        "agent_failure": ("bad", "Agent stopped before evaluation"),
        "infrastructure_error": ("bad", "Infrastructure error"),
    }
    tone, label = labels.get(
        outcome,
        ("neutral", outcome.replace("_", " ").title()),
    )
    terminal = result.get("terminal_error") or {}
    description = terminal.get("message")
    if not description:
        description = (
            f"Evaluation status: {result.get('evaluation_status', 'unknown')} · "
            f"official={str(result.get('official', False)).lower()}"
        )
    return {"tone": tone, "label": label, "description": description}


@app.get("/healthz")
def health() -> dict:
    return {"ok": True}


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"runs": _state().list_runs()},
    )


@app.get("/runs/{run_id}")
def run_detail(request: Request, run_id: str):
    state = _state()
    try:
        manifest = state.get_manifest(run_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
    row = next(item for item in state.list_runs() if item["run_id"] == run_id)
    events = state.list_events(run_id)
    checkpoint = state.latest_checkpoint(run_id)
    patch_path = runtime_root() / "runs" / run_id / "submitted.patch"
    try:
        qualification = load_trace_qualification(run_id, root=runtime_root())
    except ContractError:
        qualification = None
    return templates.TemplateResponse(
        request=request,
        name="run.html",
        context={
            "row": row,
            "manifest": manifest,
            "events": events,
            "checkpoint": checkpoint,
            "checkpoints": state.list_checkpoints(run_id),
            "patch_available": patch_path.exists(),
            "patch_text": (patch_path.read_text(encoding="utf-8") if patch_path.exists() else ""),
            "result_json": json.dumps(row["result"], indent=2, ensure_ascii=False),
            "outcome": _outcome_view(row["result"]),
            "qualification": qualification,
            "trace": _build_trace_view(events),
        },
    )


@app.get("/runs/{run_id}/patch")
def run_patch(run_id: str):
    path = runtime_root() / "runs" / run_id / "submitted.patch"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="patch not found")
    return FileResponse(path, media_type="text/x-diff", filename=f"{run_id}.patch")


@app.get("/runs/{run_id}/events")
def run_events(request: Request, run_id: str):
    state = _state()
    if not state.has_run(run_id):
        raise HTTPException(status_code=404, detail="run not found")
    return templates.TemplateResponse(
        request=request,
        name="events.html",
        context={"trace": _build_trace_view(state.list_events(run_id))},
    )


@app.get("/experiments")
def experiments(request: Request):
    records = []
    for path in sorted((runtime_root() / "experiments").glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        records.append(
            {
                "experiment_id": raw["experiment_id"],
                "completed_runs": raw["completed_runs"],
                "expected_runs": raw["expected_runs"],
                "infrastructure_errors": raw["infrastructure_errors"],
            }
        )
    return templates.TemplateResponse(
        request=request,
        name="experiments.html",
        context={"experiments": records},
    )


@app.get("/experiments/{experiment_id}")
def experiment_detail(request: Request, experiment_id: str):
    path = runtime_root() / "experiments" / f"{experiment_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="experiment not found")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return templates.TemplateResponse(
        request=request,
        name="experiment.html",
        context={"experiment": raw},
    )
