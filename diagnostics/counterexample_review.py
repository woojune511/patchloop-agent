"""Freeze a voluntary counterexample-review comparison; no execution entry point.

Only public checkpoint restoration and one system-prompt suffix are implemented.
The bounded rollout adapter still needs separate implementation/mock validation.
"""

from __future__ import annotations

import argparse
import copy
import json
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

from diagnostics.probe_first_view import require, wire
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, ModelConfig
from patchloop.dev import runner
from patchloop.dev.conversation import history_metadata, reconstruct_state, validate_model_input
from patchloop.dev.cost import pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SCHEMA = "counterexample-review-design-v1"
SOURCE_ID = "run_dev_8d592587618448b7"
TURN_NUMBER = 22
MODEL = "gpt-5.4-mini-2026-03-17"
PROMPT_SUFFIX = """

<counterexample_review>
Before submitting, identify one assumption in the current patch that the existing
public checks have not established. Derive a small input from the public requirements
that could refute that assumption and use run_probe to check the current candidate.
If the observation exposes a defect, revise the patch and rerun the affected visible
checks. If it does not, do not claim broader correctness than the evidence supports.
Use the existing tools and budgets; no separate plan or memory update is required.
</counterexample_review>"""
REFERENCES = {
    "evaluation": "https://developers.openai.com/api/docs/guides/evaluation-best-practices",
    "prompting": ("https://developers.openai.com/api/docs/guides/latest-model"
                  "?model=gpt-5.4#prompting-best-practices"),
    "pricing": "https://developers.openai.com/api/docs/pricing",
}


class PublicStore(ArtifactStore):
    """Do not mkdir/write the original store; inventory only actually read objects."""

    def __init__(self, root: Path):
        self.root, self.objects = root, root / "objects/sha256"
        require(self.objects.is_dir(), "missing source store")
        self.reads: dict[str, str] = {}

    def read_bytes(self, artifact: Artifact) -> bytes:
        raw = super().read_bytes(artifact)
        self.reads[str(Path(artifact.path).resolve())] = sha256_bytes(raw)
        return raw

    def put_bytes(self, *args, **kwargs):
        raise ValueError("source store is read-only")


def implementation_hashes() -> dict:
    root = repository_root()
    names = ("diagnostics/counterexample_review.py", "diagnostics/probe_first_view.py")
    return {name: sha256_bytes((root / name).read_bytes()) for name in names}


