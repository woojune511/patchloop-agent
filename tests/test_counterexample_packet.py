"""Offline public evidence validation; no task, provider, or Docker execution."""

from __future__ import annotations

import copy
import json

import pytest

from diagnostics import counterexample_packet as packet
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes


def outcome(location=None):
    return {"status": "ImportError"} if location is None else {
        "status": "found", "type": "PY_NAMESPACE", "location": None,
        "namespace_paths": [location],
    }


def rows(candidate):
    values = []
    for name in packet.CASE_IDS:
        reference = outcome()
        public = reference
        if name in packet.PREEXISTING_IDS:
            reference = outcome("$FIXTURE/left/ns")
        elif candidate and name in packet.REGRESSION_IDS:
            public = outcome("$FIXTURE/left/ns")
        values.append({
            "case": name, "parts": ["ns"], "mode": "explicit", "search": ["$FIXTURE/left"],
            "public_api": copy.deepcopy(public), "lower_resolver": outcome(),
            "importlib_reference": reference, "matches_reference": public == reference,
        })
    return values


def receipt(values, program_hash):
    report = {"python": [3, 9, 25], "method": packet.METHOD, "rows": values}
    return {"status": "passed", "exit_code": 0, "cleanup_failed": False,
            "timed_out": False, "truncated": False, "deadline_exhausted": False,
            "source_hash": program_hash, "image_digest": "image", "profile_hash": "profile",
            "execution_policy": {"cleanup_status": "confirmed", "dependencies": {"pin": "1"}},
            "stdout": packet.PREFIX + json.dumps(report) + "\n"}


@pytest.fixture
def saved(tmp_path, monkeypatch):
    root = tmp_path / "comparison" / "run-v1"
    artifacts = root / "artifacts"
    artifacts.mkdir(parents=True)
    program = root.parent / "probe.py"
    source = b"# Public fixture program, never executed by this test.\n"
    program.write_bytes(source)
    program_hash = sha256_bytes(source)

    def artifact(raw):
        digest = sha256_bytes(raw)
        path = artifacts / digest.removeprefix("sha256:")
        path.write_bytes(raw)
        return {"path": str(path), "content_hash": digest, "size_bytes": len(raw)}

    def wire(value):
        return (canonical_json(value) + "\n").encode()

    observations, receipts = {}, {}
    for variant in ("base", "candidate"):
        values = rows(variant == "candidate")
        receipts[variant] = receipt(values, program_hash)
        observations[variant] = {
            "diff_hash": (packet.CANDIDATE_DIFF_HASH if variant == "candidate"
                          else sha256_bytes(b"")),
            "receipt": artifact(wire(receipts[variant])), "python": [3, 9, 25],
            "method": packet.METHOD, "rows": values,
        }
    manifest = {
        "schema": "public-path-contract-comparison-v1", "official": False,
        "order": ["base", "candidate"], "candidate_patch_hash": packet.CANDIDATE_DIFF_HASH,
        "input_hashes": {str(program): program_hash}, "execution": artifact(source),
        "task": "HOST_TASK_PATH_SENTINEL", "baseline": "base",
        "hypothesis": "OPERATOR_DIAGNOSIS_SENTINEL", "private_note": "PRIVATE_NOTE_SENTINEL",
    }
    result = {
        "schema": "public-path-contract-result-v1", "status": "COMPLETED", "official": False,
        "probe_identity": {"image_digest": "image", "profile_hash": "profile"},
        "observations": observations, "private_status": "PRIVATE_STATUS_SENTINEL",
    }

    def freeze():
        (root / "manifest.json").write_bytes(wire(manifest))
        (root / "result.json").write_bytes(wire(result))
        monkeypatch.setattr(packet, "SOURCE_HASHES", {
            "manifest": sha256_bytes(wire(manifest)), "result": sha256_bytes(wire(result)),
            "program": program_hash,
        })

    freeze()
    return {"root": root, "manifest": manifest, "result": result, "receipts": receipts,
            "program_hash": program_hash, "artifact": artifact, "wire": wire, "freeze": freeze}


def test_packet_projects_public_inputs_and_outcomes_without_operator_or_host_context(saved):
    result = packet.build_packet(saved["root"])
    assert len(result["mandatory_case_ids"]) == 11
    assert result["regressions"] == list(packet.REGRESSION_IDS)
    assert result["preexisting_discrepancies"] == list(packet.PREEXISTING_IDS)
    assert len(result["evidence_files"]) == 6  # Manifest, result, source, and three artifacts.
    visible = packet.model_visible(result, packet.CANDIDATE_DIFF_HASH)
    text = json.dumps(visible)
    for excluded in ("OPERATOR_DIAGNOSIS_SENTINEL", "PRIVATE_NOTE_SENTINEL",
                     "PRIVATE_STATUS_SENTINEL", "HOST_TASK_PATH_SENTINEL", str(saved["root"]),
                     "evidence_files", "task_path", "environment"):
        assert excluded not in text
    assert visible["program_text"] == result["program_text"]
    assert visible["observations_current"] and not visible["new_verification_required"]
    stale = packet.model_visible(result, "changed-diff")
    assert not stale["observations_current"] and stale["new_verification_required"]
    visible["cases"][0]["parts"].append("mutated")
    assert result["cases"][0]["parts"] == ["ns"]


