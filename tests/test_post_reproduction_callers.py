"""Explicit caller registration survives checkpoint preparation and fresh dispatch."""

from __future__ import annotations

import copy
import json
import shutil
import sys
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from test_caller_source_registration import caller_bundle
from test_observation_exposure import original_source, settled_source  # noqa: F401

from diagnostics import post_reproduction_repair as diagnostic
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunEnvelope
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.prepared_probe_dependencies import read_descriptor
from patchloop.util import canonical_json, sha256_bytes, sha256_json

ROOTS = {"caller-dist": "caller"}
CAP = Decimal("4.13241570")


@pytest.fixture(scope="module")
def caller_checkpoint(settled_source, original_source, tmp_path_factory):  # noqa: F811
    saved, cut, task_dir, package = settled_source
    root = tmp_path_factory.mktemp("caller-checkpoint")
    copied = root / "source"
    shutil.copytree(saved.root, copied)
    original_journal = DevJournal(saved.root, saved.run_id)
    reader = diagnostic.exposure._parent_reader(saved, original_journal.events())
    store = ArtifactStore(copied / "artifacts")
    fork = json.loads((copied / "fork.json").read_bytes())
    pending, references = list(diagnostic.exposure._artifacts(original_journal.events())), {}
    while pending:
        ref = pending.pop()
        key = sha256_json(ref.model_dump(mode="json"))
        if key in references:
            continue
        data = reader(ref)
        references[key] = [ref.model_dump(mode="json"),
                           store.put_bytes(data, ref.media_type).model_dump(mode="json")]
        if ref.media_type.startswith("application/json"):
            pending.extend(diagnostic.exposure._artifacts(json.loads(data)))
    (copied / "fork.json").write_text(canonical_json({**fork, "references": references}),
                                      encoding="utf-8")
    # Only a new synthetic source fixture changes; the shared source is immutable.
    descriptor = caller_bundle(root, package.public)
    identity = read_descriptor(descriptor)[1]
    journal = DevJournal(copied, saved.run_id)
    value = json.loads(journal.envelope_path.read_bytes())
    value.update(prepared_probe_dependencies_path=str(descriptor),
                 probe_dependencies=identity.model_dump(mode="json"),
                 probe_profile_hash=runner.probe_profile_hash(identity),
                 caller_source_roots=ROOTS)
    envelope = DevRunEnvelope.model_validate(value)
    journal.envelope_path.write_text(canonical_json(envelope.model_dump(mode="json")),
                                     encoding="utf-8")
    saved = replace(saved, root=copied,
                    envelope_hash=sha256_bytes(journal.envelope_path.read_bytes()))
    return SimpleNamespace(source=saved, cut=cut, task_dir=task_dir, package=package,
                           env_file=original_source[2], root=root)


def restore(checkpoint, root, **options):
    with patch.object(runner, "_resolve_task_file",
                      lambda _: (checkpoint.task_dir, checkpoint.package)):
        return diagnostic.restore(checkpoint.source, checkpoint.cut["sequence"], root,
                                  CAP, checkpoint.env_file, **options)


def test_fork_inherits_roots_or_binds_normalized_explicit_override(caller_checkpoint, tmp_path):
    checkpoint = caller_checkpoint
    source_journal = DevJournal(checkpoint.source.root, checkpoint.source.run_id)
    before = source_journal.path.read_bytes(), source_journal.envelope_path.read_bytes()
    inherited = restore(checkpoint, tmp_path / "inherited")
    explicit = restore(checkpoint, tmp_path / "explicit",
                       caller_source_roots={"Caller_Dist": "caller"})
    cleared = restore(checkpoint, tmp_path / "cleared", caller_source_roots={})
    for branch in (inherited, explicit):
        assert branch.request.caller_source_roots == branch.envelope.caller_source_roots == ROOTS
        assert runner._model_hash(branch.request, branch.pricing) == branch.envelope.model_hash
    assert inherited.envelope.model_hash == explicit.envelope.model_hash
    assert cleared.request.caller_source_roots == cleared.envelope.caller_source_roots == {}
    assert cleared.envelope.model_hash != inherited.envelope.model_hash
    assert "caller_source_roots" not in cleared.envelope.model_dump()
    def marker(branch):
        return json.loads((branch.root / "fork.json").read_bytes())["marker"]

    assert "caller_source_roots_override" not in marker(inherited)
    assert marker(explicit)["caller_source_roots_override"] == ROOTS
    assert marker(cleared)["caller_source_roots_override"] == {}
    model_cut = next(event for event in reversed(source_journal.events())
                     if event["event_type"] == "model_input_prepared")
    with patch.object(runner, "_resolve_task_file",
                      lambda _: (checkpoint.task_dir, checkpoint.package)):
        ordinary = diagnostic.exposure._fork(
            checkpoint.source, model_cut["sequence"], tmp_path / "ordinary", "B",
            new_cap_usd=CAP, mode="offline-scripted-only", env_file=checkpoint.env_file,
        )
    assert ordinary.request.caller_source_roots == ordinary.envelope.caller_source_roots == {}
    assert "caller_source_roots_override" not in marker(ordinary)
    assert before == (source_journal.path.read_bytes(), source_journal.envelope_path.read_bytes())


@pytest.mark.parametrize("roots,preserve,match", [
    ({"caller-dist": "caller"}, False, "preserved parent"),
    ({"caller-dist": "../private"}, True, "relative path"),
    ({"Caller_Dist": "caller", "caller-dist": "other"}, True, "unique"),
])
def test_invalid_override_rejected_before_source_read_or_output(tmp_path, roots, preserve, match):
    output = tmp_path / "never-created"
    with pytest.raises(ContractError, match=match):
        diagnostic.exposure._fork(
            None, 1, output, "B", new_cap_usd=CAP, mode="offline-scripted-only",
            env_file=tmp_path / "absent.env", preserve_parent_configuration=preserve,
            caller_source_roots=roots,
        )
    assert not output.exists()


