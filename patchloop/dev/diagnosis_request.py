"""Host construction of a pending original-call diagnosis, without target execution."""

from __future__ import annotations

from patchloop.dev import repair_path
from patchloop.errors import ContractError
from patchloop.sandbox import call_path_trace

POLICY = "host-call-path-request-v1"


def symbolic(request):
    return isinstance(request, dict) and "call_id" not in request


def prepare(arguments, state, workspace, source_preflight, *, deadline=None):
    """Freeze only public choices and current host identities before action_started."""
    if state.get("status") != "needs_path_diagnosis":
        raise ContractError("symbolic call_path requires a pending original-call diagnosis")
    if any(arguments.get(key) is not None for key in (
        "replay_action_id", "question", "python_source", "purpose", "reproduction",
        "case_id", "reference_action_id",
    )) or arguments.get("save_program"):
        raise ContractError("symbolic diagnosis uses the pending original; "
                            "leave replay/source null")
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