def add_review(request: dict) -> tuple[dict, dict]:
    """No task-specific case, new source, changed tool choice or reasoning reset."""
    require(request.get("model") == MODEL and request.get("reasoning") == {"effort": "medium"},
            "fixed model/effort required")
    require(request.get("max_output_tokens") == 25000 and request.get("store") is False
            and request.get("include") == ["reasoning.encrypted_content"]
            and request.get("tool_choice") == "required", "request contract changed")
    items = request["input"]
    validate_model_input(items, history_metadata(items))
    require(PROMPT_SUFFIX not in items[0]["content"], "review already present")
    state = reconstruct_state(items)
    names = [t["name"] for t in request["tools"]]
    require(len(names) == len(set(names)) and set(names) == set(state["available_tool_names"])
            and {"run_probe", "replace_text", "finish_task", "stop_task"} <= set(names),
            "voluntary probe, repair and submission tools required")
    diff = state["current_diff"]
    require(bool(diff["patch"]) and state.get("workflow_gate") == "ready_to_submit",
            "post-check nonempty candidate required")
    checks = state["visible_check_status"]
    require(bool(checks) and all(c["status"] == "PASS" and c["diff_hash"] == diff["patch_hash"]
                                for c in checks), "all current visible checks must pass")
    budget = state["remaining_budget"]
    require(type(budget["accepted_mutations"]) is int and budget["accepted_mutations"] > 0,
            "remaining repair opportunity required")
    horizon = state["action_horizon"]["mutation_completion_horizon"]
    minimum = horizon["minimum_calls"] + 1  # One probe, then the conditional repair path.
    require(horizon["minimum_possible"] is True and minimum <= 8
            and min(budget["model_calls"], budget["tool_actions"]) >= minimum,
            "probe plus repair/check/finish must fit")
    reasoning = [i for i in items if i.get("type") == "reasoning"]
    require(all(set(i) <= {"type", "id", "encrypted_content", "summary", "status"}
                and bool(i.get("encrypted_content")) and i.get("summary") == [] for i in reasoning),
            "only opaque reasoning is allowed")
    calls = [i["call_id"] for i in items if i.get("type") == "function_call"]
    outputs = [i["call_id"] for i in items if i.get("type") == "function_call_output"]
    require(calls == outputs and len(set(calls)) == len(calls), "native action pairing changed")
    alternate = copy.deepcopy(request)
    alternate["input"][0]["content"] += PROMPT_SUFFIX
    require(reconstruct_state(alternate["input"]) == state, "public evidence changed")
    return alternate, {
        "workflow_gate": state["workflow_gate"], "current_diff_hash": diff["patch_hash"],
        "remaining_budget": budget, "visible_checks": checks,
        "probe_plus_minimum_repair_calls": minimum,
        "native_item_count": len(items), "reasoning_item_count": len(reasoning),
        "native_action_pair_count": len(calls), "tools_in_order": names,
        "unchanged_tools_hash": sha256_bytes(wire(request["tools"])),
        "unchanged_evidence_and_continuation_hash": sha256_bytes(wire(items[1:])),
        "control_request_bytes": len(wire(request)),
        "treatment_request_bytes": len(wire(alternate)),
        "changed_field": "input[0].content (one suffix)",
    }


def restore(source_root: Path) -> tuple[dict, dict]:
    """Replay only the public prefix, never load the final workspace or evaluator."""
    source = source_root.resolve()
    require((source / "runs").is_dir(), "source runs missing")
    journal = DevJournal(source, SOURCE_ID)
    envelope = journal.load_envelope()
    require(envelope is not None and envelope.model == MODEL
            and envelope.reasoning_effort == "medium" and envelope.context_policy == "append-v1"
            and envelope.runtime_hash == runtime_content_hash()
            and envelope.compaction_contract is None, "source runtime/config mismatch")
    events = journal.events()  # Verify the complete chain; use only the selected public prefix.
    positions = [i for i, e in enumerate(events) if e["event_type"] == "turn_started"]
    index = positions[TURN_NUMBER - 1]
    event, turn = events[index], events[index]["payload"]
    prefix = SimpleNamespace(events=lambda: events[:index])
    store = PublicStore(source / "artifacts")
    context = store.read_bytes(Artifact.model_validate(turn["context_artifact"])).decode()
    items = json.loads(store.read_bytes(Artifact.model_validate(turn["model_input_artifact"])))
    expected = runner._build_model_input(
        journal=prefix, artifact_store=store, context=context,
        latest_tool_results=DevJournal.latest_tool_batch_results(prefix),
        context_policy=envelope.context_policy,
    )
    require(items == expected, "public prefix replay mismatch")
    validate_model_input(items, turn["native_history"])
    state = reconstruct_state(items)
    # The provider view intentionally replaces duplicate bodies with native references.
    # Full projection equality is already proved by replay above, not raw-context equality.
    context_state = json.loads(context)
    for key in ("public_task", "current_diff", "remaining_budget", "available_tool_names",
                "visible_check_status", "workflow_gate", "current_public_failure"):
        require(state[key] == context_state[key], f"current {key} mismatch")
    schemas = dev_tool_schemas(
        finish_enabled="finish_task" in turn["available_tool_names"],
        check_ids=[c["check_id"] for c in state["visible_check_status"]
                   if c["status"] == "NOT_RUN"],
        allowed_tools=turn["available_tool_names"], read_paths=turn["targeted_read_paths"],
    )
    config = ModelConfig(provider="openai", model_id=MODEL, reasoning_effort="medium",
                         reasoning_continuation="encrypted-v1", transport_max_retries=0,
                         max_output_tokens=25000)
    request = OpenAIResponsesAdapter.request_payload(
        SimpleNamespace(config=config), items, schemas, system_prompt=runner.DEV_SYSTEM_PROMPT,
    )
    # Later count/dispatch metadata is identity-only evidence; never import its response.
    metadata = [e["payload"] for e in events[index + 1:]
                if e["event_type"] in {"input_count_started", "provider_call_started"}
                and e["payload"].get("turn_id") == turn["turn_id"]]
    require(len(metadata) == 2 and all(m["request_hash"] == sha256_json(request) for m in metadata),
            "original count/dispatch request mismatch")
    privacy = canonical_json(items).replace(".patchloop-hidden/**", "")
    require(not any(marker in privacy for marker in (
        ".patchloop-hidden", "reference.patch", '"private_spec"', "private.yaml",
    )), "nonpublic material in source input")
    return request, {
        "source_root": str(source), "source_run_id": SOURCE_ID, "turn_number": TURN_NUMBER,
        "turn_id": turn["turn_id"], "cutoff_event_sequence": event["sequence"],
        "cutoff_event_hash": event["event_hash"], "prefix_event_count": index,
        "context_artifact": turn["context_artifact"],
        "native_input_artifact": turn["model_input_artifact"],
        "source_runtime_hash": envelope.runtime_hash, "source_model_hash": envelope.model_hash,
        "task_content_hash": envelope.task_content_hash, "base_commit": envelope.base_commit,
        "original_request_hash": sha256_json(request),
        "verified_source_files": {
            str(journal.path): sha256_bytes(journal.path.read_bytes()),
            str(journal.envelope_path): sha256_bytes(journal.envelope_path.read_bytes()),
            **store.reads,
        },
    }


