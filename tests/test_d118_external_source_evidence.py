from __future__ import annotations

import builtins
import copy
import inspect
import json
import os
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Any

import pytest

from patchloop.memory import d118_external_source_evidence as d118
from patchloop.util import canonical_json, sha256_text

REPOSITORY = Path(__file__).resolve().parents[1]


def _copy(relative: str | Path, destination: Path) -> None:
    source = REPOSITORY / relative
    target = destination / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _copy_materialization_repository(destination: Path) -> None:
    paths = {
        *(Path(spec["path"]) for spec in d118.PROTECTED_FILE_SPECS),
        *d118.D118_IMPLEMENTATION_PATHS,
        *(
            Path(source["local_root"]) / file_spec["path"]
            for source in d118.SOURCE_SPECS
            for file_spec in source["requested_paths"]
        ),
    }
    for relative in sorted(paths, key=lambda value: value.as_posix()):
        _copy(relative, destination)


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rehash(payload: dict[str, Any], *, id_field: str, id_prefix: str) -> None:
    body_hash = sha256_text(canonical_json(payload["semantic_body"]))
    payload["semantic_body_hash"] = body_hash
    payload[id_field] = id_prefix + body_hash.removeprefix("sha256:")


def _build_evidence(repository: Path) -> dict[str, Any]:
    context = d118._load_exact_d117_context(repository)
    protected = d118._protected_state(repository)
    implementation = d118._implementation_state(repository)
    external = d118._expected_external_object_state()
    receipt = d118.build_d118_approval_receipt(repository=repository, context=context)
    preflight = d118.build_d118_preflight(
        receipt,
        repository=repository,
        context=context,
        protected_pre=protected,
    )
    evidence_pack = d118.build_d118_evidence_pack(
        receipt,
        preflight,
        external_pre=external,
        external_post=external,
        protected_pre=protected,
        protected_post=protected,
    )
    gate = d118.build_d118_source_gate(
        receipt,
        preflight,
        evidence_pack,
        repository=repository,
        context=context,
        implementation_pre=implementation,
        implementation_post=implementation,
    )
    return {
        "context": context,
        "protected": protected,
        "implementation": implementation,
        "external": external,
        "receipt": receipt,
        "preflight": preflight,
        "evidence_pack": evidence_pack,
        "gate": gate,
    }


@pytest.fixture(scope="module")
def built_evidence() -> dict[str, Any]:
    return _build_evidence(REPOSITORY)


@pytest.fixture(scope="module")
def materialized_repository(tmp_path_factory: pytest.TempPathFactory) -> Path:
    repository = tmp_path_factory.mktemp("d118-materialized")
    _copy_materialization_repository(repository)
    d118.run_d118_external_source_evidence(repository=repository)
    return repository


