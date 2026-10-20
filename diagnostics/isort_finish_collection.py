"""Prepare an exact manifest; collect is a separate, explicitly funded entry point.

Preparation never reads a credential, calls model/count/metadata APIs, starts
Docker, or executes isort. The frozen packet and committed connector are bound
to provider-free evidence before any later authorization.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from time import monotonic
from unittest.mock import patch

from diagnostics import isort_finish_checkpoint as checkpoint
from diagnostics import isort_finish_execution as execution
from diagnostics import observation_comparison, observation_exposure
from diagnostics.decision_sampler import require
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner
from patchloop.dev.state import DevJournal
from patchloop.runtime import git_commit, repository_root
from patchloop.util import canonical_json, sha256_bytes


def file_ref(path):
    return {"path": str(path.resolve()), "content_hash": sha256_bytes(path.read_bytes())}


def prepare(rehearsal_root, live_output, manifest_path, validation_path):
    plan, source, feedback = checkpoint.load_design()
    observation_comparison.clean_implementation()
    require(not live_output.exists() and not manifest_path.exists(), "fresh output paths required")
    observation_exposure.disjoint(
        live_output.resolve(),
        (
            repository_root(),
            source.root,
            checkpoint.DESIGN.parent,
            rehearsal_root.resolve(),
        ),
    )
    result_path = rehearsal_root / "result.json"
    result = json.loads(result_path.read_bytes())
    require(
        result["provider_free"]
        and result["design_hash"] == checkpoint.DESIGN_HASH
        and result["provider_calls"] == result["credential_reads"] == result["metadata_calls"] == 0
        and result["row"]["first_input_verified"]
        and not result["row"]["stop_remaining"]
        and result["row"]["C"] == "PASS"
        and result["row"]["R"] == "NOT_OBSERVABLE"
        and result["row"]["A"] == "PASS"
        and result["row"]["first_response"]["category"] == "CONTINUES_WITH_PUBLIC_ACTION",
        "successful fixed-checkpoint rehearsal required",
    )
    require(
        result["row"]["result"]["terminal"] == "AGENT_STOPPED"
        and result["row"]["new_counts"] == result["row"]["new_generations"] == 2
        and result["row"]["new_tool_actions"] == 2
        and result["row"]["accepted_new_edits"] == 0,
        "rehearsal must complete the fixed read/stop script",
    )
    journal = DevJournal(rehearsal_root, "run_dev_isortfinishbridge")
    binding = next(
        e["payload"] for e in journal.events() if e["event_type"] == "isort_finish_mock_started"
    )
    validation = json.loads(validation_path.read_bytes())
    require(
        binding["diagnostic_implementation_hash"]
        == validation["implementation_hash"]
        == observation_exposure.implementation_hash(),
        "connector changed after verification",
    )
    require(
        validation["provider_free"] and validation["status"] == "PASS",
        "provider-free contract validation required",
    )
    first_request = json.loads(checkpoint.read_bound(result["first_request"]))
    parity = checkpoint.compare_first_request(
        first_request, checkpoint.expected_first_request(plan)
    )
    require(result["row"]["first_input_parity"] == parity, "rehearsal first input parity changed")
    receipt = feedback["snapshots"][1]["receipt"]
    manifest = {
        "schema": "isort-finish-advice-execution-v1",
        "official": False,
        "paid_authorized": False,
        "design_hash": checkpoint.DESIGN_HASH,
        "harness_git_commit": git_commit(),
        "runtime_hash": runner._runtime_hash(),
        "implementation_hash": observation_exposure.implementation_hash(),
        "source": source.record(),
        "row": "I4",
        "repeat": 1,
        **{
            k: plan[k]
            for k in (
                "model",
                "reasoning_effort",
                "service_tier",
                "caps",
                "cost_basis",
                "credential_file",
                "feedback",
                "grading",
                "retention_policy",
                "observed_candidate_diff",
                "limits_and_criteria",
                "treatment_policy",
                "cap_application",
                "historical_observation",
                "terminal_public_oracle",
            )
        },
        "task": plan["task_path"],
        "live_output": str(live_output.resolve()),
        "executing_probe_identity": {k: receipt[k] for k in ("image_digest", "profile_hash")},
        "rehearsal_result": file_ref(result_path),
        "first_request": result["first_request"],
        "first_input_parity": parity,
        "static_parity": plan["static_parity"],
        "validation": file_ref(validation_path),
        "rehearsal_journal_head": journal.events()[-1]["event_hash"],
        "public_review_protocol": (
            "Seal A/D, first-response classification and unchanged semantic U/C/R with public "
            "citations before both terminal assessments inside 720s. C/R remain secondary; "
            "primary local success requires A/D/U/P/I/safety PASS, not just a different action."
        ),
        "live_readiness": (
            "NOT_RUN; fresh official price review, read-only environment check "
            "and one model metadata read required."
        ),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical_json(manifest) + "\n")
    return {
        "manifest": str(manifest_path),
        "manifest_hash": file_ref(manifest_path)["content_hash"],
        "paid_authorized": False,
        "provider_calls": 0,
    }


def collect(manifest_path, approved_hash, approved_cap_usd, *, pricing_review, reviewer=None):
    """One fresh I4 only; no retries/resume/automatic follow-up on any outcome."""
    started = monotonic()
    require(approved_cap_usd == Decimal("3.50"), "exact positive USD 3.50 approval required")
    manifest = json.loads(
        checkpoint.read_bound({"path": str(manifest_path), "content_hash": approved_hash})
    )
    plan, source, feedback = checkpoint.load_design()
    require(
        manifest["design_hash"] == checkpoint.DESIGN_HASH
        and manifest["source"] == source.record()
        and manifest["runtime_hash"] == runner._runtime_hash()
        and manifest["implementation_hash"] == observation_exposure.implementation_hash()
        and manifest["harness_git_commit"] == git_commit(),
        "approved execution identity changed",
    )
    require(
        all(
            manifest[k] == plan[k]
            for k in (
                "model",
                "reasoning_effort",
                "service_tier",
                "caps",
                "cost_basis",
                "credential_file",
                "feedback",
                "grading",
                "retention_policy",
                "observed_candidate_diff",
                "limits_and_criteria",
                "treatment_policy",
                "cap_application",
                "historical_observation",
                "terminal_public_oracle",
            )
        )
        and manifest["task"] == plan["task_path"]
        and manifest["row"] == "I4"
        and manifest["repeat"] == 1,
        "approved scope changed",
    )
    receipt = feedback["snapshots"][1]["receipt"]
    require(
        manifest["executing_probe_identity"]
        == {k: receipt[k] for k in ("image_digest", "profile_hash")},
        "approved probe identity changed",
    )
    require(
        pricing_review
        == {
            "verified_on": datetime.now(UTC).date().isoformat(),
            "source": "https://developers.openai.com/api/docs/pricing",
            "usd_per_million": {"input": "2.50", "cached_input": "0.25", "output": "15.00"},
            "model": plan["model"],
            "service_tier": "default",
        },
        "fresh official price review required; price changes require a new design",
    )
    observation_comparison.clean_implementation()
    rehearsed = json.loads(checkpoint.read_bound(manifest["rehearsal_result"]))
    require(
        manifest["static_parity"] == plan["static_parity"]
        and manifest["first_request"] == rehearsed["first_request"],
        "approved parity binding changed",
    )
    parity = checkpoint.compare_first_request(
        json.loads(checkpoint.read_bound(manifest["first_request"])),
        checkpoint.expected_first_request(plan),
    )
    require(parity == manifest["first_input_parity"], "approved first input parity changed")
    checkpoint.read_bound(manifest["validation"])
    output = Path(manifest["live_output"])
    observation_exposure.disjoint(
        output.resolve(),
        (
            repository_root(),
            source.root,
            checkpoint.DESIGN.parent,
            Path(manifest_path).parent,
        ),
    )
    require(not output.exists(), "fresh output root required; no retry or resume")
    output.mkdir()
    journal, store = DevJournal(output, "run_dev_isortfinishcollection"), ArtifactStore(output)
    group = execution.Invocation(journal, started=started, clock=monotonic)
    solver_deadline = ExecutionDeadline(group.started + 281, group.clock)
    journal.append(
        "isort_finish_invocation_approved",
        {
            "manifest_hash": approved_hash,
            "approved_cap_usd": str(approved_cap_usd),
            "pricing_review": pricing_review,
        },
    )
    metadata_reads, row = 0, None

    class PreflightDeadline:
        @staticmethod
        def from_remaining(seconds):
            return ExecutionDeadline(
                min(group.clock() + seconds, group.deadline.expires_at, solver_deadline.expires_at),
                group.clock,
            )

    try:
        group.check()
        solver_deadline.check()
        with patch.object(observation_comparison, "ExecutionDeadline", PreflightDeadline):
            readiness = observation_comparison.check_environment(
                {
                    "source": source.record(),
                    "executing_probe_identity": manifest["executing_probe_identity"],
                },
                Path(plan["credential_file"]),
            )
        journal.append("isort_finish_environment_readiness", readiness)
        require(readiness["status"] == "READY", "exact environment unavailable")
        group.check()
        solver_deadline.check()
        from openai import OpenAI

        key = runner.load_exact_openai_api_key(Path(plan["credential_file"]))
        solver_deadline.check()
        metadata_reads += 1
        journal.append("isort_finish_metadata_started", {"model": plan["model"], "attempt": 1})
        with OpenAI(
            api_key=key,
            base_url="https://api.openai.com/v1",
            max_retries=0,
            timeout=min(
                30, solver_deadline.remaining_seconds(), group.deadline.remaining_seconds()
            ),
        ) as client:
            metadata = client.models.retrieve(plan["model"])
        require(metadata.id == plan["model"], "exact model unavailable")
        journal.append("isort_finish_metadata_finished", {"model": metadata.id})
        group.check()
        solver_deadline.check()
        branch = checkpoint.restore_branch(
            source,
            plan["inheritance"]["prepared_cut_sequence"],
            feedback,
            output / "I4",
            provider_free=False,
            credential_file=Path(plan["credential_file"]),
            started=started,
            clock=group.clock,
            deadline=group.deadline,
        )
        row = execution.run_row(
            branch,
            group,
            checkpoint.read_bound(plan["terminal_public_oracle"]).decode(),
            reviewer=reviewer or execution.file_reviewer(output),
        )
    except (Exception, execution.BoundStop) as exc:
        group.stopped = True
        row = {"row": "I4", "status": "STOPPED", "reason": f"{type(exc).__name__}: {exc}"}
        journal.append("isort_finish_invocation_stopped", row)
    # Automatic summary excludes isolated verdicts. Public U is already sealed.
    full = store.put_json(row)
    result = {
        "official": False,
        "row": {k: v for k, v in row.items() if k != "result"},
        "model_metadata_reads": metadata_reads,
        "counts": group.counts,
        "generations": group.generations,
        "provisional_cost_nanos": group.ledger.spent_nanos,
        "total_cost_known": row.get("billing_known", group.counts == group.generations == 0),
        "full_result": full.model_dump(mode="json"),
    }
    journal.append("isort_finish_invocation_closed", result)
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
