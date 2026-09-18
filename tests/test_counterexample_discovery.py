"""Fresh discovery inputs must not inherit outcomes, cases or hidden material."""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from diagnostics import counterexample_discovery as design
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import PublicTask
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.prepared_probe_dependencies import MANIFEST
from patchloop.prepared_source import prepare_source
from patchloop.repository import WorkspaceManager
from patchloop.sandbox.probes import PROBE_IMAGE
from patchloop.util import directory_hash, sha256_bytes, sha256_json


@pytest.fixture(scope="module")
def inputs(tmp_path_factory):
    root = tmp_path_factory.mktemp("discovery-inputs")
    fixtures = root / "fixtures"
    origin = fixtures / "discovery-toy"
    origin.mkdir(parents=True)
    (origin / "toy.py").write_bytes(b"def value():\n    return 0\n")
    public = PublicTask.model_validate({
        "schema_version": "task-public-v1", "task_id": "discovery-toy", "split": "dev-train",
        "repository": {"url": "snapshot://discovery-toy", "base_commit": directory_hash(origin),
                       "language": "python"},
        "issue": {"title": "Public toy requirement", "description": "value() returns zero."},
        "constraints": {"allowed_paths": ["toy.py"]},
        "visible_checks": [{"id": "public-example", "command": ["python", "-c", "print(0)"]}],
    })
    task = root / "task"
    task.mkdir()
    public_path = task / "public.yaml"
    public_path.write_text(yaml.safe_dump(public.model_dump(mode="json")), encoding="utf-8")
    for name in ("private.yaml", "reference.patch", "prior-journal.jsonl", "P11-case.py", ".env"):
        (task / name).write_text("FORBIDDEN_SIBLING_SENTINEL", encoding="utf-8")
    source = prepare_source(repository_url=public.repository.url,
                            base_commit=public.repository.base_commit,
                            output=root / "prepared", fixture_root=fixtures)
    manager = WorkspaceManager(fixtures, root / "patch-export",
                               prepared_source=source,
                               prepared_source_hash=sha256_bytes(source.read_bytes()))
    workspace = manager.create("export", public.repository.url, public.repository.base_commit)
    (workspace / "toy.py").write_bytes(b"def value():\n    return 1\n")
    patch = root / "candidate" / "supplied.diff"
    patch.parent.mkdir()
    patch.write_bytes(manager.diff_summary(workspace).patch.encode())
    bundle = root / "dependencies"
    installed = bundle / "site-packages"
    installed.mkdir(parents=True)
    (installed / "dependency.py").write_bytes(b"VALUE = 2\n")
    files = {"dependency.py": sha256_bytes(b"VALUE = 2\n")}
    descriptor = bundle / MANIFEST
    descriptor.write_bytes(design.wire({
        "schema_version": "prepared-probe-dependencies-v1", "image": PROBE_IMAGE,
        "repository_url": public.repository.url, "base_commit": public.repository.base_commit,
        "python": "3.12", "platform": "linux/amd64", "source_roots": [],
        "files": files, "content_hash": sha256_json(files),
    }))
    return design.Inputs(public_path, patch, source, descriptor)