def test_exact_d117_candidate_gate_and_next_action_are_bound(
    built_evidence: dict[str, Any],
) -> None:
    context = built_evidence["context"]
    receipt = built_evidence["receipt"]["semantic_body"]
    preflight = built_evidence["preflight"]["semantic_body"]

    assert d118.EXPECTED_D117_CANDIDATE_ID == (
        "d117blindprotocolcandidate_"
        "27622afdd9d46e43cb9e23675a334b5a4e91fc768298374cae61ab440c850dae"
    )
    assert d118.EXPECTED_D117_CANDIDATE_BODY_SHA == (
        "sha256:27622afdd9d46e43cb9e23675a334b5a4e91fc768298374cae61ab440c850dae"
    )
    assert d118.EXPECTED_D117_CANDIDATE_BYTES == 7_999
    assert d118.EXPECTED_D117_CANDIDATE_FILE_SHA == (
        "sha256:d10bbe5b3b65050868a1202cd1af9f130c89bbe43ceccf9359af145cac96cda7"
    )
    assert d118.EXPECTED_D117_GATE_ID == (
        "d117_750cd5a0a8946984aafe75b0939417bf026120cdb3dbc54d09180fd795202589"
    )
    assert d118.EXPECTED_D117_GATE_BODY_SHA == (
        "sha256:750cd5a0a8946984aafe75b0939417bf026120cdb3dbc54d09180fd795202589"
    )
    assert d118.EXPECTED_D117_GATE_BYTES == 16_813
    assert d118.EXPECTED_D117_GATE_FILE_SHA == (
        "sha256:a439fc936b5b594c043b4ea90cd57bb676e79004cf4de8794b83f3af15fb13e3"
    )
    assert d118.EXPECTED_D117_PROPOSED_ACTION_HASH == (
        "sha256:362cf3f74c9d57ecc4238f4b7c024b470c8ad65038ee6a599581a1df82fc6c06"
    )

    assert context["candidate"]["candidate_id"] == (d118.EXPECTED_D117_CANDIDATE_ID)
    assert context["candidate"]["semantic_body_hash"] == d118.EXPECTED_D117_CANDIDATE_BODY_SHA
    assert context["gate"]["gate_id"] == d118.EXPECTED_D117_GATE_ID
    assert context["gate"]["semantic_body_hash"] == d118.EXPECTED_D117_GATE_BODY_SHA
    assert receipt["approval_reference"] == {
        "candidate_id": d118.EXPECTED_D117_CANDIDATE_ID,
        "semantic_body_hash": d118.EXPECTED_D117_CANDIDATE_BODY_SHA,
        "file_sha256": d118.EXPECTED_D117_CANDIDATE_FILE_SHA,
    }
    assert receipt["authorized_scope"] == d118.AUTHORIZED_SCOPE
    assert receipt["authorized_action_hash"] == d118.AUTHORIZED_ACTION_HASH
    assert (
        receipt["claim_semantics"][
            "d117_later_execution_candidate_action_not_authorized_or_consumed"
        ]
        is True
    )
    assert receipt["claim_semantics"]["external_triples_prerequisite_not_satisfied"] is True
    assert preflight["d117_candidate"]["file_sha256"] == (d118.EXPECTED_D117_CANDIDATE_FILE_SHA)
    assert preflight["d117_source_gate"]["file_sha256"] == (d118.EXPECTED_D117_GATE_FILE_SHA)


@pytest.mark.parametrize(
    ("constant", "message"),
    [
        ("EXPECTED_D117_CANDIDATE_FILE_SHA", "candidate file SHA drifted"),
        ("EXPECTED_D117_GATE_FILE_SHA", "source gate file SHA drifted"),
        ("EXPECTED_D117_PROPOSED_ACTION_HASH", "proposed action hash drifted"),
    ],
)
def test_d117_binding_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    constant: str,
    message: str,
) -> None:
    monkeypatch.setattr(d118, constant, "sha256:" + "0" * 64)
    with pytest.raises(d118.D118ExternalEvidenceError, match=message):
        d118._load_exact_d117_context(REPOSITORY)


def test_six_external_objects_match_exact_opaque_hash_set() -> None:
    expected = d118._expected_external_object_state()
    observed = d118.observe_external_objects(repository=REPOSITORY)

    exact_files = [
        {
            "source_id": "swe-bench-dev-f5351",
            "path": ".patchloop/external-evidence/d118/swe-bench-f5351/.gitattributes",
            "file_bytes": 2_307,
            "file_sha256": (
                "sha256:f4e703ea6e44bbebe53aceed2a89c11e40b88b7ae130c480c89860ab805ffc8f"
            ),
            "media_kind": "source-level-git-metadata",
        },
        {
            "source_id": "swe-bench-dev-f5351",
            "path": ".patchloop/external-evidence/d118/swe-bench-f5351/README.md",
            "file_bytes": 3_880,
            "file_sha256": (
                "sha256:807eeb9e3a95b1b06958d7b7d93bc796c9b454fffdfa22f646ccfff2e17af45c"
            ),
            "media_kind": "source-level-dataset-card",
        },
        {
            "source_id": "swe-bench-dev-f5351",
            "path": (
                ".patchloop/external-evidence/d118/swe-bench-f5351/data/dev-00000-of-00001.parquet"
            ),
            "file_bytes": 1_382_594,
            "file_sha256": (
                "sha256:d758d54540aa4140d0274ed0cc93b8288aa6f323c3c603e2557e7666a47fc41b"
            ),
            "media_kind": "opaque-record-container",
        },
        {
            "source_id": "swe-gym-train-26a6",
            "path": ".patchloop/external-evidence/d118/swe-gym-26a6/.gitattributes",
            "file_bytes": 2_461,
            "file_sha256": (
                "sha256:e7a120ab07b1bc5b486be249e9fc6c83d59448d0093e1dfebe95d1566d9cafc0"
            ),
            "media_kind": "source-level-git-metadata",
        },
        {
            "source_id": "swe-gym-train-26a6",
            "path": ".patchloop/external-evidence/d118/swe-gym-26a6/README.md",
            "file_bytes": 680,
            "file_sha256": (
                "sha256:e6aadc383f198bb7592af3c077d8dd71d350a86bea76e1218fd1042fe4b99a04"
            ),
            "media_kind": "source-level-dataset-card",
        },
        {
            "source_id": "swe-gym-train-26a6",
            "path": (
                ".patchloop/external-evidence/d118/swe-gym-26a6/data/train-00000-of-00001.parquet"
            ),
            "file_bytes": 43_644_473,
            "file_sha256": (
                "sha256:60569cea74bb281f7a5579467436a2bc1932c6e0c5f2f7fa0d084392abd9ad97"
            ),
            "media_kind": "opaque-record-container",
        },
    ]

    assert observed == expected
    assert observed["files"] == exact_files
    assert observed["file_count"] == 6
    assert len(observed["files"]) == 6
    assert {row["media_kind"] for row in observed["files"]} == {
        "source-level-git-metadata",
        "source-level-dataset-card",
        "opaque-record-container",
    }
    assert sum(row["media_kind"] == "opaque-record-container" for row in observed["files"]) == 2
    assert all(str(row["file_sha256"]).startswith("sha256:") for row in observed["files"])


