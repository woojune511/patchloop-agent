"""Offline preparation and immutable admission for the verification-state A/B."""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import xml.etree.ElementTree as ET
from contextlib import suppress
from pathlib import Path
from unittest.mock import patch

from diagnostics import caller_uptake as prior
from diagnostics import caller_uptake_grading, portfolio_dev20, probe_recheck_panel
from diagnostics import verification_state_off as off
from diagnostics.positive_verification_panel import require, save
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.dev import reproduction, runner, segments, thin_policy
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.conversation import STATE_KIND, reconstruct_state, segment_seed
from patchloop.dev.state import DevJournal
from patchloop.runtime import (
    git_commit,
    repository_root,
    runtime_content_hash,
    runtime_content_paths,
)
from patchloop.task_loader import load_public_task
from patchloop.util import canonical_json, sha256_json

MODEL, TASK, ORDER = prior.MODEL, prior.TASK, prior.ORDER
ROW_CAP, ARM_CAP, CAP = prior.ROW_CAP, prior.ARM_CAP, prior.CAP
SPEC = ".agent/plans/verification-state-comparison.md"
REDUCED_SPEC = ".agent/plans/verification-state-reduced-comparison.md"
DEPENDENCIES = Path("C:/pt/calleruptake18/preparation-v2/B/prepared-probe-dependencies.json")
JOURNAL = "run_dev_verificationstate43"


def allocation(repeat_per_arm):
    require(type(repeat_per_arm) is int and repeat_per_arm in (3, 6),
            "fixed three- or six-per-arm allocation required")
    return {
        "repeat_per_arm": repeat_per_arm, "order": list(ORDER[:2 * repeat_per_arm]),
        "row_cap_usd": str(ROW_CAP), "arm_cap_usd": str(ROW_CAP * repeat_per_arm),
        "total_cap_usd": str(ROW_CAP * repeat_per_arm * 2),
    }


def request(live, label):
    value = prior.request(DEPENDENCIES.parent.parent, live, label).model_dump(mode="json")
    value.update(history_search_policy="public-v1",
                 prepared_probe_dependencies=str(DEPENDENCIES))
    return DevRunRequest.model_validate(value)


def bindings():
    repo = repository_root()
    paths = [SPEC, REDUCED_SPEC, "tests/test_verification_state_comparison.py",
             "tests/test_verification_state_grading.py", "tests/quick.txt"]
    paths += [p.relative_to(repo).as_posix() for p in (repo / "diagnostics").rglob("*.py")]
    return {name: prior.file_ref(repo / name)["hash"] for name in sorted(paths)}


def identity(live):
    repo = repository_root()
    runner._require_tracked_clean_paths(repo, runtime_content_paths() + list(bindings()))
    require(not subprocess.check_output(
        ["git", "diff", off.BASE, "--name-only", "--", "patchloop", "tasks", "pyproject.toml",
         "uv.lock", "docker"], cwd=repo, text=True).strip(), "common product runtime changed")
    req = request(live, ORDER[0])
    package, _, _, environment = probe_recheck_panel.environment(req)
    runner._live_source_preflight(req.task.parent, package)
    require(prior.invariants()["references"] == 2, "reference limit changed")
    return {
        "head": git_commit(), "runtime_hash": runtime_content_hash(),
        "implementation": bindings(), "invariants": prior.invariants(),
        "environment": environment, "public_hash": package.public_spec_hash,
        "task_hash": package.task_content_hash, "source": prior.file_ref(prior.SOURCE),
        "dependencies": prior.file_ref(DEPENDENCIES),
        "native_identity": portfolio_dev20.native_identity(), "native_input": prior.native_input(),
        "pricing": portfolio_dev20.price(), "prompts": off.PROMPT_HASHES,
    }


class Captured(BaseException):
    pass


def capture(root, arm):
    req = request(root / "capture", arm + "-r1-t13")
    require(not req.state_root.exists(), "capture must be fresh")
    wires = []

    class Capture(OpenAIResponsesAdapter):
        def __init__(self, config, *, api_key):
            self.config = config

        def request_payload(self, *args, **kwargs):
            wires.append(super().request_payload(*args, **kwargs))
            raise Captured

        def count_input_tokens_v2(self, *args, **kwargs):
            raise AssertionError("offline capture cannot count tokens")

        def execute_request(self, *args, **kwargs):
            raise AssertionError("offline capture cannot dispatch")

    with (off.assigned(arm),
          patch.object(runner, "OpenAIResponsesAdapter", Capture),
          patch.object(runner, "load_exact_openai_api_key", return_value="offline-unused"),
          patch.object(runner, "monotonic", return_value=10000.0), suppress(Captured)):
        runner.run_dev(req)
    require(len(wires) == 1, "capture exactly one request")
    journal_path, = (req.state_root / "runs").glob("*.jsonl")
    events = DevJournal(req.state_root, journal_path.stem).events()
    require(not any(e["event_type"] in {"provider_call_started", "input_count_started"}
                    for e in events), "provider operation during capture")
    for event in events:
        if event["event_type"] in {segments.EVENT, segments.PREPARED_EVENT}:
            segments.load_binding(event["payload"], ArtifactStore(req.state_root / "artifacts"))
    workspace, = (req.state_root / "workspaces").glob("*/repo")
    require(not subprocess.check_output(
        ["git", "-C", str(workspace), "status", "--porcelain"], text=True).strip(),
        "capture changed public source")
    save(root, "initial-" + arm + ".json", wires[0])
    return wires[0]


