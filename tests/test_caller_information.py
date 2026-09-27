"""Evidence provenance and first-input-only intervention; all SDK usage is synthetic."""

import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest
from test_anyio_caller_probe import observations
from test_checkpoint_comparison import install_sdk
from test_checkpoint_continuation import call, stop_steps
from test_mutation_advice_checkpoint import source as source  # noqa: F401

from diagnostics import anyio_caller_probe as probe
from diagnostics import caller_information as info
from diagnostics import checkpoint_comparison as comparison
from diagnostics import checkpoint_continuation as continuation
from diagnostics import mutation_advice_checkpoint as checkpoint
from diagnostics.segmented_input_audit import verify_turn
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError
from patchloop.task_loader import load_public_task
from patchloop.util import canonical_json, sha256_bytes, sha256_json


@pytest.fixture(scope="module")
def packet(source, tmp_path_factory):
    return checkpoint.prepare(source, tmp_path_factory.mktemp("caller-pair") / "packet")


@pytest.fixture
def evidence(source, packet, tmp_path):
    root = tmp_path / "operator"
    store = ArtifactStore(root / "artifacts")
    journal = DevJournal(root, "run_dev_callerstateprobe")
    envelope = DevJournal(source.root, source.run_id).load_envelope()
    journal.append("operator_probe_prepared", {
        "packet_hash": packet["packet_hash"], "runtime_hash": envelope.runtime_hash,
        "public_task_hash": sha256_bytes(source.public_path.read_bytes()),
        "implementation_hash": sha256_bytes(Path(probe.__file__).read_bytes()),
        "origin": "operator", "official": False,
        "programs": {m: store.put_text(probe.program(m)).model_dump(mode="json")
                     for m in probe.MODES},
    })
    journal.append("operator_environment_ready", {
        "base_commit": load_public_task(source.public_path).repository.base_commit,
        "diff_hash": sha256_bytes(b""), "image_digest": envelope.probe_image_digest,
        "profile_hash": envelope.probe_profile_hash,
    })
    rows, receipts = observations(), []
    for row in rows:
        receipt = {
            "source_hash": sha256_bytes(probe.program(row["mode"]).encode()),
            "status": "passed", "exit_code": 0, "image_digest": envelope.probe_image_digest,
            "profile_hash": envelope.probe_profile_hash,
            "execution_policy": {"dependencies": envelope.probe_dependencies.model_dump(mode="json")
                                 if envelope.probe_dependencies else None},
            "stdout": canonical_json(row),
        }
        entry = {"mode": row["mode"], "artifact": store.put_json(receipt).model_dump(mode="json")}
        receipts.append(entry)
        journal.append("operator_probe_finished", entry)
    result = {"origin": "operator", "official": False, "model_calls": 0, "input_counts": 0,
              "observations": rows, "receipts": receipts, "interpretation": probe.interpret(rows)}
    journal.append("operator_observation_completed", {
        "artifact": store.put_json(result).model_dump(mode="json")})
    path = root / "result.json"
    path.write_text(canonical_json(result) + "\n", encoding="utf-8")
    return {"path": str(path), "hash": sha256_bytes(path.read_bytes())}


def load(evidence, packet, source):
    envelope = DevJournal(source.root, source.run_id).load_envelope()
    return info.load(evidence, packet["packet_hash"], source, envelope)


def test_projection_only_adds_measured_public_evidence(evidence, packet, source):
    supplement, binding = load(evidence, packet, source)
    assert binding["supplement_hash"] == sha256_json(supplement)
    original = checkpoint.load(source).request
    frozen = copy.deepcopy(original)
    projected = info.project(original, supplement)
    assert original == frozen and projected["input"][:-1] == original["input"][:-1]
    state = json.loads(projected["input"][-1]["content"])
    assert state["state"].pop(info.FIELD) == supplement
    assert state == json.loads(original["input"][-1]["content"])
    assert {k: v for k, v in projected.items() if k != "input"} == {
        k: v for k, v in original.items() if k != "input"}
    assert "interpretation" not in supplement and "verdict" not in supplement


