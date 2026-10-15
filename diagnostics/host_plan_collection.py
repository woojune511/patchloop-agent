"""Prepare a nonauthorized manifest; collect requires exact later human approval.

The CLI only prepares. Preparation does not read a credential or contact Docker,
model metadata, input-count, generation, diagnostic or evaluator services.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from time import monotonic
from unittest.mock import patch

from diagnostics import host_plan_checkpoint as checkpoint
from diagnostics import host_plan_execution as execution
from diagnostics import host_plan_review as review
from diagnostics import observation_comparison, observation_exposure
from diagnostics.decision_sampler import require
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner
from patchloop.dev.state import DevJournal
from patchloop.runtime import git_commit, repository_root
from patchloop.sandbox.runner import DockerSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json

FROZEN_KEYS = (
    "model",
    "reasoning_effort",
    "service_tier",
    "caps",
    "common_configuration",
    "cost_basis",
    "credential_file",
    "grading",
    "cap_application",
    "treatment",
    "terminal_public_assessment",
    "task_path",
    "stop_rules",
)


def file_ref(path):
    return {"path": str(path.resolve()), "content_hash": sha256_bytes(path.read_bytes())}


def differences(left, right, path="$", found=None):
    """Enumerate all shared historical/current drift; never normalize it away."""
    found = [] if found is None else found
    if type(left) is not type(right):
        found.append({"path": path, "before": left, "after": right})
    elif isinstance(left, dict):
        for key in sorted(set(left) | set(right)):
            if key not in left or key not in right:
                found.append(
                    {"path": path + "." + key, "before": left.get(key), "after": right.get(key)}
                )
            else:
                differences(left[key], right[key], path + "." + key, found)
    elif isinstance(left, list) and len(left) == len(right):
        for index, (a, b) in enumerate(zip(left, right, strict=True)):
            differences(a, b, path + f"[{index}]", found)
    elif left != right:
        found.append({"path": path, "before": left, "after": right})
    return found


def profile_differences(source, old, current, public):
    """Operator-only environment provenance; no later result is added to the seed."""
    receipts = [
        e
        for e in DevJournal(source.root, source.run_id).events()
        if e["event_type"] == "action_finished" and e["payload"]["result"]["tool"] == "run_probe"
    ]
    require(receipts, "historical probe profile evidence unavailable")
    event = receipts[0]
    policy = event["payload"]["result"]["output"]["execution_policy"]
    historical = {
        k: v
        for k, v in policy.items()
        if k
        not in {
            "cleanup_status",
            "effective_timeout_seconds",
            "profile_hash",
            "requested_timeout_seconds",
            "row_deadline_limited",
        }
    }
    dependencies = runner.load_dependencies(
        Path(old.prepared_probe_dependencies_path), public, old.probe_dependencies
    )
    actual = runner.DockerProbeSandbox(dependencies=dependencies).current_profile()
    require(
        sha256_json(historical) == old.probe_profile_hash
        and sha256_json(actual) == current.probe_profile_hash,
        "profile provenance does not reproduce bound hashes",
    )
    return {
        "historical_metadata_sequence": event["sequence"],
        "solver_feedback": False,
        "historical": historical,
        "current": actual,
        "differences": differences(historical, actual),
    }


def prepare(rehearsal_root, live_output, manifest_path, validation_path):
    plan, source = checkpoint.load_design()
    observation_comparison.clean_implementation()
    require(not live_output.exists() and not manifest_path.exists(), "fresh output paths required")
    observation_exposure.disjoint(
        live_output.resolve(),
        (
            repository_root(),
            source.root,
            checkpoint.DESIGN.parent,
            rehearsal_root.resolve(),
            manifest_path.parent.resolve(),
        ),
    )
    result_path = rehearsal_root / "result.json"
    result = json.loads(result_path.read_bytes())
    validation = json.loads(validation_path.read_bytes())
    journal = DevJournal(rehearsal_root, "run_dev_hostplanmock")
    events = journal.events()
    start = next(e["payload"] for e in events if e["event_type"] == "host_plan_mock_started")
    finish = next(e["payload"] for e in events if e["event_type"] == "host_plan_mock_finished")
    require(
        json.loads(checkpoint.read_bound(finish["result"])) == result,
        "rehearsal result differs from its sealed journal artifact",
    )
    require(
        start["implementation_hash"] == result["implementation_hash"]
        and start["runtime_hash"] == runner._runtime_hash()
        and start["harness_git_commit"] == git_commit(),
        "rehearsal implementation/head changed during or after execution",
    )
    require(
        result["status"] == "PASS"
        and result["provider_free"]
        and result["design_hash"] == checkpoint.DESIGN_HASH
        and result["provider_calls"] == result["credential_reads"] == result["metadata_calls"] == 0,
        "successful fixed-checkpoint provider-free pair required",
    )
    require(
        result["implementation_hash"]
        == validation["implementation_hash"]
        == observation_exposure.implementation_hash(),
        "connector changed after verification",
    )
    require(
        validation["provider_free"] and validation["status"] == "PASS",
        "provider-free contract validation required",
    )
    require([r["row"] for r in result["rows"]] == ["O1-A", "O1-B"], "frozen roster changed")
    first = [json.loads(checkpoint.read_bound(r["first_request"])) for r in result["rows"]]
    parity = checkpoint.first_parity(*first, plan["systems"])
    old = DevJournal(source.root, source.run_id).load_envelope()
    current = DevJournal(rehearsal_root / "O1-A", source.run_id).load_envelope()
    saved = json.loads(checkpoint.read_bound(plan["source"]["original_prepared"]))["request"]
    # Serialized harness JSON is decoded for readable, exact field-level differences.
    before, after = json.loads(canonical_json(saved)), json.loads(canonical_json(first[0]))
    for request in (before, after):
        for item in request["input"]:
            if item.get("role") == "developer":
                item["content"] = json.loads(item["content"])
    drift = {
        "historical_to_common_capped_request": differences(before, after),
        "historical_probe_profile": old.probe_profile_hash,
        "current_probe_profile": current.probe_profile_hash,
        "historical_runtime": old.runtime_hash,
        "current_runtime": current.runtime_hash,
        "probe_profile_fields": profile_differences(
            source, old, current, runner._resolve_task_file(source.public_path)[1].public
        ),
        "interpretation": "Shared by A/B; not treatment effects or a historical exact replay.",
    }
    store = ArtifactStore(manifest_path.parent / "artifacts")
    drift_ref = store.put_json(drift)
    manifest = {
        "schema": "host-plan-execution-v1",
        "official": False,
        "claim_eligible": False,
        "paid_authorized": False,
        "executable_manifest_ready": True,
        "design_hash": checkpoint.DESIGN_HASH,
        "harness_git_commit": git_commit(),
        "runtime_hash": runner._runtime_hash(),
        "implementation_hash": observation_exposure.implementation_hash(),
        "source": source.record(),
        "checkpoint": plan["source"],
        **{k: plan[k] for k in FROZEN_KEYS},
        "live_output": str(live_output.resolve()),
        "executing_probe_identity": {
            "image_digest": current.probe_image_digest,
            "profile_hash": current.probe_profile_hash,
        },
        "first_requests": {r["row"]: r["first_request"] for r in result["rows"]},
        "first_input_parity": parity,
        "shared_runtime_differences": drift_ref.model_dump(mode="json"),
        "rehearsal_result": file_ref(result_path),
        "validation": file_ref(validation_path),
        "rehearsal_journal_head": journal.events()[-1]["event_hash"],
        "public_review_protocol": "One row-specific public-review-ready/public-grade file pair. "
        "Seal E/U/R within 120s before either terminal assessment. No paid judge or retrograding.",
        "live_readiness": "NOT_RUN; fresh official pricing, exact existing environment, "
        "one model metadata read and explicit exact-manifest approval are still required.",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical_json(manifest) + "\n")
    return {"manifest": file_ref(manifest_path), "paid_authorized": False, "provider_calls": 0}


def validate_manifest(manifest_path, approved_hash, approved_cap_usd, pricing_review):
    require(approved_cap_usd == Decimal("11.00"), "exact USD 11 approval required")
    manifest = json.loads(
        checkpoint.read_bound({"path": str(manifest_path), "content_hash": approved_hash})
    )
    plan, source = checkpoint.load_design()
    require(
        manifest["schema"] == "host-plan-execution-v1"
        and manifest["design_hash"] == checkpoint.DESIGN_HASH
        and manifest["source"] == source.record()
        and manifest["checkpoint"] == plan["source"]
        and manifest["runtime_hash"] == runner._runtime_hash()
        and manifest["implementation_hash"] == observation_exposure.implementation_hash()
        and manifest["harness_git_commit"] == git_commit(),
        "approved implementation changed",
    )
    require(all(manifest[k] == plan[k] for k in FROZEN_KEYS), "approved conditions changed")
    require(
        pricing_review
        == {
            "verified_on": datetime.now(UTC).date().isoformat(),
            "source": "https://developers.openai.com/api/docs/pricing",
            "model": plan["model"],
            "service_tier": "default",
            "usd_per_million": {"input": "2.50", "cached_input": "0.25", "output": "15.00"},
        },
        "fresh unchanged official rates required before dispatch",
    )
    observation_comparison.clean_implementation()
    for key in ("rehearsal_result", "validation", "shared_runtime_differences"):
        checkpoint.read_bound(manifest[key])
    for ref in manifest["first_requests"].values():
        checkpoint.read_bound(ref)
    return manifest, plan, source


def collect(manifest_path, approved_hash, approved_cap_usd, *, pricing_review, reviewer=None):
    """Separate live entry point. No CLI shortcut, retries, resume or replacement rows."""
    started = monotonic()
    manifest, plan, source = validate_manifest(
        manifest_path, approved_hash, approved_cap_usd, pricing_review
    )
    output = Path(manifest["live_output"])
    observation_exposure.disjoint(
        output, (repository_root(), source.root, checkpoint.DESIGN.parent, manifest_path.parent)
    )
    output.mkdir()
    journal, store = DevJournal(output, "run_dev_hostplancollection"), ArtifactStore(output)
    group = execution.Invocation(journal, started=started)
    journal.append(
        "host_plan_invocation_approved",
        {
            "manifest_hash": approved_hash,
            "approved_cap_usd": str(approved_cap_usd),
            "pricing_review": pricing_review,
        },
    )
    metadata_reads = 0
    solver_end = started + 1697

    class ReadinessDeadline:
        @staticmethod
        def from_remaining(seconds):
            return ExecutionDeadline(
                min(group.clock() + seconds, solver_end, group.deadline.expires_at), group.clock
            )

    try:
        with patch.object(observation_comparison, "ExecutionDeadline", ReadinessDeadline):
            readiness = observation_comparison.check_environment(
                {
                    "source": source.record(),
                    "executing_probe_identity": manifest["executing_probe_identity"],
                },
                Path(plan["credential_file"]),
            )
        journal.append("host_plan_environment_readiness", readiness)
        require(readiness["status"] == "READY", "exact environment unavailable")
        env = json.loads(checkpoint.read_bound(plan["terminal_public_assessment"]))["environment"]
        require(
            DockerSandbox(env["image"]).image_identity(
                deadline=ReadinessDeadline.from_remaining(30)
            )
            == env["image"].split("@", 1)[1],
            "exact public assessment image unavailable",
        )
        from openai import OpenAI

        deadline = ReadinessDeadline.from_remaining(30)
        deadline.check()
        key = runner.load_exact_openai_api_key(Path(plan["credential_file"]))
        metadata_reads += 1
        journal.append("host_plan_metadata_started", {"model": plan["model"], "attempt": 1})
        with OpenAI(
            api_key=key,
            base_url="https://api.openai.com/v1",
            max_retries=0,
            timeout=deadline.remaining_seconds(),
        ) as client:
            metadata = client.models.retrieve(plan["model"])
        require(metadata.id == plan["model"], "exact model unavailable")
        journal.append("host_plan_metadata_finished", {"model": metadata.id})
    except (Exception, execution.BoundStop) as exc:
        group.stopped = True
        journal.append("host_plan_readiness_stopped", {"reason": f"{type(exc).__name__}: {exc}"})

    def prepare_row(arm):
        branch = checkpoint.restore_branch(
            plan,
            source,
            output / ("O1-" + arm),
            arm,
            provider_free=False,
            credential_file=Path(plan["credential_file"]),
            started=started if arm == "A" else group.clock(),
            clock=group.clock,
            deadline=group.deadline,
        )
        branch.expected_first = json.loads(
            checkpoint.read_bound(manifest["first_requests"]["O1-" + arm])
        )
        require(
            {
                "image_digest": branch.envelope.probe_image_digest,
                "profile_hash": branch.envelope.probe_profile_hash,
            }
            == manifest["executing_probe_identity"],
            "approved current probe identity changed",
        )
        return branch

    rows = execution.run_roster(
        group,
        prepare_row,
        lambda branch: execution.run_row(
            branch, group, reviewer=reviewer or review.file_reviewer(branch.root)
        ),
    )
    # Public E/U/R already sealed; private terminal verdicts never enter B's restored prefix.
    result = {
        "official": False,
        "rows": rows,
        "comparison": review.pair_result(rows),
        "model_metadata_reads": metadata_reads,
        "counts": group.counts,
        "generations": group.generations,
        "provisional_cost_nanos": group.ledger.spent_nanos,
        "total_cost_known": all(r.get("billing_known", r.get("status") == "NOT_RUN") for r in rows),
        "no_adoption_or_followup_authorized": True,
    }
    journal.append(
        "host_plan_invocation_closed", {"result": store.put_json(result).model_dump(mode="json")}
    )
    with (output / "result.json").open("x", encoding="utf-8") as stream:
        stream.write(canonical_json(result) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rehearsal-root", type=Path, required=True)
    parser.add_argument("--live-output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    args = parser.parse_args()
    print(
        canonical_json(
            prepare(args.rehearsal_root, args.live_output, args.manifest, args.validation)
        )
    )


if __name__ == "__main__":
    main()
