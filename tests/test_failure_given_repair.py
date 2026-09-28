from __future__ import annotations

import ast
import copy
import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from test_counterexample_review import request_at_submission

from diagnostics import failure_given_repair as design
from patchloop.dev.conversation import assemble_model_input, history_metadata, reconstruct_state
from patchloop.dev.state import DevJournal
from patchloop.util import sha256_bytes, sha256_json


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    request = request_at_submission()
    view = json.loads(request["input"][-1]["content"])
    diff = view["state"]["current_diff"]
    diff["patch_hash"] = sha256_bytes(diff["patch"].encode())
    for check in view["state"]["visible_check_status"]:
        check["diff_hash"] = diff["patch_hash"]
    view["state"]["current_sources"] = [{"path": "pyfakefs/fake_os.py", "file_hash": "source"}]
    request["input"][-1]["content"] = design.wire(view).decode()
    checkpoint = {"source_run_id": design.seed.SOURCE_ID, "base_commit": "base"}
    root, source_root = tmp_path / "evidence", tmp_path / "old-state"
    root.mkdir()
    source_root.mkdir()
    spec = tmp_path / "public.yaml"
    spec.write_text("PUBLIC_SPEC", encoding="utf-8")
    monkeypatch.setattr(design, "PUBLIC_SPEC", spec)
    monkeypatch.setattr(design, "runtime_content_hash", lambda: "runtime")
    case = {"id": "multi_parent", "path": "a/../b/../c", "requirement": "traversal side effects"}
    other = {"id": "other", "path": "OTHER_CASE_SENTINEL"}
    probe = f"CASES = {[case, other]!r}\n\ndef main():\n    return CASES\n".encode()
    subject = {"subject": "A2", "diff_hash": diff["patch_hash"], "source_hash": "source",
               "run_id": design.seed.SOURCE_ID, "workspace": "unused"}
    packet = {"cases": [case, other], "subjects": [subject], "baseline_commit": "base",
              "runtime_hash": "runtime", "public_spec_path": str(spec),
              "public_spec_hash": sha256_bytes(spec.read_bytes()),
              "probe_source_hash": sha256_bytes(probe),
              "sandbox_identity": {"image_digest": "image", "profile_hash": "profile"}}
    journal = DevJournal(root, "run_dev_public_counterexamples_20260913")
    identity = {"run_id": journal.run_id, "action_id": "panel_A2", "input_hash": sha256_json({
        "packet": sha256_bytes(design.wire(packet)), "subject": subject})}
    row = {"id": "multi_parent", "matches": False,
           "real": {"error": None, "entries": [[p, "dir", "0o755"] for p in ("a", "b", "c")]},
           "fake": {"error": None, "entries": [[p, "dir", "0o755"] for p in ("a", "c")]}}
    data = {"platform": "Linux", "python": "3.12.13", "umask": "0o022",
            "rows": [row, {"id": "other", "private": "UNRELATED_OBSERVATION_SENTINEL"}]}
    policy = {"cleanup_status": "confirmed"}
    execution = {"subject": "A2", "identity": identity, "status": "passed", "exit_code": 0,
                 "source_hash": sha256_bytes(probe), "execution_policy": policy,
                 "execution_policy_hash": sha256_json(policy), "snapshot_hash": "snapshot",
                 "image_digest": "image", "profile_hash": "profile", "timed_out": False,
                 "truncated": False, "deadline_exhausted": False, "cleanup_failed": False,
                 "stdout": json.dumps(data), "unprojected": "RAW_REASONING_SENTINEL"}
    files = {"packet.json": design.wire(packet), "A2-execution.json": design.wire(execution),
             "probe.py": probe}
    for name, raw in files.items():
        (root / name).write_bytes(raw)
    journal.append("public_panel_started", {"subject": "A2", "execution_identity": identity})
    journal.append("public_panel_finished", {"subject": "A2", "result_hash": sha256_bytes(
        files["A2-execution.json"])})
    files[journal.path.relative_to(root).as_posix()] = journal.path.read_bytes()
    completion = design.wire({"files": {name: sha256_bytes(raw) for name, raw in files.items()}})
    (root / "completion.json").write_bytes(completion)
    monkeypatch.setattr(design, "COMPLETION_HASH", sha256_bytes(completion))
    monkeypatch.setattr(design.seed, "restore", lambda _: (request, checkpoint))
    for name in (".env", "private.yaml", "reference.patch", "future-provider-result.json"):
        (source_root / name).write_text("SECRET_FUTURE_SENTINEL", encoding="utf-8")
    return request, checkpoint, root, source_root


