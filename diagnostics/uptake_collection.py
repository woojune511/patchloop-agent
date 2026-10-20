"""Bind the rehearsed connector; paid collection requires an exact separate approval.

The command-line entry point only writes a manifest. It never reads a credential,
calls a provider, starts Docker, or executes a task. collect() is intentionally a
separate entry point for a later, explicitly authorized invocation.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from time import monotonic
from unittest.mock import patch

from diagnostics import observation_comparison, observation_exposure
from diagnostics import uptake_checkpoint as checkpoint
from diagnostics import uptake_execution as execution
from diagnostics.decision_sampler import require
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner
from patchloop.dev.state import DevJournal
from patchloop.runtime import git_commit, repository_root
from patchloop.util import canonical_json, sha256_bytes


def prepare(rehearsal_root, live_output, manifest_path):
    plan, source, _ = checkpoint.load_design()
    observation_comparison.clean_implementation()
    require(not live_output.exists() and not manifest_path.exists(), "fresh output paths required")
    observation_exposure.disjoint(
        live_output.resolve(),
        (repository_root(), source.root, checkpoint.DESIGN.parent, rehearsal_root.resolve()),
    )
    result_path = rehearsal_root / "result.json"
    result = json.loads(result_path.read_bytes())
    require(
        result["provider_free"]
        and result["design_hash"] == checkpoint.DESIGN_HASH
        and result["provider_calls"] == result["credential_reads"] == 0
        and [r["cell"] for r in result["rows"]] == ["B1", "B2"]
        and all(r.get("first_input_verified") and not r["stop_remaining"] for r in result["rows"]),
        "successful fixed-row rehearsal required",
    )
    journal = DevJournal(rehearsal_root, "run_dev_uptakebridge")
    binding = next(
        e["payload"] for e in journal.events() if e["event_type"] == "uptake_mock_started"
    )
    require(
        binding["diagnostic_implementation_hash"] == observation_exposure.implementation_hash(),
        "connector changed after the rehearsal",
    )
    manifest = {
        "schema": "pre-edit-uptake-execution-v1",
        "official": False,
        "paid_authorized": False,
        "design_hash": checkpoint.DESIGN_HASH,
        "harness_git_commit": git_commit(),
        "runtime_hash": runner._runtime_hash(),
        "implementation_hash": observation_exposure.implementation_hash(),
        "source": source.record(),
        "model": plan["model"],
        "task": plan["task_path"],
        "credential_file": plan["credential_file"],
        "order": plan["order"],
        "caps": plan["caps"],
        "cost": plan["cost"],
        "rows": plan["rows"],
        "live_output": str(live_output.resolve()),
        "rehearsal_result": {
            "path": str(result_path.resolve()),
            "content_hash": sha256_bytes(result_path.read_bytes()),
        },
        "rehearsal_journal_head": journal.events()[-1]["event_hash"],
        "live_readiness": (
            "NOT_RUN; fresh official price review and one model metadata read required"
        ),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical_json(manifest) + "\n")
    return {
        "manifest": str(manifest_path),
        "manifest_hash": sha256_bytes(manifest_path.read_bytes()),
        "paid_authorized": False,
        "provider_calls": 0,
    }


def collect(manifest_path, approved_hash, approved_cap_usd, *, pricing_review):
    """Never called by preparation/rehearsal. No retries, resume, replacement or tuning."""
    started = monotonic()
    require(approved_cap_usd == Decimal("7.00"), "exact positive USD 7 approval required")
    manifest = json.loads(
        checkpoint.read_bound({"path": str(manifest_path), "content_hash": approved_hash})
    )
    plan, source, selected = checkpoint.load_design()
    require(
        manifest["design_hash"] == checkpoint.DESIGN_HASH
        and manifest["source"] == source.record()
        and manifest["runtime_hash"] == runner._runtime_hash()
        and manifest["implementation_hash"] == observation_exposure.implementation_hash()
        and manifest["harness_git_commit"] == git_commit(),
        "approved execution identity changed",
    )
    require(
        all(manifest[k] == plan[k] for k in ("caps", "cost", "rows", "order", "model"))
        and manifest["credential_file"] == plan["credential_file"]
        and manifest["task"] == plan["task_path"],
        "approved scope changed",
    )
    prices = json.loads(checkpoint.read_bound(plan["cost"]["pricing"]))
    require(
        pricing_review
        == {
            "verified_on": datetime.now(UTC).date().isoformat(),
            "source": prices["source"],
            "usd_per_million": prices["usd_per_million"],
            "model": plan["model"],
            "service_tier": "default",
        },
        "fresh official price review is required before paid execution",
    )
    observation_comparison.clean_implementation()
    checkpoint.read_bound(manifest["rehearsal_result"])
    output = Path(manifest["live_output"])
    observation_exposure.disjoint(
        output.resolve(), (repository_root(), source.root, checkpoint.DESIGN.parent)
    )
    output.mkdir()
    journal, store = DevJournal(output, "run_dev_uptakecollection"), ArtifactStore(output)
    group = execution.Invocation(journal, started=started)
    journal.append(
        "uptake_invocation_approved",
        {
            "manifest_hash": approved_hash,
            "approved_cap_usd": str(approved_cap_usd),
            "pricing_review": pricing_review,
        },
    )
    metadata_reads = 0
    try:
        group.check()
        old = DevJournal(source.root, source.run_id).load_envelope()
        preflight_row = {
            "source": source.record(),
            "executing_probe_identity": {
                "image_digest": old.probe_image_digest,
                "profile_hash": old.probe_profile_hash,
            },
        }

        class PreflightDeadline:
            @staticmethod
            def from_remaining(seconds):
                return ExecutionDeadline(min(monotonic() + seconds, group.deadline.expires_at))

        with patch.object(observation_comparison, "ExecutionDeadline", PreflightDeadline):
            readiness = observation_comparison.check_environment(
                preflight_row, Path(plan["credential_file"])
            )
        journal.append("uptake_environment_readiness", readiness)
        require(readiness["status"] == "READY", "exact images/source/dependencies unavailable")
        group.check()
        from openai import OpenAI

        key = runner.load_exact_openai_api_key(Path(plan["credential_file"]))
        metadata_reads += 1
        journal.append("uptake_model_metadata_started", {"model": plan["model"], "attempt": 1})
        with OpenAI(
            api_key=key,
            base_url="https://api.openai.com/v1",
            max_retries=0,
            timeout=min(30, group.deadline.remaining_seconds()),
        ) as client:
            metadata = client.models.retrieve(plan["model"])
        require(metadata.id == plan["model"], "exact model unavailable")
        journal.append("uptake_model_metadata_finished", {"model": metadata.id})
    except (Exception, execution.BoundStop) as exc:
        group.stopped = True
        journal.append("uptake_preflight_stopped", {"error": type(exc).__name__})

    def prepare_row(row):
        saved, usage = checkpoint.saved_turn(row, selected)
        with patch.object(checkpoint.exposure, "ExecutionDeadline", PreflightDeadline):
            return checkpoint.restore_branch(
                source,
                plan["inheritance"]["prepared_cut_sequence"],
                selected,
                saved,
                usage,
                row,
                output / row["cell"],
                provider_free=False,
                credential_file=Path(plan["credential_file"]),
            )

    def execute_row(branch):
        return execution.run_row(
            branch, group, checkpoint.read_bound(plan["terminal_public_oracle"]).decode()
        )

    rows = execution.run_roster(plan["rows"], group, prepare_row, execute_row)
    full = store.put_json({"rows": rows})
    # Keep private verdicts out of the automatic operator summary as well as the solver.
    # Public trace uptake/repair grading must precede opening these verdicts.
    public_rows = [{k: v for k, v in row.items() if k != "result"} for row in rows]
    result = {
        "official": False,
        "rows": public_rows,
        "model_metadata_reads": metadata_reads,
        "counts": group.counts,
        "generations": group.generations,
        "provisional_cost_nanos": group.ledger.spent_nanos,
        "total_cost_known": all(r.get("billing_known", True) for r in rows),
        "verdicts_pending_public_review": full.model_dump(mode="json"),
    }
    journal.append("uptake_invocation_closed", result)
    (output / "result.json").write_text(canonical_json(result) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rehearsal-root", required=True, type=Path)
    parser.add_argument("--live-output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    print(canonical_json(prepare(args.rehearsal_root, args.live_output, args.manifest)))


if __name__ == "__main__":
    main()
