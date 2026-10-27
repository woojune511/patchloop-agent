"""Saved-A public-feedback continuation with partial versus complete current source.

Preparation/validation are offline. Collection has two single-use rows, exact
manifest/cap admission, and independent public/opaque verification after one edit.
"""
from __future__ import annotations

import argparse
import copy
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from diagnostics import exception_frame_repair as loop
from diagnostics import selection_observation as host
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import disjoint
from diagnostics.source_ready_packet import _read_workspace
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import PublicTask, TaskEnvironment
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.contracts import DevLimits
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas
from patchloop.git_execution import run_git
from patchloop.prepared_probe_dependencies import load_dependencies, read_descriptor
from patchloop.prepared_source import load_source
from patchloop.repository import WorkspaceManager
from patchloop.runtime import (
    git_commit,
    repository_root,
    runtime_content_hash,
    runtime_content_paths,
)
from patchloop.sandbox import DockerSandbox
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.util import canonical_json, load_unique_yaml, sha256_bytes, sha256_json

SCHEMA = "feedback-source-pair-v1"
PROFILE = loop.RepairProfile(SCHEMA, ("R0", "R1"), 8, Decimal("1.20"),
                             reserve_opportunity=True, annotation_policy="thin")
SEED_HASH = "sha256:93b024b3f11ef89311d9cbf5a06a56328b14f7b7d7687746e6d24a8b9fb8e3e5"
FILE_HASH = "sha256:7728b5200cd0049919dbeeb049a7fafa6f83b2063acd7d5f6044ca8f9313bb46"
PACKET_BUILDER = Path(__file__).with_name("feedback_source_packet.py")
PROMPT = (
    "Repair the supplied public task from the saved candidate. The previous authored "
    "hypothesis is unverified; the supplied public observations describe that candidate. "
    "Current source spans are registered edit anchors. You may inspect further source "
    "with the same offered tools. You have at most eight normal responses, one protocol "
    "correction, twelve model tool actions, one diagnostic probe request and one additional "
    "accepted source edit. Stop if no justified edit is available. A successful replace_text "
    "ends this model phase. The host then checks the original caller, public controls, "
    "regression and isolated acceptance. These later results are not fed back to this "
    "conversation. Use only the offered tools; no shell or dependency installation."
)


def request_payload(common, arm, *, history=(), remaining=None, correction=None,
                    probe_used=False, profile=PROFILE, source_packet=None, opportunity=None):
    require(profile == PROFILE and arm in PROFILE.order and source_packet is None,
            "unexpected feedback/source profile")
    remaining = remaining if remaining is not None else {
        "normal_calls": PROFILE.normal_calls, "tool_actions": loop.TOOL_ACTIONS,
        "diagnostic_probes": 1, "accepted_mutations": 1,
        "cost_nanos": int(PROFILE.row_cap * 1_000_000_000)}
    opportunity = opportunity or loop.repair_opportunity(
        normal_remaining=remaining["normal_calls"], tool_remaining=remaining["tool_actions"],
        probe_used=probe_used, correction=correction is not None)
    items = [{"role": "system", "content": PROMPT},
             {"role": "user", "content": canonical_json({
                 "public_feedback": common["feedback"],
                 "current_source": common["source_packets"][arm]})}, *copy.deepcopy(history),
             {"role": "developer", "content": canonical_json({
                 "remaining": remaining, "protocol_correction": correction,
                 "opportunity": opportunity.public()})}]
    schemas = dev_tool_schemas(finish_enabled=False, allowed_tools=opportunity.allowed,
        probe_environment=common.get("probe_environment"), agent_policy="thin",
        read_range_only=True)
    adapter = loop.OpenAIResponsesAdapter(loop.config(), api_key="",
                                          client=SimpleNamespace(max_retries=0))
    payload = adapter.request_payload(items, schemas, system_prompt=PROMPT)
    payload["max_output_tokens"] = loop.CORRECTION_OUTPUT if correction else loop.NORMAL_OUTPUT
    return payload