def test_report_only_contains_selected_public_observation_with_real_provenance(evidence):
    request, checkpoint, root, _ = evidence
    report, provenance, source = design.load_report(request, checkpoint, root)
    assert report["origin"] == "operator_executed_public_diagnostic"
    assert report["expected"]["entries"][1] == ["b", "dir", "0o755"]
    assert report["actual"]["entries"] == [["a", "dir", "0o755"], ["c", "dir", "0o755"]]
    assert len(provenance["verified_source_files"]) == 6
    assert provenance["operator_execution_identity"]["action_id"] == "panel_A2"
    assert b"SENTINEL" not in design.wire(report) + source
    assert "action_id" not in report and "source_hash" not in report
    cases = ast.literal_eval(ast.parse(source).body[0].value)
    assert len(cases) == 1 and cases[0]["id"] == design.CASE_ID


def test_only_latest_unsent_snapshot_changes_not_prompt_tools_native_items_or_verdicts(evidence):
    request, checkpoint, root, _ = evidence
    before = design.wire(request)
    report, _, _ = design.load_report(request, checkpoint, root)
    changed = design.add_report(request, report)
    assert design.wire(request) == before
    assert changed["input"][:-1] == request["input"][:-1]
    assert {k: v for k, v in changed.items() if k != "input"} == {
        k: v for k, v in request.items() if k != "input"}
    current, original = reconstruct_state(changed["input"]), reconstruct_state(request["input"])
    overlay = current.pop(design.FIELD)
    assert current == original and overlay["currency"] == "current_candidate"
    assert current["workflow_gate"] == "ready_to_submit"
    assert current["current_public_failure"] is None
    assert all(c["status"] == "PASS" for c in current["visible_check_status"])
    assert design.add_report(changed, report) == changed
    assert design.seed.PROMPT_SUFFIX not in changed["input"][0]["content"]
    for key in ("reasoning_item_count", "function_call_count", "function_output_count",
                "user_message_count", "state_update_count"):
        assert history_metadata(changed["input"])[key] == history_metadata(request["input"])[key]


def test_native_followup_and_recovery_keep_report_but_expire_candidate_currency(evidence):
    request, checkpoint, root, _ = evidence
    report, _, _ = design.load_report(request, checkpoint, root)
    initial = design.add_report(request, report)
    state = reconstruct_state(initial["input"])
    state["current_diff"]["patch_hash"] = "changed-candidate"
    state["remaining_budget"]["accepted_mutations"] -= 1
    history = [
        {"type": "reasoning", "id": "next", "encrypted_content": "OPAQUE", "summary": []},
        {"type": "function_call", "call_id": "edit", "name": "replace_text", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "edit", "output": "ACTUAL_MUTATION_RESULT"},
    ]
    following = copy.deepcopy(initial)
    following["input"] = assemble_model_input(system_prompt="unused", state=state,
                                              history=history, previous_input=initial["input"])
    changed = design.add_report(following, report)
    assert changed["input"][:len(initial["input"])] == initial["input"]
    assert reconstruct_state(changed["input"])[design.FIELD]["currency"] == "historical_candidate"
    # JSON round-trip/reapplication does not duplicate the report or invent a result.
    assert design.add_report(json.loads(design.wire(changed)), report) == changed
    outputs = [i for i in changed["input"] if i.get("type") == "function_call_output"]
    assert outputs[-1] == history[-1]