def protocol(metrics: dict) -> dict:
    return {
        "schema_version": SCHEMA, "status": "PREPARED_NOT_EXECUTABLE",
        "collector_implemented": False, "paid_execution_authorized": False,
        "model": MODEL, "reasoning_effort": "medium", "output_ceiling": 25000,
        "context_policy": "append-v1", "encrypted_continuation": "retained identically",
        "arms": {"A": "unchanged", "B": "one proactive falsification instruction"},
        "branch_order": ["A1", "B1", "B2", "A2"],
        "schedule": "round-robin in branch_order; skip terminal branches",
        "new_model_calls_each": 8, "maximum_new_model_calls": 32,
        "inherited_remaining_budget_each": metrics["remaining_budget"],
        "planning_cap_usd_each": "0.50", "planning_cap_usd_total": "2.00",
        "budget_transfer": False, "automatic_retry_resume_or_extra_sample": False,
        "cost_admission": "count exact request immediately before dispatch; reserve uncached "
                          "input plus all 25000 output tokens; never shrink the ceiling",
        "pricing": {**{k: str(v) for k, v in asdict(pricing_for_model(MODEL)).items()},
                    "source": REFERENCES["pricing"], "verified_on": "2026-09-13",
                    "service_tier": "default", "count_billing_and_invoice": "UNVERIFIED"},
        "treatment_lifecycle": "append suffix once to the branch's initial system message; "
                               "preserve it thereafter; no per-turn reminders",
        "action_policy": "normal budget-derived tools/choice in both arms, including finish; "
                         "no mandatory probe admission gate",
        "feedback": "execute only the branch's admitted public tools in its isolated workspace; "
                    "deliver real native tool results, including probe errors; no operator repair",
        "stop_all_on": ["count uncertainty", "transport/billing uncertainty",
                        "continuation integrity failure", "unconfirmed owned-container cleanup"],
        "censoring": "cost/turn/time bound is incomplete observation, not semantic task failure; "
                     "8 calls per branch are maxima, not guaranteed funded calls",
        "review_axes": {
            "behavior": "first action, probe choice, actual execution, response to feedback",
            "case_quality": "publicly justified expectation that can refute a patch assumption; "
                            "execution success alone and prints without an oracle are insufficient",
            "repair": "exact anchor/scope admission, code addressing the observed discrepancy, "
                      "rerun the same diagnostic case against the changed diff",
            "completion": "both current visible checks and finish identity; hidden NOT_RUN",
            "cost": "input/cached/output tokens, known cost, cache impact and censored outcomes",
        },
        "review_procedure": "record public code/tool evidence with arm labels hidden first; "
                            "then unblind; no paid judge, hidden or operator-case injection",
        "limits_of_inference": [
            "One post-hoc-selected public-PASS checkpoint, two new samples per arm.",
            "Historical response is not a new control; source continuation is shared, not reset.",
            "Successful prompted verification is local evidence, not a general ability proof.",
            "Non-use or no repair may be ambiguity, case quality or censoring; not incapability.",
            "System suffix changes cache prefix; compare behavior and cost separately.",
            "No default prompt, forced probe, planning or memory policy follows from this alone.",
        ],
        "next_required_work": [
            "Adapt the existing short-rollout branch engine to this exact v38 checkpoint.",
            "Derive inherited counters from prefix (2 accepted), not the old hard-coded 3.",
            "Mock-test native feedback, idempotency, deadline, exact ceiling and all-branch stops.",
            "Seal executable packet and obtain separate exact paid-execution approval.",
        ],
        "boundaries": {"provider_calls": 0, "input_count_calls": 0, "tool_executions": 0,
                       "docker_operations": 0, "credential_reads": 0, "official": False,
                       "claim_eligible": False, "task_acceptance": "NOT_RUN"},
        "references": REFERENCES,
    }


