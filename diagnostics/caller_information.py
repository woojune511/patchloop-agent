"""Verify later operator evidence and project it into one checkpoint input only."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from diagnostics.decision_sampler import require
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev.state import DevJournal
from patchloop.util import canonical_json, sha256_bytes, sha256_json

FIELD = "operator_caller_observation"


def load(descriptor, packet_hash, source, envelope):
    # Local import avoids the probe driver's dependency on the shared collector.
    from diagnostics import anyio_caller_probe as probe

    path = Path(descriptor["path"])
    raw = path.read_bytes()
    require(sha256_bytes(raw) == descriptor["hash"], "operator result hash changed")
    result = json.loads(raw)
    journal = DevJournal(path.parent, "run_dev_callerstateprobe")
    events = journal.events()  # Validates the complete hash chain.
    store = ArtifactStore(path.parent / "artifacts")

    def one(kind):
        matching = [e["payload"] for e in events if e["event_type"] == kind]
        require(len(matching) == 1, "operator evidence boundary is ambiguous: " + kind)
        return matching[0]

    def read(ref):
        return store.read_bytes(Artifact.model_validate(ref))

    prepared = one("operator_probe_prepared")
    environment = one("operator_environment_ready")
    require(json.loads(read(one("operator_observation_completed")["artifact"])) == result,
            "operator result differs from completed journal artifact")
    require(prepared["packet_hash"] == packet_hash
            and prepared["runtime_hash"] == envelope.runtime_hash
            and prepared["public_task_hash"] == sha256_bytes(source.public_path.read_bytes())
            and prepared["implementation_hash"] == sha256_bytes(Path(probe.__file__).read_bytes())
            and prepared["origin"] == result["origin"] == "operator"
            and prepared["official"] is result["official"] is False
            and result["model_calls"] == result["input_counts"] == 0,
            "operator provenance differs from checkpoint")
    from patchloop.task_loader import load_public_task

    public = load_public_task(source.public_path)
    require(environment == {
        "base_commit": public.repository.base_commit, "diff_hash": sha256_bytes(b""),
        "image_digest": envelope.probe_image_digest, "profile_hash": envelope.probe_profile_hash,
    }, "operator observation is not on the pinned unchanged base")
    rows, programs = [], {}
    dependencies = (envelope.probe_dependencies.model_dump(mode="json")
                    if envelope.probe_dependencies else None)
    finished = [e["payload"] for e in events if e["event_type"] == "operator_probe_finished"]
    require(finished == result["receipts"] and len(finished) == 2,
            "operator receipts differ from journal")
    for mode, entry in zip(probe.MODES, finished, strict=True):
        program = read(prepared["programs"][mode]).decode()
        receipt = json.loads(read(entry["artifact"]))
        require(entry["mode"] == mode and program == probe.program(mode)
                and receipt["source_hash"] == sha256_bytes(program.encode())
                and receipt["status"] == "passed" and receipt["exit_code"] == 0
                and not any(receipt.get(k) for k in
                            ("cleanup_failed", "timed_out", "truncated", "deadline_exhausted"))
                and receipt["image_digest"] == envelope.probe_image_digest
                and receipt["profile_hash"] == envelope.probe_profile_hash
                and receipt["execution_policy"]["dependencies"]
                == dependencies,
                "operator probe code or execution receipt differs")
        row = json.loads(receipt["stdout"])
        require(row["mode"] == mode, "operator observation mode changed")
        rows.append(row)
        programs[mode] = program
    require(rows == result["observations"] and probe.interpret(rows) == result["interpretation"],
            "operator observations differ from measured stdout")
    # Project executable reproduction + raw observations, never the interpretation,
    # old model outcomes, proposed repair, private evaluator or an invented tool result.
    supplement = {
        "origin": "operator", "kind": "later_public_probe_observation",
        "timing": "Collected after this saved checkpoint, on a separate unchanged base workspace.",
        "scope": "These callback-trigger and explicit waiting-caller cancellation executions only.",
        "base_commit": environment["base_commit"],
        "probe_image_digest": environment["image_digest"],
        "program_template": programs[probe.MODES[0]].split("\n", 1)[1],
        "execution": "Each program prepends MODE = repr(mode) to program_template.",
        "observations": rows,
    }
    binding = {"path": str(path.resolve()), "hash": descriptor["hash"],
               "journal_hash": sha256_bytes(journal.path.read_bytes()),
               "supplement_hash": sha256_json(supplement)}
    return supplement, binding


def project(original, supplement):
    selected = copy.deepcopy(original)
    item = selected["input"][-1]
    state = json.loads(item["content"])
    require(item["role"] == "developer" and state["kind"] == "harness_current_state"
            and FIELD not in state["state"], "unexpected first-input projection boundary")
    state["state"][FIELD] = copy.deepcopy(supplement)
    item["content"] = canonical_json(state)
    return selected
