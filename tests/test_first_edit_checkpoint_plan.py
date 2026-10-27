"""Offline first-edit preparation, fresh anchors, and whole-pair uncertainty stops."""

from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from diagnostics import first_edit_checkpoint as checkpoint
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes


def forbidden(*args, **kwargs):
    pytest.fail("offline plan validation must not execute or access credentials")


@pytest.fixture
def prepared_plan(tmp_path, monkeypatch, request):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    marker = inputs / "public-evidence.json"
    marker.write_text('{"public":"fixed"}', encoding="utf-8")

    def binding(path):
        raw = marker.read_bytes()
        return {"path": str(Path(path).resolve()), "hash": sha256_bytes(raw), "bytes": len(raw)}

    evidence = {"saved_public_evidence": [{"task": "synthetic public task"}]}
    loaded = SimpleNamespace(
        bundle={"input_bindings": [binding(marker)]},
        checkpoint=SimpleNamespace(bindings=[binding(marker)],
                                   provenance={"cutoff_sequence": 120, "helper_sequence": 113}),
        common={"evidence": evidence,
                "deduplicated_evidence": checkpoint.dedup.deduplicate(evidence)},
        requests={arm: {"model": "fixture", "input": [{"role": "user", "content": arm}]}
                  for arm in checkpoint.PROFILE.order},
    )
    monkeypatch.setattr(checkpoint, "load_inputs", lambda: loaded)
    monkeypatch.setattr(checkpoint.source, "file_binding", binding)
    monkeypatch.setattr(checkpoint, "runtime_content_hash", lambda: "fixed-runtime")
    monkeypatch.setattr(checkpoint, "git_commit", lambda: "fixed-commit")
    monkeypatch.setattr(checkpoint.loop, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(checkpoint.loop, "OpenAIResponsesAdapter", forbidden)
    monkeypatch.setattr(checkpoint.source.host, "public_checks", forbidden)
    monkeypatch.setattr(checkpoint.source, "acceptance", forbidden)
    output, result_root = tmp_path / "prepared", tmp_path / "results"
    credential = tmp_path / "never-created-or-read.env"
    receipt = checkpoint.prepare(
        output, result_root, credential, arm=getattr(request, "param", None))
    return SimpleNamespace(output=output, result_root=result_root, credential=credential,
                           receipt=receipt, manifest=output / "manifest.json", loaded=loaded,
                           marker=marker)


def test_prepare_and_validate_freeze_offline_pair_with_exact_new_budget(prepared_plan):
    case = prepared_plan
    assert all(case.receipt[key] == 0 for key in (
        "provider_calls", "input_count_calls", "credential_reads", "target_executions"))
    assert case.receipt["acceptance"] == "NOT_RUN"
    assert not case.result_root.exists() and not case.credential.exists()
    plan, loaded = checkpoint.validate(
        case.manifest, case.receipt["manifest_hash"], approved_cap_usd=Decimal("2.40"))
    assert loaded is case.loaded and plan["paid_execution_authorized"] is False
    assert plan["scope"]["order"] == ["A", "B"]
    assert plan["scope"]["row_cap_usd"] == "1.20"
    assert plan["scope"]["total_cap_usd"] == "2.40"
    assert plan["scope"]["normal_calls"] == 2 and plan["scope"]["correction_calls"] == 1
    assert plan["scope"]["tool_actions"] == 2 and plan["scope"]["accepted_mutations"] == 1
    assert plan["scope"]["diagnostic_probes"] == 0
    assert plan["scope"]["original_selection_requests"] == 0
    assert plan["scope"]["fresh_counters"] is True
    assert plan["checkpoint_provenance"] == loaded.checkpoint.provenance
    assert json.loads((case.output / "evidence.json").read_bytes()) == loaded.common
    for arm in ("A", "B"):
        assert json.loads((case.output / f"{arm}-first.json").read_bytes()) == loaded.requests[arm]


def test_collect_rejects_wrong_cap_before_validation_or_loading(monkeypatch):
    monkeypatch.setattr(checkpoint, "validate", forbidden)
    with pytest.raises(ContractError, match="cap"):
        checkpoint.collect(None, "unused", Decimal("0.60"))


@pytest.mark.parametrize("prepared_plan", ["A"], indirect=True)
def test_single_a_preparation_seals_only_a_with_one_row_cap(prepared_plan):
    case = prepared_plan
    plan, loaded = checkpoint.validate(
        case.manifest, case.receipt["manifest_hash"], approved_cap_usd=Decimal("1.20"))
    assert plan["scope"]["order"] == ["A"]
    assert plan["scope"]["row_cap_usd"] == plan["scope"]["total_cap_usd"] == "1.20"
    assert set(plan["first_request_hashes"]) == {"A"}
    assert json.loads((case.output / "A-first.json").read_bytes()) == loaded.requests["A"]
    assert not (case.output / "B-first.json").exists()
    assert plan["paid_execution_authorized"] is False
    assert not case.result_root.exists() and not case.credential.exists()
    assert all(case.receipt[key] == 0 for key in (
        "provider_calls", "input_count_calls", "credential_reads", "target_executions"))


@pytest.mark.parametrize("prepared_plan,cap", [("A", "2.40"), (None, "1.20")],
                         indirect=["prepared_plan"])
def test_selected_manifest_cap_mismatch_stops_before_credentials_or_loading(
    prepared_plan, monkeypatch, cap,
):
    case = prepared_plan
    monkeypatch.setattr(checkpoint, "load_inputs", forbidden)
    with pytest.raises(ContractError, match="cap"):
        checkpoint.collect(case.manifest, case.receipt["manifest_hash"], Decimal(cap))
    assert not case.result_root.exists() and not case.credential.exists()


def test_single_b_is_not_an_authorized_preparation_selection(tmp_path, monkeypatch):
    monkeypatch.setattr(checkpoint, "load_inputs", forbidden)
    with pytest.raises(ContractError):
        checkpoint.prepare(tmp_path / "prepared", tmp_path / "results", tmp_path / "unread.env",
                           arm="B")
    assert not (tmp_path / "prepared").exists()


@pytest.mark.parametrize("change,match", [
    ("approval_hash", "approved manifest hash differs"),
    ("approval_cap", "cap"),
    ("runtime", "runtime changed"),
    ("bound_file", "bound code or evidence changed"),
])
def test_validate_rejects_approval_or_binding_drift_before_loading(
    prepared_plan, monkeypatch, change, match,
):
    case = prepared_plan
    digest, cap = case.receipt["manifest_hash"], checkpoint.PROFILE.invocation_cap
    if change == "approval_hash":
        digest = sha256_bytes(b"different approved manifest")
    elif change == "approval_cap":
        cap = Decimal("2.41")
    elif change == "runtime":
        monkeypatch.setattr(checkpoint, "runtime_content_hash", lambda: "changed-runtime")
    else:
        case.marker.write_text("changed public source", encoding="utf-8")
    monkeypatch.setattr(checkpoint, "load_inputs", forbidden)
    with pytest.raises(ContractError, match=match):
        checkpoint.validate(case.manifest, digest, approved_cap_usd=cap)


@pytest.mark.parametrize("filename,match", [
    ("evidence.json", "prepared public evidence changed"),
    ("A-first.json", "prepared request changed"),
    ("B-first.json", "prepared request changed"),
])
def test_validate_rejects_changed_prepared_payload(prepared_plan, filename, match):
    case = prepared_plan
    (case.output / filename).write_text("{}", encoding="utf-8")
    with pytest.raises(ContractError, match=match):
        checkpoint.validate(case.manifest, case.receipt["manifest_hash"])


def test_validate_rejects_changed_checkpoint_provenance(prepared_plan):
    case = prepared_plan
    case.loaded.checkpoint.provenance["cutoff_sequence"] = 121
    with pytest.raises(ContractError, match="prepared public evidence changed"):
        checkpoint.validate(case.manifest, case.receipt["manifest_hash"])


def test_validate_rejects_scope_change_even_if_manifest_hash_is_reapproved(prepared_plan):
    case = prepared_plan
    plan = json.loads(case.manifest.read_bytes())
    plan["scope"]["accepted_mutations"] = 2
    case.manifest.write_text(canonical_json(plan), encoding="utf-8")
    with pytest.raises(ContractError, match="experiment scope changed"):
        checkpoint.validate(case.manifest, sha256_bytes(case.manifest.read_bytes()))


def test_prepare_rejects_existing_result_directory(prepared_plan):
    case = prepared_plan
    case.result_root.mkdir()
    with pytest.raises(ContractError, match="fresh output root required"):
        checkpoint.prepare(case.output.with_name("another-plan"), case.result_root, case.credential)


def test_saved_gateway_registers_all_extra_source_anchors_and_resets_allowances(
    tmp_path, monkeypatch,
):
    first = {"path": "project.py", "start_line": 1, "end_line": 1,
             "content": "FIRST = 1", "file_hash": "source-hash"}
    extra = {**first, "start_line": 2, "end_line": 2, "content": "SECOND = 2"}
    wider = {**first, "end_line": 2, "content": "FIRST = 1\nSECOND = 2"}
    loaded = SimpleNamespace(
        bundle={"source_packets": {"R1": [first]}},
        checkpoint=SimpleNamespace(workspace_spans=[copy.deepcopy(first), extra, wider],
                                   provenance={"historical_normal_calls": 14}),
    )
    events = [{"event_type": "action_started"}, {"event_type": "action_started"}]
    journal = SimpleNamespace(events=lambda: copy.deepcopy(events),
                              append=lambda kind, payload: events.append(
                                  {"event_type": kind, "payload": payload}))
    gateway = SimpleNamespace(journal=journal, current_diff_hash=checkpoint.source.SEED_HASH,
                              limits=SimpleNamespace(max_tool_actions=100, max_model_calls=40,
                                                     max_accepted_mutations=4), deadline=None)
    restored, observed = [], []

    def saved(value, root, arm):
        restored.append((value, root, arm))
        return gateway

    def observe(value, spans):
        assert value is gateway
        observed.extend(spans)
        events.extend({"event_type": "action_started"} for _ in spans)

    monkeypatch.setattr(checkpoint.source, "saved_gateway", saved)
    monkeypatch.setattr(checkpoint.source, "observe_sources", observe)
    result = checkpoint.saved_gateway(loaded, tmp_path / "fresh")
    assert result is gateway and restored == [(loaded, tmp_path / "fresh", "R1")]
    assert observed == [extra, wider]
    assert gateway.limits.max_tool_actions == 4 + 2
    assert gateway.limits.max_model_calls == 2 + 1
    assert gateway.limits.max_accepted_mutations == 1
    assert 0 < gateway.deadline.remaining_seconds() <= checkpoint.loop.MODEL_SECONDS
    ready = events[-1]
    assert ready["event_type"] == "checkpoint_stage_ready"
    assert ready["payload"]["host_source_reads"] == 4
    assert ready["payload"]["historical_actions_imported"] is False
    assert ready["payload"]["fresh_normal_calls"] == ready["payload"]["fresh_tool_actions"] == 2


@pytest.mark.parametrize("uncertainty", ["count", "provider"])
@pytest.mark.parametrize("raise_error", [False, True])
def test_collection_stops_all_rows_on_count_or_provider_uncertainty(
    tmp_path, monkeypatch, uncertainty, raise_error,
):
    root = tmp_path / "collection"
    plan = {"scope": checkpoint.scope(), "result_root": str(root), "bindings": [],
            "credential_file": str(tmp_path / "not-read.env"),
            "first_request_hashes": {"A": "sealed-a", "B": "sealed-b"},
            "interpretation": "synthetic collection"}
    loaded = SimpleNamespace()
    monkeypatch.setattr(checkpoint, "validate", lambda *args, **kwargs: (plan, loaded))
    monkeypatch.setattr(checkpoint.loop.runner, "_require_tracked_clean_paths", lambda *args: None)
    monkeypatch.setattr(checkpoint, "runtime_content_paths", lambda: [])
    monkeypatch.setattr(checkpoint, "git_commit", lambda: "fixture-commit")
    started, closed, requested = [], [], []

    def saved(value, target):
        assert value is loaded
        started.append(target.name)
        return SimpleNamespace(current_diff_hash=checkpoint.source.SEED_HASH)

    monkeypatch.setattr(checkpoint, "saved_gateway", saved)
    monkeypatch.setattr(checkpoint, "OriginalCallRecheck", lambda *args, **kwargs: object())
    monkeypatch.setattr(checkpoint.loop, "load_exact_openai_api_key", lambda path: "fixture-only")
    monkeypatch.setattr(checkpoint.loop, "OpenAIResponsesAdapter", lambda *args, **kwargs:
                        SimpleNamespace(client=SimpleNamespace(close=lambda: closed.append(True))))
    monkeypatch.setattr(checkpoint.source.host, "public_checks", forbidden)
    monkeypatch.setattr(checkpoint.source, "acceptance", forbidden)

    def model(value, arm, gateway, adapter, group, **kwargs):
        assert value is loaded and arm == "A"
        assert group.remaining_nanos == 2_400_000_000
        assert kwargs["first_hash"] == "sealed-a" and kwargs["profile"] == checkpoint.PROFILE
        requested.append(arm)
        if raise_error:
            raise ContractError(f"{uncertainty} uncertainty")
        return {"stop_remaining": True, "new_mutations": 1,
                "terminal": f"{uncertainty.upper()}_UNCERTAIN"}

    monkeypatch.setattr(checkpoint.loop, "run_model", model)
    arguments = (tmp_path / "prepared/manifest.json", "approved", checkpoint.PROFILE.invocation_cap)
    if raise_error:
        with pytest.raises(ContractError, match=f"{uncertainty} uncertainty"):
            checkpoint.collect(*arguments)
        assert not (root / "result.json").exists()
    else:
        result = checkpoint.collect(*arguments)
        assert result["allocation_closed"] and result["cost_nanos"] == 0
        assert [row["arm"] for row in result["rows"]] == ["A"]
        assert result["rows"][0]["terminal"] == f"{uncertainty.upper()}_UNCERTAIN"
    assert started == requested == ["A"] and closed == [True]
    assert not (root / "B").exists()
    events = DevJournal(root, "run_dev_firsteditcomparison").events()
    assert events[-1]["event_type"] == ("collection_interrupted" if raise_error else "closed")


@pytest.mark.parametrize("order,cap", [(("A",), "1.20"), (("A", "B"), "2.40")])
def test_collection_runs_only_manifest_selected_arms_with_exact_group_cap(
    tmp_path, monkeypatch, order, cap,
):
    selected_cap = Decimal(cap)
    plan = {"scope": checkpoint.scope(order), "result_root": str(tmp_path / "collection"),
            "bindings": [], "credential_file": str(tmp_path / "not-read.env"),
            "first_request_hashes": {arm: f"sealed-{arm}" for arm in order},
            "interpretation": "synthetic selected trial"}
    monkeypatch.setattr(checkpoint, "validate", lambda *args, **kwargs: (plan, SimpleNamespace()))
    monkeypatch.setattr(checkpoint.loop.runner, "_require_tracked_clean_paths", lambda *args: None)
    monkeypatch.setattr(checkpoint, "runtime_content_paths", lambda: [])
    monkeypatch.setattr(checkpoint, "git_commit", lambda: "fixture-commit")
    started, requested, closed, credentials = [], [], [], []
    monkeypatch.setattr(checkpoint, "saved_gateway",
                        lambda _loaded, root: started.append(root.name))
    monkeypatch.setattr(checkpoint, "OriginalCallRecheck", lambda *args, **kwargs: None)

    def credential(path):
        credentials.append(path)
        return "fixture-key"

    monkeypatch.setattr(checkpoint.loop, "load_exact_openai_api_key", credential)
    monkeypatch.setattr(checkpoint.loop, "OpenAIResponsesAdapter", lambda *args, **kwargs:
                        SimpleNamespace(client=SimpleNamespace(close=lambda: closed.append(True))))
    monkeypatch.setattr(checkpoint.source.host, "public_checks", forbidden)
    monkeypatch.setattr(checkpoint.source, "acceptance", forbidden)

    def model(_loaded, arm, _gateway, _adapter, group, **kwargs):
        requested.append(arm)
        assert group.remaining_nanos == int(selected_cap * 1_000_000_000)
        assert kwargs["first_hash"] == f"sealed-{arm}" and kwargs["profile"] == checkpoint.PROFILE
        return {"stop_remaining": False, "new_mutations": 0, "task_acceptance": "NOT_RUN"}

    monkeypatch.setattr(checkpoint.loop, "run_model", model)
    result = checkpoint.collect(tmp_path / "prepared/manifest.json", "approved", selected_cap)
    assert started == requested == list(order)
    assert [row["arm"] for row in result["rows"]] == list(order)
    assert len(credentials) == len(closed) == len(order)
    assert result["allocation_closed"] and result["cost_nanos"] == 0
