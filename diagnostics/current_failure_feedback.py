"""Freeze a current-candidate failure comparison; preparation only, no run command.

Use the report-only A2 checkpoint before its final decision. Restore its actual
native input, including opaque continuation, without importing that decision.
Only B receives the already executed public observation on this identical diff.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from types import SimpleNamespace

from diagnostics import failure_given_repair as prior
from patchloop.contracts import Artifact, ModelConfig
from patchloop.dev.conversation import history_metadata, reconstruct_state, validate_model_input
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.util import canonical_json, sha256_bytes, sha256_json

seed, require, wire = prior.seed, prior.require, prior.wire
SCHEMA = "current-failure-feedback-design-v1"
FIELD = "operator_current_candidate_feedback"
SOURCE = Path("C:/pt/analyses/report-review-live-20260914")
COMPLETION_HASH = "sha256:5808686ecab0d433e904730e7dcd096a2a02bf4bb5204a5488f2b60a00976b35"
RUN_ID = "run_dev_report_review_ad246d9b87544161"
TURN_ID = "turn_25853d06430f4e199d6b7b8ae68fd82f"
DIFF_HASH = "sha256:5c3c2067afbe67dde890e26f1460da770ea0e03498a76660192e8bb2e61cd3c5"
FILE_HASH = "sha256:499e0a1768c8492ea71e7ab33fd01d8c8fe849b1eea99246617fb8273e16899c"
CASE_SOURCE = Path("C:/pt/analyses/failure-given-repair-20260914/ready/verification-case.py")
CASE_HASH = "sha256:23fb8358421f4bcc22da75f585470a451fa4a9d91fad202b48be80f42ee2cf07"
DOC_URL = "https://developers.openai.com/api/docs/guides/migrate-to-responses"


class SealedSource:
    """Read only selected files from the completed experiment, never update its seal."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        path = self.root / "completion.json"
        raw = path.read_bytes()
        require(sha256_bytes(raw) == COMPLETION_HASH, "source completion changed")
        self.seal = json.loads(raw)
        self.reads = {str(path): COMPLETION_HASH}

    def read(self, name: str) -> bytes:
        path = (self.root / name).resolve()
        require(path.is_relative_to(self.root), "source path outside sealed root")
        relative = str(path.relative_to(self.root)).replace("/", "\\")
        expected = self.seal["files"].get(relative)
        require(expected is not None, "source file not sealed")
        raw = path.read_bytes()
        require(sha256_bytes(raw) == expected, "sealed source file changed")
        self.reads[str(path)] = expected
        return raw

    def artifact(self, value: dict) -> bytes:
        ref = Artifact.model_validate(value)
        raw = self.read(ref.path)
        require(sha256_bytes(raw) == ref.content_hash and len(raw) == ref.size_bytes,
                "artifact identity mismatch")
        return raw

    def events(self, branch: str, run_id: str) -> list[dict]:
        root = self.root / branch
        self.read(str(root / "runs" / f"{run_id}.jsonl"))
        # The sealed runs directory already exists; no append or execution lock.
        return DevJournal(root, run_id).events()


