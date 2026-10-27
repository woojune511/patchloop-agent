"""Finite feedback/source continuation tests, without provider or target execution."""
from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_exception_frame_repair import edit_call, no_external, stop_call  # noqa: F401

from diagnostics import feedback_source as d
from diagnostics.checkpoint_continuation import ScriptedClient
from patchloop.dev.context import source_lines
from patchloop.dev.contracts import RequestedTool
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.errors import ContractError
from patchloop.repository import WorkspaceManager
from patchloop.util import canonical_json, sha256_bytes, sha256_json


def bundle(monkeypatch):
    seed = "public saved patch\n"
    monkeypatch.setattr(d, "SEED_HASH", sha256_bytes(seed.encode()))
    lines = [f"source line {index}" for index in range(1, 677)]

    def span(start, end):
        return {"path": "astroid/modutils.py", "start_line": start, "end_line": end,
                "content": "\n".join(lines[start - 1:end]), "file_hash": d.FILE_HASH}

    return {"common": {"saved_patch": seed, "hypothesis": "unverified authored hypothesis",
                        "post_edit_failure": {"stdout": "F0010"}},
            "source_packets": {"R0": [span(265, 273)],
                               "R1": [span(1, 400), span(401, 676)]},
            "seed_patch": seed, "input_bindings": [],
            "provenance": {"candidate_diff_hash": d.SEED_HASH}}


def common(value):
    return {"feedback": {**value["common"], "public_task": {"description": "original issue"}},
            "source_packets": value["source_packets"]}


def test_pair_only_changes_source_in_normal_and_correction(monkeypatch):
    data = common(bundle(monkeypatch))
    for options in ({}, {"history": [{"role": "user", "content": "same public result"}],
                        "remaining": {"normal_calls": 3, "tool_actions": 4},
                        "correction": "invalid request", "probe_used": True}):
        requests = [d.request_payload(data, arm, **options) for arm in d.PROFILE.order]
        d.verify_pair(*requests)
        assert requests[0]["model"] == requests[1]["model"] == d.loop.MODEL
        assert requests[0]["tools"] == requests[1]["tools"]
        for request in requests:
            encoded = canonical_json(request)
            assert "original issue" in encoded and "public saved patch" in encoded
            read = next(tool for tool in request["tools"] if tool["name"] == "read_file")
            assert read["parameters"]["properties"]["start_line"]["type"] == "integer"
            assert read["parameters"]["properties"]["end_line"]["type"] == "integer"
            assert request["max_output_tokens"] == (25_000 if options else 40_000)
        requests[1]["max_output_tokens"] += 1
        with pytest.raises(ContractError, match="beyond"):
            d.verify_pair(*requests)


@pytest.mark.parametrize("change", ["range", "content", "patch", "field", "source_hash"])
def test_bundle_rejects_changed_source_or_seed(monkeypatch, change):
    value = bundle(monkeypatch)
    d.validate_bundle(value)
    if change == "range":
        value["source_packets"]["R1"][1]["start_line"] = 402
    elif change == "content":
        value["source_packets"]["R0"][0]["content"] = "\n".join(["different"] * 9)
    elif change == "patch":
        value["common"]["saved_patch"] = "missing full diff"
    elif change == "field":
        value["unlisted"] = "must not be projected"
    else:
        value["source_packets"]["R1"][0]["file_hash"] = "sha256:" + "0" * 64
    with pytest.raises(ContractError):
        d.validate_bundle(value)


