"""Approved six-row caller-plus-helper comparison on explicit current-runtime forks."""

from __future__ import annotations

import argparse
import copy
import json
from contextlib import contextmanager
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from diagnostics import observation_comparison as common
from diagnostics import observation_exposure as exposure
from diagnostics.checkpoint_continuation import ScriptedClient, inherited_reads
from diagnostics.declaration_checkpoint import Source
from diagnostics.helper_path_probe import SPEC, TASK, export_result
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

MODEL = "gpt-5.4-mini-2026-03-17"
ROW_CAP, CAP = Decimal("0.50736730"), Decimal("3.04420380")
ORDER = ("A1", "B1", "B2", "A2", "A3", "B3")
FIELD = "operator_caller_observation"
EXTRA = "operator_helper_path_observation"
GATE = Path("C:/pt/helperpath22-g0")
ENV = repository_root() / ".env"
NOTE = ".agent/plans/helper-path-comparison.md"


def require(condition, message):
    if not condition:
        raise ContractError(message)


def source():
    s = json.loads(SPEC.read_bytes())["source"]
    return Source(Path(s["root"]), s["run_id"], s["journal"]["hash"], s["envelope"]["hash"],
                  repository_root() / TASK, sha256_bytes((repository_root() / TASK).read_bytes()))


def evidence():
    from diagnostics.caller_uptake import read_ref

    spec = json.loads(SPEC.read_bytes())
    original = json.loads(read_ref(spec["observation"]))
    result = json.loads((GATE / "result.json").read_bytes())
    review = json.loads((GATE / "gate-review.json").read_bytes())
    require(review["decision"] == "PASS" and result["paid_calls"] == 0,
            "information gate not passed")
    store = ArtifactStore(GATE / "artifacts")
    from patchloop.contracts import Artifact

    events = DevJournal(GATE, "run_dev_helperpathgate").events()
    completed = [e for e in events if e["event_type"] == "helper_path_gate_completed"]
    require(len(completed) == 1 and json.loads(store.read_bytes(Artifact.model_validate(
        completed[0]["payload"]["artifact"]))) == result, "unbound diagnostic result")
    recorded = [json.loads(store.read_bytes(Artifact.model_validate(e["payload"]["artifact"])))
                for e in events if e["event_type"] == "helper_path_review_recorded"
                and e["payload"]["name"] == "gate-review.json"]
    require(recorded == [review], "unbound information review")
    frozen = events[0]["payload"]
    extra = {
        "kind": "saved_public_helper_observation", "origin": "operator_supplied",
        "snapshot_hash": original["snapshot_hash"], "base_commit": original["base_commit"],
        "probe_identity": result["probe_identity"],
        "scope": "Previously collected on unchanged base; not executed by this continuation.",
        "bounds": "String arrays contain at most eight entries. Lines are executed source lines. "
                  "An exception followed by return:null is not a successful None return.",
        "observations": {case: {"fixture_root": result["observations"][case + "-on"][0][
            "input"]["cwd"], "helper_path": result["observations"][case + "-on"][2]}
                         for case in ("missing", "present")},
        "program_template": store.read_bytes(Artifact.model_validate(
            frozen["programs"]["missing-on"])).decode(),
        "present_variant": "Replace the single line PRESENT = False with PRESENT = True.",
    }
    # Keep the old packet exact. The new packet contains measured facts and collector code only.
    return {FIELD: original}, {FIELD: original, EXTRA: extra}


def attach(request, additions):
    value = copy.deepcopy(request)
    last = value["input"][-1]
    item = json.loads(last["content"])
    require(last["role"] == "developer" and item["kind"] == "harness_current_state",
            "unknown observation delivery boundary")
    for key, data in additions.items():
        require(key not in item["state"] or item["state"][key] == data, "observation collision")
        item["state"][key] = copy.deepcopy(data)
    last["content"] = canonical_json(item)
    return value


