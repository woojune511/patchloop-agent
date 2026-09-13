from __future__ import annotations

import copy
import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from test_counterexample_review import request_at_submission

from diagnostics import current_failure_feedback as design
from patchloop.dev.conversation import assemble_model_input, history_metadata, reconstruct_state
from patchloop.util import sha256_bytes, sha256_json


@pytest.fixture
def sample(monkeypatch):
    request = request_at_submission()
    view = json.loads(request["input"][-1]["content"])
    state = view["state"]
    patch_hash = sha256_bytes(state["current_diff"]["patch"].encode())
    monkeypatch.setattr(design, "DIFF_HASH", patch_hash)
    state["current_diff"]["patch_hash"] = patch_hash
    for check in state["visible_check_status"]:
        check["diff_hash"] = patch_hash
    expected = {"error": None, "entries": [[p, "dir", "0o755"] for p in ("a", "b", "c")]}
    state[design.prior.FIELD] = {
        "environment": {"platform": "Linux", "python": "3.12.13", "umask": "0o022"},
        "expected": expected, "actual": {"error": None, "entries": []},
        "input": {"path": "a/../b/../c", "mode": "0o777", "exist_ok": False},
        "observed_on_diff_hash": "original-candidate", "currency": "historical_candidate",
    }
    policy = {"cleanup_status": "confirmed"}
    data = {**state[design.prior.FIELD]["environment"], "rows": [{
        "id": "multi_parent", "real": expected,
        "fake": {"error": None, "entries": [[p, "dir", "0o755"] for p in ("a", "a/b", "c")]},
        "matches": False}]}
    receipt = {"status": "passed", "exit_code": 0, "timed_out": False, "truncated": False,
               "cleanup_failed": False, "deadline_exhausted": False,
               "source_hash": design.CASE_HASH, "execution_policy": policy,
               "execution_policy_hash": sha256_json(policy), "image_digest": "image",
               "profile_hash": "profile", "stdout": json.dumps(data),
               "unprojected": "RAW_REASONING_SENTINEL"}
    probe = {"probe_image_digest": "image", "probe_profile_hash": "profile"}
    request["input"][-1]["content"] = design.wire(view).decode()
    report = design.make_report(state, receipt, "receipt-hash", probe)
    return request, state, receipt, probe, report


def forbid_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("no-call preparation executed network or subprocess")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    read = Path.read_bytes

    def guarded(path):
        assert path.name not in {".env", "private.yaml", "reference.patch"}
        return read(path)

    monkeypatch.setattr(Path, "read_bytes", guarded)


def test_one_observation_only_no_prompt_advice_fake_result_or_gate(sample):
    request, state, _, _, report = sample
    before = design.wire(request)
    changed = design.add_feedback(request, report)
    assert design.wire(request) == before
    assert changed["input"][:-1] == request["input"][:-1]
    assert {k: v for k, v in request.items() if k != "input"} == {
        k: v for k, v in changed.items() if k != "input"}
    current = reconstruct_state(changed["input"])
    original = reconstruct_state(request["input"])
    overlay = current.pop(design.FIELD)
    assert current == original
    assert overlay["currency"] == "current_candidate"
    assert overlay["case_definition_ref"] == design.prior.FIELD
    assert overlay["actual"]["entries"][1] == ["a/b", "dir", "0o755"]
    assert overlay["expected"]["entries"][1] == ["b", "dir", "0o755"]
    assert not overlay["model_authored"]
    assert "SENTINEL" not in design.wire(report).decode()
    assert current["workflow_gate"] == "ready_to_submit" and "finish_task" in {
        t["name"] for t in changed["tools"]}
    assert current["current_public_failure"] is None
    assert all(c["status"] == "PASS" for c in current["visible_check_status"])
    assert current[design.prior.FIELD] == state[design.prior.FIELD]
    assert design.add_feedback(changed, report) == changed
    for name in ("reasoning_item_count", "function_call_count", "function_output_count"):
        assert history_metadata(changed["input"])[name] == history_metadata(request["input"])[name]