@pytest.mark.parametrize("filename", ["manifest.json", "result.json", "../probe.py"])
def test_immutable_source_byte_change_is_rejected(saved, filename):
    path = saved["root"] / filename
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ContractError, match="hash changed"):
        packet.build_packet(saved["root"])


def test_raw_receipt_and_saved_result_must_match(saved):
    saved["result"]["observations"]["candidate"]["rows"][0]["search"] = ["$FIXTURE/other"]
    saved["freeze"]()
    with pytest.raises(ContractError, match="raw public report mismatch"):
        packet.build_packet(saved["root"])


@pytest.mark.parametrize("change", ["hash", "size", "outside"])
def test_artifact_identity_and_scope_are_checked(saved, change):
    ref = saved["result"]["observations"]["candidate"]["receipt"]
    if change == "hash":
        ref["content_hash"] = sha256_bytes(b"changed")
    elif change == "size":
        ref["size_bytes"] += 1
    else:
        ref["path"] = str(saved["root"] / "result.json")
    saved["freeze"]()
    with pytest.raises(ContractError, match="hash changed|size changed|outside comparison root"):
        packet.build_packet(saved["root"])


@pytest.mark.parametrize("key,value,match", [
    ("source_hash", "changed", "program hash"),
    ("truncated", True, "incomplete or uncertain"),
    ("timed_out", None, "incomplete or uncertain"),
    ("execution_policy", {"cleanup_status": "unknown"}, "cleanup is uncertain"),
])
def test_parser_rejects_uncertain_or_wrong_program_receipt(saved, key, value, match):
    current = copy.deepcopy(saved["receipts"]["candidate"])
    current[key] = value
    with pytest.raises(ContractError, match=match):
        packet.parse_receipt(current, saved["program_hash"])


@pytest.mark.parametrize("change,match", [
    ("duplicate", "duplicate or unexpected"), ("stale", "stale public case verdict"),
    ("unexpected", "unexpected diagnostic error"), ("missing", "incomplete case matrix"),
])
def test_parser_rejects_incomplete_duplicate_and_contradictory_rows(saved, change, match):
    current = rows(True)
    if change == "duplicate":
        current[-1] = copy.deepcopy(current[0])
    elif change == "stale":
        current[0]["matches_reference"] = False
    elif change == "unexpected":
        current[0]["public_api"] = {"status": "unexpected_error", "type": "RuntimeError"}
    else:
        current.pop()
    with pytest.raises(ContractError, match=match):
        packet.parse_receipt(receipt(current, saved["program_hash"]), saved["program_hash"])


def test_three_repairs_pass_with_shared_preexisting_discrepancy_still_failing(saved):
    frozen = packet.build_packet(saved["root"])
    corrected = rows(False)
    result = packet.assess_rows(frozen, corrected)
    assert result["status"] == "PASS"
    assert len(result["preservation"]["passed_case_ids"]) == 11
    assert result["regressions"]["passed_case_ids"] == list(packet.REGRESSION_IDS)
    assert result["preexisting"]["status"] == "FAIL"
    assert result["preexisting"]["mandatory"] is False
    assert result["preexisting"]["failed_case_ids"] == ["namespace_root_empty"]
    assert packet.assess_rows(frozen, rows(True))["status"] == "FAIL"


def test_new_failure_in_previously_correct_case_blocks_acceptance(saved):
    frozen = packet.build_packet(saved["root"])
    changed = rows(False)
    changed[0]["public_api"] = outcome("$FIXTURE/left/ns")
    changed[0]["matches_reference"] = False
    result = packet.assess_rows(frozen, changed)
    assert result["regressions"]["status"] == "PASS"
    assert result["status"] == "FAIL"
    assert result["preservation"]["failed_case_ids"] == ["namespace_root_explicit"]


@pytest.mark.parametrize("change", ["input", "reference"])
def test_reexecution_cannot_change_case_input_or_expected_reference(saved, change):
    frozen = packet.build_packet(saved["root"])
    changed = rows(False)
    if change == "input":
        changed[0]["search"] = ["$FIXTURE/other"]
    else:
        changed[0]["importlib_reference"] = outcome("$FIXTURE/left/ns")
        changed[0]["matches_reference"] = False
    with pytest.raises(ContractError, match="verification case inputs|verification reference"):
        packet.assess_rows(frozen, changed)