def restore(source: SealedSource) -> tuple[dict, dict, bytes]:
    envelope = json.loads(source.read("envelope.json"))
    require(envelope["runtime_hash"] == seed.runtime_content_hash()
            and envelope["model"] == seed.MODEL and envelope["reasoning"] == "medium"
            and envelope["context_policy"] == "append-v1" and not envelope["compaction"],
            "source runtime/config mismatch")
    events = source.events("A2", RUN_ID)
    selected = [i for i, e in enumerate(events) if e["event_type"] == "turn_started"
                and e["payload"].get("turn_id") == TURN_ID]
    require(len(selected) == 1, "fixed checkpoint missing or ambiguous")
    index = selected[0]
    event, turn = events[index], events[index]["payload"]
    prefix = SimpleNamespace(events=lambda: events[:index])
    context_raw = source.artifact(turn["context_artifact"])
    items = json.loads(source.artifact(turn["model_input_artifact"]))
    store = seed.PublicStore(source.root / "A2/artifacts")
    expected = seed.runner._build_model_input(
        journal=prefix, artifact_store=store, context=context_raw.decode(),
        latest_tool_results=DevJournal.latest_tool_batch_results(prefix),
        context_policy="append-v1")
    # The diagnostic overlay serialized its unsent view in insertion order, while
    # the native builder sorts state keys. Compare that view structurally, retain
    # its recorded bytes below, and require every already-sent item byte-exact.
    require(items[:-1] == expected[:-1]
            and items[-1].get("role") == expected[-1].get("role")
            and json.loads(items[-1]["content"]) == json.loads(expected[-1]["content"]),
            "public prefix replay mismatch")
    for path in store.reads:
        source.read(path)
    validate_model_input(items, turn["native_history"])
    # Inspect later count/dispatch identities, never their response or final notes.
    count = prior.one([e["payload"] for e in events[index + 1:]
                       if e["event_type"] == "input_count_started"], "turn_id", TURN_ID)
    request_raw = source.artifact(count["request_artifact"])
    request = json.loads(request_raw)
    require(request["input"] == items and wire(request) == request_raw,
            "counted request differs from recorded model input")
    require(count["ordered_request_hash"] == sha256_bytes(request_raw)
            and count["request_hash"] == sha256_json(request), "count request mismatch")
    dispatch = prior.one([e["payload"] for e in events[index + 1:]
                          if e["event_type"] == "provider_call_started"], "turn_id", TURN_ID)
    require(dispatch["request_hash"] == count["request_hash"]
            and dispatch["ordered_request_hash"] == count["ordered_request_hash"],
            "dispatch request mismatch")
    state = reconstruct_state(items)
    schemas = dev_tool_schemas(finish_enabled=True, check_ids=[],
                              allowed_tools=turn["available_tool_names"],
                              read_paths=turn["targeted_read_paths"])
    config = ModelConfig(provider="openai", model_id=seed.MODEL, reasoning_effort="medium",
                         reasoning_continuation="encrypted-v1", transport_max_retries=0,
                         max_output_tokens=25000)
    restored = seed.OpenAIResponsesAdapter.request_payload(
        SimpleNamespace(config=config), items, schemas, system_prompt=seed.runner.DEV_SYSTEM_PROMPT)
    require(restored == request, "current adapter/schema differs from the source request")
    seed.add_review(request)  # Eligibility and opaque/native checks only; discard its suffix.
    require(seed.PROMPT_SUFFIX not in items[0]["content"]
            and "reported_issue_review" not in state["working_notes"],
            "source must be report-only, not the previous B treatment")
    raw_state = json.loads(context_raw)
    for key in ("public_task", "current_diff", "remaining_budget", "available_tool_names",
                "workflow_gate", "visible_check_status", "current_public_failure", prior.FIELD):
        require(state[key] == raw_state[key], f"current {key} mismatch")
    budget = state["remaining_budget"]
    counters = seed.runner._restore_counters(prefix)
    require(counters.model_calls == 40 - budget["model_calls"]
            and counters.tool_actions == 100 - budget["tool_actions"], "counter replay mismatch")
    require(state["current_diff"]["patch_hash"] == DIFF_HASH
            == sha256_bytes(state["current_diff"]["patch"].encode())
            and prior.one(state["current_sources"], "path", "pyfakefs/fake_os.py")["file_hash"]
            == FILE_HASH, "checkpoint candidate mismatch")
    public_input = canonical_json(items).replace(".patchloop-hidden/**", "")
    require(not any(s in public_input for s in (
        ".patchloop-hidden", "reference.patch", '"private_spec"', "private.yaml")),
        "nonpublic input in checkpoint")
    return request, {
        "source_root": str(source.root / "A2"), "source_run_id": RUN_ID, "turn_id": TURN_ID,
        "cutoff_event_sequence": event["sequence"], "cutoff_event_hash": event["event_hash"],
        "prefix_event_count": index, "native_history": turn["native_history"],
        "context_artifact": turn["context_artifact"],
        "model_input_artifact": turn["model_input_artifact"],
        "original_request_hash": count["request_hash"],
        "ordered_request_hash": count["ordered_request_hash"],
        "runtime_hash": envelope["runtime_hash"],
        "tool_surface_hash": envelope["tool_surface_hash"],
        "task_id": envelope["task_id"], "task_version": envelope["task_version"],
        "task_content_hash": envelope["task_content_hash"], "probe": envelope["probe"],
        "remaining_budget": budget, "candidate_file_hash": FILE_HASH,
        "cutoff_rule": "Before the selected turn and its provider response; no terminal resume.",
    }, context_raw