def test_followup_expires_only_new_candidate_currency_and_rollback_restores_it(sample):
    request, _, _, _, report = sample
    initial = design.add_feedback(request, report)
    state = reconstruct_state(initial["input"])
    state["current_diff"]["patch_hash"] = "new-candidate"
    history = [
        {"type": "reasoning", "id": "next", "summary": [], "encrypted_content": "OPAQUE"},
        {"type": "function_call", "call_id": "edit", "name": "replace_text", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "edit", "output": "PUBLIC_MUTATION_RESULT"}]
    following = copy.deepcopy(initial)
    following["input"] = assemble_model_input(system_prompt="unused", state=state,
                                              history=history, previous_input=initial["input"])
    changed = design.add_feedback(following, report)
    assert changed["input"][:len(initial["input"])] == initial["input"]
    assert reconstruct_state(changed["input"])[design.FIELD]["currency"] == "historical_candidate"
    assert design.add_feedback(json.loads(design.wire(changed)), report) == changed
    # Rejected edit/rollback preserves the baseline; not a failed check or extra allowance.
    restored = copy.deepcopy(changed)
    view = json.loads(restored["input"][-1]["content"])
    view["state"]["current_diff"]["patch_hash"] = report["observed_on_diff_hash"]
    restored["input"][-1]["content"] = design.wire(view).decode()
    assert reconstruct_state(design.add_feedback(restored, report)["input"])[design.FIELD][
        "currency"] == "current_candidate"


@pytest.mark.parametrize("fault", ["timed_out", "truncated", "cleanup_failed", "deadline_exhausted",
                                    "source_hash", "image_digest", "profile_hash", "policy",
                                    "wrong_actual", "wrong_expected", "extra_case", "environment"])
def test_incomplete_or_unbound_observation_is_rejected(sample, fault):
    _, state, receipt, probe, _ = sample
    if fault in {"timed_out", "truncated", "cleanup_failed", "deadline_exhausted"}:
        receipt[fault] = True
    elif fault in {"source_hash", "image_digest", "profile_hash"}:
        receipt[fault] = "changed"
    elif fault == "policy":
        receipt["execution_policy"]["cleanup_status"] = "unknown"
        receipt["execution_policy_hash"] = sha256_json(receipt["execution_policy"])
    else:
        data = json.loads(receipt["stdout"])
        if fault == "wrong_actual":
            data["rows"][0]["fake"] = data["rows"][0]["real"]
        elif fault == "wrong_expected":
            data["rows"][0]["real"] = data["rows"][0]["fake"]
        elif fault == "extra_case":
            data["rows"].append({"id": "PRIVATE_OTHER_CASE_SENTINEL"})
        else:
            data["platform"] = "Windows"
        receipt["stdout"] = json.dumps(data)
    with pytest.raises(ValueError):
        design.make_report(state, receipt, "receipt-hash", probe)


def test_missing_reference_and_conflict_do_not_silently_pass(sample):
    request, _, _, _, report = sample
    changed = design.add_feedback(request, report)
    with pytest.raises(ValueError, match="conflicting"):
        design.add_feedback(changed, {**report, "expected": {}})
    view = json.loads(request["input"][-1]["content"])
    del view["state"][design.prior.FIELD]
    request["input"][-1]["content"] = design.wire(view).decode()
    with pytest.raises(ValueError, match="referenced"):
        design.add_feedback(request, report)


def test_sealed_source_rejects_tamper_and_unsealed_file(tmp_path, monkeypatch):
    file = tmp_path / "public.json"
    file.write_bytes(b"{}")
    completion = design.wire({"files": {"public.json": sha256_bytes(b"{}")}})
    (tmp_path / "completion.json").write_bytes(completion)
    monkeypatch.setattr(design, "COMPLETION_HASH", sha256_bytes(completion))
    source = design.SealedSource(tmp_path)
    assert source.read("public.json") == b"{}"
    with pytest.raises(ValueError, match="outside"):
        source.read(str(tmp_path.parent / "private.yaml"))
    with pytest.raises(ValueError, match="not sealed"):
        source.read("unsealed.json")
    file.write_bytes(b"tamper")
    with pytest.raises(ValueError, match="changed"):
        source.read("public.json")


