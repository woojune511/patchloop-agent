"""Offline preparation and dispatch binding after a real local reproduction."""

from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import test_observation_exposure as fixtures

from diagnostics import post_reproduction_repair as diagnostic
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.cost import DevCostLedger
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_json

original_source = fixtures.original_source
settled_source = fixtures.settled_source


@pytest.fixture(scope="module")
def prepared(settled_source, original_source, tmp_path_factory):
    saved, cut, task_dir, package = settled_source
    root = tmp_path_factory.mktemp("post-original-preparation")
    env_file = original_source[2]
    historical = DevJournal(saved.root, saved.run_id)
    before = historical.path.read_bytes()
    with patch.object(runner, "_resolve_task_file", lambda _: (task_dir, package)):
        receipt = diagnostic.prepare(
            saved, cut["sequence"], env_file, root / "results", root / "prepared", Decimal("2"),
        )
    assert historical.path.read_bytes() == before
    manifest = Path(receipt["manifest"])
    request = json.loads((manifest.parent / "first-request.json").read_bytes())
    prefix = [event for event in historical.events() if event["sequence"] <= cut["sequence"]]
    _, _, latest, obligation = diagnostic.exposure._settled_batch_state(
        prefix, historical.load_envelope(), package,
    )
    return SimpleNamespace(
        receipt=receipt, manifest=manifest, request=request, saved=saved, cut=cut,
        task_dir=task_dir, package=package, env_file=env_file,
        audit_branch=SimpleNamespace(latest_results=latest, original_obligation=obligation),
    )


def test_preview_delivers_latest_original_failure_without_new_execution(prepared):
    audit = prepared.receipt["feedback_audit"]
    assert audit["status"] == "PASS" and audit["original_failure_delivered"] is True
    assert audit["latest_action_ids"] == ["first-original"]
    assert len(audit["baseline_failure_case_ids"]) == 1
    assert audit["new_target_executions"] == audit["historical_opaque_items"] == 0
    assert prepared.receipt["provider_calls"] == 0
    assert prepared.receipt["paid_execution_authorized"] is False
    assert prepared.receipt["new_cap_nanos"] == 2 * 10**9
    request = prepared.request
    serialized = canonical_json(request["input"])
    assert "first-original" in serialized and "refuted" in serialized
    assert audit["baseline_failure_case_ids"][0] in serialized
    assert not any(item.get("type") == "reasoning" for item in request["input"])
    state = json.loads(request["input"][-1]["content"])["state"]
    assert state["workflow_gate"] != "needs_original_reproduction"
    journal = DevJournal(prepared.manifest.parent / "preview", prepared.saved.run_id)
    actions = [event["payload"]["tool"] for event in journal.events()
               if event["sequence"] > prepared.cut["sequence"]
               and event["event_type"] == "action_started"]
    assert actions == ["stop_task"]


def changed_state(request, change):
    result = copy.deepcopy(request)
    message = json.loads(result["input"][-1]["content"])
    change(message["state"])
    result["input"][-1]["content"] = canonical_json(message)
    return result


def test_feedback_audit_rejects_changed_original_observation(prepared):
    assert diagnostic.feedback_audit(prepared.audit_branch, prepared.request)["status"] == "PASS"

    def corrupt_observation(state):
        result = next(item for item in state["latest_tool_results"]
                      if item["action_id"] == "first-original")
        result["output"]["reproduction"]["observed_json"] = '{"tampered":true}'

    altered = changed_state(prepared.request, corrupt_observation)
    with pytest.raises(ContractError, match="call captures changed"):
        diagnostic.feedback_audit(prepared.audit_branch, altered)


def test_normalizer_ignores_only_clock_and_segment_identity(prepared):
    baseline = diagnostic.normalized_request(prepared.request)

    def clocks(state):
        state["remaining_budget"]["active_wall_time_seconds"] += 17
        state["remaining_budget"]["total_active_wall_time_seconds"] += 17
        state["remaining_budget"]["cost"]["completion_cost"]["remaining_seconds"] += 17
        state["segment_handoff"]["segment_id"] = "different-derived-id"

    clock_changed = changed_state(prepared.request, clocks)
    clock_changed["timeout"] = 1.0
    assert diagnostic.normalized_request(clock_changed) == baseline
    for field, value in (("model_calls", 999), ("tool_actions", 999)):
        altered = changed_state(prepared.request, lambda state, k=field, v=value:
                                state["remaining_budget"].update({k: v}))
        assert diagnostic.normalized_request(altered) != baseline
    altered = changed_state(prepared.request, lambda state: state.update(
        reproduction_review={"completion": {"status": "cases_verified"}},
    ))
    assert diagnostic.normalized_request(altered) != baseline


def test_offline_dispatch_matches_prepared_first_input(prepared, tmp_path):
    with patch.object(runner, "_resolve_task_file",
                      lambda _: (prepared.task_dir, prepared.package)):
        branch = diagnostic.restore(
            prepared.saved, prepared.cut["sequence"], tmp_path / "continued", Decimal("2"),
            prepared.env_file, funded=True,
        )
    client = diagnostic.stop_client()
    journal = DevJournal(tmp_path / "group", "run_dev_postrepairtest")
    result = diagnostic.run_branch(
        branch, DevCostLedger(Decimal("2"), branch.pricing), journal,
        ArtifactStore(tmp_path / "artifacts"), sha256_json(prepared.request), client=client,
    )
    assert result["result"]["terminal"] == "AGENT_STOPPED", result
    assert result["input_counts"] == result["dispatches"] == 1
    assert diagnostic.normalized_request(client.created[0]) == prepared.request
    assert not any(event["event_type"] == "probe_execution_started"
                   for event in branch.journal.events()[branch.inherited_events:])


def test_manifest_rejects_wrong_hash_cap_and_implementation_drift(prepared, monkeypatch):
    digest = prepared.receipt["manifest_hash"]
    plan = diagnostic.validate(prepared.manifest, digest, Decimal("2"))
    assert plan["new_cap_nanos"] == 2 * 10**9
    with pytest.raises(ContractError, match="manifest hash"):
        diagnostic.validate(prepared.manifest, "sha256:wrong", Decimal("2"))
    with pytest.raises(ContractError, match="approved new cap"):
        diagnostic.validate(prepared.manifest, digest, Decimal("3"))
    monkeypatch.setattr(diagnostic.exposure, "implementation_hash", lambda: "changed")
    with pytest.raises(ContractError, match="implementation drift"):
        diagnostic.validate(prepared.manifest, digest, Decimal("2"))