def verify_pair(r0, r1):
    requests = copy.deepcopy([r0, r1])
    sources = []
    for request in requests:
        data = json.loads(request["input"][1]["content"])
        sources.append(data.pop("current_source"))
        request["input"][1]["content"] = canonical_json(data)
    require(sources[0] != sources[1] and requests[0] == requests[1],
            "requests differ beyond the assigned current source")


def file_binding(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return {"path": str(path), "hash": sha256_bytes(raw), "bytes": len(raw)}


def build_packet_bundle():
    from diagnostics.feedback_source_packet import build_packet_bundle as build

    return build()


def validate_bundle(bundle):
    require(set(bundle) == {"common", "source_packets", "seed_patch", "input_bindings",
                            "provenance"}, "unexpected bundle fields")
    require(sha256_bytes(bundle["seed_patch"].encode()) == SEED_HASH
            and canonical_json(bundle["seed_patch"]) in canonical_json(bundle["common"]),
            "saved patch changed or missing from common feedback")
    require(bundle["provenance"]["candidate_diff_hash"] == SEED_HASH,
            "source candidate differs")
    packets = bundle["source_packets"]
    require(set(packets) == set(PROFILE.order), "source arms differ")
    for arm, ranges in (("R0", [(265, 273)]), ("R1", [(1, 400), (401, 676)])):
        require(len(packets[arm]) == len(ranges), "source range count differs")
        for span, (start, end) in zip(packets[arm], ranges, strict=True):
            require(set(span) == {"path", "start_line", "end_line", "content", "file_hash"}
                    and span["path"] == "astroid/modutils.py"
                    and (span["start_line"], span["end_line"]) == (start, end)
                    and span["file_hash"] == FILE_HASH
                    and len(span["content"].split("\n")) == end - start + 1
                    and len(span["content"]) <= 24_000,
                    "source span is incomplete or has changed identity")
    full = "\n".join(span["content"] for span in packets["R1"]).split("\n")
    require(packets["R0"][0]["content"] == "\n".join(full[264:273]),
            "partial and complete packets differ on the same current lines")
    for binding in bundle["input_bindings"]:
        require(file_binding(binding["path"]) == binding, "public bundle input changed")


def load_inputs():
    bundle = build_packet_bundle()
    validate_bundle(bundle)
    public = PublicTask.model_validate(load_unique_yaml(host.PUBLIC.read_text("utf-8")))
    require(public.split == "dev-train", "only dev-train tasks allowed")
    environment = TaskEnvironment.model_validate(load_unique_yaml(
        host.PUBLIC.with_name("environment.yaml").read_text("utf-8")))
    load_source(host.SOURCE, public.repository.url, public.repository.base_commit,
                expected_hash=host.SOURCE_HASH)
    require(sha256_bytes(host.DEPENDENCIES.read_bytes()) == host.DEPENDENCY_HASH,
            "dependency descriptor changed")
    dependencies = load_dependencies(host.DEPENDENCIES, public,
                                     read_descriptor(host.DEPENDENCIES)[1])
    provenance = bundle["provenance"]
    require(Path(provenance["public_task_path"]).resolve() == host.PUBLIC.resolve()
            and provenance["public_hash"] == sha256_bytes(host.PUBLIC.read_bytes())
            and Path(provenance["prepared_source_path"]).resolve() == host.SOURCE.resolve()
            and provenance["prepared_source_hash"] == host.SOURCE_HASH,
            "bundle task or prepared source differs")
    original = copy.deepcopy(provenance["original_arguments"])
    require(type(original) is dict, "original public request is unavailable")
    require(sha256_bytes(host.CALIBRATION.read_bytes()) == host.CALIBRATION_HASH
            and original == json.loads(host.CALIBRATION.read_bytes())["original_arguments"],
            "original host request differs from the frozen public program")
    common = {"feedback": {**bundle["common"], "public_task": public.model_dump(mode="json")},
              "source_packets": bundle["source_packets"],
              "probe_environment": dependencies.environment}
    requests = {arm: request_payload(common, arm) for arm in PROFILE.order}
    verify_pair(requests["R0"], requests["R1"])
    return SimpleNamespace(public=public, environment=environment, dependencies=dependencies,
                           bundle=bundle, common=common, requests=requests,
                           original_arguments=original)


def scope():
    return {**host.scope(), "order": list(PROFILE.order), "starting_diff": SEED_HASH,
            "source_ranges": {"R0": [[265, 273]], "R1": [[1, 400], [401, 676]]},
            "read_range_only": True, "additional_model_edits": 1,
            "host_source_reads": {"R0": 1, "R1": 2}}


def prepare(output, result_root, credential_file):
    output, result_root = output.resolve(), result_root.resolve()
    protected = (repository_root(), host.SOURCE.parent, host.DEPENDENCIES.parent)
    disjoint(output, (*protected, result_root))
    disjoint(result_root, (*protected, output))
    require(not result_root.exists(), "result root already exists")
    loaded = load_inputs()
    paths = [Path(__file__), Path(loop.__file__), Path(host.__file__), PACKET_BUILDER,
             Path(__file__).with_name("source_ready_packet.py"), host.HELPER,
             Path(__file__).with_name("saved_candidate_acceptance.py"), host.PUBLIC,
             host.PUBLIC.with_name("environment.yaml"), host.SOURCE, host.DEPENDENCIES,
             host.CALIBRATION]
    paths.extend(Path(row["path"]) for row in loaded.bundle["input_bindings"])
    bindings = [file_binding(path) for path in dict.fromkeys(paths)]
    # Preserve every historical input directory; generated output must be elsewhere.
    for root in (output, result_root):
        disjoint(root, tuple(Path(row["path"]).parent for row in bindings))
    plan = {"schema": SCHEMA, "official": False, "paid_execution_authorized": False,
            "runtime_hash": runtime_content_hash(), "prepared_at_commit": git_commit(),
            "scope": scope(), "result_root": str(result_root),
            "credential_file": str(credential_file.resolve()), "bindings": bindings,
            "bundle_hash": sha256_json(loaded.bundle),
            "first_request_hashes": {arm: sha256_json(request)
                                     for arm, request in loaded.requests.items()},
            "interpretation": "Assisted saved-candidate continuation, one run per condition. "
                "Compares current source content, acquisition burden and editable-anchor coverage "
                "under identical public feedback and opportunities. Not fresh solve, literal "
                "conversation resume, feedback-only effect or general agent-quality evidence."}
    output.mkdir()
    files = {"packet-bundle": loaded.bundle, "manifest": plan,
             **{arm + "-first": value for arm, value in loaded.requests.items()}}
    for name, value in files.items():
        with (output / f"{name}.json").open("x", encoding="utf-8") as stream:
            stream.write(canonical_json(value) + "\n")
    receipt = {"manifest": str(output / "manifest.json"),
               "manifest_hash": sha256_bytes((output / "manifest.json").read_bytes()),
               "provider_calls": 0, "credential_reads": 0, "input_count_calls": 0,
               "target_executions": 0, "acceptance": "NOT_RUN"}
    DevJournal(output, "run_dev_feedbacksourcepreparation").append("prepared", receipt)
    return receipt


def validate(manifest, digest):
    require(sha256_bytes(manifest.read_bytes()) == digest, "approved manifest hash differs")
    plan = json.loads(manifest.read_bytes())
    require(plan["schema"] == SCHEMA and plan["scope"] == scope(), "comparison scope changed")
    require(plan["runtime_hash"] == runtime_content_hash(), "runtime changed")
    for binding in plan["bindings"]:
        require(file_binding(binding["path"]) == binding, "bound code or evidence changed")
    loaded = load_inputs()
    require(sha256_json(loaded.bundle) == plan["bundle_hash"]
            and json.loads((manifest.parent / "packet-bundle.json").read_bytes()) == loaded.bundle,
            "prepared packet bundle changed")
    for arm, request in loaded.requests.items():
        require(sha256_json(request) == plan["first_request_hashes"][arm]
                and json.loads((manifest.parent / f"{arm}-first.json").read_bytes()) == request,
                "prepared request changed")
    return plan, loaded


def observe_sources(gateway, spans):
    require(gateway.current_diff_hash == SEED_HASH, "source registration candidate differs")
    for span in spans:
        observed = _read_workspace(gateway, span, SEED_HASH)
        observed.pop("origin")
        require(observed == span, "registered source differs from delivered source")
    require(gateway.current_diff_hash == SEED_HASH and gateway.accepted_mutations == 0,
            "source registration mutated the saved candidate")


def saved_gateway(loaded, root, arm):
    require(arm in PROFILE.order, "unknown continuation arm")
    setup_deadline = ExecutionDeadline.from_remaining(loop.MODEL_SECONDS)
    workspace = WorkspaceManager(repository_root() / "fixtures/repositories", root / "workspaces",
        prepared_source=host.SOURCE, prepared_source_hash=host.SOURCE_HASH).create(
            "saved", loaded.public.repository.url, loaded.public.repository.base_commit,
            deadline=setup_deadline)
    require(WorkspaceManager.diff_summary(workspace).patch_hash == host.EMPTY_DIFF,
            "restoration base is not clean")
    # Prepared task bytes are authoritative; Windows global checkout conversion
    # must not rewrite the saved LF postimage while applying an identical patch.
    run_git(workspace, "config", "core.autocrlf", "false", deadline=setup_deadline)
    patch = ArtifactStore(root / "artifacts").put_text(loaded.bundle["seed_patch"], "text/x-diff")
    require(patch.content_hash == SEED_HASH, "saved patch artifact changed")
    WorkspaceManager.apply_patch(workspace, patch.path, deadline=setup_deadline)
    diff = WorkspaceManager.diff_summary(workspace, deadline=setup_deadline)
    require(diff.patch_hash == SEED_HASH and not diff.untracked_files, "saved candidate changed")
    probe = DockerProbeSandbox(dependencies=loaded.dependencies)
    identity = probe.preflight(deadline=setup_deadline)
    require(identity["image_digest"] == host.PROBE_IMAGE
            and identity["profile_hash"] == host.PROBE_PROFILE
            and loaded.dependencies.identity.manifest_hash == host.DEPENDENCY_HASH,
            "probe identity changed")
    sandbox = DockerSandbox(loaded.environment.evaluator_image)
    require(sandbox.image_identity(deadline=setup_deadline) == loaded.environment.image_digest,
            "public regression image changed or missing")
    journal = DevJournal(root, "run_dev_feedbacksourcemodel")
    journal.append("saved_candidate_restored", {"candidate_diff_hash": SEED_HASH,
        "source_artifact": patch.model_dump(mode="json"), "model_mutation": False,
        "historical_actions_imported": False, "prepared_source_hash": host.SOURCE_HASH,
        "probe_identity": identity})
    spans = loaded.bundle["source_packets"][arm]
    gateway = DevToolGateway(workspace=workspace, public_task=loaded.public, sandbox=sandbox,
        probe_sandbox=probe, journal=journal, agent_policy="thin", read_range_only=True,
        limits=DevLimits(max_accepted_mutations=1, max_model_calls=9,
                         max_tool_actions=loop.TOOL_ACTIONS + len(spans)), deadline=setup_deadline)
    observe_sources(gateway, spans)
    journal.append("model_stage_ready", {"candidate_diff_hash": SEED_HASH,
        "host_source_reads": len(spans), "model_tool_allowance": loop.TOOL_ACTIONS,
        "source_packet_hash": sha256_json(spans), "read_range_only": True})
    gateway.deadline = ExecutionDeadline.from_remaining(loop.MODEL_SECONDS)
    return gateway


def acceptance(gateway, root, passed):
    """A settled return to clean base is no repair, not evaluator uncertainty."""
    if gateway.current_diff_hash == host.EMPTY_DIFF:
        return {"official": False, "status": "NOT_RUN_NO_DIFF", "acceptance": "not_run",
                "candidate_patch_hash": host.EMPTY_DIFF, "evaluator_dispatches": 0,
                "scope_compliant_success": False, "stop_remaining": False}
    return host.acceptance(gateway, root, passed)


def collect(manifest, approved_manifest_hash, approved_cap_usd):
    require(approved_cap_usd == PROFILE.invocation_cap, "exact new cap approval required")
    plan, loaded = validate(manifest, approved_manifest_hash)
    root = Path(plan["result_root"])
    disjoint(root, (repository_root(), manifest.parent,
                    host.SOURCE.parent, host.DEPENDENCIES.parent,
                    *(Path(row["path"]).parent for row in plan["bindings"])))
    relative = [Path(row["path"]).relative_to(repository_root()).as_posix()
                for row in plan["bindings"] if Path(row["path"]).is_relative_to(repository_root())]
    loop.runner._require_tracked_clean_paths(repository_root(),
                                             [*runtime_content_paths(), *relative])
    root.mkdir()
    journal = DevJournal(root, "run_dev_feedbacksourcecomparison")
    journal.append("approved_collection_started", {"manifest_hash": approved_manifest_hash,
        "cap_usd": str(approved_cap_usd), "git_commit": git_commit()})
    group = DevCostLedger(PROFILE.invocation_cap, pricing_for_model(loop.MODEL))
    rows = []
    try:
        for arm in PROFILE.order:
            gateway = saved_gateway(loaded, root / arm, arm)
            key = loop.load_exact_openai_api_key(Path(plan["credential_file"]))
            adapter = loop.OpenAIResponsesAdapter(loop.config(), api_key=key)
            del key
            try:
                row = loop.run_model(loaded, arm, gateway, adapter, group,
                    first_hash=plan["first_request_hashes"][arm], profile=PROFILE,
                    request_builder=request_payload)
            finally:
                adapter.client.close()
            rows.append({"arm": arm, **row})
            journal.append("model_row_finished", rows[-1])
            if row["stop_remaining"]:
                break
            if row["terminal"] == "CANDIDATE_PRODUCED":
                checks = host.public_checks(loaded, gateway, root / arm / "public")
                rows[-1]["public_checks"] = checks
                journal.append("candidate_ready_for_evaluation", {"arm": arm, **checks})
                rows[-1]["acceptance"] = acceptance(
                    gateway, root / arm / "acceptance", checks["regression_passed"])
                rows[-1]["task_acceptance"] = rows[-1]["acceptance"].get("acceptance", "not_run")
            journal.append("row_finished", rows[-1])
    except BaseException as exc:
        journal.append("collection_interrupted", {"error_type": type(exc).__name__,
                                                   "resume_allowed": False})
        raise
    result = {"official": False, "rows": rows, "cost_nanos": group.spent_nanos,
              "interpretation": plan["interpretation"], "allocation_closed": True}
    (root / "result.json").write_text(canonical_json(result) + "\n", encoding="utf-8")
    journal.append("closed", {"artifact": ArtifactStore(root / "artifacts")
                             .put_json(result).model_dump(mode="json")})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    for name in ("output", "result-root", "credential-file"):
        prep.add_argument("--" + name, type=Path, required=True)
    for name in ("validate", "collect"):
        command = commands.add_parser(name)
        command.add_argument("--manifest", type=Path, required=True)
        command.add_argument("--approved-manifest-hash", required=True)
        if name == "collect":
            command.add_argument("--approved-cap-usd", type=Decimal, required=True)
    args = vars(parser.parse_args())
    name = args.pop("command")
    if name == "validate":
        validate(args["manifest"], args["approved_manifest_hash"])
        result = {"status": "VALIDATED_OFFLINE", "provider_calls": 0}
    else:
        result = globals()[name](**args)
    print(canonical_json(result))


if __name__ == "__main__":
    main()