def observation(request: dict, source: SealedSource) -> tuple[dict, bytes]:
    result = json.loads(source.read("result.json"))
    subject = prior.one(result["operator_case_audits"], "branch", "A2")
    require(subject["diff_hash"] == DIFF_HASH and subject["case_outcome"] == "FAIL"
            and subject["origin"] == "operator" and subject["agent_credit"] is False,
            "selected public observation mismatch")
    receipt_raw = source.artifact(subject["result_artifact"])
    receipt = json.loads(receipt_raw)
    case_source = CASE_SOURCE.read_bytes()
    require(sha256_bytes(case_source) == CASE_HASH, "frozen public case changed")
    source.reads[str(CASE_SOURCE.resolve())] = CASE_HASH
    observer = "run_dev_feedback_observer"
    events = source.events("", observer)
    started = prior.one([e["payload"] for e in events
                         if e["event_type"] == "operator_case_started"], "diff_hash", DIFF_HASH)
    finished = prior.one([e["payload"] for e in events
                          if e["event_type"] == "operator_case_finished"], "diff_hash", DIFF_HASH)
    require(started["execution_identity"] == {
        "run_id": observer, "action_id": "case_" + DIFF_HASH.split(":")[-1][:16],
        "input_hash": sha256_json({"diff_hash": DIFF_HASH, "source": case_source.decode()})}
        and finished["result_artifact"] == subject["result_artifact"],
        "operator journal/candidate/source mismatch")
    probe = json.loads(source.read("envelope.json"))["probe"]
    report = make_report(reconstruct_state(request["input"]), receipt,
                         sha256_bytes(receipt_raw), probe)
    return report, case_source


def make_report(state: dict, receipt: dict, receipt_hash: str, probe: dict) -> dict:
    """Allowlist concrete public outputs; never import diagnoses or other branch code."""
    require(receipt["status"] == "passed" and receipt["exit_code"] == 0
            and not any(receipt[k] for k in (
                "truncated", "timed_out", "cleanup_failed", "deadline_exhausted")),
            "public diagnostic incomplete")
    require(receipt["source_hash"] == CASE_HASH
            and receipt["execution_policy_hash"] == sha256_json(receipt["execution_policy"])
            and receipt["execution_policy"]["cleanup_status"] == "confirmed"
            and receipt["image_digest"] == probe["probe_image_digest"]
            and receipt["profile_hash"] == probe["probe_profile_hash"],
            "execution binding mismatch")
    old = state[prior.FIELD]
    data = json.loads(receipt["stdout"])
    require({k: data[k] for k in old["environment"]} == old["environment"]
            and len(data["rows"]) == 1, "public fixture/environment mismatch")
    row = prior.one(data["rows"], "id", prior.CASE_ID)
    actual = {"error": None, "entries": [[p, "dir", "0o755"] for p in ("a", "a/b", "c")]}
    require(row["real"] == old["expected"] and row["fake"] == actual and row["matches"] is False
            and state["current_diff"]["patch_hash"] == DIFF_HASH, "current failure mismatch")
    return {
        "kind": "operator_current_candidate_observation_v1",
        "origin": "operator_executed_public_diagnostic", "model_authored": False,
        "notice": "An external execution observation, not an agent action or registered check.",
        "observed_on_diff_hash": DIFF_HASH,
        "case_definition_ref": prior.FIELD,
        "case_definition": "Same input, initial_state, environment, observables and oracle as "
                           "the referenced public report; this is a newer candidate observation.",
        "expected": copy.deepcopy(row["real"]), "actual": copy.deepcopy(row["fake"]),
        "matches_expected": False,
        "provenance": {"case_id": prior.CASE_ID, "public_execution_receipt_hash": receipt_hash,
                       "case_source_hash": CASE_HASH},
    }