def test_opaque_observation_never_parses_decodes_imports_or_uses_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_paths = {
        (REPOSITORY / row["path"]).resolve()
        for row in d118._expected_external_object_state()["files"]
    }
    opened: list[tuple[Path, str]] = []
    original_open = Path.open
    original_import = builtins.__import__

    def tracked_open(path: Path, *args: Any, **kwargs: Any) -> Any:
        mode = str(args[0]) if args else str(kwargs.get("mode", "r"))
        resolved = path.resolve()
        assert resolved in expected_paths, f"unexpected D-118 opaque read: {resolved}"
        assert mode == "rb"
        opened.append((resolved, mode))
        return original_open(path, *args, **kwargs)

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("D-118 crossed the hash-only local boundary")

    forbidden_imports = (
        "pyarrow",
        "pandas",
        "datasets",
        "duckdb",
        "fastparquet",
        "huggingface_hub",
        "requests",
        "httpx",
        "urllib",
        "openai",
    )

    def guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.startswith(forbidden_imports):
            raise AssertionError(f"D-118 imported forbidden module: {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(Path, "open", tracked_open)
    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(d118.json, "loads", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)

    assert d118.observe_external_objects(repository=REPOSITORY) == (
        d118._expected_external_object_state()
    )
    assert {path for path, _mode in opened} == expected_paths
    assert len(opened) == 6


def test_no_record_parser_projector_downloader_or_runtime_entrypoint_exists() -> None:
    function_names = {
        name
        for name, value in inspect.getmembers(d118, inspect.isfunction)
        if value.__module__ == d118.__name__
    }

    assert function_names.isdisjoint(
        {
            "download",
            "download_snapshot",
            "parse_parquet",
            "read_schema",
            "read_records",
            "project_records",
            "sanitize_records",
            "select_pool",
            "acquire_pool",
            "freeze_pool",
            "label_issues",
            "execute_matcher",
            "run_classifier",
            "run_calibration",
            "run_agent",
        }
    )


def test_opaque_membership_cutoff_and_isolation_contracts_remain_blocked(
    built_evidence: dict[str, Any],
) -> None:
    body = built_evidence["preflight"]["semantic_body"]
    opaque = body["opaque_handling_contract"]
    membership = body["membership_preflight_contract"]
    cutoff = body["cutoff_preflight_contract"]
    isolation = body["isolation_profile"]

    assert opaque["binary_stream_hash_only"] is True
    assert opaque["parquet_footer_schema_statistics_or_row_parse_allowed"] is False
    assert opaque["archive_extraction_or_decompression_allowed"] is False
    assert opaque["utf8_decode_of_opaque_container_allowed"] is False
    assert opaque["record_field_read_count"] == 0
    assert opaque["issue_prose_label_hint_patch_test_or_oracle_read_count"] == 0

    assert membership["all_rules_provider_reported_content_bound"] is True
    assert membership["all_rules_content_bound_verified_from_bound_inputs_by_d118"] is False
    assert membership["all_rules_trusted_pre_d116_time_bound"] is False
    assert membership["membership_ready_for_independent_calibration"] is False
    assert len(membership["rules"]) == 2
    for rule in membership["rules"]:
        assert rule["verified_member_count"] is None
        assert rule["member_id_read_count"] == 0
        assert rule["record_content_read_count"] == 0
        assert rule["content_or_label_dependent_selection"] is False
        assert rule["provider_reports_rule_and_shard_content_bound_in_tree"] is True
        assert rule["provider_tree_binding_verified_from_bound_inputs_by_d118"] is False
        assert rule["readme_rule_or_count_parsed_by_d118"] is False
        assert rule["rule_trusted_pre_d116_time_bound"] is False

    assert cutoff["d116_cutoff_exclusive"] == d118.EXPECTED_D116_CUTOFF
    assert cutoff["trusted_cutoff_anchor_verified"] is False
    for source in cutoff["sources"]:
        assert source["signature_payload_and_key_verified_locally"] is False
        assert source["git_timestamp_accepted_as_trusted_time"] is False
        assert source["trusted_anchor_binds_snapshot_and_membership_rule"] is False
        assert source["strictly_before_d116_cutoff_verified"] is False

    assert isolation["immutable_image_digest"] is None
    assert isolation["network_mode"] == "none"
    assert isolation["root_filesystem_read_only"] is True
    assert isolation["run_as_non_root"] is True
    assert isolation["capabilities_drop"] == ["ALL"]
    assert isolation["host_pid_ipc_or_docker_socket_allowed"] is False
    assert isolation["current_process_or_same_checkout_agent_eligible_as_blind_role"] is False
    assert isolation["technical_negative_probe_executed"] is False
    assert isolation["isolation_session_count"] == 0
    assert body["isolation_profile_hash"] == sha256_text(canonical_json(isolation))


def test_source_candidates_are_hash_evidence_not_a_pool(
    built_evidence: dict[str, Any],
) -> None:
    pack = built_evidence["evidence_pack"]["semantic_body"]

    assert pack["aggregate_disposition"] == {
        "status": "BLOCKED_INSUFFICIENT_PREEXISTENCE",
        "snapshot_hashes_verified_during_d118_materialization": True,
        "exhaustive_development_split_rules_provider_reported_content_bound": True,
        "provider_tree_or_membership_proof_rebuilt_from_bound_inputs": False,
        "trusted_cutoff_anchor_verified": False,
        "technical_isolation_verified": False,
        "post_hoc": True,
        "independent": False,
        "eligible_for_independent_calibration": False,
        "execution_authorization_candidate_ready": False,
    }
    assert len(pack["source_candidates"]) == 2
    for candidate in pack["source_candidates"]:
        assert candidate["snapshot_hash_and_size_verified"] is True
        assert candidate["snapshot_body_decoded"] is False
        assert candidate["archive_extracted"] is False
        assert candidate["record_fields_read"] == []
        assert candidate["issue_or_task_record_read_count"] == 0
        assert candidate["verified_member_count"] is None
        assert candidate["provider_tree_or_signature_proof_bound_in_pack"] is False
        assert candidate["lineage_overlap_with_existing_tasks_checked"] is False
        assert candidate["public_only_sanitized_projection_created"] is False
        assert candidate["pool_selected_acquired_or_frozen"] is False
        assert candidate["post_hoc"] is True
        assert candidate["independent"] is False
        assert candidate["eligible_for_independent_calibration"] is False


def test_authority_is_exactly_closed_across_all_artifacts(
    built_evidence: dict[str, Any],
) -> None:
    expected = d118._authority()
    for artifact_name in ("preflight", "evidence_pack", "gate"):
        assert built_evidence[artifact_name]["semantic_body"]["authority"] == expected

    assert expected["external_source_evidence_preparation_authorized"] is True
    assert expected["revision_pinned_opaque_snapshot_download_authorized"] is True
    assert expected["source_pool_selection_acquisition_or_freeze_authorized"] is False
    assert expected["source_pool_selected"] is False
    assert expected["source_pool_acquired"] is False
    assert expected["source_pool_frozen"] is False
    assert expected["trusted_cutoff_anchor_verified"] is False
    assert expected["d118_execution_authorization_candidate_ready"] is False
    assert expected["retrieval_ready"] is False
    assert expected["core_campaign_unlocked"] is False
    for key in (
        "issue_or_task_record_read_count",
        "issue_labeling_or_review_count",
        "matcher_execution_count",
        "classifier_execution_count",
        "calibration_execution_count",
        "independent_positive_count",
        "retrieval_calls",
        "runtime_memory_injection_count",
        "agent_runs",
        "provider_calls_made",
        "evaluator_calls_made",
    ):
        assert expected[key] == 0


@pytest.mark.parametrize("state_kind", ["protected", "external", "implementation"])
def test_pre_post_state_drift_fails_closed(
    built_evidence: dict[str, Any],
    state_kind: str,
) -> None:
    if state_kind in {"protected", "external"}:
        protected_post = copy.deepcopy(built_evidence["protected"])
        external_post = copy.deepcopy(built_evidence["external"])
        if state_kind == "protected":
            protected_post["fingerprint"] = "sha256:" + "0" * 64
            message = "protected inputs changed"
        else:
            external_post["fingerprint"] = "sha256:" + "0" * 64
            message = "opaque external objects changed"
        with pytest.raises(d118.D118ExternalEvidenceError, match=message):
            d118.build_d118_evidence_pack(
                built_evidence["receipt"],
                built_evidence["preflight"],
                external_pre=built_evidence["external"],
                external_post=external_post,
                protected_pre=built_evidence["protected"],
                protected_post=protected_post,
            )
        return

    implementation_post = copy.deepcopy(built_evidence["implementation"])
    implementation_post["fingerprint"] = "sha256:" + "0" * 64
    with pytest.raises(d118.D118ExternalEvidenceError, match="implementation changed"):
        d118.build_d118_source_gate(
            built_evidence["receipt"],
            built_evidence["preflight"],
            built_evidence["evidence_pack"],
            repository=REPOSITORY,
            context=built_evidence["context"],
            implementation_pre=built_evidence["implementation"],
            implementation_post=implementation_post,
        )


def test_protected_file_hash_drift_fails_closed(
    tmp_path: Path,
) -> None:
    for spec in d118.PROTECTED_FILE_SPECS:
        _copy(spec["path"], tmp_path)
    selected = tmp_path / d118.PROTECTED_FILE_SPECS[0]["path"]
    selected.write_bytes(selected.read_bytes() + b"tamper")

    with pytest.raises(d118.D118ExternalEvidenceError, match="protected input drifted"):
        d118._protected_state(tmp_path)


def test_partial_output_set_is_never_repaired_or_overwritten(tmp_path: Path) -> None:
    conflict = tmp_path / d118.DEFAULT_EVIDENCE_PACK_PATH
    conflict.parent.mkdir(parents=True, exist_ok=True)
    conflict.write_bytes(b"conflicting-pack")

    with pytest.raises(d118.D118ExternalEvidenceError, match="partial artifact set exists"):
        d118.run_d118_external_source_evidence(repository=tmp_path)

    assert conflict.read_bytes() == b"conflicting-pack"
    assert not (tmp_path / d118.DEFAULT_RECEIPT_PATH).exists()
    assert not (tmp_path / d118.DEFAULT_PREFLIGHT_PATH).exists()
    assert not (tmp_path / d118.DEFAULT_SOURCE_GATE_PATH).exists()


def test_dangling_linklike_output_is_rejected_before_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logical_output = tmp_path / d118.DEFAULT_RECEIPT_PATH
    redirected_target = tmp_path / "reports/memory-development/redirected.json"
    logical_output.parent.mkdir(parents=True, exist_ok=True)
    real_is_linklike = d118._is_linklike

    def simulated_dangling_link(path: Path) -> bool:
        return path == logical_output or real_is_linklike(path)

    monkeypatch.setattr(d118, "_is_linklike", simulated_dangling_link)

    with pytest.raises(d118.D118ExternalEvidenceError, match="linked final component"):
        d118.run_d118_external_source_evidence(repository=tmp_path)

    assert not logical_output.exists()
    assert not redirected_target.exists()


def test_deterministic_rebuild_is_exact_and_idempotent(
    materialized_repository: Path,
) -> None:
    paths = (
        d118.DEFAULT_RECEIPT_PATH,
        d118.DEFAULT_PREFLIGHT_PATH,
        d118.DEFAULT_EVIDENCE_PACK_PATH,
        d118.DEFAULT_SOURCE_GATE_PATH,
    )
    first_bytes = {path: (materialized_repository / path).read_bytes() for path in paths}

    second = d118.run_d118_external_source_evidence(repository=materialized_repository)

    assert second["complete_exact_set_preexisted"] is True
    assert first_bytes == {path: (materialized_repository / path).read_bytes() for path in paths}
    assert second["aggregate_disposition"] == "BLOCKED_INSUFFICIENT_PREEXISTENCE"
    assert second["validation_mode"] == "current-object"
    assert second["sealed_historical_pack_validated"] is True
    assert second["current_external_objects_reverified"] is True
    assert second["record_read_count"] == 0
    assert second["execution_authorization_candidate_ready"] is False


@pytest.mark.parametrize(
    ("tamper", "message"),
    [
        ("unknown-field", "exact key set/order mismatch"),
        ("full-payload", "full expected payload mismatch"),
        ("noncanonical-bytes", "canonical bytes drifted"),
    ],
)
def test_evidence_pack_tamper_fails_even_after_full_rehash(
    materialized_repository: Path,
    tamper: str,
    message: str,
) -> None:
    path = materialized_repository / d118.DEFAULT_EVIDENCE_PACK_PATH
    original = path.read_bytes()
    payload = _json(path)
    try:
        if tamper == "noncanonical-bytes":
            path.write_bytes(original + b" \n")
        else:
            if tamper == "unknown-field":
                payload["semantic_body"]["unknown_claim"] = False
            else:
                payload["semantic_body"]["aggregate_disposition"]["status"] = "READY"
            _rehash(
                payload,
                id_field="evidence_pack_id",
                id_prefix="d118evidencepack_",
            )
            path.write_bytes(d118._pretty_json(payload))

        with pytest.raises(d118.D118ExternalEvidenceError, match=message):
            d118.validate_d118_artifacts(repository=materialized_repository)
    finally:
        path.write_bytes(original)


def test_chronology_rejects_equal_reversed_and_naive_times(
    built_evidence: dict[str, Any],
) -> None:
    receipt = built_evidence["receipt"]
    preflight = copy.deepcopy(built_evidence["preflight"])
    preflight["semantic_body"]["recorded_at"] = receipt["semantic_body"]["recorded_at"]
    with pytest.raises(d118.D118ExternalEvidenceError, match="strictly increasing"):
        d118._validate_chronology(receipt, preflight)

    with pytest.raises(d118.D118ExternalEvidenceError, match="timezone-aware"):
        d118._parse_time("2026-08-07T10:17:00", label="tampered")


def test_sealed_historical_validation_does_not_require_current_opaque_objects(
    materialized_repository: Path,
    tmp_path: Path,
) -> None:
    paths = {
        *(Path(spec["path"]) for spec in d118.PROTECTED_FILE_SPECS),
        *d118.D118_IMPLEMENTATION_PATHS,
        d118.DEFAULT_RECEIPT_PATH,
        d118.DEFAULT_PREFLIGHT_PATH,
        d118.DEFAULT_EVIDENCE_PACK_PATH,
        d118.DEFAULT_SOURCE_GATE_PATH,
    }
    for relative in sorted(paths, key=lambda value: value.as_posix()):
        source = materialized_repository / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    sealed = d118.validate_d118_artifacts(repository=tmp_path)
    assert sealed["validation_mode"] == "sealed-historical"
    assert sealed["sealed_historical_pack_validated"] is True
    assert sealed["current_external_objects_reverified"] is False

    with pytest.raises((d118.D118ExternalEvidenceError, FileNotFoundError)):
        d118.validate_d118_artifacts(repository=tmp_path, mode="current-object")


def test_validation_rejects_unknown_mode(materialized_repository: Path) -> None:
    with pytest.raises(d118.D118ExternalEvidenceError, match="validation mode"):
        d118.validate_d118_artifacts(repository=materialized_repository, mode="current")