def normalize_initial(wire):
    value = copy.deepcopy(wire)
    state = reconstruct_state(value["input"], context_policy="segmented-v1")
    require(not state["current_diff"]["patch"], "initial input has an edit")
    segment = state["segment_handoff"]["segment_id"]

    def transform(item):
        if isinstance(item, str):
            if item == segment:
                return "<derived-segment-id>"
            try:
                parsed = json.loads(item)
            except (ValueError, TypeError):
                return item
            return transform(parsed) if isinstance(parsed, (dict, list)) else item
        if isinstance(item, list):
            return [transform(v) for v in item]
        if isinstance(item, dict):
            return {k: transform(v) for k, v in item.items()}
        return item
    return transform(value)


def initial_pair(wires):
    left, right = (normalize_initial(wires[arm]) for arm in "AB")
    expected = copy.deepcopy(left)
    a_state = reconstruct_state(wires["A"]["input"], context_policy="segmented-v1")
    b_state = reconstruct_state(wires["B"]["input"], context_policy="segmented-v1")
    prompts = {}
    for arm in "AB":
        with off.assigned(arm):
            prompts[arm] = segment_seed(thin_policy.system_prompt(
                "current", "brief-v1", history_search_policy="public-v1"),
                a_state["public_task"])[0]["content"]
    require(left["input"][0]["content"] == prompts["A"], "control prompt differs")
    expected["input"][0]["content"] = prompts["B"]
    public = load_public_task(repository_root() / TASK)
    require(a_state["public_task"] == b_state["public_task"] == public.model_dump(mode="json"),
            "initial public task changed")
    require(a_state["reproduction_review"] == off.legacy_review(
        [], a_state["current_diff"]["patch_hash"]),
            "control initial review differs")
    review = reproduction.review([], b_state["current_diff"]["patch_hash"], public_task=public)
    require(b_state["reproduction_review"] == review, "treatment initial review differs")
    paths = ["/input/0/content"]
    for index, item in enumerate(expected["input"]):
        frame = item.get("content")
        if isinstance(frame, dict) and frame.get("kind") == STATE_KIND:
            frame["state"]["reproduction_review"] = review
            paths.append(f"/input/{index}/content/state/reproduction_review")
            verification = frame["state"].get("working_notes", {}).get("verification")
            if verification is not None:
                require(verification["items"] == [] and verification["unresolved_ids"] == [],
                        "initial concerns are not empty")
                verification["model_open_concern_ids"] = verification.pop("unresolved_ids")
                paths.append(f"/input/{index}/content/state/working_notes/verification/"
                             "unresolved_ids->model_open_concern_ids")
    require(expected == right, "unexpected complete initial request difference")
    return {"allowed_paths": paths, "derived_segment_ids_checked": True,
            "wire_bytes": {a: len(canonical_json(w).encode()) for a, w in wires.items()},
            "tools_equal": wires["A"]["tools"] == wires["B"]["tools"]}


def xml_receipt(path, *, full=False):
    cases = list(ET.parse(path).iter("testcase"))
    failed = [c for c in cases if c.find("failure") is not None or c.find("error") is not None]
    skipped = [c for c in cases if c.find("skipped") is not None]
    require(cases and not failed, "validation failed or empty: " + str(path))
    if full:
        baseline = ET.parse("C:/pt/regression-contract40/full-final2.xml")
        def skip_ids(values):
            return {(c.attrib["classname"], c.attrib["name"], c.find("skipped").get("message"))
                    for c in values if c.find("skipped") is not None}
        require(skip_ids(cases) == skip_ids(baseline.iter("testcase")), "skip set changed")
        require(len(cases) - len(skipped) >= 5463, "full suite shrank")
    else:
        require(not skipped, "selected validation skipped")
    return {"file": prior.file_ref(path), "passed": len(cases) - len(skipped),
            "skipped": len(skipped), "failed": 0}


