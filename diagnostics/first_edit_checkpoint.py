"""Fresh first-edit trials from the same saved public post-helper evidence.

A retains duplicate public context; B encodes the same facts once with references.
Preparation is offline. Collection needs an exact new manifest and total cap.
"""
from __future__ import annotations

import argparse
import copy
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from diagnostics import checkpoint_delivery as delivery
from diagnostics import feedback_source as source
from diagnostics import first_edit_checkpoint_source as checkpoint_source
from diagnostics import public_context_dedup as dedup
from diagnostics import repair_cycle_tools
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import disjoint
from diagnostics.public_regression import PublicRegressionRecheck
from diagnostics.repair_cycle import OriginalCallRecheck
from diagnostics.repair_cycle_budget import CycleLimits, regression_opportunity
from diagnostics.repair_cycle_context import HANDOFF_KIND
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.conversation import SEGMENT_RULES
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.native_sources import PUBLIC_EVIDENCE_KIND, public_exchanges
from patchloop.dev.state import DevJournal
from patchloop.runtime import (
    git_commit,
    repository_root,
    runtime_content_hash,
    runtime_content_paths,
)
from patchloop.util import canonical_json, sha256_bytes, sha256_json

loop = source.loop
SCHEMA = "first-edit-checkpoint-pair-v1"
PROFILE = loop.RepairProfile(SCHEMA, ("A", "B"), 4, Decimal("1.20"),
                             reserve_opportunity=True, annotation_policy="thin")
LIMITS = CycleLimits(model_tools=5, helper_probes=0, original_requests=0, accepted_edits=2,
                     future_edit_output=40_000, final_response_output=8_192)
MODEL_SECONDS = 1_200
MINIMUM_CORRECTION_SECONDS = 30.0
PROMPT = (
    "Repair the supplied public task from the saved candidate using the saved public evidence. "
    "This is a new trial with four normal responses, one protocol correction, five model tool "
    "actions and at most two accepted source edits. The supplied source lines have been checked "
    "against this restored candidate and registered as edit anchors. Use replace_text for a "
    "justified edit or stop_task if no justified edit is available. After an accepted edit the "
    "host rechecks the original public caller and registered public regression checks before "
    "the next response. If either fails, use the bounded read/search opportunity and one further "
    "edit to address that evidence, then both checks run again. Once both pass, stop. If repair "
    "or verification cannot finish within the remaining allowance, report the unresolved result. "
    "Final public controls and isolated evaluation follow. Private evaluator details "
    "are never model inputs. Saved observations and authored hypotheses describe the earlier "
    "candidate; hypotheses are unverified. Saved action IDs are evidence, not pending actions "
    "or authorization to repeat them. Current-trial counters and results are supplied separately. "
    "A public-context-dedup-v1 object represents the same evidence: start at document, follow "
    "$ref in definitions and $source with its line range in sources. Source content is printed "
    "once; references do not add or select repair advice. Use only the offered tools."
)


def evidence_document(checkpoint):
    bodies = copy.deepcopy(checkpoint.bodies)
    state = bodies[1]["state"]
    # Historical resource counters are not new-run allowances. Both arms receive
    # identical fresh counters outside the frozen task/evidence document.
    state.pop("counters")
    state.pop("protocol_correction")
    bodies[1]["kind"] = "saved_public_checkpoint_state_v1"
    bodies[1]["instructions"] = (
        "Saved public evidence for the starting candidate. This is not live current-trial "
        "state; new budgets, tool receipts and original-call results are supplied separately.")
    return {"saved_public_evidence": bodies}