@pytest.mark.parametrize("filename", ["A.json", "B.json", "feedback.json", "criteria.json",
                                       "verification-case.py", "packet.json"])
def test_packet_immutable_repeated_validation_without_network_or_credentials(
    sample, tmp_path, monkeypatch, filename,
):
    request, _, _, _, report = sample

    class Source:
        reads = {}

        def __init__(self, root):
            pass

    monkeypatch.setattr(design, "SealedSource", Source)
    monkeypatch.setattr(design, "restore", lambda _: (request, {"cutoff": "public"}, b"{}"))
    monkeypatch.setattr(design, "observation", lambda *_: (report, b"PUBLIC_CASE_SOURCE"))
    forbid_execution(monkeypatch)
    root = tmp_path / "packet"
    packet = design.prepare(tmp_path / "old", root)
    assert design.validate(root) == design.validate(root) == packet
    assert packet["boundaries"] == design.prior.BOUNDARIES
    assert packet["metrics"]["input_tokens"] == "NOT_COUNTED"
    assert not json.loads((root / "protocol.json").read_bytes())["collector_implemented"]
    with pytest.raises(ValueError, match="fresh external"):
        design.prepare(tmp_path / "old", root)
    (root / filename).write_bytes(b"{}")
    with pytest.raises((KeyError, ValueError)):
        design.validate(root)


@pytest.mark.skipif(not design.SOURCE.is_dir(), reason="local immutable diagnostic absent")
def test_actual_nested_checkpoint_replays_only_public_prefix_and_single_observation(monkeypatch):
    forbid_execution(monkeypatch)
    packet, files = design.compile_packet(design.SOURCE)
    a, b = json.loads(files["A.json"]), json.loads(files["B.json"])
    state = reconstruct_state(a["input"])
    assert packet["metrics"]["request_bytes_A"] == 540827
    assert packet["metrics"]["added_bytes"] == 1296
    assert packet["metrics"]["history"]["reasoning_item_count"] == 24
    assert packet["metrics"]["history"]["function_call_count"] == 24
    assert state["remaining_budget"]["accepted_mutations"] == 1
    assert state["remaining_budget"]["model_calls"] == 16
    assert state["current_diff"]["patch_hash"] == design.DIFF_HASH
    assert a["input"][:-1] == b["input"][:-1]
    assert sha256_bytes(files["A.json"]) == (
        "sha256:042ded513d51523fa04bad5982a5b660b223c14d67d77e0fade58a2b34009170")
    # The future finish and B1's correct patch must not be imported.
    assert b"call_zHbiPiWZL7JV77L31Qus8Lap" not in files["A.json"] + files["B.json"]
    assert b"b82adff49b673f95551322c7d0f0bce0de83345285bbbf26892459067ae58d67" not in (
        files["A.json"] + files["B.json"])
    assert sha256_bytes(files["verification-case.py"]) == design.CASE_HASH
    assert design.FIELD not in state
    source = design.SealedSource(design.SOURCE)
    monkeypatch.setattr(design.seed, "runtime_content_hash", lambda: "different-runtime")
    with pytest.raises(ValueError, match="runtime/config"):
        design.restore(source)


def test_cli_has_no_execution_or_credentials_and_rubric_keeps_claim_limits(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["current_failure_feedback", "--help"])
    with pytest.raises(SystemExit) as error:
        design.main()
    assert error.value.code == 0
    help_text = capsys.readouterr().out
    assert "{prepare,validate}" in help_text and "--credential" not in help_text
    rubric = design.criteria()
    assert "b is absent and a/b exists" in rubric["axes"]["recognition"]
    assert "never agent credit" in rubric["axes"]["operator_same_case_audit"]
    assert rubric["task_acceptance"] == "NOT_RUN" and not rubric["official"]
