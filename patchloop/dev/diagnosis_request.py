"""Host construction of a pending original-call diagnosis, without target execution."""

from __future__ import annotations

from patchloop.dev import repair_path
from patchloop.errors import ContractError
from patchloop.sandbox import call_path_trace

POLICY = "host-call-path-request-v1"
NULL_FIELDS = ("question", "python_source", "replay_action_id", "purpose")


def tool_schema():
    """Expose only selections the model can change at the pending diagnosis gate."""
    return {
        "type": "function", "name": "run_probe", "strict": True,
        "description": (
            "Diagnose the pending original-call failure on the current candidate. "
            "Select call_path focus (a public caller enclosing the suspected path) and "
            "1-4 watched public functions with up to six named scalar fields each. "
            "At least one watch must cover an unobserved changed range reported in repair_path. "
            "Set question, python_source, replay_action_id and purpose to null. "
            "The host binds the pending original root and failing call, reuses the frozen "
            "program, inputs and expected result, and selects up to 32 executable lines "
            "per function with changed lines first. Do not supply call IDs or line numbers. "
            "Returned evidence includes bounded inputs, returns, exceptions and line entries. "
            "Function entry does not prove changed-branch execution; unknown is not no-hit. "
            "Diagnosis gives no repair or required-check credit."
        ),
        "parameters": {
            "type": "object",
            "properties": {**{key: {"type": "null"} for key in NULL_FIELDS},
                           "call_path": call_path_trace.selection_schema()},
            "required": [*NULL_FIELDS, "call_path"],
            "additionalProperties": False,
        },
    }


def symbolic(request):
    return isinstance(request, dict) and "call_id" not in request


def prepare(arguments, state, workspace, source_preflight, *, deadline=None):
    """Freeze only public choices and current host identities before action_started."""
    if state.get("status") != "needs_path_diagnosis":
        raise ContractError("symbolic call_path requires a pending original-call diagnosis")
    invalid_fields = [
        {"path": f"/{key}", "requirement": "must be null for pending original-call diagnosis"}
        for key in (*NULL_FIELDS, "reproduction", "case_id", "reference_action_id")
        if arguments.get(key) is not None
    ]
    if arguments.get("save_program"):
        invalid_fields.append({"path": "/save_program",
                               "requirement": "must be false for pending original-call diagnosis"})
    if invalid_fields:
        raise ContractError(
            "invalid pending-diagnosis fields: "
            + ", ".join(item["path"] for item in invalid_fields),
            details={"invalid_fields": invalid_fields},
        )
    if not callable(source_preflight):
        raise ContractError("call-path source construction is unavailable")
    request = call_path_trace.selection_request(arguments["call_path"], state["call_id"])
    bound = source_preflight(workspace, request, deadline=deadline,
                             line_changes=state["unobserved_changes"])
    identity = ("origin", "path", "function", "file_hash")
    resolved = {"call_id": state["call_id"],
                "focus": {key: bound["focus"][key] for key in identity},
                "watches": [{key: watch[key] for key in (*identity, "lines", "fields")}
                            for watch in bound["watches"]]}
    for change in state["unobserved_changes"]:
        if any(w["origin"] == "workspace" and w["path"] == change["path"]
               and w["file_hash"] != change["file_hash"] for w in resolved["watches"]):
            raise ContractError("diagnosis source changed since the original-failure observation")
    repair_path.validate(state, "run_probe", {**arguments,
        "replay_action_id": state["replay_action_id"], "call_path": resolved})
    return {"policy": POLICY, "candidate_diff_hash": state["candidate_diff_hash"],
            "replay_action_id": state["replay_action_id"], "call_path": resolved,
            "line_selection": [{"path": watch["path"], "function": watch["function"],
                                **watch["line_selection"]} for watch in bound["watches"]]}


def arguments(raw, admission):
    """Keep raw model input immutable for action_id/input_hash recovery."""
    return {**raw, "replay_action_id": admission["replay_action_id"],
            "call_path": admission["call_path"]}