@pytest.mark.parametrize("fault", ["subject", "patch", "file_hash", "task", "receipt", "journal"])
def test_mismatched_candidate_task_or_sealed_evidence_rejected(evidence, fault):
    request, checkpoint, root, _ = evidence
    if fault == "subject":
        checkpoint["source_run_id"] = "different-run"
    elif fault in {"patch", "file_hash"}:
        view = json.loads(request["input"][-1]["content"])
        if fault == "patch":
            view["state"]["current_diff"]["patch"] += "\nchanged"
        else:
            view["state"]["current_sources"][0]["file_hash"] = "stale"
        request["input"][-1]["content"] = design.wire(view).decode()
    elif fault == "task":
        design.PUBLIC_SPEC.write_text("CHANGED", encoding="utf-8")
    else:
        path = (root / "A2-execution.json" if fault == "receipt"
                else next((root / "runs").glob("*.jsonl")))
        path.write_bytes(b"tampered")
    with pytest.raises(ValueError):
        design.load_report(request, checkpoint, root)


@pytest.mark.parametrize("fault", ["truncated", "timed_out", "cleanup_failed", "wrong_observation",
                                    "ambiguous_case", "wrong_platform"])
def test_invalid_observation_cannot_become_feedback(evidence, fault):
    _, _, root, _ = evidence
    packet = json.loads((root / "packet.json").read_bytes())
    execution = json.loads((root / "A2-execution.json").read_bytes())
    if fault in {"truncated", "timed_out", "cleanup_failed"}:
        execution[fault] = True
    elif fault == "ambiguous_case":
        packet["cases"].append(packet["cases"][0])
    else:
        data = json.loads(execution["stdout"])
        if fault == "wrong_platform":
            data["platform"] = "Windows"
        else:
            data["rows"][0]["fake"] = data["rows"][0]["real"]
        execution["stdout"] = json.dumps(data)
    with pytest.raises(ValueError):
        design.select_case(packet, execution)


@pytest.mark.parametrize("tamper", ["feedback-request.json", "feedback.json", "criteria.json",
                                    "verification-case.py", "packet.json"])
def test_packet_replay_is_no_call_read_only_private_free_and_tamper_evident(
    evidence, monkeypatch, tmp_path, tamper,
):
    _, _, root, source = evidence

    def forbidden(*args, **kwargs):
        pytest.fail("no-call preparation executed a process or network operation")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    original_read = Path.read_bytes

    def read_bytes(path):
        assert path.name not in {".env", "private.yaml", "reference.patch",
                                 "future-provider-result.json"}
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    protected = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    destination = tmp_path / "new-packet"
    packet = design.prepare(source, destination, root)
    assert design.validate(destination) == design.validate(destination) == packet
    assert all(p.read_bytes() == raw for p, raw in protected.items())
    assert not packet["boundaries"]["paid_execution_authorized"]
    assert packet["boundaries"]["provider_calls"] == packet["boundaries"]["tool_executions"] == 0
    assert packet["boundaries"]["task_acceptance"] == "NOT_RUN"
    assert packet["metrics"]["added_bytes"] > 0
    assert b"SENTINEL" not in b"".join(p.read_bytes() for p in destination.iterdir() if p.is_file())
    with pytest.raises(ValueError, match="fresh external"):
        design.prepare(source, destination, root)
    (destination / tamper).write_bytes(b"{}")
    with pytest.raises((ValueError, KeyError)):
        design.validate(destination)


def test_rubric_separates_agent_behavior_operator_audit_and_claims():
    rubric = design.criteria()
    assert rubric["initial_scores"] == rubric["task_acceptance"] == "NOT_RUN"
    assert "never agent credit" in rubric["axes"]["operator_same_case_audit"]
    assert "gateway-rejected" in rubric["axes"]["repair_attempt"]
    assert "not new randomized controls" in rubric["limits"][1]
    assert not rubric["official"]


def test_cli_cannot_execute_paid_or_docker_work(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["failure_given_repair", "--help"])
    with pytest.raises(SystemExit) as exc:
        design.main()
    assert exc.value.code == 0
    help_text = capsys.readouterr().out
    assert "{prepare,validate}" in help_text
    assert "--credential" not in help_text and "{run}" not in help_text
