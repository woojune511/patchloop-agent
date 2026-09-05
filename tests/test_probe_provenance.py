from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_evaluator import (
    PolicySandbox,
    _copy_smoke_task,
    _engine,
    _manifest_for,
    _submitted_patch_bytes,
    _write_manifest,
)

from patchloop.contracts import VerdictState
from patchloop.errors import ContractError
from patchloop.sandbox.probes import (
    PROBE_IMAGE_DIGEST,
    probe_execution_policy,
    probe_profile_hash,
)
from patchloop.util import sha256_bytes, sha256_json


def _prepared(tmp_path):
    task_dir, package = _copy_smoke_task(tmp_path, with_environment=True)
    patch_bytes = _submitted_patch_bytes(tmp_path, task_dir, package)
    image = package.environment.evaluator_image
    sandbox = PolicySandbox(image)
    engine, store, workspace_root = _engine(tmp_path, sandbox)
    patch = store.put_bytes(patch_bytes, "text/x-diff")
    manifest = _manifest_for(package, patch_bytes, backend="docker", image=image).model_copy(
        update={
            "probe_image_digest": PROBE_IMAGE_DIGEST, "probe_profile_hash": probe_profile_hash(),
            "sandbox_identity_hash": sha256_json({
                "backend": "docker", "evaluator_image": image,
                "image_digest": package.environment.image_digest,
                "probe_image_digest": PROBE_IMAGE_DIGEST,
                "probe_profile_hash": probe_profile_hash(),
            }),
        }
    )
    policy = probe_execution_policy(
        effective_timeout_seconds=8.0, row_deadline_limited=True, cleanup_status="confirmed",
    )
    receipt = {
        "schema_version": "dev-probe-receipt-v1",
        "run_id": manifest.run_id,
        "action_id": "probe_" + "x" * 494,
        "input_hash": sha256_json({"python_source": "assert False"}),
        "source_hash": sha256_bytes(b"assert False"),
        "snapshot_hash": sha256_json({"public.py": "observed current source"}),
        "workspace_diff_hash": sha256_bytes(b"earlier diff"),
        "diff_hash": sha256_bytes(b"earlier diff"),
        "image_digest": PROBE_IMAGE_DIGEST,
        "profile_hash": probe_profile_hash(),
        "execution_policy": policy,
        "execution_policy_hash": sha256_json(policy),
        "status": "failed",
        "exit_code": 1,
        "cleanup_failed": False,
    }
    return task_dir, engine, store, sandbox, workspace_root, patch, manifest, receipt


@pytest.mark.parametrize("violation", [False, True])
def test_probe_safety_is_independent_of_probe_exit_and_required_checks(tmp_path, violation):
    task_dir, engine, store, sandbox, _, patch, manifest, receipt = _prepared(tmp_path)
    if violation:
        receipt["execution_policy"]["network"] = "host"
        receipt["execution_policy_hash"] = sha256_json(receipt["execution_policy"])
    evidence = store.put_json(receipt)
    manifest = manifest.model_copy(
        update={"probe_evidence": [evidence], "probe_execution_count": 1}
    )
    _write_manifest(store, manifest)

    result = engine.evaluate(task_dir, patch.path, manifest, submitted_patch_artifact=patch)

    assert sandbox.calls > 0
    assert result.scope_compliant_success
    assert result.verdicts.safety_policy == (VerdictState.FAIL if violation else VerdictState.PASS)
    assert all(item.check_type != "probe" for item in result.verifier_results)
    evidence_record = next(item for item in result.safety_evidence if item.details.get("kind"))
    assert evidence_record.details["grants_required_check_credit"] is False
    provenance = json.loads((store.root / "runs" / manifest.run_id / "provenance.json").read_text())
    assert provenance["probe_evidence_hashes"] == [evidence.content_hash]
    assert receipt["execution_policy_hash"] in provenance["execution_policy_hashes"]


@pytest.mark.parametrize("fault", ["missing", "tampered", "hash", "diff", "run", "cleanup"])
def test_invalid_probe_receipt_stops_before_evaluator_workspace(tmp_path, fault):
    task_dir, engine, store, sandbox, workspace_root, patch, manifest, receipt = _prepared(tmp_path)
    if fault == "hash":
        receipt["execution_policy_hash"] = sha256_json("wrong policy")
    elif fault == "diff":
        receipt["workspace_diff_hash"] = sha256_json("different source")
    elif fault == "run":
        receipt["run_id"] = "run_dev_other"
    elif fault == "cleanup":
        receipt["cleanup_failed"] = True
    evidence = store.put_json(receipt)
    if fault == "tampered":
        Path(evidence.path).write_bytes(b"tampered evidence")
    manifest = manifest.model_copy(update={
        "probe_evidence": [] if fault == "missing" else [evidence], "probe_execution_count": 1,
    })
    _write_manifest(store, manifest)

    with pytest.raises(ContractError, match="probe execution receipts"):
        engine.evaluate(task_dir, patch.path, manifest, submitted_patch_artifact=patch)

    assert sandbox.calls == 0
    assert list(workspace_root.iterdir()) == []
    provenance = json.loads((store.root / "runs" / manifest.run_id / "provenance.json").read_text())
    record = next(item for item in provenance["safety_evidence"] if item["details"].get("kind"))
    assert record["state"] == VerdictState.ERROR.value
    assert record["details"]["integrity_errors"]
    assert provenance["probe_evidence_hashes"] == [
        item.content_hash for item in manifest.probe_evidence
    ]


def test_enabled_but_unused_probe_needs_no_execution_receipt(tmp_path):
    _, engine, _, _, _, _, manifest, _ = _prepared(tmp_path)
    evidence = engine._probe_policy_evidence(manifest)
    assert evidence.state == VerdictState.PASS
    assert evidence.details["recorded_probe_count"] == 0
    disabled = manifest.model_copy(update={"probe_image_digest": None, "probe_profile_hash": None})
    assert engine._probe_policy_evidence(disabled) is None


def test_probe_provenance_survives_later_evaluator_failure(tmp_path):
    task_dir, engine, store, sandbox, _, patch, manifest, receipt = _prepared(tmp_path)
    sandbox.mode = "error_after_one"
    evidence = store.put_json(receipt)
    manifest = manifest.model_copy(
        update={"probe_evidence": [evidence], "probe_execution_count": 1}
    )
    _write_manifest(store, manifest)
    with pytest.raises(RuntimeError, match="evaluator interruption"):
        engine.evaluate(task_dir, patch.path, manifest, submitted_patch_artifact=patch)

    provenance = json.loads((store.root / "runs" / manifest.run_id / "provenance.json").read_text())
    assert provenance["probe_evidence_hashes"] == [evidence.content_hash]
    assert receipt["execution_policy_hash"] in provenance["execution_policy_hashes"]
    assert provenance["evaluation_status"] == "error"
    assert len(provenance["completed_check_results"]) == 1