def request_payload(common, arm, *, history=(), remaining=None, correction=None,
                    probe_used=False, profile=PROFILE, source_packet=None, opportunity=None,
                    original_feedback=None, public_regression_feedback=None):
    del probe_used
    require(profile == PROFILE and arm in PROFILE.order and source_packet is None,
            "unexpected first-edit checkpoint profile")
    remaining = remaining if remaining is not None else {
        "normal_calls": PROFILE.normal_calls, "tool_actions": LIMITS.model_tools,
        "diagnostic_probes": 0, "original_rechecks": 0,
        "accepted_mutations": LIMITS.accepted_edits,
        "cost_nanos": int(PROFILE.row_cap * 1_000_000_000)}
    opportunity = opportunity or regression_opportunity(
        original_feedback=original_feedback, regression_feedback=public_regression_feedback,
        initial=remaining["accepted_mutations"] == LIMITS.accepted_edits,
        normal_remaining=remaining["normal_calls"], tool_remaining=remaining["tool_actions"],
        probes_remaining=0, original_remaining=0,
        edits_remaining=remaining["accepted_mutations"], correction=correction is not None,
        limits=LIMITS)
    require(opportunity.allowed <= {"replace_text", "stop_task", "read_file", "search_files"},
            "checkpoint revision cannot introduce helper execution")
    evidence = common["evidence"]
    # Both conditions keep completed public exchanges. Opaque generation state is
    # archived by the runner but never redispatched in this new diagnostic profile.
    exchanges = delivery.project_exchanges(evidence, list(
        public_exchanges(history, archive_kind=PUBLIC_EVIDENCE_KIND)))
    handoff = None
    for item in history:
        if item.get("role") != "developer":
            continue
        try:
            record = json.loads(item["content"])
        except (KeyError, TypeError, ValueError):
            continue
        if isinstance(record, dict) and record.get("kind") == HANDOFF_KIND:
            handoff = record
    encoded = evidence if arm == "A" else common["deduplicated_evidence"]
    if handoff is not None:
        # The boundary applies equally to both arms. Keep the frozen observations,
        # actually consume fresh state, and deduplicate the whole public document.
        structured = copy.deepcopy(exchanges)
        for item in structured:
            if item.get("type") == "function_call_output":
                item["output"] = json.loads(item["output"])
        encoded = dedup.deduplicate({**evidence, "current_handoff": handoff,
                                    "completed_public_exchanges": structured})
    items = [{"role": "system", "content": PROMPT},
             {"role": "user", "content": canonical_json(encoded)}]
    if exchanges and handoff is None:
        items.append(SEGMENT_RULES.archive(exchanges=exchanges))
    items.append({"role": "developer", "content": canonical_json({
        "remaining": remaining, "protocol_correction": correction,
        **({"source_delivery": delivery.REFERENCE_RULES} if exchanges or handoff else {}),
        "opportunity": opportunity.public(), "current_trial_original_recheck": original_feedback,
        "current_trial_public_regression": public_regression_feedback,
        "verification_reserve": {"original_actions_max": LIMITS.host_original_actions,
            "original_seconds_per_action": LIMITS.original_recheck_seconds,
            "minimum_correction_seconds": MINIMUM_CORRECTION_SECONDS,
            "registered_regression_passes_max": LIMITS.accepted_edits,
            "final_public_seconds": LIMITS.final_public_seconds,
            "isolated_acceptance_seconds": LIMITS.acceptance_seconds}})})
    adapter = loop.OpenAIResponsesAdapter(loop.config(), api_key="",
                                          client=SimpleNamespace(max_retries=0))
    payload = adapter.request_payload(items, repair_cycle_tools.schemas(opportunity,
        dependency_sources=common.get("dependency_sources")),
                                      system_prompt=PROMPT)
    payload["parallel_tool_calls"] = repair_cycle_tools.parallel_calls(opportunity)
    payload["max_output_tokens"] = loop.CORRECTION_OUTPUT if correction else loop.NORMAL_OUTPUT
    return payload


def verify_pair(a, b):
    restored = copy.deepcopy(b)
    restored["input"][1]["content"] = canonical_json(
        dedup.expand(json.loads(restored["input"][1]["content"])))
    require(a == restored, "A/B differs beyond lossless public-context representation")