def test_prepare_rejects_invalid_roots_before_creating_directory(tmp_path):
    output = tmp_path / "never-created"
    with pytest.raises(ContractError, match="relative path"):
        diagnostic.prepare(None, 1, tmp_path / "absent.env", tmp_path / "results", output,
                           CAP, caller_source_roots={"caller-dist": "../private"})
    assert not output.exists()


@pytest.fixture(scope="module")
def caller_prepared(caller_checkpoint, tmp_path_factory):
    checkpoint = caller_checkpoint
    root = tmp_path_factory.mktemp("caller-plan")
    with patch.object(runner, "_resolve_task_file",
                      lambda _: (checkpoint.task_dir, checkpoint.package)):
        receipt = diagnostic.prepare(
            checkpoint.source, checkpoint.cut["sequence"], checkpoint.env_file,
            root / "results", root / "prepared", CAP,
            caller_source_roots={"Caller_Dist": "caller"},
        )
    manifest = Path(receipt["manifest"])
    request = json.loads((manifest.parent / "first-request.json").read_bytes())
    return SimpleNamespace(receipt=receipt, manifest=manifest, checkpoint=checkpoint,
                           plan=json.loads(manifest.read_bytes()), request=request)


def test_prepared_scopes_match_count_dispatch_and_public_failure(caller_prepared):
    prepared = caller_prepared
    plan, audit = prepared.plan, prepared.receipt["feedback_audit"]
    assert plan["caller_source_roots"] == ROOTS
    assert audit["caller_sources"]["caller_source_roots"] == ROOTS
    assert set(audit["caller_sources"]["offered_source_tools"]) == {"read_file", "search_files"}
    assert audit["fresh_offline_dispatch_match"] and audit["original_failure_delivered"]
    assert audit["new_target_executions"] == audit["historical_opaque_items"] == 0
    assert prepared.receipt["provider_calls"] == 0
    assert "PINNED_CALLER_BODY" not in canonical_json(prepared.request["input"])
    for name in ("preview", "dispatch-rehearsal"):
        journal = DevJournal(prepared.manifest.parent / name, prepared.checkpoint.source.run_id)
        assert journal.load_envelope().caller_source_roots == ROOTS
        assert json.loads((journal.root / "fork.json").read_bytes())["marker"][
            "caller_source_roots_override"] == ROOTS
    assert diagnostic.validate(prepared.manifest, prepared.receipt["manifest_hash"], CAP) == plan


@pytest.mark.parametrize("change,match", [
    (lambda plan: plan.update(caller_source_roots={}), "unexpected caller"),
    (lambda plan: plan.update(caller_source_roots={"caller-dist": "call"}), "roots missing"),
    (lambda plan: plan.update(caller_source_roots={"Caller_Dist": "caller"}), "not normalized"),
])
def test_validate_rejects_root_drift_even_with_new_manifest_digest(
    caller_prepared, tmp_path, change, match,
):
    plan = copy.deepcopy(caller_prepared.plan)
    change(plan)
    path = tmp_path / "changed.json"
    raw = canonical_json(plan).encode()
    path.write_bytes(raw)
    with pytest.raises(ContractError, match=match):
        diagnostic.validate(path, sha256_bytes(raw), CAP)


def test_scope_audit_rejects_missing_first_turn_exploration(caller_prepared):
    request = copy.deepcopy(caller_prepared.request)
    request["tools"] = [tool for tool in request["tools"] if tool["name"] != "search_files"]
    with pytest.raises(ContractError, match="both be offered"):
        diagnostic.caller_scope_audit(request, ROOTS)


def test_collect_restores_only_manifest_mapping_before_dispatch(caller_prepared, monkeypatch):
    prepared = caller_prepared
    captured = []
    branch = SimpleNamespace(remaining_budget=prepared.plan["remaining_budget"])
    monkeypatch.setattr(diagnostic, "validate", lambda *a: copy.deepcopy(prepared.plan))
    monkeypatch.setattr(diagnostic.original, "clean_implementation", lambda: None)
    monkeypatch.setattr(diagnostic.live, "check_environment", lambda *a: {"status": "READY"})
    monkeypatch.setattr(diagnostic, "restore",
                        lambda *a, **kw: captured.append(kw) or branch)
    monkeypatch.setattr(diagnostic, "run_branch", lambda *a: {"billing_known": True})
    result = diagnostic.collect(prepared.manifest, prepared.receipt["manifest_hash"], CAP)
    assert captured == [{"funded": True, "caller_source_roots": ROOTS}]
    assert result["new_cost_nanos"] == 0


def test_prepare_cli_reuses_repeated_explicit_root_parser(monkeypatch, tmp_path):
    captured = []
    monkeypatch.setattr(diagnostic.original, "source_record", lambda *a: "source")
    monkeypatch.setattr(diagnostic, "prepare",
                        lambda *a, **kw: captured.append(kw) or {"provider_calls": 0})
    args = ["diagnostic", "prepare", "--run-id", "run_dev_fixture", "--cut-sequence", "84",
            "--new-cap-usd", str(CAP), "--caller-source", "Caller_Dist=caller",
            "--caller-source", "other=other_module"]
    for name in ("source-root", "public-task", "env-file", "result-root", "output"):
        args.extend(["--" + name, str(tmp_path / name)])
    monkeypatch.setattr(sys, "argv", args)
    diagnostic.main()
    assert captured == [{"caller_source_roots": {"caller-dist": "caller", "other": "other_module"}}]
