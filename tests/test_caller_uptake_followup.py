"""Real Git/artifact boundaries, with only sandbox/native execution replaced."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from diagnostics import caller_uptake as panel
from diagnostics import caller_uptake_execution as execution
from diagnostics import caller_uptake_followup as followup
from diagnostics.positive_verification_panel import save
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import TaskConstraints
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError
from patchloop.git_execution import run_git
from patchloop.repository import WorkspaceManager
from patchloop.util import sha256_bytes, sha256_json


def saved_fixture(tmp_path, monkeypatch, *, tests_only=False, stop=None):
    source, output, state = (tmp_path / name for name in ("original", "followup", "live"))
    source.mkdir()
    workspace = state / "workspaces/run_dev_fixture/repo"
    (workspace / "tests").mkdir(parents=True)
    (workspace / "src.py").write_bytes(b"value = 1\n")
    base_test = b"def test_original():\n    assert True\n"
    (workspace / "tests/test_src.py").write_bytes(base_test)
    for args in (("init", "-q"), ("config", "core.autocrlf", "false"), ("add", "."),
                 ("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                  "commit", "-qm", "base")):
        run_git(workspace, *args)
    revision = run_git(workspace, "rev-parse", "HEAD").stdout.strip()
    if not tests_only:
        (workspace / "src.py").write_bytes(b"value = 2\n")
    (workspace / "tests/test_src.py").write_bytes(
        base_test + b"\n\ndef test_addition():\n    assert 2 == 2\n")
    submitted = WorkspaceManager.diff_summary(workspace).patch_hash
    request = panel.request(tmp_path / "deps", state.parent, panel.ORDER[0]).model_copy(
        update={"state_root": state})
    public = SimpleNamespace(
        repository=SimpleNamespace(url="snapshot://fixture", base_commit=revision),
        constraints=TaskConstraints(allowed_paths=["**"], additive_test_roots=["tests"]))
    monkeypatch.setattr(execution, "load_task_package", lambda *_: SimpleNamespace(public=public))
    monkeypatch.setattr(execution, "admission_hash", lambda *_: "source")

    class LocalManager(WorkspaceManager):
        def __init__(self, fixtures, workspaces, **kwargs):
            super().__init__(fixtures, workspaces, local_source=workspace)

    monkeypatch.setattr(execution, "WorkspaceManager", LocalManager)
    monkeypatch.setattr(execution, "admit", lambda *_: SimpleNamespace(manifest_hash="deps"))
    monkeypatch.setattr(execution, "load_dependencies", lambda *_: None)
    seen = []

    class Sandbox:
        def __init__(self, **kwargs):
            pass

        def preflight(self, **kwargs):
            deadline = kwargs["deadline"]
            now = deadline.clock()
            assert now < deadline.expires_at <= now + 600

        def run_probe(self, staged, purpose, program, **kwargs):
            assert kwargs["execution_identity"]["run_id"] == followup.JOURNAL
            assert (staged / "src.py").read_bytes() == (
                b"value = 1\n" if tests_only else b"value = 2\n")
            assert (staged / "tests/test_src.py").read_bytes() == base_test
            seen.append(program)
            return {"execution_policy": {"cleanup_status": "confirmed"}}

    monkeypatch.setattr(execution, "DockerProbeSandbox", Sandbox)
    monkeypatch.setattr(execution.grading, "caller_grade", lambda *a, **kw: {
        "status": "ERROR" if stop == "caller_error" else "PASS"})

    def native(folder, req, patch, entry, deadline):
        now = deadline.clock()
        assert now < deadline.expires_at <= now + 600
        assert (folder.parent / "source-only.patch").read_bytes() == patch
        assert bool(patch) is not tests_only
        seen.append("native")
        folder.mkdir()
        save(folder, "receipt.json", {"source_only_diff": sha256_bytes(patch)})
        return "PASS" if stop == "disagreement" else "FAIL"

    monkeypatch.setattr(execution, "native_assessment", native)
    programs = {}
    for case in ("missing", "present"):
        path = source / (case + ".py")
        path.write_text(case)
        programs[case] = panel.file_ref(path)
    packet = {"live_root": str(state), "head": "original-head", "invariants": panel.invariants(),
        "native_input": {"instance_id": "fixture", "rows": programs["missing"]},
        "programs": programs, "environments": {"B": {"dependencies": {"path": "deps"}}},
        "rows": [{"row_id": label, "request": request.model_dump(mode="json")}
                 for label in panel.ORDER]}
    store = ArtifactStore(source / "sealed")
    bounds = []
    for index, label in enumerate(panel.ORDER):
        run = {"run_id": "run_dev_fixture", "artifact_hashes":
               {"submitted_patch": submitted} if index < 2 else {},
               "evaluator": {"task_acceptance": "FAIL", "safety_state": "PASS"}}
        artifact = store.put_json({"ok": True, "result": {"runs": [run]}})
        bounds.append({"row_id": label, "sealed": artifact.model_dump(mode="json")})
    save(source, "collection.json", {"rows": bounds})
    seal = {"uptake": dict.fromkeys(panel.ORDER, "NO_OBSERVED"), "exposure": []}
    refs = [panel.file_ref(source / "collection.json")]
    monkeypatch.setattr(followup, "validate_source", lambda *_: (packet, seal, [{}, {}], refs))
    monkeypatch.setattr(panel.runner, "_require_tracked_clean_paths", lambda *_: None)
    return source, output, seen


@pytest.mark.parametrize("tests_only", [False, True])
def test_saved_assessment_writes_inside_own_store_and_preserves_original(
    tmp_path, monkeypatch, tests_only,
):
    source, output, seen = saved_fixture(tmp_path, monkeypatch, tests_only=tests_only)
    before = {p.relative_to(source): p.read_bytes() for p in source.rglob("*") if p.is_file()}
    result = followup.assess_saved(source, "digest", output,
                                   expected_submissions=2, authorization="local fixture")
    assert seen == ["missing", "present", "native"] * 2
    assert result["complete"] and result["provider_calls"] == result["input_count_calls"] == 0
    assert result["execution_kind"] == "saved_patch_followup"
    assert result["arms"]["A"]["S"] == result["arms"]["B"]["S"] == 0
    after = {p.relative_to(source): p.read_bytes() for p in source.rglob("*") if p.is_file()}
    assert before == after
    assert not (source / "assessments").exists()
    assert (output / "assessments" / panel.ORDER[0] / "source-only.patch").read_bytes() == (
        b"" if tests_only else run_git(
            tmp_path / "live/workspaces/run_dev_fixture/repo", "diff", "--binary", "HEAD",
            "--", "src.py").stdout.encode())
    with pytest.raises(ContractError, match="no retry"):
        followup.assess_saved(source, "digest", output,
                              expected_submissions=2, authorization="local fixture")
    with pytest.raises(RecoveryError, match="escapes"):
        ArtifactStore(output / "artifacts").write_bytes_atomic(output / "escape.patch", b"bad")


@pytest.mark.parametrize("stop,expected", [
    ("caller_error", ["missing"]), ("disagreement", ["missing", "present", "native"]),
])
def test_failed_assessment_stops_remaining_rows_and_preserves_error(
    tmp_path, monkeypatch, stop, expected,
):
    source, output, seen = saved_fixture(tmp_path, monkeypatch, stop=stop)
    with pytest.raises(ContractError, match="stop remaining"):
        followup.assess_saved(source, "digest", output,
                              expected_submissions=2, authorization="local fixture")
    assert seen == expected and not (output / "result.json").exists()
    events = DevJournal(output, followup.JOURNAL).events()
    assert events[-2]["event_type"] == "assessment_stopped"
    assert events[-1]["event_type"] == "original_evidence_preserved"
    assert not (output / "assessments" / panel.ORDER[1]).exists()


@pytest.mark.parametrize("bad", ["scope", "overlap", "authorization"])
def test_saved_assessment_rejects_wrong_scope_before_execution(tmp_path, monkeypatch, bad):
    source, output, seen = saved_fixture(tmp_path, monkeypatch)
    with pytest.raises(ContractError):
        followup.assess_saved(source, "digest", source / "nested" if bad == "overlap" else output,
            expected_submissions=3 if bad == "scope" else 2,
            authorization="" if bad == "authorization" else "local fixture")
    assert not seen and not output.exists()


@pytest.mark.parametrize("patch", [b"patch", b""])
def test_native_empty_projection_flag_is_scoped_and_receipt_bound(tmp_path, monkeypatch, patch):
    def run(argv, **kwargs):
        assert ("--empty-source-projection" in argv) is (patch == b"")
        assert 0 < kwargs["timeout"] <= 20
        prediction = json.loads(Path(argv[argv.index("--predictions") + 1]).read_bytes())
        assert prediction["model_patch"].encode() == patch
        folder = Path(argv[argv.index("--output") + 1])
        folder.mkdir()
        save(folder, "cleanup.json", {"remaining": []})
        save(folder, "control-1.json", {"instance_id": "fixture", "complete": True,
                                       "missing_count": 0, "resolved": False})
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(execution.subprocess, "run", run)
    folder = tmp_path / "native"
    assert execution.native_assessment(folder, SimpleNamespace(model="fixture"), patch,
        {"instance_id": "fixture", "native_row": "opaque"},
        execution.assessment_deadline(10, clock=lambda: 590)) == "FAIL"
    receipt = json.loads((folder / "receipt.json").read_bytes())
    assert receipt["source_only_diff"] == sha256_bytes(patch)
    assert receipt["empty_source_projection"] is (patch == b"")


@pytest.mark.parametrize("change", ["packet", "runtime", "oracle"])
def test_saved_input_validation_rejects_unrelated_changes_before_environment_use(
    tmp_path, monkeypatch, change,
):
    packet = {"paid_authorized": False, "runtime_hash": "runtime", "invariants": {},
        "implementation": {"diagnostics/caller_uptake_grading.py": "oracle"}}
    save(tmp_path, "manifest.json", packet)
    monkeypatch.setattr(followup, "runtime_content_hash",
                        lambda: "changed" if change == "runtime" else "runtime")
    monkeypatch.setattr(panel, "invariants", lambda: {})
    monkeypatch.setattr(panel, "bindings", lambda: {
        "diagnostics/caller_uptake_grading.py": "changed" if change == "oracle" else "oracle"})
    monkeypatch.setattr(panel, "environments", lambda *a: pytest.fail("unexpected environment use"))
    with pytest.raises(ContractError, match="changed"):
        followup.validate_source(tmp_path, "wrong" if change == "packet" else sha256_json(packet))