def add_feedback(request: dict, report: dict) -> dict:
    """One separate current-view field; retain the older report and every sent item."""
    items = request["input"]
    validate_model_input(items, history_metadata(items))
    original = reconstruct_state(items)
    require(prior.FIELD in original, "referenced public case missing")
    require(items[-1].get("role") == "developer", "unsent current view required")
    view = json.loads(items[-1]["content"])
    require(view["kind"] == prior.STATE_KIND, "latest current view required")
    overlay = {**copy.deepcopy(report), "currency": (
        "current_candidate" if original["current_diff"]["patch_hash"]
        == report["observed_on_diff_hash"] else "historical_candidate"),
        "currency_rule": "This observation is bound only to observed_on_diff_hash. After an edit, "
                         "it does not determine whether the new candidate passes or fails."}
    require(FIELD not in original
            or {**original[FIELD], "currency": overlay["currency"]} == overlay,
            "conflicting current-candidate feedback")
    changed = copy.deepcopy(request)
    view["state"][FIELD] = overlay
    changed["input"][-1]["content"] = wire(view).decode()
    validate_model_input(changed["input"], history_metadata(changed["input"]))
    require(reconstruct_state(changed["input"]) == {**original, FIELD: overlay},
            "unrelated current state changed")
    return changed


def criteria() -> dict:
    rubric = prior.criteria()
    rubric["axes"]["recognition"] = (
        "Record public acknowledgment that expected b is absent and a/b exists. "
        "Silence is unobserved, not proof of the model's internal interpretation.")
    return {
        **rubric,
        "comparison": "Fresh A1/B1/B2/A2 continuations from the same report-only A2 pre-finish "
                      "checkpoint. A has the old historical report; B additionally has actual "
                      "failure output on the current candidate. Never reuse the old finish as A.",
        "interpretation_limit": "A selected failure checkpoint and two samples per arm test "
                                "repair with supplied evidence, not autonomous discovery, the "
                                "effect of encrypted reasoning, or broad task acceptance.",
        "selection": "A2 lacks the earlier review/advice treatment; B2 has the same diff but "
                     "different history. This post-hoc choice is fixed before any new response.",
    }


