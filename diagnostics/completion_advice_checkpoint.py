"""Offline input pair for removing completion action recommendations."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from diagnostics import post_edit_budget_checkpoint as checkpoint
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source, disjoint
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SCHEMA = "completion-advice-offline-v1"
READY_FACT = (
    "All required visible checks pass on the current diff; submission is eligible, "
    "not proof of untested behavior."
)
READY_ADVICE = (
    " Use run_probe if a concrete remaining public uncertainty could change the edit; "
    "otherwise use finish_task to submit. No extra experiment is required."
)


def project(request):
    """Remove only local action advice; reject unsupported guidance rather than guess."""
    selected = copy.deepcopy(request)
    view = json.loads(selected["input"][-1]["content"])
    state = view["state"]
    require(checkpoint.SCOPE_FIELD not in state, "scope cue would confound advice removal")
    guidance = state["completion_guidance"]
    if guidance["stage"] == "needs_visible_checks":
        action = guidance["next_action"]
        require(action.get("tool") == "run_check" and not guidance["submission_ready"],
                "check guidance is inconsistent")
        check_id = action["check_id"]
        expected = (
            f"Run one remaining visible check for the current diff: {check_id}. "
            "Use run_check; PASS on a different diff does not count toward completion. "
            "Submission becomes available when all required checks pass on this scoped patch."
        )
        factual = (
            f"Remaining visible check for the current diff: {check_id}. "
            "PASS on a different diff does not count toward completion. "
            "Submission becomes available when all required checks pass on this scoped patch."
        )
    elif guidance["stage"] == "ready_to_submit":
        require(guidance["submission_ready"] and guidance["next_action"] == {"tool": "finish_task"},
                "ready guidance is inconsistent")
        expected = READY_FACT + (READY_ADVICE if "run_probe" in
            [t["name"] for t in request["tools"]] else
            " Use finish_task to submit; keep any remaining uncertainty explicit.")
        factual = READY_FACT
    elif guidance["stage"] == "needs_mutation":
        require(not guidance["submission_ready"]
                and guidance["next_action"] == {"tool": "replace_text"},
                "mutation guidance is inconsistent")
        expected = (
            "The current candidate needs a repair. Use replace_text for a supported edit; "
            "available anchor evidence does not establish a correct solution. "
            "Submission waits for a scoped patch and its required visible checks.")
        factual = (
            "The current candidate needs a repair. "
            "Available anchor evidence does not establish a correct solution. "
            "Submission waits for a scoped patch and its required visible checks.")
    elif guidance["stage"] == "needs_source_evidence":
        tool = guidance["next_action"]["tool"]
        require(tool in {"read_file", "search_files"} and not guidance["submission_ready"],
                "source guidance is inconsistent")
        expected = (
            "replace_text is temporarily unavailable: current editable source evidence "
            f"is missing. Use {tool} on an allowed source file. After evidence is "
            "delivered, edit availability is reevaluated with remaining budgets. "
            "Submission waits for a scoped patch and its required visible checks.")
        factual = (
            "replace_text is temporarily unavailable: current editable source evidence "
            "is missing. After evidence is delivered, edit availability is reevaluated "
            "with remaining budgets. Submission waits for a scoped patch and its "
            "required visible checks.")
    elif guidance["stage"] == "blocked":
        require(guidance["next_action"] is None, "blocked guidance has recommendation")
        expected = factual = (
            "No completion action is currently offered under the current state and budgets. "
            "stop_task abandons without submission or evaluation.")
    else:
        raise ContractError("unsupported completion stage")
    require(guidance["message"] == expected, "completion wording changed")
    guidance["next_action"] = None
    guidance["message"] = factual
    selected["input"][-1]["content"] = canonical_json(view)
    return selected


def prepare(source: Source, output: Path, *, new_cap_nanos: int):
    """Freeze equal-budget A/B requests; no collector, credentials or dispatch."""
    disjoint(output.resolve(), (repository_root(), source.root, source.public_path.parent))
    loaded = checkpoint.load(source)
    control = checkpoint.project(loaded.request, new_cap_nanos)
    treatment = project(control)
    output.mkdir()
    store = ArtifactStore(output / "artifacts")
    packet = {
        "schema": SCHEMA, "official": False, "paid_execution_authorized": False,
        "execution_status": "NOT_RUN", "source": source.record(),
        "checkpoint": loaded.receipt, "runtime_hash": runtime_content_hash(),
        "implementation_hash": sha256_bytes(Path(__file__).read_bytes()),
        "checkpoint_implementation_hashes": checkpoint.implementation_hashes(),
        "proposed_new_cap_nanos_per_arm": new_cap_nanos,
        "control": store.put_json(control).model_dump(mode="json"),
        "treatment": store.put_json(treatment).model_dump(mode="json"),
        "control_hash": sha256_json(control), "treatment_hash": sha256_json(treatment),
    }
    raw = (canonical_json(packet) + "\n").encode()
    (output / "packet.json").write_bytes(raw)
    digest = sha256_bytes(raw)
    DevJournal(output, "run_dev_advicepreparation").append(
        "offline_pair_prepared", {"packet_hash": digest, "provider_calls": 0})
    return {"packet": str(output / "packet.json"), "packet_hash": digest}


def validate(path: Path, digest: str):
    require(sha256_bytes(path.read_bytes()) == digest, "packet identity changed")
    packet = json.loads(path.read_bytes())
    require(packet["schema"] == SCHEMA and packet["paid_execution_authorized"] is False
            and packet["execution_status"] == "NOT_RUN", "offline packet required")
    require(packet["runtime_hash"] == runtime_content_hash()
            and packet["implementation_hash"] == sha256_bytes(Path(__file__).read_bytes())
            and packet["checkpoint_implementation_hashes"] == checkpoint.implementation_hashes(),
            "implementation changed")
    loaded = checkpoint.load(Source.from_record(packet["source"]))
    require(loaded.receipt == packet["checkpoint"], "checkpoint changed")
    control = checkpoint.project(loaded.request, packet["proposed_new_cap_nanos_per_arm"])
    store = ArtifactStore(path.parent / "artifacts")
    for key, expected in (("control", control), ("treatment", project(control))):
        actual = json.loads(store.read_bytes(Artifact.model_validate(packet[key])))
        require(actual == expected and sha256_json(actual) == packet[f"{key}_hash"],
                "input pair changed")
    events = DevJournal(path.parent, "run_dev_advicepreparation").events()
    require(len(events) == 1 and events[0]["payload"]["packet_hash"] == digest,
            "preparation binding changed")
    return {"verified": True, "provider_calls": 0, "execution_status": "NOT_RUN"}