def load_inputs():
    loaded = source.load_inputs()
    checkpoint = checkpoint_source.load_checkpoint()
    evidence = evidence_document(checkpoint)
    require(evidence["saved_public_evidence"][0]["public_feedback"]["public_task"]
            == loaded.public.model_dump(mode="json"), "checkpoint public task changed")
    encoded = dedup.deduplicate(evidence)
    require(dedup.expand(encoded) == evidence, "deduplication changes public evidence")
    loaded.checkpoint = checkpoint
    loaded.common = {"evidence": evidence, "deduplicated_evidence": encoded,
                     "dependency_sources": loaded.dependency_sources.catalog()}
    loaded.requests = {arm: request_payload(loaded.common, arm) for arm in PROFILE.order}
    verify_pair(loaded.requests["A"], loaded.requests["B"])
    return loaded


def scope(order=PROFILE.order):
    require(tuple(order) in {PROFILE.order, ("A",)}, "unsupported checkpoint selection")
    conditions = {"A": "full-public-context", "B": dedup.FORMAT}
    return {**source.host.scope(), "order": list(order),
        "task": "Astroid-1333/dev-train/current-dev20/13", "starting_diff": source.SEED_HASH,
        "normal_calls": PROFILE.normal_calls, "correction_calls": 1,
        "tool_actions": LIMITS.model_tools, "diagnostic_probes": 0,
        "original_selection_requests": 0, "accepted_mutations": LIMITS.accepted_edits,
        "additional_model_edits": LIMITS.accepted_edits, "post_edit_original_recheck": True,
        "post_edit_public_regression": "registered-checks-before-response-v1",
        "revision_policy": "one-additional-edit-after-public-failure-v1",
        "model_seconds_per_arm": MODEL_SECONDS,
        "followup_output_reserves": [LIMITS.future_diagnostic_output,
                                     LIMITS.future_edit_output, LIMITS.final_response_output],
        "host_original_actions_max": LIMITS.host_original_actions,
        "minimum_correction_seconds": MINIMUM_CORRECTION_SECONDS,
        "row_cap_usd": str(PROFILE.row_cap), "total_cap_usd": str(PROFILE.row_cap * len(order)),
        "conditions": {arm: conditions[arm] for arm in order},
        "checkpoint": "post-helper-before-response-15", "fresh_counters": True,
        "continuation": "public-exchanges-only", "source_selection": "all-unique-evidence",
        "post_edit_delivery": "exact-visible-source-references-v1",
        "context_handoff": "combined-public-state-lossless-v1"}


def prepare(output, result_root, credential_file, arm=None):
    selected_scope = scope(PROFILE.order if arm is None else (arm,))
    order = selected_scope["order"]
    output, result_root = output.resolve(), result_root.resolve()
    loaded = load_inputs()
    paths = [Path(__file__), Path(source.__file__), Path(loop.__file__),
             Path(source.host.__file__), source.PACKET_BUILDER, source.host.HELPER,
             source.host.PUBLIC, source.host.PUBLIC.with_name("environment.yaml"),
             source.host.SOURCE, source.host.DEPENDENCIES, source.host.CALIBRATION]
    paths.extend(Path(__file__).with_name(name + ".py") for name in (
        "first_edit_checkpoint_source", "public_context_dedup", "checkpoint_delivery",
        "repair_cycle",
        "repair_cycle_budget", "repair_cycle_tools", "repair_cycle_context", "public_regression",
        "source_ready_packet", "saved_candidate_acceptance", "decision_sampler",
        "declaration_checkpoint"))
    paths.extend(Path(row["path"]) for row in (
        *loaded.bundle["input_bindings"], *loaded.checkpoint.bindings))
    bindings = [source.file_binding(path) for path in dict.fromkeys(paths)]
    protected = (repository_root(), *(Path(row["path"]).parent for row in bindings))
    disjoint(output, (*protected, result_root))
    disjoint(result_root, (*protected, output))
    require(not result_root.exists(), "result root already exists")
    plan = {"schema": SCHEMA, "official": False, "paid_execution_authorized": False,
        "runtime_hash": runtime_content_hash(), "prepared_at_commit": git_commit(),
        "scope": selected_scope, "result_root": str(result_root),
        "credential_file": str(credential_file.resolve()), "bindings": bindings,
        "evidence_hash": sha256_json(loaded.common["evidence"]),
        "deduplicated_hash": sha256_json(loaded.common["deduplicated_evidence"]),
        "checkpoint_provenance": loaded.checkpoint.provenance,
        "representation_statistics": dedup.statistics(loaded.common["deduplicated_evidence"]),
        "first_request_hashes": {arm: sha256_json(loaded.requests[arm]) for arm in order},
        "interpretation": "One saved-evidence first-edit trial per condition. Same unique public "
            "facts, source anchors, model and fresh budgets; vary duplicate/full versus reference "
            "representation. Not fresh solve, literal resume, pure token-length effect or general "
            "quality evidence. Earlier costs and uncertain calls remain in the closed old run."}
    if arm is not None:
        plan["interpretation"] = (
            "One full-context saved-evidence first-edit trial with compact post-edit source "
            "delivery, registered regression feedback and one bounded revision. "
            "Measures current-diff verification delivery "
            "and honest model completion separately from repair acceptance. Historical A is "
            "a baseline, not a concurrent control. Not fresh solve, literal resume, causal "
            "repair gain or general quality evidence. Earlier allocations remain closed.")
    output.mkdir()
    for name, data in {"manifest": plan, "evidence": loaded.common,
                       **{arm + "-first": loaded.requests[arm] for arm in order}}.items():
        with (output / (name + ".json")).open("x", encoding="utf-8") as stream:
            stream.write(canonical_json(data) + "\n")
    receipt = {"manifest": str(output / "manifest.json"),
        "manifest_hash": sha256_bytes((output / "manifest.json").read_bytes()),
        "provider_calls": 0, "input_count_calls": 0, "credential_reads": 0,
        "target_executions": 0, "acceptance": "NOT_RUN"}
    DevJournal(output, "run_dev_firsteditpreparation").append("prepared", receipt)
    return receipt


