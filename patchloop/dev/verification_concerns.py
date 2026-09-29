"""Bounded model-authored verification concerns, independent of source-note expiry."""

from __future__ import annotations

import copy
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from patchloop.dev.verification_observations import verification_observation


class _VerificationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    operation: Literal["upsert", "resolve", "dismiss"]
    concern_id: str | None = Field(pattern=r"^v[1-9][0-9]*$", max_length=30)
    statement: str | None = Field(max_length=400)
    evidence_action_id: str | None = Field(max_length=500)
    reason: str | None = Field(max_length=400)


_FEEDBACK = {
    "observation_already_bound": "Keep the original observation; create a distinct concern "
    "for a different observation.",
    "unobserved_verification_observation": "Link a completed unsuccessful public check/probe, "
    "or use null for a concern without an observed failure.",
    "invalid_verification_updates": "Use an array of at most three verification updates.",
    "invalid_verification_update": "This verification update does not match its public schema.",
    "unknown_concern_id": "Use an existing concern ID, or upsert with null to create one.",
    "statement_required": "Upsert requires a public concern or a progress note about its original.",
    "reason_required": "Resolve or dismiss requires a nonempty public reason.",
    "concern_capacity": "Three unresolved concerns are already retained; update or address one.",
    "unobserved_verification_result": (
        "Resolve must cite an already completed public check or probe."
    ),
    "verification_result_not_current": (
        "This result tested another diff; the concern remains unresolved."
    ),
    "verification_result_not_successful": (
        "Resolve requires a successful current-diff check or healthy probe."
    ),
}


def empty_verification_state() -> dict[str, Any]:
    return {"next_id": 1, "items": []}


def _effective_status(item: dict[str, Any], diff_hash: str) -> str:
    decision = item.get("decision")
    return (
        decision["outcome"]
        if decision is not None and decision["diff_hash"] == diff_hash
        else "unresolved"
    )


def project_verification_concerns(
    state: dict[str, Any], *, diff_hash: str,
) -> dict[str, Any]:
    """Evidence currency is checked; the model's interpretation is not certified."""

    items = copy.deepcopy(state["items"])
    for item in items:
        item.setdefault("progress_note", None)
        item["status"] = _effective_status(item, diff_hash)
        item["model_authored"] = True
        item["interpretation_status"] = "model_authored_unverified"
        if item.get("observation"):
            origin_hash = item["observation"]["diff_hash"]
            item["observation"]["currency"] = (
                "unknown" if origin_hash is None else
                "current" if origin_hash == diff_hash else "historical"
            )
        decision = item.get("decision")
        if decision is not None:
            currency = "current" if decision["diff_hash"] == diff_hash else "historical"
            decision["currency"] = currency
            decision["basis"] = (
                "model_dismissal" if decision["outcome"] == "dismissed"
                else "model_interpretation_of_result"
            )
            if decision["evidence"] is not None:
                decision["evidence"]["currency"] = currency
    return {
        "items": items,
        "unresolved_ids": [item["concern_id"] for item in items if item["status"] == "unresolved"],
        "interpretation": (
            "Model-authored public verification concerns survive focus-question changes and "
            "source-note expiry. Statement preserves the original concern; progress_note is "
            "its latest update, not a replacement question. Create a distinct concern with "
            "a null ID. Repeating the original statement or retained progress does not "
            "change the concern or reopen a decision. Resolution binds a prior successful "
            "result to this diff; "
            "it does not prove that the result addresses the concern. Dismissal records "
            "the model's reason, not verification. Both decisions become historical and "
            "the concern becomes unresolved when the diff changes. These are advisory, "
            "not additional required checks or a finish gate."
        ),
    }


def _resolution_evidence(
    action_id: str | None, prior_results: dict[str, Any], diff_hash: str,
) -> tuple[dict[str, Any] | None, str | None]:
    result = prior_results.get(action_id) if action_id else None
    if (
        not isinstance(result, dict) or result.get("action_id") != action_id
        or result.get("tool") not in {"run_check", "run_probe"}
        or not isinstance(result.get("input_hash"), str) or not result["input_hash"]
    ):
        return None, "unobserved_verification_result"
    output = result.get("output")
    if not isinstance(output, dict):
        return None, "verification_result_not_successful"
    if (
        output.get("diff_hash") != diff_hash
        or result.get("workspace_diff_hash") != diff_hash
    ):
        return None, "verification_result_not_current"
    healthy = not any(output.get(flag, False) for flag in (
        "timed_out", "deadline_exhausted", "cleanup_failed",
    ))
    if result["tool"] == "run_check":
        passed = output.get("passed") is True
    else:
        passed = (
            output.get("status") == "passed" and type(output.get("exit_code")) is int
            and output["exit_code"] == 0 and not output.get("truncated", False)
        )
    if result.get("status") != "succeeded" or not healthy or not passed:
        return None, "verification_result_not_successful"
    return {
        "action_id": action_id, "input_hash": result["input_hash"],
        "tool": result["tool"], "diff_hash": diff_hash,
        **({"check_id": output["check_id"]}
           if result["tool"] == "run_check" and isinstance(output.get("check_id"), str)
           else {}),
    }, None


