from __future__ import annotations

import copy
import json
from dataclasses import replace
from decimal import Decimal

import httpx
import pytest

from diagnostics import segmented_pilot as pilot
from patchloop.dev import runner, segments
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.conversation import reconstruct_state
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_json


@pytest.fixture(autouse=True)
def no_external_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("packet preparation must not access credentials/provider/Docker/execution")

    monkeypatch.setattr(runner, "run_dev", forbidden)
    monkeypatch.setattr(runner, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(runner.DockerSandbox, "available", forbidden)
    monkeypatch.setattr(runner.DockerProbeSandbox, "preflight", forbidden)
    monkeypatch.setattr(httpx.Client, "send", forbidden)
    # Packet tests assume admitted source, not a committed developer checkout.
    # The real tracked/HEAD-clean gate has isolated Git-repository tests in
    # test_dev_runner; keep that production gate intact.
    monkeypatch.setattr(runner, "_live_source_preflight", lambda *args, **kwargs: None)


@pytest.fixture
def prepared(tmp_path):
    root = tmp_path / "packet"
    receipt = pilot.prepare(root, pricing_verified_on="2026-09-14")
    return root, receipt, json.loads((root / "packet.json").read_text(encoding="utf-8"))


def test_no_call_packet_exact_contrast_and_read_only_inspect(prepared):
    root, receipt, packet = prepared
    raw = (root / "packet.json").read_bytes()
    a, b = (copy.deepcopy(packet["frozen"]["requests"][arm]) for arm in ("A", "B"))
    assert a.pop("context_policy") == "append-v1"
    assert b.pop("context_policy") == "segmented-v1"
    assert a == b and a["planning_policy"] == "brief-v1"
    assert a["enable_probes"] and a["repair_recheck"] and a["repeat"] == 1
    assert a["resume_run_id"] is a["state_root"] is a["compact_at_input_tokens"] is None
    assert not (root / "state").exists()
    assert packet["order"] == ["A1", "B1", "B2", "A2"]
    assert packet["run_cap_nanos"] == 1_200_000_000
    assert packet["cap_nanos"] == len(packet["slots"]) * packet["run_cap_nanos"] == 4_800_000_000
    assert packet["authorization"].startswith("NOT_AUTHORIZED")
    for slot in packet["slots"]:
        req = DevRunRequest.model_validate(slot["request"])
        assert req.state_root == root / "state" / slot["label"]
        assert req.context_policy == pilot.POLICIES[slot["arm"]]
    first = pilot.inspect(root, packet_hash=receipt["packet_hash"])
    assert first == pilot.inspect(root, packet_hash=receipt["packet_hash"])
    assert first["provider_calls"] == first["count_calls"] == 0
    assert first["actual_input_fit"] == "NOT_MEASURED" and not first["authorized"]
    assert (root / "packet.json").read_bytes() == raw


def test_rehearsal_keeps_public_goal_without_prior_evidence_or_hidden_content(prepared):
    _, _, packet = prepared
    frozen = packet["frozen"]
    examples = frozen["task_only_serialization_rehearsal"]
    for arm, items in examples.items():
        assert reconstruct_state(items, context_policy=pilot.POLICIES[arm]) == {
            "public_task": frozen["public_task"],
        }
        assert not any("type" in item for item in items)  # no native/opaque history injection
        public_input = canonical_json(items)
        # The public task itself declares a .patchloop-hidden/** denylist. Preserve it;
        # privacy is exact public-task equality, not banning that public constraint.
        for excluded in ("private_spec", "private.yaml", "reference.patch", "encrypted_content"):
            assert excluded not in public_input
    assert examples["B"][0]["content"] == (
        examples["A"][0]["content"] + "\n" + segments.INSTRUCTIONS
    )
    assert frozen["model_hashes"]["A"] != frozen["model_hashes"]["B"]
    assert {s["name"] for s in frozen["registered_schema_catalog"]} == {
        "read_file", "search_files", "replace_text", "run_check", "run_probe",
        "finish_task", "stop_task",
    }
    assert packet["preparation_scope"]["credential"] == "NOT_READ"


def test_changed_packet_rejected_even_when_well_formed(prepared):
    root, receipt, packet = prepared
    packet["slots"][0]["request"]["max_cost_usd"] = "2"
    (root / "packet.json").write_text(canonical_json(packet), encoding="utf-8")
    with pytest.raises(RecoveryError, match="content hash mismatch"):
        pilot.inspect(root, packet_hash=receipt["packet_hash"])


@pytest.mark.parametrize("field", ["runtime_hash", "task_content_hash", "preparer_hash",
                                  "installed_libraries", "probe_profile_hash"])
def test_identity_drift_fails_before_execution(prepared, monkeypatch, field):
    root, receipt, packet = prepared
    changed = copy.deepcopy(packet["frozen"])
    changed[field] = "drift"
    monkeypatch.setattr(pilot, "freeze", lambda: changed)
    with pytest.raises(RecoveryError, match="contract changed"):
        pilot.inspect(root, packet_hash=receipt["packet_hash"])


def test_existing_root_cannot_be_reused(prepared):
    root, _, _ = prepared
    raw = (root / "packet.json").read_bytes()
    with pytest.raises(RecoveryError, match="unused directory"):
        pilot.prepare(root, pricing_verified_on="2026-09-14")
    assert (root / "packet.json").read_bytes() == raw


def test_repository_output_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(pilot, "repository_root", lambda: tmp_path)
    root = tmp_path / "uncreated"
    with pytest.raises(RecoveryError, match="must be external"):
        pilot.prepare(root, pricing_verified_on="2026-09-14")
    assert not root.exists()


def test_price_mismatch_fails_without_creating_packet(tmp_path, monkeypatch):
    original = pilot.pricing_for_model(pilot.MODEL)
    monkeypatch.setattr(pilot, "pricing_for_model", lambda model: replace(
        original, input_per_million_usd=Decimal("0.8"),
    ))
    root = tmp_path / "uncreated"
    with pytest.raises(RecoveryError, match="price changed"):
        pilot.prepare(root, pricing_verified_on="2026-09-14")
    assert not root.exists()


def test_source_preflight_rejection_blocks_packet_creation(tmp_path, monkeypatch):
    observed = []

    def reject(task_dir, package):
        observed.append(package.public.task_id)
        raise ContractError("uncommitted test source")

    monkeypatch.setattr(runner, "_live_source_preflight", reject)
    root = tmp_path / "uncreated"
    with pytest.raises(ContractError, match="uncommitted test source"):
        pilot.prepare(root, pricing_verified_on="2026-09-14")
    assert len(observed) == 1 and not root.exists()


def test_hash_is_exact_content_identity(prepared):
    _, receipt, packet = prepared
    assert receipt["packet_hash"] == sha256_json(packet)
    assert not receipt["authorized"]