def validate(manifest, digest, *, approved_cap_usd=None):
    require(sha256_bytes(manifest.read_bytes()) == digest, "approved manifest hash differs")
    plan = json.loads(manifest.read_bytes())
    order = plan["scope"]["order"]
    require(plan["schema"] == SCHEMA and plan["scope"] == scope(order),
            "experiment scope changed")
    if approved_cap_usd is not None:
        require(approved_cap_usd == Decimal(plan["scope"]["total_cap_usd"]),
                "exact new total cap required")
    require(plan["runtime_hash"] == runtime_content_hash(), "runtime changed")
    for binding in plan["bindings"]:
        require(source.file_binding(binding["path"]) == binding, "bound code or evidence changed")
    loaded = load_inputs()
    require(plan["checkpoint_provenance"] == loaded.checkpoint.provenance
            and plan["evidence_hash"] == sha256_json(loaded.common["evidence"])
            and plan["deduplicated_hash"] == sha256_json(loaded.common["deduplicated_evidence"])
            and json.loads((manifest.parent / "evidence.json").read_bytes()) == loaded.common,
            "prepared public evidence changed")
    require(set(plan["first_request_hashes"]) == set(order), "request set changed")
    for arm in order:
        request = loaded.requests[arm]
        require(plan["first_request_hashes"][arm] == sha256_json(request)
                and json.loads((manifest.parent / f"{arm}-first.json").read_bytes()) == request,
                "prepared request changed")
    return plan, loaded


def saved_gateway(loaded, root):
    gateway = source.saved_gateway(loaded, root, "R1")
    initial = {sha256_json(span) for span in loaded.bundle["source_packets"]["R1"]}
    extra = [span for span in loaded.checkpoint.workspace_spans if sha256_json(span) not in initial]
    source.observe_sources(gateway, extra)
    host_reads = sum(e["event_type"] == "action_started" for e in gateway.journal.events())
    gateway.limits.max_tool_actions = host_reads + LIMITS.model_tools
    gateway.limits.max_model_calls = PROFILE.normal_calls + 1
    gateway.limits.max_accepted_mutations = LIMITS.accepted_edits
    gateway.journal.append("checkpoint_stage_ready", {
        "checkpoint": loaded.checkpoint.provenance, "host_source_reads": host_reads,
        "candidate_diff_hash": gateway.current_diff_hash, "historical_actions_imported": False,
        "fresh_normal_calls": PROFILE.normal_calls, "fresh_tool_actions": LIMITS.model_tools})
    gateway.deadline = ExecutionDeadline.from_remaining(MODEL_SECONDS)
    return gateway