@pytest.fixture
def offline(inputs, monkeypatch):
    monkeypatch.setattr(design, "EXPECTED_HASHES", {
        name: sha256_bytes(path.read_bytes()) for name, path in inputs.paths().items()
    })

    def forbidden(*args, **kwargs):
        pytest.fail("provider/network access during offline preparation")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(OpenAIResponsesAdapter, "__init__", forbidden)
    original = subprocess.Popen

    def git_only(command, *args, **kwargs):
        assert Path(command[0]).name.lower() in {"git", "git.exe"}
        assert not {"fetch", "pull", "ls-remote"}.intersection(command)
        return original(command, *args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", git_only)
    read_bytes, read_text = Path.read_bytes, Path.read_text

    def guarded_bytes(path):
        assert path.name not in {"private.yaml", "reference.patch", "prior-journal.jsonl",
                                 "P11-case.py", ".env"}
        return read_bytes(path)

    def guarded_text(path, *args, **kwargs):
        guarded_bytes(path)
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", guarded_bytes)
    monkeypatch.setattr(Path, "read_text", guarded_text)
    return inputs


def test_only_original_public_inputs_reach_request(offline, tmp_path):
    root = tmp_path / "packet"
    packet = design.prepare(offline, root)
    assert design.validate(root) == design.validate(root) == packet
    request = json.loads((root / "request.json").read_bytes())
    assert [item["role"] for item in request["input"]] == ["system", "user"]
    context = json.loads(request["input"][1]["content"])
    assert set(context) == {"public_task", "candidate", "probe_environment", "review_limits"}
    public = design.load_public_task(offline.public_task)
    assert context["public_task"] == public.model_dump(mode="json")
    assert context["candidate"]["patch"].encode() == offline.candidate_patch.read_bytes()
    assert set(t["name"] for t in request["tools"]) == {
        "search_files", "read_file", "run_probe", "report_discovery",
    }
    assert request["model"] == design.MODEL and request["reasoning"] == {"effort": "medium"}
    assert request["max_output_tokens"] == 25_000 and request["store"] is False
    raw = design.wire(request)
    assert b"FORBIDDEN_SIBLING_SENTINEL" not in raw
    assert all(str(path).encode() not in raw for path in offline.paths().values())
    assert b"scope_reasoning" not in raw and b"profile-scope-contrast" not in raw
    assert packet["provider_calls"] == packet["input_count_calls"] == 0


@pytest.mark.parametrize("name", ["request.json", "candidate.patch", "public.yaml", "prompt.txt",
                                  "protocol.json", "packet.json"])
def test_changed_frozen_file_is_rejected(offline, tmp_path, name):
    root = tmp_path / "packet"
    design.prepare(offline, root)
    if name == "packet.json":
        packet = json.loads((root / name).read_bytes())
        packet["runtime_hash"] = "sha256:" + "0" * 64
        (root / name).write_bytes(design.wire(packet))
    else:
        with (root / name).open("ab") as stream:
            stream.write(b"CHANGED")
    with pytest.raises(ContractError, match="changed"):
        design.validate(root)


@pytest.mark.parametrize("name", list(design.EXPECTED_HASHES))
def test_wrong_task_patch_or_source_identity_never_publishes(offline, tmp_path, name):
    paths = offline.paths()
    wrong = tmp_path / "wrong" / paths[name].name
    wrong.parent.mkdir()
    wrong.write_bytes(paths[name].read_bytes() + b"CHANGED")
    paths[name] = wrong
    root = tmp_path / "packet"
    with pytest.raises(ContractError, match="identity changed"):
        design.prepare(design.Inputs(**paths), root)
    assert not root.exists()


def test_interrupted_preparation_cannot_be_reused(offline, tmp_path, monkeypatch):
    root = tmp_path / "packet"
    original = ArtifactStore.write_text_immutable

    def interrupted(store, path, content):
        if Path(path).name == "protocol.json":
            raise OSError("fixture interrupted publication")
        return original(store, path, content)

    monkeypatch.setattr(ArtifactStore, "write_text_immutable", interrupted)
    with pytest.raises(OSError, match="interrupted"):
        design.prepare(offline, root)
    assert root.is_dir() and not (root / "packet.json").exists()
    with pytest.raises(ContractError, match="fresh external"):
        design.prepare(offline, root)


def test_offline_rehearsal_reads_exact_independent_candidate_and_replays_receipt(offline, tmp_path):
    root = tmp_path / "packet"
    design.prepare(offline, root)
    first = design.rehearse(root, tmp_path / "first")
    second = design.rehearse(root, tmp_path / "second")
    assert first["status"] == second["status"] == "OFFLINE_REHEARSAL_PASS"
    assert first["candidate_hash"] == sha256_bytes(offline.candidate_patch.read_bytes())
    assert first["dependencies_verified"] and first["read_replayed_without_execution"]
    assert first["provider_calls"] == first["docker_operations"] == first["probe_executions"] == 0
    assert first["discovery_outcome"] == "NOT_RUN"
    spans = first["public_read"]["output"]["spans"]
    assert "return 1" in spans[0]["content"]
    second_file = Path(second["workspace"]) / "toy.py"
    prepared_file = offline.prepared_source.parent / "workspaces/source/repo/toy.py"
    second_bytes, prepared_bytes = second_file.read_bytes(), prepared_file.read_bytes()
    (Path(first["workspace"]) / "toy.py").write_bytes(b"local change\n")
    assert second_file.read_bytes() == second_bytes
    assert prepared_file.read_bytes() == prepared_bytes
    events = DevJournal(tmp_path / "first", "run_dev_discovery_rehearsal").events()
    assert sum(e["event_type"] == "action_started" for e in events) == 1
    assert sum(e["event_type"] == "action_finished" for e in events) == 1


def test_dependency_content_loss_stops_rehearsal_without_a_result(offline, tmp_path):
    copied_bundle = tmp_path / "copied-dependencies"
    shutil.copytree(offline.prepared_dependencies.parent, copied_bundle)
    offline = replace(offline, prepared_dependencies=copied_bundle / MANIFEST)
    root = tmp_path / "packet"
    design.prepare(offline, root)
    damaged = offline.prepared_dependencies.parent / "site-packages/dependency.py"
    damaged.write_bytes(b"changed dependency\n")
    with pytest.raises(ContractError, match="missing or changed"):
        design.rehearse(root, tmp_path / "rehearsal")
    assert not (tmp_path / "rehearsal/result.json").exists()
    assert DevJournal(tmp_path / "rehearsal", "run_dev_discovery_rehearsal").events()[-1][
        "event_type"] == "diagnostic_rehearsal_stopped"


def test_report_schema_is_strict_and_does_not_require_a_positive_claim():
    schema = design.report_schema()
    parameters = schema["parameters"]
    assert schema["strict"] and parameters["additionalProperties"] is False
    assert set(parameters["required"]) == set(parameters["properties"])
    assert {"no_counterexample_found", "blocked"} <= set(
        parameters["properties"]["outcome"]["enum"])
    for name in ("probe_action_id", "requirement_excerpt", "expected", "observed"):
        assert "null" in parameters["properties"][name]["type"]


def test_guidance_changes_only_system_instruction_and_bound_metadata(offline, tmp_path):
    original = tmp_path / "original"
    guided = tmp_path / "guided"
    control = design.prepare(offline, original)
    treatment = design.prepare(offline, guided, review_guidance="requirement-scope-v1")
    assert design.validate(original) == control
    assert design.validate(guided) == treatment
    assert "review_guidance" not in control
    assert treatment["review_guidance"] == "requirement-scope-v1"
    before = json.loads((original / "request.json").read_bytes())
    after = json.loads((guided / "request.json").read_bytes())
    assert before["input"][0] != after["input"][0]
    assert before["input"][1:] == after["input"][1:]
    after["input"][0] = before["input"][0]
    assert design.wire(after) == design.wire(before)
    assert {k for k in treatment if treatment[k] != control.get(k)} == {
        "review_guidance", "request_hash", "file_hashes"}
    assert {k for k in treatment["file_hashes"]
            if treatment["file_hashes"][k] != control["file_hashes"][k]} == {
        "request.json", "prompt.txt", "protocol.json"}


def test_case_selection_changes_only_guidance_and_probe_annotation(offline, tmp_path):
    original, selected = tmp_path / "original", tmp_path / "selected"
    before_packet = design.prepare(offline, original, review_guidance="requirement-scope-v1")
    packet = design.prepare(offline, selected, review_guidance="preservation-cases-v1")
    assert design.validate(selected) == packet
    assert packet["case_selection_implementation_hash"] == sha256_bytes(
        Path(design.case_selection.__file__).read_bytes())
    before = json.loads((original / "request.json").read_bytes())
    after = json.loads((selected / "request.json").read_bytes())
    assert after["input"][0] != before["input"][0]
    after["input"][0] = before["input"][0]
    probe = next(t for t in after["tools"] if t["name"] == "run_probe")["parameters"]
    annotation = probe["properties"].pop("case_selection")
    assert "null" in annotation["type"]
    assert set(annotation["properties"]) == set(annotation["required"]) == {
        "change", "preserve", "scope_basis", "selected"}
    assert "null" in annotation["properties"]["preserve"]["type"]
    probe["required"].remove("case_selection")
    assert design.wire(after) == design.wire(before)
    assert set(packet) - set(before_packet) == {"case_selection_implementation_hash"}


def test_applicability_contrast_adds_only_generic_guidance_and_nullable_annotation(
        offline, tmp_path):
    before_root, after_root = tmp_path / "before", tmp_path / "after"
    before_packet = design.prepare(offline, before_root, review_guidance="preservation-cases-v1")
    packet = design.prepare(offline, after_root, review_guidance="applicability-contrast-v1")
    assert design.validate(after_root) == packet
    assert set(packet) == set(before_packet)
    assert packet["case_selection_implementation_hash"] == sha256_bytes(
        Path(design.case_selection.__file__).read_bytes())
    before = json.loads((before_root / "request.json").read_bytes())
    after = json.loads((after_root / "request.json").read_bytes())
    assert after["input"][0] != before["input"][0]
    after["input"][0] = before["input"][0]
    probe = next(t for t in after["tools"] if t["name"] == "run_probe")["parameters"]
    annotation = probe["properties"]["case_selection"]
    contrast = annotation["properties"].pop("trigger_contrast")
    assert contrast["type"] == ["object", "null"]
    assert contrast["additionalProperties"] is False
    assert set(contrast["required"]) == set(contrast["properties"]) == {
        "candidate_trigger", "preserve_satisfies_trigger", "applicability_difference"}
    assert contrast["properties"]["preserve_satisfies_trigger"]["type"] == ["boolean", "null"]
    annotation["required"].remove("trigger_contrast")
    assert design.wire(after) == design.wire(before)


@pytest.mark.parametrize("guidance", design.REVIEW_GUIDANCE[1:])
@pytest.mark.parametrize("replacement", [None, "original", "unknown"])
def test_guidance_cannot_be_removed_or_switched_in_a_frozen_packet(
        offline, tmp_path, replacement, guidance):
    root = tmp_path / "packet"
    packet = design.prepare(offline, root, review_guidance=guidance)
    if replacement is None:
        packet.pop("review_guidance")
    else:
        packet["review_guidance"] = replacement
    (root / "packet.json").write_bytes(design.wire(packet))
    with pytest.raises(ContractError, match="changed|unknown review guidance"):
        design.validate(root)


def test_unknown_guidance_fails_before_source_reads(tmp_path):
    missing = design.Inputs(*(tmp_path / name for name in design.EXPECTED_HASHES))
    with pytest.raises(ContractError, match="unknown review guidance"):
        design.compile_packet(missing, review_guidance="unknown")


@pytest.mark.parametrize("guidance", design.REVIEW_GUIDANCE[1:])
def test_cli_prepares_selected_guidance_offline(offline, tmp_path, monkeypatch, capsys, guidance):
    root = tmp_path / "packet"
    args = ["prepare", "--output", str(root), "--review-guidance", guidance]
    for name, path in offline.paths().items():
        args.extend(["--" + name.replace("_", "-"), str(path)])
    monkeypatch.setattr(sys, "argv", ["counterexample_discovery", *args])
    design.main()
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "PREPARED_NOT_EXECUTABLE" and result["provider_calls"] == 0
    assert design.validate(root)["review_guidance"] == guidance
