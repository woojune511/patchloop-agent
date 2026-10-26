"""Host construction of a pending original-call diagnosis, without target execution."""

from __future__ import annotations

import ast

from patchloop.dev import repair_path
from patchloop.errors import ContractError
from patchloop.sandbox import call_path_trace
from patchloop.util import sha256_bytes

POLICY = "host-call-path-request-v1"
NULL_FIELDS = ("question", "python_source", "replay_action_id", "purpose")


def tool_schema():
    """Expose only selections the model can change at the pending diagnosis gate."""
    return {
        "type": "function", "name": "run_probe", "strict": True,
        "description": (
            "Diagnose the pending original-call failure on the current candidate. "
            "Select only a public function on the suspected failure path as focus. The host "
            "observes it and the changed-function watches across the entire selected call, "
            "including outside the focus frame. It supplies the original call, parameter "
            "fields and executable lines. "
            "The frozen program, inputs and expected result do not change. "
            "No plan or memory annotation is required. A complete trace informs the next "
            "repair; it does not verify that repair. Unknown is not no-hit."
        ),
        "parameters": {
            "type": "object",
            "properties": {"focus": call_path_trace.schema()["properties"]["focus"]},
            "required": ["focus"],
            "additionalProperties": False,
        },
    }


def symbolic(request):
    return isinstance(request, dict) and "call_id" not in request


def validate_selection(arguments):
    """The same focus-only contract is used by fresh batch and execution admission."""
    if set(arguments) != {"focus"}:
        fields = sorted(set(arguments) - {"focus"}) or ["focus"]
        raise ContractError("diagnosis selects only /focus; invalid fields: "
                            + ", ".join(f"/{key}" for key in fields),
                            details={"invalid_fields": [
                                {"path": f"/{key}", "requirement": "only focus is accepted"}
                                for key in fields]})
    try:
        focus = arguments["focus"]
        call_path_trace.selection_request({"focus": focus, "watches": [
            {**focus, "fields": []} if isinstance(focus, dict) else focus]}, "call-1")
    except ValueError as exc:
        raise ContractError(f"/focus: {exc}", details={"invalid_fields": [
            {"path": "/focus", "requirement": str(exc)}]}) from exc


def _functions(tree):
    found = []

    def visit(node, prefix=""):
        for child in ast.iter_child_nodes(node):
            name = prefix
            if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                name += child.name
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    found.append((name, child))
                name += "."
            visit(child, name)

    visit(tree)
    return found


def watch_plan(state, read_source):
    """Map the observed changed ranges to their own function frames, without execution."""
    watches = {}
    try:
        for change in state["unobserved_changes"]:
            raw = read_source(change["path"])
            if len(raw) > 2_000_000 or sha256_bytes(raw) != change["file_hash"]:
                raise ValueError("changed source unavailable or differs from observed candidate")
            functions = _functions(ast.parse(raw))
            for start, end in change["ranges"]:
                for line in range(start, end + 1):
                    enclosing = [(name, node) for name, node in functions
                                 if node.lineno <= line <= node.end_lineno]
                    if not enclosing:
                        raise ValueError("changed range is outside a Python function frame")
                    name, node = min(enclosing,
                                     key=lambda item: item[1].end_lineno - item[1].lineno)
                    # Duplicate definitions cannot be selected uniquely by the existing tracer.
                    if sum(other == name for other, _ in functions) != 1:
                        raise ValueError("changed function does not have a unique public name")
                    parameters = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
                    parameters += [arg for arg in (node.args.vararg, node.args.kwarg) if arg]
                    watches[change["path"], name] = {
                        "origin": "workspace", "path": change["path"], "function": name,
                        "fields": [arg.arg for arg in parameters[:call_path_trace.MAX_FIELDS]],
                    }
        if not 1 <= len(watches) <= call_path_trace.MAX_WATCHES:
            raise ValueError("changed functions exceed the bounded watch capacity")
    except (OSError, SyntaxError, ValueError, ContractError) as exc:
        return {"status": "unavailable", "reason": str(exc), "watches": []}
    return {"status": "ready", "watches": list(watches.values()),
            "policy": "changed-function-parameters-v1", "author": "host"}


def prepare(arguments, state, workspace, source_preflight, *, deadline=None, read_source=None):
    """Freeze only public choices and current host identities before action_started."""
    if state.get("status") != "needs_path_diagnosis":
        raise ContractError("symbolic call_path requires a pending original-call diagnosis")
    if "focus" in arguments:
        validate_selection(arguments)
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
    host_watches = None
    if "focus" in arguments:
        if not callable(read_source):
            raise ContractError("changed-source reader is unavailable")
        host_watches = watch_plan(state, read_source)
        if host_watches["status"] != "ready":
            raise ContractError(host_watches["reason"], details={"watch_plan": host_watches})
        try:
            request = call_path_trace.selection_request(
                {"focus": arguments["focus"], "watches": host_watches["watches"]}, state["call_id"])
            request["scope"] = "selected_call"
        except ValueError as exc:
            raise ContractError(str(exc), details={"invalid_fields": [
                {"path": "/focus", "requirement": str(exc)}]}) from exc
    else:
        # Saved symbolic admissions remain recoverable; fresh schemas expose only focus.
        if not symbolic(arguments.get("call_path")):
            raise ContractError("diagnosis requires focus", details={"invalid_fields": [
                {"path": "/focus", "requirement": "select a public failure-path function"}]})
        request = call_path_trace.selection_request(arguments["call_path"], state["call_id"])
    try:
        bound = source_preflight(workspace, request, deadline=deadline,
                                 line_changes=state["unobserved_changes"])
    except ValueError as exc:
        # The watches are host-derived from hash-verified source. Do not change
        # the original or invent another watch to admit a failed focus selection.
        if host_watches is None:
            raise
        raise ContractError(f"/focus source binding: {exc}", details={"invalid_fields": [
            {"path": "/focus", "requirement": str(exc)}]}) from exc
    identity = ("origin", "path", "function", "file_hash")
    resolved = {"call_id": state["call_id"],
                **({"scope": request["scope"]} if "scope" in request else {}),
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
            **({"host_watches": host_watches} if host_watches is not None else {}),
            "line_selection": [{"path": watch["path"], "function": watch["function"],
                                **watch["line_selection"]} for watch in bound["watches"]]}


def arguments(raw, admission):
    """Keep raw model input immutable for action_id/input_hash recovery."""
    return {**{key: value for key, value in raw.items() if key != "focus"},
            "replay_action_id": admission["replay_action_id"],
            "call_path": admission["call_path"]}