def test_load_inputs_includes_issue_and_exact_public_original_request(
    monkeypatch, tmp_path, smoke_package,
):
    value = bundle(monkeypatch)
    public = smoke_package.public.model_copy(update={"split": "dev-train"})
    public_path, source, deps = (tmp_path / name for name in
                                 ("public.yaml", "prepared-source.json", "dependencies.json"))
    public_path.write_text(public.model_dump_json(), encoding="utf-8")
    public_path.with_name("environment.yaml").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(d.TaskEnvironment, "model_validate", lambda _: SimpleNamespace())
    source.write_text("source identity", encoding="utf-8")
    deps.write_text("dependency identity", encoding="utf-8")
    original = {"python_source": "print('original public caller')", "purpose": {"kind": "helper"}}
    calibration = tmp_path / "calibration.json"
    calibration.write_text(json.dumps({"original_arguments": original}), encoding="utf-8")
    for key, path in (("PUBLIC", public_path), ("SOURCE", source), ("DEPENDENCIES", deps),
                      ("CALIBRATION", calibration)):
        monkeypatch.setattr(d.host, key, path)
    monkeypatch.setattr(d.host, "DEPENDENCY_HASH", sha256_bytes(deps.read_bytes()))
    monkeypatch.setattr(d.host, "CALIBRATION_HASH", sha256_bytes(calibration.read_bytes()))
    value["provenance"].update(public_task_path=str(public_path),
        public_hash=sha256_bytes(public_path.read_bytes()), prepared_source_path=str(source),
        prepared_source_hash=d.host.SOURCE_HASH, original_arguments=original)
    monkeypatch.setattr(d, "build_packet_bundle", lambda: copy.deepcopy(value))
    monkeypatch.setattr(d, "load_source", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(d, "read_descriptor", lambda _: ({}, "identity"))
    monkeypatch.setattr(d, "load_dependencies", lambda *_: SimpleNamespace(environment=None))
    loaded = d.load_inputs()
    assert loaded.common["feedback"]["public_task"] == public.model_dump(mode="json")
    assert loaded.original_arguments == original
    for request in loaded.requests.values():
        feedback = json.loads(request["input"][1]["content"])["public_feedback"]
        assert feedback["public_task"] == public.model_dump(mode="json")
    value["provenance"]["original_arguments"] = {"python_source": "changed"}
    with pytest.raises(ContractError, match="original host request"):
        d.load_inputs()


def test_prepare_and_validate_are_offline_and_preserve_frozen_requests(tmp_path, monkeypatch):
    value = bundle(monkeypatch)
    data = common(value)
    loaded = SimpleNamespace(bundle=value,
        requests={arm: d.request_payload(data, arm) for arm in d.PROFILE.order})
    monkeypatch.setattr(d, "load_inputs", lambda: loaded)
    monkeypatch.setattr(d, "file_binding", lambda path: {
        "path": str(Path(path).resolve()), "hash": "fixture", "bytes": 1})
    output = tmp_path / "plan"
    receipt = d.prepare(output, tmp_path / "live", tmp_path / "unread.env")
    assert receipt["credential_reads"] == receipt["provider_calls"] == 0
    plan, _ = d.validate(output / "manifest.json", receipt["manifest_hash"])
    assert plan["paid_execution_authorized"] is False
    assert plan["scope"]["starting_diff"] == d.SEED_HASH
    assert plan["scope"]["total_cap_usd"] == "2.40" and plan["scope"]["read_range_only"]
    before = (output / "manifest.json").read_bytes()
    with pytest.raises(ContractError, match="fresh output root"):
        d.prepare(output, tmp_path / "live", tmp_path / "unread.env")
    assert (output / "manifest.json").read_bytes() == before
    (output / "R0-first.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ContractError, match="prepared request changed"):
        d.validate(output / "manifest.json", receipt["manifest_hash"])


def test_restore_seed_register_anchors_and_allow_exactly_one_additional_edit(
    gateway_factory, monkeypatch, tmp_path,
):
    existing, _, workspace = gateway_factory()
    path = workspace / "mini_data_utils/csvlite.py"
    base = path.read_bytes().replace(b"\r\n", b"\n")
    path.write_bytes(base + b"\n# synthetic saved state\n")
    seed = WorkspaceManager.diff_summary(workspace)
    raw = path.read_bytes()
    lines = source_lines(raw.decode())
    spans = [{"path": "mini_data_utils/csvlite.py", "start_line": 1, "end_line": len(lines),
              "content": "\n".join(lines), "file_hash": sha256_bytes(raw)}]
    path.write_bytes(base)
    monkeypatch.setattr(d, "SEED_HASH", seed.patch_hash)

    class Manager:
        diff_summary = staticmethod(WorkspaceManager.diff_summary)
        apply_patch = staticmethod(WorkspaceManager.apply_patch)

        def __init__(self, *_args, **_kwargs):
            pass

        def create(self, *_args, **_kwargs):
            return workspace

    monkeypatch.setattr(d, "WorkspaceManager", Manager)
    monkeypatch.setattr(d, "DockerProbeSandbox", lambda **_: SimpleNamespace(preflight=lambda **_: {
        "image_digest": d.host.PROBE_IMAGE, "profile_hash": d.host.PROBE_PROFILE}))
    monkeypatch.setattr(d, "DockerSandbox", lambda _: SimpleNamespace(
        image_identity=lambda **_: "public-image"))
    packets = {arm: spans for arm in d.PROFILE.order}
    loaded = SimpleNamespace(public=existing.public_task,
        dependencies=SimpleNamespace(identity=SimpleNamespace(manifest_hash=d.host.DEPENDENCY_HASH)),
        environment=SimpleNamespace(evaluator_image="public-image", image_digest="public-image"),
        bundle={"seed_patch": seed.patch, "source_packets": packets},
        common={"feedback": {"saved_patch": seed.patch}, "source_packets": packets})
    gateway = d.saved_gateway(loaded, tmp_path / "restored", "R0")
    assert gateway.current_diff_hash == seed.patch_hash and gateway.accepted_mutations == 0
    assert gateway.read_range_only is True and gateway.limits.max_tool_actions == 13
    client = ScriptedClient([[edit_call()], [stop_call()]])
    adapter = d.loop.OpenAIResponsesAdapter(d.loop.config(), api_key="", client=client)
    group = DevCostLedger(d.PROFILE.invocation_cap, pricing_for_model(d.loop.MODEL))
    result = d.loop.run_model(loaded, "R0", gateway, adapter, group,
        first_hash=sha256_json(d.request_payload(loaded.common, "R0")), profile=d.PROFILE,
        request_builder=d.request_payload)
    assert result["terminal"] == "CANDIDATE_PRODUCED" and result["new_mutations"] == 1
    assert result["normal_calls"] == result["tool_actions"] == len(client.created) == 1
    assert result["candidate_diff_hash"] != seed.patch_hash
    assert len([event for event in gateway.journal.events()
                if event["event_type"] == "action_finished"]) == 2


def test_cap_approval_precedes_all_loading(monkeypatch):
    monkeypatch.setattr(d, "validate", lambda *_: pytest.fail("must reject before loading"))
    with pytest.raises(ContractError, match="exact new cap"):
        d.collect(None, "none", Decimal("1.20"))


@pytest.mark.parametrize("wide", [False, True])
def test_only_delivered_current_ranges_become_editable(gateway_factory, monkeypatch, wide):
    gateway, _, workspace = gateway_factory()
    gateway.agent_policy = "thin"
    gateway.read_range_only = True
    raw = (workspace / "mini_data_utils/csvlite.py").read_bytes()
    lines = source_lines(raw.decode())
    end = len(lines) if wide else 1
    spans = [{"path": "mini_data_utils/csvlite.py", "start_line": 1, "end_line": end,
              "content": "\n".join(lines[:end]), "file_hash": sha256_bytes(raw)}]
    monkeypatch.setattr(d, "SEED_HASH", gateway.current_diff_hash)
    d.observe_sources(gateway, spans)
    # The hypothetical common diff is not an imported observation: only reads count.
    result = gateway.execute(RequestedTool(**edit_call()))
    assert (result.status == "succeeded" and result.error_code is None) is wide
    assert gateway.accepted_mutations == int(wide)


@pytest.mark.parametrize("stop", ["model", "host", "acceptance", "none", "no_diff"])
def test_collection_stops_on_uncertainty_and_evaluates_semantic_failures(
    tmp_path, monkeypatch, stop,
):
    plan = {"result_root": str(tmp_path / "live"), "bindings": [],
        "credential_file": "unread.env", "first_request_hashes": {"R0": "r0", "R1": "r1"},
        "interpretation": "synthetic controlled pair"}
    monkeypatch.setattr(d, "validate", lambda *_: (plan, SimpleNamespace()))
    monkeypatch.setattr(d.loop.runner, "_require_tracked_clean_paths", lambda *_: None)
    arms, accepted = [], []

    def gateway(_, root, arm):
        arms.append(arm)
        return SimpleNamespace(current_diff_hash=d.host.EMPTY_DIFF
            if stop == "no_diff" and arm == "R0" else d.SEED_HASH)

    monkeypatch.setattr(d, "saved_gateway", gateway)
    monkeypatch.setattr(d.loop, "load_exact_openai_api_key", lambda _: "synthetic")
    monkeypatch.setattr(d.loop, "OpenAIResponsesAdapter", lambda *_args, **_kwargs: SimpleNamespace(
        client=SimpleNamespace(close=lambda: None)))
    monkeypatch.setattr(d.loop, "run_model", lambda *_args, **_kwargs: {
        "stop_remaining": stop == "model", "terminal": "CANDIDATE_PRODUCED"})

    def checks(*_):
        if stop == "host":
            raise ContractError("unsettled host cleanup")
        return {"regression_passed": True, "public_cases_passed": False}

    monkeypatch.setattr(d.host, "public_checks", checks)

    def opaque(_, root, passed):
        accepted.append((root.parent.name, passed))
        if stop == "acceptance":
            raise ContractError("unsettled opaque evaluation")
        return {"acceptance": "fail"}

    monkeypatch.setattr(d.host, "acceptance", opaque)
    arguments = (tmp_path / "plan/manifest.json", "hash", d.PROFILE.invocation_cap)
    if stop in {"host", "acceptance"}:
        with pytest.raises(ContractError, match="unsettled"):
            d.collect(*arguments)
    else:
        result = d.collect(*arguments)
        assert result["allocation_closed"]
        if stop == "no_diff":
            skipped = result["rows"][0]["acceptance"]
            assert skipped["status"] == "NOT_RUN_NO_DIFF" and not skipped["stop_remaining"]
            assert skipped["candidate_patch_hash"] == d.host.EMPTY_DIFF
            assert skipped["evaluator_dispatches"] == 0
    assert arms == (["R0", "R1"] if stop in {"none", "no_diff"} else ["R0"])
    expected = {"none": [("R0", True), ("R1", True)], "no_diff": [("R1", True)],
                "acceptance": [("R0", True)]}
    assert accepted == expected.get(stop, [])