@pytest.mark.parametrize("tamper", ["result", "cas", "checkpoint"])
def test_evidence_tampering_or_wrong_checkpoint_fails(evidence, packet, source, tamper):
    path = Path(evidence["path"])
    if tamper == "result":
        result = json.loads(path.read_bytes())
        result["observations"][0]["observations"][0]["caller"]["cancelling"] = 9
        path.write_text(canonical_json(result), encoding="utf-8")
        # A new file hash cannot rebind the completed journal artifact.
        evidence["hash"] = sha256_bytes(path.read_bytes())
    elif tamper == "cas":
        ref = json.loads(path.read_bytes())["receipts"][0]["artifact"]
        Path(ref["path"]).write_bytes(b"tampered")
    else:
        packet = {**packet, "packet_hash": "sha256:wrong"}
    with pytest.raises((ContractError, RecoveryError)):
        load(evidence, packet, source)


def test_four_rows_preserve_advice_history_and_drop_supplement_after_first_input(
    evidence, packet, source, tmp_path, monkeypatch,
):
    def forbidden(*a, **kw):
        pytest.fail("network forbidden")

    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr(runner, "_require_tracked_clean_paths", lambda *a, **kw: None)
    monkeypatch.setattr(comparison, "check_environment", lambda *a: {"status": "READY"})
    prepared = comparison.prepare(
        Path(packet["packet"]), packet["packet_hash"], source.root.parent / "absent.env",
        tmp_path / "result", tmp_path / "plan", caller_evidence=evidence,
    )
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    args = {k: getattr(mutation, k) for k in
            ("path", "old_text", "new_text", "hypothesis", "expected_behavior")}
    args.update(occurrence=1, causal_revision=None)
    repair = [[call("replace_text", args, "mutate")],
              [call("run_check", {"check_id": "existing-unit-tests"}, "verify")],
              [call("finish_task", {}, "finish")]]
    clients = [continuation.ScriptedClient(repair) for _ in comparison.ORDER]
    install_sdk(monkeypatch, source, clients)
    result = comparison.collect(Path(prepared["manifest"]), prepared["manifest_hash"],
                                Decimal(prepared["new_cap_usd"]))
    assert result["stop_reason"] is None, result
    plan = json.loads(Path(prepared["manifest"]).read_bytes())
    for row, client in zip(result["rows"], clients, strict=True):
        assert row["result"]["terminal"] == "EVALUATOR_PASS", row
        actual = {k: v for k, v in client.created[0].items() if k != "timeout"}
        assert sha256_json(actual) == plan["first_request_hashes"][row["row"][0] + "_request_hash"]
        assert (info.FIELD in json.loads(actual["input"][-1]["content"])["state"]) == (
            row["row"].startswith("B"))
        for later in client.created[1:]:
            assert info.FIELD not in canonical_json(later["input"])
        root = Path(plan["result_root"]) / row["row"]
        journal = DevJournal(root, source.run_id)
        events = journal.events()
        fork = next(e for e in events if e["event_type"] == "diagnostic_checkpoint_fork")
        # Later turns use copied references; first audit resolves immutable old refs.
        branch = type("Branch", (), {"store": ArtifactStore(root / "artifacts"),
                                     "references": fork["payload"]["artifact_references"]})()
        with continuation.inherited_reads(branch):
            for event in events[fork["sequence"]:]:
                if event["event_type"] == "turn_started":
                    assert verify_turn(event, events, branch.store)["verified"]
    assert result["new_cost_nanos"] == 12 * (100 * 2500 + 20 * 15000)


def test_new_evidence_comparison_stops_on_uncertain_dispatch(
    evidence, packet, source, tmp_path, monkeypatch,
):
    monkeypatch.setattr(runner, "_require_tracked_clean_paths", lambda *a, **kw: None)
    monkeypatch.setattr(comparison, "check_environment", lambda *a: {"status": "READY"})
    prepared = comparison.prepare(
        Path(packet["packet"]), packet["packet_hash"], source.root.parent / "absent.env",
        tmp_path / "result", tmp_path / "plan", caller_evidence=evidence,
    )
    install_sdk(monkeypatch, source,
                [continuation.ScriptedClient(stop_steps(), failure="transport")])
    result = comparison.collect(Path(prepared["manifest"]), prepared["manifest_hash"],
                                Decimal(prepared["new_cap_usd"]))
    assert result["new_cost_nanos"] is None
    assert all(row["status"] == "NOT_RUN" for row in result["rows"][1:])
