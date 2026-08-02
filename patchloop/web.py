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
        if tool == "run_check" and payload.get("passed") is not None:
            check_state = "passed" if payload["passed"] is True else "failed"
            if payload.get("timed_out") is True:
                check_state = "timed out"
            return f"run_check {check_state}{suffix}"
        if tool == "run_probe":
            probe_state = (
                "timed out"
                if payload.get("timed_out") is True
                else "passed"
                if payload.get("passed") is True
                else "failed"
            )
            profile = payload.get("probe_id")
            profile_label = f" · {profile}" if profile else ""
            return (
                f"temporary probe {probe_state}{profile_label} · "
                "dedicated clean image · non-authoritative"
            )
        if tool == "review_task":
            if event.type == EventType.TOOL_SUCCEEDED:
                if payload.get("review_schema_version") == "task-review-v3":
                    total = payload.get("coverage_target_count")
                    verified = payload.get("verified_coverage_target_ids")
                    verified_count = (
                        len(verified) if isinstance(verified, list) else 0
                    )
                    coverage_state = (
                        "complete"
                        if payload.get("coverage_complete") is True
                        else "incomplete"
                    )
                    target_counts = (
                        f" · {verified_count}/{total} targets verified"
                        if type(total) is int
                        else ""
                    )
                    return (
                        f"public coverage review {coverage_state}"
                        f"{target_counts}"
                    )
                requirements = payload.get("requirement_count")
                validations = payload.get("targeted_validation_count")
                risks = payload.get("residual_risk_count")
                counts = (
                    f" · {requirements} requirements / "
                    f"{validations} validations / {risks} residual risks"
                    if all(
                        isinstance(value, int)
                        for value in (
                            requirements,
                            validations,
                            risks,
                        )
                    )
                    else ""
                )
                return (
                    "structured public-evidence review recorded"
                    f"{counts}"
                )
            return "structured review rejected"
        if payload.get("passed") is not None:
            suffix += f" · passed={str(payload['passed']).lower()}"
        return f"{tool} {event.type.value.removeprefix('Tool').lower()}{suffix}"
    if event.type == EventType.PATCH_APPLIED:
        return f"Patch applied · {payload.get('patch_hash', 'hash unavailable')}"
    if event.type == EventType.REVIEW_RECORDED:
        if payload.get("self_attestation") is True:
            return (
                "Structured self-review and final diff were bound to "
                f"submission · review event "
                f"{payload.get('source_task_review_sequence', '?')}"
            )
        return (
            "Complete final diff was presented and review was recorded · "
            f"source event {payload.get('source_get_diff_sequence', '?')}"
        )
    if event.type == EventType.SUBMISSION_ATTEMPTED:
        return (
            f"Submission attempt {payload.get('attempt_number', '?')} · "
            f"{payload.get('submission_method', 'unknown method')}"
        )
    if event.type == EventType.SUBMISSION_REJECTED:
        return (
            "Submission returned to the agent · "
            f"{payload.get('reason_code', 'precondition missing')}"
        )
    if event.type == EventType.SUBMISSION_ACCEPTED:
        return "Submission accepted for deterministic evaluation"
    if event.type == EventType.LOOP_DETECTED:
        return (
            f"Repeated {payload.get('tool', 'tool')} call detected · "
            f"occurrence {payload.get('occurrences', '?')} · advisory"
        )
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
    partial_coverage_review = (
        event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "review_task"
        and event.payload.get("review_schema_version") == "task-review-v3"
        and event.payload.get("coverage_complete") is not True
    )
    if partial_coverage_review:
        return "accent"
    failed_check = (
        event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "run_check"
        and (
            event.payload.get("passed") is False
            or event.payload.get("timed_out") is True
        )
    )
    if failed_check:
        return "bad"
    if event.type in {
        EventType.RUN_FAILED,
        EventType.TOOL_FAILED,
        EventType.SUBMISSION_REJECTED,
    }:
        return "bad"
    if event.type in {
        EventType.RUN_COMPLETED,
        EventType.PATCH_APPLIED,
        EventType.TOOL_SUCCEEDED,
        EventType.REVIEW_RECORDED,
        EventType.SUBMISSION_ACCEPTED,
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
        or (
            event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool") == "run_check"
            and (
                event.payload.get("passed") is False
                or event.payload.get("timed_out") is True
            )
        )
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


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _coverage_target_metadata(
    public_review_contract: Any | None,
) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    requirements = _field(public_review_contract, "requirements", []) or []
    for requirement in requirements:
        requirement_id = _field(requirement, "requirement_id", "unknown")
        for target in _field(requirement, "coverage_targets", []) or []:
            target_id = _field(target, "coverage_target_id")
            if not isinstance(target_id, str):
                continue
            evidence_kind = _field(target, "evidence_kind", "unknown")
            path = _field(target, "path")
            anchor = _field(target, "anchor")
            check_ids = list(_field(target, "check_ids", []) or [])
            if evidence_kind == "current_diff_inspection":
                evidence_label = f"read {path} · anchor {anchor}"
            elif evidence_kind == "passing_validation":
                evidence_label = (
                    "passing visible check · " + ", ".join(check_ids)
                )
            else:
                evidence_label = str(evidence_kind)
            targets.append(
                {
                    "coverage_target_id": target_id,
                    "requirement_id": requirement_id,
                    "description": _field(
                        target,
                        "description",
                        "Declared public coverage target",
                    ),
                    "evidence_kind": evidence_kind,
                    "evidence_label": evidence_label,
                }
            )
    return targets


def _coverage_review_view(
    events: list[RunEvent],
    *,
    tool_schema_version: str | None,
    public_review_contract: Any | None,
) -> dict[str, Any]:
    declared_targets = _coverage_target_metadata(public_review_contract)
    metadata_by_id = {
        item["coverage_target_id"]: item for item in declared_targets
    }
    reviews: list[dict[str, Any]] = []
    for event in events:
        if not (
            event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool") == "review_task"
            and event.payload.get("review_schema_version") == "task-review-v3"
        ):
            continue
        review_document = event.payload.get("review")
        if not isinstance(review_document, dict):
            review_document = {}
        coverage = event.payload.get("public_review_coverage")
        if not isinstance(coverage, dict):
            nested_coverage = review_document.get("public_review_coverage")
            coverage = nested_coverage if isinstance(nested_coverage, dict) else {}
        raw_rows = review_document.get("coverage_targets")
        rows: list[dict[str, Any]] = []
        if isinstance(raw_rows, list):
            for raw_row in raw_rows:
                if not isinstance(raw_row, dict):
                    continue
                target_id = raw_row.get("coverage_target_id")
                if not isinstance(target_id, str):
                    continue
                metadata = metadata_by_id.get(target_id, {})
                sequences = raw_row.get("evidence_event_sequences")
                if not isinstance(sequences, list):
                    sequences = []
                status = str(raw_row.get("status", "unknown"))
                rows.append(
                    {
                        "coverage_target_id": target_id,
                        "requirement_id": raw_row.get(
                            "requirement_id",
                            metadata.get("requirement_id", "unknown"),
                        ),
                        "description": metadata.get(
                            "description",
                            "Declared public coverage target",
                        ),
                        "evidence_label": metadata.get(
                            "evidence_label",
                            "public evidence",
                        ),
                        "status": status,
                        "tone": (
                            "completed"
                            if status == "verified"
                            else "failed"
                            if status == "unverified"
                            else "neutral"
                        ),
                        "evidence_event_sequences": sequences,
                        "evidence_sequences_label": (
                            ", ".join(str(sequence) for sequence in sequences)
                            if sequences
                            else "none"
                        ),
                        "notes": raw_row.get("notes", ""),
                    }
                )
        authoritative_ids = coverage.get(
            "authoritative_coverage_target_ids",
            [item["coverage_target_id"] for item in declared_targets],
        )
        verified_ids = coverage.get(
            "verified_coverage_target_ids",
            event.payload.get("verified_coverage_target_ids", []),
        )
        unresolved_ids = coverage.get(
            "unresolved_coverage_target_ids",
            event.payload.get("unresolved_coverage_target_ids", []),
        )
        total = (
            len(authoritative_ids)
            if isinstance(authoritative_ids, list)
            else event.payload.get("coverage_target_count", len(rows))
        )
        verified_count = len(verified_ids) if isinstance(verified_ids, list) else 0
        complete = coverage.get("coverage_complete") is True
        if not coverage:
            complete = event.payload.get("coverage_complete") is True
        reviews.append(
            {
                "sequence": event.sequence,
                "schema_version": event.payload.get("review_schema_version"),
                "worktree_diff_hash": event.payload.get(
                    "worktree_diff_hash",
                    review_document.get("worktree_diff_hash", "unknown"),
                ),
                "coverage_complete": complete,
                "tone": "completed" if complete else "failed",
                "status_label": (
                    f"{verified_count}/{total} targets verified"
                ),
                "verified_count": verified_count,
                "target_count": total,
                "unresolved_coverage_target_ids": (
                    unresolved_ids if isinstance(unresolved_ids, list) else []
                ),
                "rows": rows,
            }
        )
    return {
        "supported": tool_schema_version in {"v5", "v6"},
        "recorded": bool(reviews),
        "declared_targets": declared_targets,
        "declared_target_count": len(declared_targets),
        "reviews": reviews,
        "latest": reviews[-1] if reviews else None,
    }


def _build_trace_view(
    events: list[RunEvent],
    *,
    tool_schema_version: str | None = None,
    public_review_contract: Any | None = None,
) -> dict[str, Any]:
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
        EventType.REVIEW_RECORDED,
        EventType.SUBMISSION_ATTEMPTED,
        EventType.SUBMISSION_REJECTED,
        EventType.SUBMISSION_ACCEPTED,
        EventType.LOOP_DETECTED,
        EventType.FAILURE_TAGGED,
        EventType.RUN_COMPLETED,
        EventType.RUN_FAILED,
    }
    critical = [
        _event_view(event)
        for event in events
        if event.type in critical_types
        or (
            event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool")
            in {"run_check", "get_diff", "run_probe", "review_task"}
        )
    ]
    review_events = [
        event for event in events if event.type == EventType.REVIEW_RECORDED
    ]
    accepted_events = [
        event for event in events if event.type == EventType.SUBMISSION_ACCEPTED
    ]
    rejected_events = [
        event for event in events if event.type == EventType.SUBMISSION_REJECTED
    ]
    attempted_events = [
        event for event in events if event.type == EventType.SUBMISSION_ATTEMPTED
    ]
    coverage_review = _coverage_review_view(
        events,
        tool_schema_version=tool_schema_version,
        public_review_contract=public_review_contract,
    )
    if accepted_events:
        submission = {
            "tone": "completed",
            "label": "submission accepted for evaluator",
        }
    elif rejected_events:
        submission = {
            "tone": "failed",
            "label": f"{len(rejected_events)} submission attempt(s) rejected",
        }
    elif attempted_events:
        submission = {
            "tone": "failed",
            "label": (
                f"{len(attempted_events)} submission attempt(s) have no "
                "recorded outcome"
            ),
        }
    elif tool_schema_version in {"v2", "v3", "v4", "v5", "v6"}:
        submission = {
            "tone": "neutral",
            "label": "submission not attempted",
        }
    else:
        submission = {
            "tone": "neutral",
            "label": "legacy lifecycle telemetry unavailable",
        }
    lifecycle_available = bool(
        review_events or accepted_events or rejected_events
        or attempted_events
    )
    if tool_schema_version in {"v5", "v6"}:
        latest_coverage = coverage_review["latest"]
        if review_events and latest_coverage is not None:
            review = {
                "tone": "completed",
                "label": "public coverage review bound to final diff",
            }
        elif latest_coverage is not None:
            review = {
                "tone": (
                    "completed"
                    if latest_coverage["coverage_complete"]
                    else "failed"
                ),
                "label": (
                    "public coverage review complete; submission not yet bound"
                    if latest_coverage["coverage_complete"]
                    else "public coverage review incomplete · "
                    + latest_coverage["status_label"]
                ),
            }
        else:
            review = {
                "tone": "neutral",
                "label": "public coverage review not recorded",
            }
    else:
        review = {
            "tone": "completed" if review_events else "neutral",
            "label": (
                "structured self-review bound to final diff"
                if (
                    review_events
                    and review_events[-1].payload.get(
                        "self_attestation"
                    )
                    is True
                )
                else "final diff review recorded"
                if review_events
                else "final diff review not recorded"
                if lifecycle_available
                else "final diff review not reached"
                if tool_schema_version in {"v2", "v3", "v4"}
                else "legacy review telemetry unavailable"
            ),
        }
    return {
        "event_count": len(events),
        "model_turn_count": len(model_events),
        "turns": turns,
        "prelude": [_event_view(event) for event in prelude],
        "critical": critical,
        "raw_events": [_event_view(event) for event in events],
        "lifecycle": {
            "review": review,
            "submission": submission,
            "rejected_count": len(rejected_events),
            "probe_count": sum(
                event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("tool") == "run_probe"
                for event in events
            ),
        },
        "coverage_review": coverage_review,
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


def _checkpoint_action_label(checkpoint: Any) -> str:
    if checkpoint is None:
        return "unavailable"
    if checkpoint.phase.value == "DONE":
        return "submission complete"
    if checkpoint.current_plan:
        return ", ".join(checkpoint.current_plan)
    return "recomputed in the next model context"


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
            "checkpoint_action_label": _checkpoint_action_label(checkpoint),
            "checkpoints": state.list_checkpoints(run_id),
            "patch_available": patch_path.exists(),
            "patch_text": (patch_path.read_text(encoding="utf-8") if patch_path.exists() else ""),
            "result_json": json.dumps(row["result"], indent=2, ensure_ascii=False),
            "outcome": _outcome_view(row["result"]),
            "qualification": qualification,
            "trace": _build_trace_view(
                events,
                tool_schema_version=manifest.tool_schema_version,
                public_review_contract=getattr(
                    manifest,
                    "public_review_contract",
                    None,
                ),
            ),
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
    manifest = state.get_manifest(run_id)
    return templates.TemplateResponse(
        request=request,
        name="events.html",
        context={
            "trace": _build_trace_view(
                state.list_events(run_id),
                tool_schema_version=manifest.tool_schema_version,
                public_review_contract=getattr(
                    manifest,
                    "public_review_contract",
                    None,
                ),
            )
        },
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