def compile_packet(source_root: Path) -> tuple[dict, dict[str, bytes]]:
    source = SealedSource(source_root)
    request, checkpoint, context = restore(source)
    report, case = observation(request, source)
    changed = add_feedback(request, report)
    protocol = {
        "schema_version": SCHEMA, "status": "PREPARED_INPUTS_ONLY", "collector_implemented": False,
        "branch_order": ["A1", "B1", "B2", "A2"], "samples_per_arm": 2,
        "model": seed.MODEL, "reasoning_effort": "medium", "max_output_tokens": 25000,
        "context_policy": "append-v1", "encrypted_continuation": "retained",
        "new_calls_each": 8, "planning_cap_usd_each": "1.00", "planning_cap_usd_total": "4.00",
        "cap_rationale": "A planning increase from the prior 0.50 per branch to reduce known "
                         "cost censoring of a four-call repair/check/finish path. Not permission "
                         "to spend, and not a guarantee of eight uncached calls.",
        "schedule": "Independent continuations, fixed round-robin order, no budget transfer.",
        "lifecycle": "B overlays the observation once in each latest unsent view, with diff-bound "
                     "currency. A never receives it. Keep the old public report in both arms. "
                     "Do not add a fake tool result, failed check, allowance or model note.",
        "unchanged": "All source evidence, old native/opaque items, system prompt, working notes, "
                     "completion guidance, tool schemas/order, current PASS and eligibility.",
        "stops": "No retry, resume, replacement samples, cap transfer, automatic Docker start, "
                 "pull/build or hidden execution. Count/transport/cost uncertainty stops all.",
        "scoring": "Independent fixed public case after settled episodes, unique candidate hash "
                   "reuse, blind public code observation before labeled outcomes, never agent "
                   "credit or feedback. Exploration is not automatic failure. Resource censoring "
                   "leaves ability unevaluated; cached cost differences are not efficiency proof.",
        "next_required_work": "Adapt the existing bounded collector to this nested checkpoint, "
                              "mock replay/lifecycle/cost handling, review current official prices "
                              "and seal an executable packet before exact separate paid approval.",
        "references": {"continuation": DOC_URL, "pricing": seed.REFERENCES["pricing"]},
        "boundaries": prior.BOUNDARIES,
    }
    files = {
        "A.json": wire(request), "B.json": wire(changed), "feedback.json": wire(report),
        "checkpoint.json": wire(checkpoint), "context.json": context,
        "candidate.patch": reconstruct_state(request["input"])["current_diff"]["patch"].encode(),
        "verification-case.py": case, "criteria.json": wire(criteria()),
        "protocol.json": wire(protocol), "provenance.json": wire({
            "verified_source_files": source.reads,
            "intentional_post_cutoff_input": "Only B's selected public observation, executed "
                                             "later on the same diff. No future agent decision, "
                                             "other candidate, or hidden evaluation is imported."}),
    }
    return {
        "schema_version": SCHEMA, "status": "PREPARED_INPUTS_ONLY",
        "source_root": str(source_root.resolve()), "runtime_hash": seed.runtime_content_hash(),
        "implementation_hashes": {**seed.implementation_hashes(),
                                  "diagnostics/failure_given_repair.py": sha256_bytes(
                                      Path(prior.__file__).read_bytes()),
                                  "diagnostics/current_failure_feedback.py": sha256_bytes(
                                      Path(__file__).read_bytes())},
        "file_hashes": {name: sha256_bytes(raw) for name, raw in files.items()},
        "metrics": {"request_bytes_A": len(wire(request)), "request_bytes_B": len(wire(changed)),
                    "added_bytes": len(wire(changed)) - len(wire(request)),
                    "unchanged_native_prefix_hash": sha256_bytes(wire(request["input"][:-1])),
                    "unchanged_tools_hash": sha256_bytes(wire(request["tools"])),
                    "history": history_metadata(request["input"]), "input_tokens": "NOT_COUNTED"},
        "boundaries": prior.BOUNDARIES,
    }, files


def prepare(source_root: Path, output_root: Path) -> dict:
    require(source_root.is_absolute() and output_root.is_absolute(), "absolute roots required")
    root = output_root.resolve()
    require(not root.exists() and root.parent.is_dir(), "fresh external root required")
    require(all(not root.is_relative_to(p.resolve()) and not p.resolve().is_relative_to(root)
                for p in (seed.repository_root(), source_root, CASE_SOURCE.parent)),
            "protected root overlap")
    packet, files = compile_packet(source_root)
    store = prior.ArtifactStore(root)
    for name, raw in {**files, "packet.json": wire(packet)}.items():
        store.write_text_immutable(root / name, raw.decode())
    return packet


def validate(root: Path) -> dict:
    packet = json.loads((root / "packet.json").read_bytes())
    expected, files = compile_packet(Path(packet["source_root"]))
    require(packet == expected, "packet/source/runtime/implementation changed")
    require(all((root / name).read_bytes() == raw for name, raw in files.items()),
            "frozen packet file changed")
    return packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("prepare")
    p.add_argument("--source-root", type=Path, default=SOURCE)
    p.add_argument("--output-root", type=Path, required=True)
    v = commands.add_parser("validate")
    v.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    packet = (prepare(args.source_root, args.output_root) if args.command == "prepare"
              else validate(args.root))
    print(wire({"status": packet["status"], "metrics": packet["metrics"],
                "boundaries": packet["boundaries"]}).decode())


if __name__ == "__main__":
    main()