@contextmanager
def first_observation(branch, additions):
    context_builder, input_builder = runner._build_context, runner._build_model_input

    def first():
        return not any(e["event_type"] == "provider_call_started"
                       for e in branch.journal.events()[branch.inherited_events:])

    def context(**kwargs):
        text = context_builder(**kwargs)
        if not first():
            return text
        value = json.loads(text)
        value.update(copy.deepcopy(additions))
        return canonical_json(value)

    def model_input(**kwargs):
        value = input_builder(**kwargs)
        return attach({"input": value}, additions)["input"] if first() else value

    with patch.object(runner, "_build_context", context), patch.object(
        runner, "_build_model_input", model_input
    ):
        yield


def controls(result_root):
    reviewed = json.loads((GATE / "pricing-review.json").read_bytes())
    rates = {k: str(v) for k, v in asdict(pricing_for_model(MODEL)).items()}
    require(all(Decimal(reviewed[k]) == Decimal(v) for k, v in rates.items()), "prices changed")
    a, b = evidence()
    parent = source()
    old = DevJournal(parent.root, parent.run_id).load_envelope()
    require(old.model == MODEL and old.reasoning_effort == "xhigh"
            and old.max_output_tokens == 25000,
            "parent model settings changed")
    return {
        "schema": "helper-path-comparison-v1", "official": False, "claim_eligible": False,
        "head": git_commit(), "runtime_hash": runtime_content_hash(),
        "implementation_hash": exposure.implementation_hash(),
        "plan_hash": sha256_bytes((repository_root() / NOTE).read_bytes()),
        "evidence_hashes": {name: sha256_bytes((GATE / name).read_bytes())
                            for name in ("result.json", "gate-review.json", "pricing-review.json")},
        "source": parent.record(), "cut_sequence": 342, "order": list(ORDER),
        "model": MODEL, "reasoning_effort": "xhigh", "max_output_tokens": 25000,
        "env_file": str(ENV), "row_cap_nanos": 507367300, "new_cap_nanos": 3044203800,
        "result_root": str(result_root.resolve()), "rates": rates,
        "additions_hashes": {"A": sha256_json(a), "B": sha256_json(b)},
        "executing_probe_identity": {"image_digest": runner.probe_profile(
            old.probe_dependencies)["image_digest"],
            "profile_hash": runner.probe_profile_hash(old.probe_dependencies)},
        "parent_runtime_hash": old.runtime_hash, "sdk_retries": 0,
        "first_input_only": True, "automatic_retry_or_resume": False,
    }


def clean():
    common.clean_implementation()
    runner._require_tracked_clean_paths(repository_root(), [NOTE,
        "diagnostics/probes/astroid_helper_trace.py", "tests/test_helper_path_probe.py",
        "tests/test_helper_path_comparison.py"])


def preflight(plan):
    clean()
    return common.check_environment(plan, ENV)


