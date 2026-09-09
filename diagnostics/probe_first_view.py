"""Prepare probe-first repair inputs; no provider, tool execution or runtime default."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from patchloop.artifacts import ArtifactStore
from patchloop.dev.conversation import history_metadata, reconstruct_state, validate_model_input
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import sha256_bytes

SCHEMA = "probe-first-repair-design-v1"
FORCED_PROBE = {"type": "function", "name": "run_probe"}
DOC_URL = "https://developers.openai.com/api/docs/guides/function-calling#tool-choice"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def wire(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def force_probe(request: dict) -> tuple[dict, dict]:
    """Change only tool_choice on a repair checkpoint with one probe's slack.

    Eligibility is an offline diagnostic selector, never a production action gate.
    The registered probe description supplies the question/source contract; no
    operator diagnosis, suggested experiment or solution enters the model input.
    """
    require(isinstance(request, dict) and isinstance(request.get("input"), list),
            "invalid request")
    require(request.get("tool_choice") == "required", "ordinary tool choice required")
    require(request.get("store") is False
            and request.get("include") == ["reasoning.encrypted_content"],
            "stateless encrypted continuation required")
    require(isinstance(request.get("model"), str) and bool(request["model"]),
            "explicit model required")
    items = request["input"]
    validate_model_input(items, history_metadata(items))
    require(len(items) > 3 and items[-1].get("role") == "developer", "latest state required")
    for item in items:
        if item.get("type") == "reasoning":
            require(isinstance(item.get("encrypted_content"), str)
                    and bool(item["encrypted_content"]) and item.get("summary") == []
                    and not item.get("text") and not item.get("content"),
                    "invalid reasoning item")
    state = reconstruct_state(items)
    tools = request.get("tools", [])
    require(isinstance(tools, list) and all(isinstance(t, dict) for t in tools),
            "registered tool list required")
    names = [t.get("name") for t in tools]
    require(all(isinstance(name, str) for name in names) and len(names) == len(set(names)),
            "unique named tools required")
    require(set(names) == set(state.get("available_tool_names", []))
            and {"run_probe", "replace_text", "stop_task"} <= set(names),
            "available repair/probe tools required")
    require(next(t for t in tools if t["name"] == "run_probe").get("type") == "function",
            "registered function probe required")
    diff = state.get("current_diff", {})
    current_hash = diff.get("patch_hash")
    require(isinstance(current_hash, str) and bool(current_hash) and bool(diff.get("patch")),
            "nonempty current diff required")
    failure = state.get("current_public_failure")
    require(isinstance(failure, dict) and failure.get("diff_hash") == current_hash,
            "current public failure required")
    checks = state.get("visible_check_status", [])
    require(isinstance(checks, list) and bool(checks)
            and all(isinstance(c, dict) and c.get("diff_hash") == current_hash
                    and c.get("status") in {"PASS", "FAIL", "NOT_RUN"} for c in checks)
            and any(c.get("check_id") == failure.get("check_id") and c["status"] == "FAIL"
                    for c in checks), "matching current failed check required")
    budget = state.get("remaining_budget", {})
    for name in ("accepted_mutations", "model_calls", "tool_actions"):
        require(type(budget.get(name)) is int and budget[name] > 0,
                "positive repair budget required")
    horizon = state.get("action_horizon", {})
    minimum = horizon.get("minimum_completion_calls")
    require(horizon.get("completion_possible") is True and type(minimum) is int
            and minimum > 0 and min(budget["model_calls"], budget["tool_actions"]) > minimum,
            "one probe plus minimum completion must fit")
    require(minimum < 8, "probe plus completion must fit the short-rollout bound")
    changed = copy.deepcopy(request)
    changed["tool_choice"] = dict(FORCED_PROBE)
    return changed, {
        "schema_version": SCHEMA, "status": "PREPARED_NOT_EXECUTABLE",
        "official": False, "claim_eligible": False,
        "provider_calls": 0, "input_count_calls": 0, "tool_executions": 0,
        "task_acceptance": "NOT_RUN", "safety_state": "NOT_RUN",
        "changed_field": "tool_choice", "original_choice": request["tool_choice"],
        "prototype_choice": dict(FORCED_PROBE), "current_diff_hash": current_hash,
        "current_failed_check_id": failure["check_id"],
        "remaining_budget": copy.deepcopy(budget),
        "original_request_bytes": len(wire(request)), "prototype_request_bytes": len(wire(changed)),
        "unchanged_input_hash": sha256_bytes(wire(items)),
        "unchanged_tools_hash": sha256_bytes(wire(tools)), "tool_names_in_order": names,
        "input_item_count": len(items),
        "reasoning_item_count": sum(i.get("type") == "reasoning" for i in items),
        "model": request["model"], "reasoning": copy.deepcopy(request.get("reasoning")),
        "max_output_tokens": request.get("max_output_tokens"),
    }


def design_contract(metrics: dict) -> dict:
    """Collector requirements and review axes are NOT appended to the model prompt."""
    return {
        "kind": SCHEMA, "status": "PREPARED_NOT_EXECUTABLE", "collector_implemented": False,
        "branches": ["A1", "B1", "B2", "A2"], "schedule": "round-robin; skip terminal branches",
        "paired_seed": "same frozen public failure checkpoint, two fresh samples per condition",
        "new_response_limit_each": 8, "shared_invocation_cap_usd": "1.20",
        "inherited_remaining_budget_each": metrics["remaining_budget"],
        "probe_phase": {
            "A": "normal loop throughout; may voluntarily probe",
            "B": "force one model-authored run_probe attempt before normal loop",
            "probe_content": "model generated from unchanged public evidence; no operator hints",
            "charge": "all probe and correction calls/actions/time/cost use the same budget",
            "release": "after the first probe result is delivered through its native batch",
            "execution_failure": "retain real failure output and release; no forced probe retry",
            "protocol_failure": "bounded correction; retain forced choice until probe attempt",
            "pending_batch": "deliver/reconcile recorded output before any new dispatch",
            "later_requests": "normal tool_choice and budget policy; no additional guidance",
        },
        "preserve": ["native prefix", "encrypted reasoning", "task and sources", "optional notes",
                     "tool schemas and order", "model and output ceiling", "checks and scope",
                     "normal admission and action idempotency"],
        "collection_boundaries": {
            "normal_runtime_change": False, "normal_live_row": False, "private_evaluation": False,
            "paid_retry_or_resume": False, "automatic_docker_start_pull_build": False,
            "count": "immediately before each dispatch; same exact request and full output ceiling",
            "uncertainty": (
                "count/provider/billing/continuation/cleanup uncertainty stops all branches"
            ),
            "cap_or_response_bound": "censored, never an uncensored task failure",
            "official": False, "claim_eligible": False,
        },
        "review_axes": {
            "question": "Does the model's probe discriminate its public repair assumptions?",
            "interpretation": "Does the next public decision agree with actual probe observations?",
            "implementation": "Does the accepted code implement that interpretation within scope?",
            "completion": "Does it rerun current-diff checks and submit through finish_task?",
        },
        "review_limits": [
            "Separate runtime success, semantic probe usefulness, correct repair and submission.",
            "No plaintext reasoning or model judge call; review public actions, results and code.",
            "Operator probes/patches are not supplied, and operator checks are not agent credit.",
            "Two samples per arm at one checkpoint do not establish general effectiveness.",
            "First-action choice changes, together with evidence and remaining trajectory budget.",
            "No default mandatory probe policy follows from this diagnostic.",
        ],
        "api_reference": DOC_URL,
    }


def _manifest(source: Path, raw: bytes) -> tuple[dict, bytes, bytes]:
    request = json.loads(raw)
    require(wire(request) == raw, "noncanonical request wire")
    alternate, metrics = force_probe(request)
    body = wire(alternate)
    protocol = wire(design_contract(metrics))
    return {
        **metrics, "source_path": str(source), "source_hash": sha256_bytes(raw),
        "prototype_hash": sha256_bytes(body), "protocol_hash": sha256_bytes(protocol),
        "implementation_hash": sha256_bytes(Path(__file__).read_bytes()),
        "runtime_hash": runtime_content_hash(),
    }, body, protocol


def prepare(input_path: Path, expected_hash: str, output_root: Path) -> dict:
    require(input_path.is_absolute() and output_root.is_absolute(), "absolute paths required")
    source, root = input_path.resolve(), output_root.resolve()
    require(not root.exists() and root.parent.is_dir(), "fresh external root required")
    require(not root.is_relative_to(repository_root().resolve())
            and not source.is_relative_to(root), "output overlaps source or repository")
    raw = source.read_bytes()
    require(sha256_bytes(raw) == expected_hash, "input hash mismatch")
    manifest, body, protocol = _manifest(source, raw)
    store = ArtifactStore(root)
    for name, content in (("A.json", raw), ("B.json", body),
                          ("protocol.json", protocol), ("manifest.json", wire(manifest))):
        store.write_text_immutable(root / name, content.decode())
    return manifest


def validate(root: Path) -> dict:
    manifest = json.loads((root / "manifest.json").read_bytes())
    require(manifest["implementation_hash"] == sha256_bytes(Path(__file__).read_bytes()),
            "preparer changed")
    require(manifest["runtime_hash"] == runtime_content_hash(), "runtime changed")
    source = Path(manifest["source_path"])
    raw = source.read_bytes()
    require(sha256_bytes(raw) == manifest["source_hash"], "source changed")
    expected, body, protocol = _manifest(source, raw)
    require((root / "A.json").read_bytes() == raw, "control changed")
    require((root / "B.json").read_bytes() == body, "prototype changed")
    require((root / "protocol.json").read_bytes() == protocol, "protocol changed")
    require(manifest == expected, "manifest changed")
    return expected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("prepare")
    p.add_argument("--input-request", type=Path, required=True)
    p.add_argument("--input-hash", required=True)
    p.add_argument("--output-root", type=Path, required=True)
    v = commands.add_parser("validate")
    v.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    result = (prepare(args.input_request, args.input_hash, args.output_root)
              if args.command == "prepare" else validate(args.root))
    print(wire(result).decode())


if __name__ == "__main__":
    main()
