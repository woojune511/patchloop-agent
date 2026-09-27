from __future__ import annotations

import copy
import json
from contextlib import nullcontext
from decimal import Decimal
from types import SimpleNamespace

import pytest

from diagnostics import probe_boundary_collector as collector
from patchloop.artifacts import ArtifactStore
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes


def test_overlay_is_exact_and_other_inputs_are_normally_validated(tmp_path, monkeypatch):
    store = ArtifactStore(tmp_path)
    system = {"role": "system", "content": "before" + collector.REMOVED + "after"}
    old = [{"role": "system", "content": "beforeafter"}, {"content": "old state"}]
    artifact = store.put_json(old)
    branch = SimpleNamespace(store=store, references={}, source_request={"input": [system]},
                             journal=SimpleNamespace(events=lambda: [{
                                 "event_type": "turn_started", "payload": {
                                     "model_input_artifact": artifact.model_dump(mode="json")}}]))
    seen = []
    monkeypatch.setattr(collector.guidance, "inputs", lambda _: nullcontext())
    monkeypatch.setattr(collector.segments, "validate_input_binding",
                        lambda items, binding, store: seen.append(copy.deepcopy(items)))
    changed = copy.deepcopy(old)
    changed[1]["content"] = "different state"
    with collector.inputs(branch):
        collector.segments.validate_input_binding(old, {}, store)
        collector.segments.validate_input_binding(changed, {}, store)
    assert seen[0] == [system, old[1]]
    assert seen[1] == changed  # No normalization of a merely similar request.
    assert old[0]["content"] == "beforeafter"


def test_funding_changes_only_cost_preserving_work_and_time():
    budget = {"model_calls": 12, "tool_actions": 60, "accepted_mutations": 1,
              "active_wall_time_seconds": 3567,
              "cost": {"settled_usage": 4_314_153_500, "invocation_cap": 7_102_528_000,
                       "remaining": 2_788_374_500}}
    source = {"input": [{"content": canonical_json({"state": {"remaining_budget": budget}})}]}
    funded = collector.fund(source, 3_000_000_000)
    actual = json.loads(funded["input"][-1]["content"])["state"]["remaining_budget"]
    assert actual == {**budget, "cost": {"settled_usage": 4_314_153_500,
                                         "invocation_cap": 7_314_153_500,
                                         "remaining": 3_000_000_000}}
    assert json.loads(source["input"][-1]["content"])["state"]["remaining_budget"] == budget


def test_approval_hash_rejected_before_controls_or_side_effects(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}")
    monkeypatch.setattr(collector, "controls", lambda *a: pytest.fail("must not reach controls"))
    with pytest.raises(ContractError, match="manifest hash"):
        collector.collect(manifest, "wrong", Decimal("3"))


def test_changed_cap_rejected_before_result_root_creation(tmp_path, monkeypatch):
    root = tmp_path / "results"
    plan = {"source_root": str(tmp_path / "source"), "env_file": str(tmp_path / ".env"),
            "result_root": str(root), "new_cap_nanos": 3_000_000_000}
    manifest = tmp_path / "manifest.json"
    manifest.write_text(canonical_json(plan))
    monkeypatch.setattr(collector, "controls", lambda *a: {**plan, "new_cap_nanos": 4_000_000_000})
    with pytest.raises(ContractError, match="controls changed"):
        collector.collect(manifest, sha256_bytes(manifest.read_bytes()), Decimal("4"))
    assert not root.exists()


def test_failed_preflight_consumes_root_without_restore_or_retry(tmp_path, monkeypatch):
    root = tmp_path / "results"
    plan = {"source_root": str(tmp_path / "source"), "env_file": str(tmp_path / ".env"),
            "result_root": str(root), "new_cap_nanos": 3_000_000_000,
            "model": "gpt-5.4-2026-03-05", "packet_hash": "test"}
    manifest = tmp_path / "manifest.json"
    manifest.write_text(canonical_json(plan))
    monkeypatch.setattr(collector, "controls", lambda *a: plan)
    monkeypatch.setattr(collector.runner, "_require_tracked_clean_paths", lambda *a: None)
    monkeypatch.setattr(collector.live, "check_environment", lambda *a: {"status": "FAILED"})
    monkeypatch.setattr(collector, "restore", lambda *a: pytest.fail("must not restore"))
    digest = sha256_bytes(manifest.read_bytes())
    result = collector.collect(manifest, digest, Decimal("3"))
    assert result["row"]["status"] == "NOT_RUN"
    assert result["new_cost_nanos"] == 0
    with pytest.raises(FileExistsError):
        collector.collect(manifest, digest, Decimal("3"))
