"""Prepare a one-field completion-signal comparison; no execution or runtime default."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from patchloop.dev.conversation import history_metadata, validate_model_input
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes, sha256_json

SCHEMA = "completion-signal-view-prototype-v1"
FIELD = "state.action_horizon.mutation_completion_horizon"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def wire(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def without_further_edit_horizon(request: dict) -> tuple[dict, dict]:
    """Remove only the redundant edit forecast when completion needs no more edits.

    Eligibility selects a diagnostic input, not a new action gate. Keep the real
    zero-mutation budget, current checks, completion guidance and every tool exact.
    In particular do not reinterpret an observed failure as an unchecked repair.
    """
    require(isinstance(request, dict) and isinstance(request.get("input"), list),
            "invalid request")
    items = request["input"]
    validate_model_input(items, history_metadata(items))
    require(len(items) > 3 and items[-1].get("role") == "developer", "latest state required")
    record = json.loads(items[-1]["content"])
    require(wire(record).decode() == items[-1]["content"], "noncanonical state wire")
    state = record["state"]
    budget = state.get("remaining_budget", {})
    require(type(budget.get("accepted_mutations")) is int
            and budget["accepted_mutations"] == 0, "zero remaining mutations required")
    horizon = state.get("action_horizon", {})
    require(horizon.get("completion_possible") is True, "completion must remain possible")
    edit = horizon.get("mutation_completion_horizon")
    require(isinstance(edit, dict) and edit.get("minimum_possible") is False
            and edit.get("protected_possible") is False, "unavailable edit forecast required")
    diff = state.get("current_diff", {})
    current_hash = diff.get("patch_hash")
    require(isinstance(current_hash, str) and bool(current_hash) and bool(diff.get("patch")),
            "nonempty current diff required")
    checks = state.get("visible_check_status", [])
    require(bool(checks) and all(isinstance(row, dict)
            and row.get("diff_hash") == current_hash
            and row.get("status") in {"NOT_RUN", "PASS"} for row in checks),
            "current nonfailed check table required")
    require(state.get("current_public_failure") is None, "current failure must not be hidden")
    tools = set(state.get("available_tool_names", []))
    wire_tools = {tool["name"] for tool in request.get("tools", [])}
    require(tools == wire_tools and "replace_text" not in tools, "tool availability mismatch")
    pending = [row["check_id"] for row in checks if row["status"] == "NOT_RUN"]
    guidance = state.get("completion_guidance", {})
    require(guidance.get("diff_hash") == current_hash, "completion guidance diff mismatch")
    expected_gate = "needs_visible_checks" if pending else "ready_to_submit"
    next_tool = "run_check" if pending else "finish_task"
    next_action = guidance.get("next_action", {})
    require(state.get("workflow_gate") == expected_gate and next_tool in tools
            and next_action.get("tool") == next_tool
            and (not pending or next_action.get("check_id") in pending),
            "available check or submission path required")
    for item in items:
        if item.get("type") == "reasoning":
            require(isinstance(item.get("encrypted_content"), str)
                    and bool(item["encrypted_content"]) and item.get("summary") == []
                    and not item.get("text") and not item.get("content"),
                    "invalid reasoning item")

    changed = copy.deepcopy(request)
    del record["state"]["action_horizon"]["mutation_completion_horizon"]
    changed["input"][-1]["content"] = wire(record).decode()
    return changed, {
        "schema_version": SCHEMA, "removed_field": FIELD,
        "removed_value_hash": sha256_json(edit), "current_diff_hash": current_hash,
        "workflow_gate": expected_gate, "remaining_accepted_mutations": 0,
        "pending_check_ids": pending, "next_action": next_action,
        "original_request_bytes": len(wire(request)),
        "prototype_request_bytes": len(wire(changed)),
        "unchanged_prefix_item_count": len(items) - 1,
        "unchanged_prefix_hash": sha256_bytes(wire(items[:-1])),
        "reasoning_item_count": sum(item.get("type") == "reasoning" for item in items),
        "official": False, "claim_eligible": False,
        "provider_calls": 0, "input_count_calls": 0, "tool_executions": 0,
        "task_acceptance": "NOT_RUN", "safety_state": "NOT_RUN",
        "status": "PREPARED_NOT_EXECUTABLE",
        "scope": "one latest-state field only; no token-saving or model-effect claim",
    }


def _manifest(source: Path, original: bytes) -> tuple[dict, bytes]:
    request = json.loads(original)
    require(wire(request) == original, "noncanonical request wire")
    changed, metrics = without_further_edit_horizon(request)
    body = wire(changed)
    return {
        **metrics, "input_path": str(source), "input_hash": sha256_bytes(original),
        "prototype_hash": sha256_bytes(body),
        "implementation_hash": sha256_bytes(Path(__file__).read_bytes()),
    }, body


def prepare(input_path: Path, expected_hash: str, output_root: Path) -> dict:
    require(input_path.is_absolute() and output_root.is_absolute(), "absolute paths required")
    source, root = input_path.resolve(), output_root.resolve()
    require(not root.exists() and root.parent.is_dir(), "fresh external root required")
    require(not root.is_relative_to(repository_root().resolve())
            and not source.is_relative_to(root), "output overlaps source or repository")
    original = source.read_bytes()
    require(sha256_bytes(original) == expected_hash, "input hash mismatch")
    manifest, body = _manifest(source, original)
    root.mkdir()
    (root / "A.json").write_bytes(original)
    (root / "B.json").write_bytes(body)
    (root / "manifest.json").write_bytes(wire(manifest))
    return manifest


def validate(root: Path) -> dict:
    manifest = json.loads((root / "manifest.json").read_bytes())
    require(manifest["implementation_hash"] == sha256_bytes(Path(__file__).read_bytes()),
            "prototype changed")
    source = Path(manifest["input_path"])
    original = source.read_bytes()
    require(sha256_bytes(original) == manifest["input_hash"], "source changed")
    expected, body = _manifest(source, original)
    require((root / "A.json").read_bytes() == original, "control request changed")
    require((root / "B.json").read_bytes() == body, "prototype request changed")
    require(manifest == expected, "manifest changed")
    return expected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--input-request", type=Path, required=True)
    prepare_parser.add_argument("--input-hash", required=True)
    prepare_parser.add_argument("--output-root", type=Path, required=True)
    validate_parser = commands.add_parser("validate")
    validate_parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    result = (prepare(args.input_request, args.input_hash, args.output_root)
              if args.mode == "prepare" else validate(args.root))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
