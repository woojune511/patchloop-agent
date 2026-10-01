"""Finite provider-free model responses with real registered Docker execution."""
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

from diagnostics.checkpoint_continuation import ScriptedClient, inherited_reads
from diagnostics.decision_sampler import require
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.dev import runner
from patchloop.errors import ContractError
from patchloop.runtime import git_commit


@contextmanager
def current_receipts(branch):
    original = runner._probe_evidence

    def evidence(journal, store, run_id):
        require(journal.path == branch.journal.path, "unexpected receipt journal")
        events = journal.events()
        marker = events[branch.inherited_events]
        require(marker["event_type"] == "diagnostic_checkpoint_fork"
                and marker["payload"]["source_journal_hash"] == branch.parent_journal_hash,
                "receipt lineage changed")
        historical = original(SimpleNamespace(events=lambda: events[:branch.inherited_events]),
                              store, run_id)
        for artifact in historical:
            store.read_bytes(artifact)
        current = original(SimpleNamespace(events=lambda: events[branch.inherited_events:]),
                           store, run_id)
        journal.append("review_probe_receipt_lineage", {
            "parent_journal_hash": branch.parent_journal_hash,
            "historical_receipts": [a.model_dump(mode="json") for a in historical],
            "current_receipts": [a.model_dump(mode="json") for a in current],
            "historical_receipts_are_current_execution": False,
        })
        return current

    with patch.object(runner, "_probe_evidence", evidence):
        yield


def repair(branch, client, report):
    from diagnostics.review_context_rehearsal import repair_inputs

    require(type(client) is ScriptedClient, "finite scripted transport required")
    require(branch.envelope.runtime_hash == runner._runtime_hash(), "fork runtime changed")
    require(not any(e["event_type"] == "review_integrated_started"
                    for e in branch.journal.events()[branch.inherited_events:]),
            "integrated execution cannot retry")
    branch.journal.append("review_integrated_started", {
        "provider_calls": 0, "sandbox": "real-docker", "mode": "scripted-responses",
    })
    original_active = runner._run_one_active
    head = git_commit()

    def active(**kwargs):
        return original_active(**{**kwargs, "harness_git_commit": head})

    def adapter(config, **kwargs):
        return OpenAIResponsesAdapter(config, api_key="offline-no-credential", client=client)

    def no_network(*args, **kwargs):
        raise ContractError("provider network forbidden in integrated rehearsal")

    with (inherited_reads(branch), current_receipts(branch),
          patch("socket.socket.connect", no_network),
          patch.object(runner, "load_exact_openai_api_key", lambda _: "offline-no-credential"),
          patch.object(runner, "OpenAIResponsesAdapter", adapter),
          patch.object(runner, "_run_one_active", active),
          repair_inputs(branch, report) as first, branch.journal.execution_lock()):
        result = runner._run_one_locked(
            request=branch.request, task_dir=branch.task_dir, package=branch.package,
            state_root=branch.root, pricing=branch.pricing, cost_ledger=branch.ledger,
            runtime_hash=branch.envelope.runtime_hash, model_hash=branch.envelope.model_hash,
            run_id=branch.journal.run_id, journal=branch.journal, envelope=branch.envelope,
            resuming=True,
        )
    known = (branch.journal.unresolved_provider_call() is None
             and runner._provider_usage_failure(branch.journal) is None)
    receipt = {
        "official": False, "mode": "scripted-real-sandbox", "live_model_calls": 0,
        "new_billed_cost_nanos": 0, "simulated_billing_known": known,
        "simulated_new_cost_nanos": branch.ledger.spent_nanos - branch.initial_spent_nanos
        if known else None,
        "first_state_restored": bool(first), "result": result.public,
        "stop_remaining": not known or result.stop_remaining
        or result.public["terminal"] == "PREFLIGHT_FAILED",
        "agent_efficacy": "NOT_RUN", "historical_probe_replayed": False,
    }
    branch.journal.append("review_integrated_finished", receipt)
    return receipt