def collect(manifest, approved_manifest_hash, approved_cap_usd):
    require(approved_cap_usd in {PROFILE.row_cap, PROFILE.invocation_cap},
            "exact new total cap required")
    plan, loaded = validate(manifest, approved_manifest_hash, approved_cap_usd=approved_cap_usd)
    root = Path(plan["result_root"])
    disjoint(root, (repository_root(), manifest.parent,
                    *(Path(row["path"]).parent for row in plan["bindings"])))
    relative = [Path(row["path"]).relative_to(repository_root()).as_posix()
                for row in plan["bindings"] if Path(row["path"]).is_relative_to(repository_root())]
    loop.runner._require_tracked_clean_paths(
        repository_root(), [*runtime_content_paths(), *relative])
    root.mkdir()
    journal = DevJournal(root, "run_dev_firsteditcomparison")
    journal.append("approved_collection_started", {"manifest_hash": approved_manifest_hash,
        "cap_usd": str(approved_cap_usd), "git_commit": git_commit()})
    group = DevCostLedger(approved_cap_usd, pricing_for_model(loop.MODEL))
    rows = []
    try:
        for arm in plan["scope"]["order"]:
            gateway = saved_gateway(loaded, root / arm)
            cycle = OriginalCallRecheck(loaded, gateway, root / arm / "original-recheck",
                                        limits=LIMITS)
            regression = PublicRegressionRecheck(loaded, gateway, root / arm / "public-regression",
                                                max_passes=LIMITS.accepted_edits)
            key = loop.load_exact_openai_api_key(Path(plan["credential_file"]))
            adapter = loop.OpenAIResponsesAdapter(loop.config(), api_key=key)
            del key
            try:
                row = loop.run_model(loaded, arm, gateway, adapter, group,
                    first_hash=plan["first_request_hashes"][arm], profile=PROFILE,
                    request_builder=request_payload, cycle=cycle,
                    regression=regression,
                    minimum_correction_seconds=MINIMUM_CORRECTION_SECONDS)
            finally:
                adapter.client.close()
            rows.append({"arm": arm, **row})
            journal.append("model_row_finished", rows[-1])
            if row["stop_remaining"]:
                break
            if row["new_mutations"]:
                originals = cycle.current_receipts()
                require(originals is not None, "edited candidate lacks original receipts")
                registered = regression.current_receipts()
                require(registered is not None, "edited candidate lacks public regression receipts")
                checks = source.host.public_checks(loaded, gateway, root / arm / "public",
                    original_receipts=originals, regression_receipts=registered)
                rows[-1]["public_checks"] = checks
                rows[-1]["final_verification"] = {"public": "completed", "isolated": "not_run"}
                journal.append("candidate_ready_for_evaluation", {"arm": arm, **checks})
                accepted = source.acceptance(gateway, root / arm / "acceptance",
                                             checks["regression_passed"])
                rows[-1]["acceptance"] = accepted
                rows[-1]["task_acceptance"] = accepted.get("acceptance", "not_run")
                rows[-1]["final_verification"]["isolated"] = (
                    "completed" if accepted.get("status") == "COMPLETED"
                    else accepted.get("status", "not_run"))
            journal.append("row_finished", rows[-1])
    except BaseException as exc:
        journal.append("collection_interrupted", {"error_type": type(exc).__name__,
                                                   "resume_allowed": False})
        raise
    result = {"official": False, "rows": rows, "cost_nanos": group.spent_nanos,
              "interpretation": plan["interpretation"], "allocation_closed": True}
    with (root / "result.json").open("x", encoding="utf-8") as stream:
        stream.write(canonical_json(result) + "\n")
    journal.append("closed", {"artifact": ArtifactStore(root / "artifacts")
                             .put_json(result).model_dump(mode="json")})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    for name in ("output", "result-root", "credential-file"):
        prep.add_argument("--" + name, type=Path, required=True)
    prep.add_argument("--arm", choices=("A",))
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