def compile_packet(source_root: Path) -> tuple[dict, dict[str, bytes]]:
    request, checkpoint = restore(source_root)
    alternate, metrics = add_review(request)
    candidate = reconstruct_state(request["input"])["current_diff"]["patch"].encode()
    files = {"A.json": wire(request), "B.json": wire(alternate),
             "checkpoint.json": wire(checkpoint), "protocol.json": wire(protocol(metrics)),
             "prompt.txt": PROMPT_SUFFIX.encode(), "candidate.patch": candidate}
    packet = {
        "schema_version": SCHEMA, "status": "PREPARED_NOT_EXECUTABLE",
        "source_root": str(source_root.resolve()), "checkpoint": {
            k: checkpoint[k] for k in ("source_run_id", "turn_number", "turn_id",
                                      "cutoff_event_sequence", "cutoff_event_hash")},
        "runtime_hash": runtime_content_hash(), "implementation_hashes": implementation_hashes(),
        "file_hashes": {name: sha256_bytes(body) for name, body in files.items()},
        "metrics": metrics, "boundaries": protocol(metrics)["boundaries"],
    }
    return packet, files


def prepare(source_root: Path, output_root: Path) -> dict:
    require(source_root.is_absolute() and output_root.is_absolute(), "absolute roots required")
    root, source = output_root.resolve(), source_root.resolve()
    require(not root.exists() and root.parent.is_dir(), "fresh external root required")
    require(not root.is_relative_to(repository_root()) and not root.is_relative_to(source)
            and not source.is_relative_to(root), "output overlaps protected source/repository")
    packet, files = compile_packet(source)
    store = ArtifactStore(root)
    for name, body in {**files, "packet.json": wire(packet)}.items():
        store.write_text_immutable(root / name, body.decode())
    return packet


def validate(root: Path) -> dict:
    packet = json.loads((root / "packet.json").read_bytes())
    expected, files = compile_packet(Path(packet["source_root"]))
    require(packet == expected, "packet/source/runtime/implementation changed")
    require(all((root / name).read_bytes() == body for name, body in files.items()),
            "frozen comparison file changed")
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("prepare")
    p.add_argument("--source-root", type=Path, required=True)
    p.add_argument("--output-root", type=Path, required=True)
    v = commands.add_parser("validate")
    v.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    result = (prepare(args.source_root, args.output_root) if args.command == "prepare"
              else validate(args.root))
    print(wire(result).decode())


if __name__ == "__main__":
    main()