def update_verification_concerns(
    state: dict[str, Any], updates: Any, *, diff_hash: str,
    prior_results: dict[str, Any], turn_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply independent annotations; never raise for invalid model updates."""

    updated = copy.deepcopy(state)
    receipt: dict[str, Any] = {
        "status": "not_requested", "updates": [], "diagnostics": [],
        "evicted_concern_ids": [], "available_concern_ids": [], "unresolved_ids": [],
    }

    def finish() -> tuple[dict[str, Any], dict[str, Any]]:
        receipt["available_concern_ids"] = [item["concern_id"] for item in updated["items"]]
        receipt["unresolved_ids"] = project_verification_concerns(
            updated, diff_hash=diff_hash,
        )["unresolved_ids"]
        return updated, receipt

    if not isinstance(updates, list) or len(updates) > 3:
        receipt["status"] = "rejected"
        receipt["diagnostics"].append({
            "code": "invalid_verification_updates",
            "message": _FEEDBACK["invalid_verification_updates"],
        })
        return finish()
    for index, raw in enumerate(updates):
        entry: dict[str, Any] = {"update_index": index, "status": "rejected"}
        receipt["updates"].append(entry)

        def reject(code: str, target: dict[str, Any] = entry) -> None:
            target.update(code=code, message=_FEEDBACK[code])

        try:
            update = _VerificationUpdate.model_validate(raw)
        except ValidationError:
            reject("invalid_verification_update")
            continue
        if update.concern_id is not None:
            entry["concern_id"] = update.concern_id
        existing = next((
            item for item in updated["items"] if item["concern_id"] == update.concern_id
        ), None)
        if existing is None and (update.concern_id is not None or update.operation != "upsert"):
            reject("unknown_concern_id")
            continue
        if update.operation == "upsert":
            if not update.statement or not update.statement.strip():
                reject("statement_required")
                continue
            observation = None
            created = existing is None
            if update.evidence_action_id is not None:
                result = prior_results.get(update.evidence_action_id)
                if (isinstance(result, dict)
                        and result.get("action_id") == update.evidence_action_id):
                    observation = verification_observation(result)
                if observation is None:
                    reject("unobserved_verification_observation")
                    continue
                if existing and existing.get("observation") not in (None, observation):
                    reject("observation_already_bound")
                    continue
            if existing is None:
                if len(updated["items"]) >= 3:
                    evictable = next((
                        item for item in updated["items"]
                        if _effective_status(item, diff_hash) != "unresolved"
                    ), None)
                    if evictable is None:
                        reject("concern_capacity")
                        continue
                    updated["items"].remove(evictable)
                    receipt["evicted_concern_ids"].append(evictable["concern_id"])
                existing = {
                    "concern_id": f"v{updated['next_id']}", "created_turn_id": turn_id,
                    "statement": update.statement, "progress_note": None,
                }
                updated["next_id"] += 1
                updated["items"].append(existing)
                entry["concern_id"] = existing["concern_id"]
            new_link = observation is not None and existing.get("observation") is None
            if not created and update.statement in (
                existing["statement"], existing.get("progress_note"),
            ) and not new_link:
                entry.update(
                    status="applied", code="unchanged",
                    message=(
                        "Original concern or retained progress repeated; state and decision "
                        "are unchanged. Use [] when there is no new progress."
                    ),
                )
                continue
            elif not created and update.statement != existing["statement"]:
                existing["progress_note"] = update.statement
            if observation is not None:
                existing["observation"] = observation
            existing.update(updated_turn_id=turn_id, decision=None)
        else:
            if not update.reason or not update.reason.strip():
                reject("reason_required")
                continue
            evidence = None
            if update.operation == "resolve":
                evidence, code = _resolution_evidence(
                    update.evidence_action_id, prior_results, diff_hash,
                )
                if code is not None:
                    reject(code)
                    continue
            existing.update(updated_turn_id=turn_id, decision={
                "outcome": "resolved" if update.operation == "resolve" else "dismissed",
                "diff_hash": diff_hash, "reason": update.reason,
                "evidence": evidence, "turn_id": turn_id,
            })
        entry.update(status="applied", code=None, message="Verification concern update stored.")
    if updates:
        accepted = sum(entry["status"] == "applied" for entry in receipt["updates"])
        receipt["status"] = (
            "applied" if accepted == len(updates)
            else "partially_applied" if accepted else "rejected"
        )
    return finish()


def verification_updates_schema() -> dict[str, Any]:
    return {
        "type": "array", "maxItems": 3,
        "description": (
            "Optional public uncertainties; [] preserves. Upsert with null ID creates; "
            "an existing ID only updates progress and reopens for changed progress. "
            "Exact repeats do nothing. Resolve requires a prior successful current-diff "
            "check/probe plus reason; dismiss requires a reason. Neither proves semantic coverage."
        ),
        "items": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["upsert", "resolve", "dismiss"]},
                "concern_id": {
                    "type": ["string", "null"], "pattern": r"^v[1-9][0-9]*$", "maxLength": 30,
                },
                "statement": {
                    "type": ["string", "null"], "maxLength": 400,
                    "description": (
                        "Upsert: original public uncertainty for a null ID; otherwise latest "
                        "progress about its immutable original, not a replacement question."
                    ),
                },
                "evidence_action_id": {
                    "type": ["string", "null"], "maxLength": 500,
                    "description": "Upsert: failed check/probe ID.",
                },
                "reason": {
                    "type": ["string", "null"], "maxLength": 400,
                    "description": "Brief public resolution/dismissal basis, not raw reasoning.",
                },
            },
            "required": ["operation", "concern_id", "statement", "evidence_action_id", "reason"],
            "additionalProperties": False,
        },
    }