def prepare(output, result_root):
    require(not output.exists() and not result_root.exists(), "fresh preparation and result roots")
    require(not output.resolve().is_relative_to(repository_root())
            and not result_root.resolve().is_relative_to(repository_root()),
            "external roots required")
    plan = controls(result_root)
    clean()
    output.mkdir()
    journal = DevJournal(output, "run_dev_helperpathpreparation")
    journal.append("preparation_started", {"controls": plan, "actual_provider_calls": 0})
    additions = dict(zip("AB", evidence(), strict=True))
    requests = {}
    for arm in "AB":
        branch = exposure.fork(source(), 342, output / arm, arm, synthetic_cap_usd=ROW_CAP,
                               preserve_parent_configuration=True)
        client = ScriptedClient([[{"name": "read_file", "action_id": "preview_read",
            "arguments": {"path": "astroid/modutils.py", "start_line": 600, "end_line": 632,
                "turn_decision": {"mode": "inspect", "basis": "Synthetic qualification only.",
                                  "evidence_goal": "Check input delivery.",
                                  "memory_update": None, "plan_update": None}}}],
            [{"name": "stop_task", "action_id": "preview_stop", "arguments": {
                "reason_code": "insufficient_public_evidence", "summary": "Synthetic stop.",
                "turn_decision": {"mode": "stop", "basis": "Synthetic qualification only.",
                                  "evidence_goal": None, "memory_update": None,
                                  "plan_update": None}}}]])
        def inject(_arm, selected=branch, material=additions[arm]):
            return first_observation(selected, material)

        with patch.object(exposure, "exposure", inject):
            receipt = exposure.rehearse(branch, client)
        require(len(client.counted) == len(client.created) == 2
                and receipt["result"]["terminal"] == "AGENT_STOPPED", "preview failed")
        requests[arm] = common.normalized(client.created[0])
        current = json.loads(client.created[1]["input"][-1]["content"])["state"]
        require(FIELD not in current and EXTRA not in current, "observation was reinjected")
        ArtifactStore(output).write_text_immutable(output / f"{arm}-first.json",
                                                  canonical_json(requests[arm]) + "\n")
        journal.append("arm_prepared", {"arm": arm, "receipt": receipt,
            "first_hash": sha256_json(requests[arm]), "second_current_state_has_supplement": False,
            "inherited_cost_nanos": branch.initial_spent_nanos,
            "restored_model": branch.request.model,
            "restored_total_cap_usd": str(branch.request.max_cost_usd)})
    without = copy.deepcopy(requests["B"])
    last = json.loads(without["input"][-1]["content"])
    del last["state"][EXTRA]
    without["input"][-1]["content"] = canonical_json(last)
    require(without == requests["A"], "first pair differs beyond qualified helper evidence")
    plan["first_request_hashes"] = {a: sha256_json(r) for a, r in requests.items()}
    plan["preparation_root"] = str(output.resolve())
    readiness = preflight(plan)
    ArtifactStore(output).write_text_immutable(output / "manifest.json",
                                              canonical_json(plan) + "\n")
    journal.append("preparation_finished", {"plan": plan, "preflight": readiness,
        "actual_provider_calls": 0, "first_bytes": {a: len(canonical_json(r).encode())
                                                    for a, r in requests.items()}})
    return {"manifest": str(output / "manifest.json"),
            "hash": sha256_bytes((output / "manifest.json").read_bytes()), "preflight": readiness}


def run_branch(branch, additions, group, journal, store, label, first_hash):
    ledger = common.ContinuationLedger(branch, group, journal, label)
    counts, dispatches = [], []
    active = runner._run_one_active
    executing_commit = git_commit()

    class RecordedAdapter(OpenAIResponsesAdapter):
        def count_input_tokens_v2(self, payload, **kwargs):
            self.pending = None
            if not counts:
                require(sha256_json(common.normalized(payload)) == first_hash,
                        "first actual input differs from prepared input")
            ref = store.put_json(payload).model_dump(mode="json")
            journal.append("actual_input_count_started", {"row": label, "artifact": ref})
            counts.append(copy.deepcopy(payload))
            result = super().count_input_tokens_v2(payload, **kwargs)
            self.pending = copy.deepcopy(payload)
            return result

        def execute_request(self, payload, **kwargs):
            expected, self.pending = self.pending, None
            require(expected is not None, "dispatch lacks fresh count")
            require(0 < payload["max_output_tokens"] <= expected["max_output_tokens"],
                    "output allowance grew after count")
            expected["max_output_tokens"] = payload["max_output_tokens"]
            require(expected == payload, "counted and dispatched inputs differ")
            ref = store.put_json(payload).model_dump(mode="json")
            journal.append("actual_dispatch_started", {"row": label, "artifact": ref})
            dispatches.append(ref)
            return super().execute_request(payload, **kwargs)

    def identity(**kwargs):
        return active(**{**kwargs, "harness_git_commit": executing_commit})

    with (inherited_reads(branch), exposure.current_probe_receipts(branch),
          first_observation(branch, additions), patch.object(runner, "OpenAIResponsesAdapter",
          RecordedAdapter), patch.object(runner, "_run_one_active", identity),
          branch.journal.execution_lock()):
        branch.journal.append("executing_runtime_git_identity", {
            "harness_git_commit": executing_commit, "inherited_identity_is_historical": True})
        result = runner._run_one_locked(request=branch.request, task_dir=branch.task_dir,
            package=branch.package, state_root=branch.root, pricing=branch.pricing,
            cost_ledger=ledger, runtime_hash=branch.envelope.runtime_hash,
            model_hash=branch.envelope.model_hash, run_id=branch.journal.run_id,
            journal=branch.journal, envelope=branch.envelope, resuming=True)
    known = runner._provider_usage_failure(branch.journal) is None
    return {"row": label, "status": "EXECUTED", "result": result.public, "billing_known": known,
        "new_cost_nanos": ledger.spent_nanos - branch.initial_spent_nanos if known else None,
        "input_counts": len(counts), "dispatches": len(dispatches),
        "stop_remaining": not known or result.public["terminal"] == "PREFLIGHT_FAILED"
        or (result.stop_remaining and result.public["terminal"] != "COST_CAP_REACHED")}