def freeze(root, live, validation, *, repeat_per_arm=6):
    assigned = allocation(repeat_per_arm)
    require(not (root / "manifest.json").exists() and not live.exists(), "fresh allocation")
    require(not root.resolve().is_relative_to(repository_root())
            and not live.resolve().is_relative_to(repository_root()), "external state required")
    value = json.loads(validation.read_bytes())
    current = identity(live)
    require(value["head"] == current["head"] and value["runtime_hash"] == current["runtime_hash"]
            and value["implementation"] == current["implementation"], "not final-commit validation")
    require(value["provider_calls"] == value["input_count_calls"] == 0,
            "offline validation required")
    for ref in value["files"]:
        prior.read_ref(ref)
    checks = {name: xml_receipt(Path(value["xml"][name]), full=name == "full")
              for name in ("focused", "quick-A", "quick-B", "full")}
    wires = {a: json.loads((root / f"initial-{a}.json").read_bytes()) for a in "AB"}
    pair = initial_pair(wires)
    programs = {case: prior.file_ref(Path(
        "C:/pt/analyses/astroid-prepared-caller-20261018-v1") / f"program-{case}.py")
        for case in ("missing", "present")}
    require(all(programs[k]["hash"] == caller_uptake_grading.PROGRAMS[k] for k in programs),
            "caller oracle changed")
    packet = {
        "schema": "verification-state-comparison-v2", **current, **assigned,
        "specification": prior.file_ref(repository_root() / (
            REDUCED_SPEC if repeat_per_arm == 3 else SPEC)),
        "paid_authorized": False, "official": False, "claim_eligible": False,
        "live_root": str(live.resolve()), "model": MODEL,
        "credential_file": str(repository_root() / ".env"),
        "rows": [{"row_id": label, "arm": label[0],
                  "public_id": "case-" + sha256_json({"head": current["head"], "row": label})[-12:],
                  "request": request(live, label).model_dump(mode="json")}
                 for label in assigned["order"]],
        "programs": programs, "initial_difference": pair, "checks": checks,
        "validation": prior.file_ref(validation), "files": value["files"],
        "initial": {a: prior.file_ref(root / f"initial-{a}.json") for a in "AB"},
        "fresh_price_review_required_at_dispatch": True,
        "no_retry_resume_transfer_replacement": True, "audit_before_grades": True,
        "preexisting_guidance": prior.file_ref(repository_root() / "AGENTS.md"),
        "environments": {a: {"dependencies": current["dependencies"]} for a in "AB"},
    }
    save(root, "manifest.json", packet)
    DevJournal(root, JOURNAL).append("packet_frozen", {
        "manifest_hash": sha256_json(packet), "paid_authorized": False,
        "validation": packet["validation"], "checks": checks,
    })
    return packet


def validate(root, digest):
    packet = json.loads((root / "manifest.json").read_bytes())
    require(sha256_json(packet) == digest and packet["paid_authorized"] is False,
            "manifest identity or authorization changed")
    assigned = allocation(packet["repeat_per_arm"])
    require(packet["schema"] == "verification-state-comparison-v2"
            and all(packet[k] == v for k, v in assigned.items()),
            "allocation order/caps changed")
    require(packet["specification"] == prior.file_ref(repository_root() / (
        REDUCED_SPEC if packet["repeat_per_arm"] == 3 else SPEC)), "specification changed")
    current = identity(Path(packet["live_root"]))
    require(all(packet[k] == v for k, v in current.items()), "runtime/environment changed")
    for ref in [packet["validation"], packet["preexisting_guidance"],
                *packet["files"], *packet["initial"].values(), *packet["programs"].values()]:
        prior.read_ref(ref)
    expected = [{"row_id": label, "arm": label[0],
                 "public_id": "case-" + sha256_json({"head": current["head"], "row": label})[-12:],
                 "request": request(Path(packet["live_root"]), label).model_dump(mode="json")}
                for label in assigned["order"]]
    require(packet["rows"] == expected, "roster changed")
    return packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("capture", "freeze", "validate"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--arm", choices=("A", "B"))
    parser.add_argument("--live", type=Path)
    parser.add_argument("--validation", type=Path)
    parser.add_argument("--hash")
    parser.add_argument("--repeat-per-arm", type=int, choices=(3, 6), default=6)
    args = parser.parse_args()
    if args.mode == "capture":
        capture(args.root, args.arm)
        print("offline capture saved")
        return
    packet = (freeze(args.root, args.live, args.validation, repeat_per_arm=args.repeat_per_arm)
              if args.mode == "freeze"
              else validate(args.root, args.hash))
    print(canonical_json({"manifest_hash": sha256_json(packet), "head": packet["head"],
                          "paid_authorized": False}))


if __name__ == "__main__":
    main()