def collect(manifest, approved_hash):
    raw = manifest.read_bytes()
    require(sha256_bytes(raw) == approved_hash, "manifest changed")
    plan = json.loads(raw)
    root = Path(plan["result_root"])
    require({k: v for k, v in plan.items() if k not in ("first_request_hashes", "preparation_root")}
            == controls(root), "execution controls changed")
    require(preflight(plan)["status"] == "READY", "preflight not ready")
    require(not root.exists(), "comparison is single use")
    root.mkdir()
    journal = DevJournal(root, "run_dev_helperpathcomparison")
    store = ArtifactStore(root / "artifacts")
    group = DevCostLedger(CAP, pricing_for_model(MODEL))
    additions = dict(zip("AB", evidence(), strict=True))
    rows = [{"row": label, "status": "NOT_RUN"} for label in ORDER]
    known, reason = True, None
    with journal.execution_lock():
        journal.append("comparison_authorized", {"manifest_hash": approved_hash, "plan": plan,
            "user_request": "그럼 방금 설계한대로 실험 진행해줘", "new_cap_usd": str(CAP)})
        for index, label in enumerate(ORDER):
            branch = None
            try:
                require(preflight(plan)["status"] == "READY", "row preflight not ready")
                branch = exposure._fork(source(), 342, root / label, label[0], new_cap_usd=ROW_CAP,
                    mode="funded-observation", env_file=ENV, preserve_parent_configuration=True)
                value = run_branch(branch, additions[label[0]], group, journal, store, label,
                                   plan["first_request_hashes"][label[0]])
            except Exception as exc:
                value = {"row": label, "status": "COLLECTOR_FAILED",
                    "error_type": type(exc).__name__,
                    "reason": str(exc), "stop_remaining": True, "billing_known": branch is None
                    or runner._provider_usage_failure(branch.journal) is None}
            rows[index] = value
            known = known and value["billing_known"]
            journal.append("row_finished", value)
            print(canonical_json({k: v for k, v in value.items() if k != "result"}), flush=True)
            if value["stop_remaining"]:
                reason = value.get("result", {}).get("terminal", value["status"])
                break
        result = {"official": False, "claim_eligible": False, "rows": rows, "billing_known": known,
            "new_cost_nanos": group.spent_nanos if known else None,
            "new_cap_nanos": group.cap_nanos,
            "stop_reason": reason, "repair_effect": "NOT_ASSESSED"}
        journal.append("comparison_finished", {
            "artifact": store.put_json(result).model_dump(mode="json")})
        export_result(root, result)
    return {k: v for k, v in result.items() if k != "rows"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--output", type=Path, required=True)
    prep.add_argument("--result-root", type=Path, required=True)
    live = sub.add_parser("collect")
    live.add_argument("--manifest", type=Path, required=True)
    live.add_argument("--approved-manifest-hash", required=True)
    args = parser.parse_args()
    result = prepare(args.output, args.result_root) if args.command == "prepare" else collect(
        args.manifest, args.approved_manifest_hash)
    print(canonical_json(result))


if __name__ == "__main__":
    main()
