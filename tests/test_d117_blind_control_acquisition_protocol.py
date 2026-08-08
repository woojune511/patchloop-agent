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

from patchloop.memory import d117_blind_control_acquisition_protocol as d117
from patchloop.util import canonical_json, sha256_bytes, sha256_text

REPOSITORY = Path(__file__).resolve().parents[1]


def _copy(relative: str | Path, destination: Path) -> None:
    source = REPOSITORY / relative
    target = destination / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _copy_materialization_repository(destination: Path) -> None:
    paths = {
        *(Path(spec["path"]) for spec in d117.PROTECTED_FILE_SPECS),
        *d117.D117_IMPLEMENTATION_PATHS,
    }
    for relative in sorted(paths, key=lambda value: value.as_posix()):
        _copy(relative, destination)


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rehash(payload: dict[str, Any], *, id_field: str, id_prefix: str) -> None:
    body_hash = sha256_text(canonical_json(payload["semantic_body"]))
    payload["semantic_body_hash"] = body_hash
    payload[id_field] = id_prefix + body_hash.removeprefix("sha256:")


def _build_protocol(repository: Path) -> dict[str, Any]:
    context = d117._load_exact_context(repository)
    protected = d117._protected_input_state(repository)
    implementation = d117._implementation_state(repository)
    receipt = d117.build_d117_approval_receipt(
        repository=repository,
        context=context,
        protected_pre=protected,
        implementation_pre=implementation,
    )
    preflight = d117.build_d117_preflight(
        receipt,
        repository=repository,
        context=context,
    )
    candidate = d117.build_d117_candidate(receipt, preflight, repository=repository)
    gate = d117.build_d117_source_gate(
        receipt,
        preflight,
        candidate,
        repository=repository,
        context=context,
        protected_pre=protected,
        protected_post=protected,
        implementation_pre=implementation,
        implementation_post=implementation,
    )
    return {
        "context": context,
        "protected": protected,
        "implementation": implementation,
        "receipt": receipt,
        "preflight": preflight,
        "candidate": candidate,
        "gate": gate,
    }


@pytest.fixture(scope="module")
def built_protocol() -> dict[str, Any]:
    return _build_protocol(REPOSITORY)


def test_exact_d116_approval_candidate_gate_and_action_are_bound(
    built_protocol: dict[str, Any],
) -> None:
    context = built_protocol["context"]
    receipt = built_protocol["receipt"]["semantic_body"]
    preflight = built_protocol["preflight"]["semantic_body"]

    assert d117.EXPECTED_D116_CANDIDATE_ID == (
        "d116classsignalcandidate_0b1b700af4ce2274cb9cb032ecf23c741ec9c41b0e86abbc06e96e18f91c74d4"
    )
    assert d117.EXPECTED_D116_CANDIDATE_BODY_SHA == (
        "sha256:0b1b700af4ce2274cb9cb032ecf23c741ec9c41b0e86abbc06e96e18f91c74d4"
    )
    assert d117.EXPECTED_D116_CANDIDATE_FILE_SHA == (
        "sha256:8299f3d400bd9412a8b7100305a0eb57f1d5b4ea78a39d8e5edad6cd5a2b15ca"
    )
    assert d117.EXPECTED_D116_ACTION_HASH == (
        "sha256:e368dcb794875064f605a341902b4c27be20fcb3ff9b86d65ca5fb66dbf35e55"
    )
    assert receipt["approval_reference"] == {
        "candidate_id": d117.EXPECTED_D116_CANDIDATE_ID,
        "semantic_body_hash": d117.EXPECTED_D116_CANDIDATE_BODY_SHA,
        "file_sha256": d117.EXPECTED_D116_CANDIDATE_FILE_SHA,
    }
    assert receipt["authorized_action_hash"] == d117.EXPECTED_D116_ACTION_HASH
    assert receipt["authorized_scope"] == context["authorized_scope"]
    assert receipt["d116_source_gate"]["gate_id"] == d117.EXPECTED_D116_GATE_ID
    assert receipt["d116_candidate"]["candidate_id"] == d117.EXPECTED_D116_CANDIDATE_ID
    assert preflight["predecessor_contract_binding"] == {
        "d116_authorized_action_hash": d117.EXPECTED_D116_ACTION_HASH,
        "d116_cutoff": d117.EXPECTED_D116_CUTOFF,
        "d116_taxonomy_contract_hash": d117.EXPECTED_D116_TAXONOMY_HASH,
        "d116_frozen_matcher_grammar_hash": d117.EXPECTED_D116_GRAMMAR_HASH,
        "d116_current_process_or_agent_eligible_as_blind_selector": False,
        "authorized_scope_exact_copy": context["authorized_scope"],
    }
    assert receipt["execution_result_present"] is False
    assert receipt["claim_semantics"]["one_use_pool_acquisition_execution_claim"] is False


@pytest.mark.parametrize(
    ("constant", "message"),
    [
        ("EXPECTED_D116_ACTION_HASH", "authorized action hash mismatch"),
        ("EXPECTED_D116_CANDIDATE_FILE_SHA", "candidate exact file binding mismatch"),
        ("EXPECTED_D105_RENDER_SET_HASH", "rubric set hash mismatch"),
    ],
)
def test_predecessor_or_rubric_binding_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    constant: str,
    message: str,
) -> None:
    monkeypatch.setattr(d117, constant, "sha256:" + "0" * 64)
    with pytest.raises(d117.D117BlindProtocolError, match=message):
        d117._load_exact_context(REPOSITORY)


def test_exact_d105_three_group_rubric_is_bound_without_d116_expectations(
    built_protocol: dict[str, Any],
) -> None:
    rubric = built_protocol["preflight"]["semantic_body"]["d105_rubric_contract"]

    assert rubric["d105_gate"]["gate_id"] == d117.EXPECTED_D105_GATE_ID
    assert rubric["ordered_render_set_hash"] == d117.EXPECTED_D105_RENDER_SET_HASH
    assert rubric["group_count"] == 3
    assert [row["order"] for row in rubric["groups"]] == [1, 2, 3]
    assert [row["semantic_group_id"] for row in rubric["groups"]] == [
        "platform-emulation-matrix-gap",
        "request-context-propagation-gap",
        "exception-origin-state-conflation",
    ]
    for row, spec in zip(rubric["groups"], d117.D105_RUBRIC_SPECS, strict=True):
        assert row == {
            "order": spec["order"],
            "semantic_group_id": spec["semantic_group_id"],
            "path": spec["path"],
            "file_bytes": spec["file_bytes"],
            "file_sha256": spec["file_sha256"],
        }
        content = (REPOSITORY / spec["path"]).read_bytes()
        assert len(content) == spec["file_bytes"]
        assert sha256_bytes(content) == spec["file_sha256"]
    assert rubric["d116_regex_predicate_or_synthetic_case_in_packet"] is False
    assert rubric["d116_source_anchor_expectation_in_packet"] is False
    assert rubric["d112_moto_hypothesis_in_packet"] is False
    assert rubric["tox_source_association_in_packet"] is False
    assert rubric["task_or_repository_identity_in_packet"] is False
    assert rubric["rubric_is_public_applicability_guidance_not_failure_cause_ground_truth"]


def test_materialization_scope_is_four_new_protocol_artifacts_only(
    built_protocol: dict[str, Any],
) -> None:
    scope = built_protocol["receipt"]["semantic_body"]["materialization_scope"]
    assert scope["new_module_script_test_only"] is True
    assert scope["new_artifact_paths"] == [
        d117.DEFAULT_RECEIPT_PATH.as_posix(),
        d117.DEFAULT_PREFLIGHT_PATH.as_posix(),
        d117.DEFAULT_CANDIDATE_PATH.as_posix(),
        d117.DEFAULT_SOURCE_GATE_PATH.as_posix(),
    ]
    assert scope["actual_pool_manifest_issue_bytes_blind_packet_or_label_allowed"] is False
    assert scope["actual_pool_or_public_issue_read_allowed"] is False
    assert scope["role_assignment_or_isolation_session_execution_allowed"] is False
    assert scope["matcher_classifier_or_calibration_implementation_or_execution_allowed"] is False
    assert scope["existing_predecessor_code_artifact_task_or_index_mutation_allowed"] is False


def test_cutoff_and_preexistence_proof_contract_fails_closed(
    built_protocol: dict[str, Any],
) -> None:
    contract = built_protocol["preflight"]["semantic_body"]["cutoff_and_preexistence_contract"]

    assert contract["source_pool_scope"] == "public-development-controls-only"
    assert contract["held_out_task_issue_or_result_membership_allowed"] is False
    assert contract["private_hidden_reference_patch_trace_or_evaluator_membership_allowed"] is False
    assert contract["d116_cutoff_exclusive"] == d117.EXPECTED_D116_CUTOFF
    assert contract["strict_relation_required"] == (
        "proof_anchor_timestamp < d116_cutoff_exclusive"
    )
    assert contract["membership_basis_domain"] == [
        "exact-byte-frozen-membership-manifest",
        "byte-frozen-grammar-independent-exhaustive-inclusion-rule",
    ]
    assert contract["exact_source_bytes_must_credibly_predate_cutoff"] is True
    assert contract["membership_basis_must_credibly_predate_cutoff"] is True
    for key in (
        "source_issue_created_before_cutoff_alone_is_sufficient",
        "membership_or_rule_authored_after_d116_allowed",
        "post_cutoff_issue_prose_rewrite_allowed",
        "current_fetch_or_newly_computed_hash_is_retroactive_preexistence_proof",
        "filesystem_mtime_is_preexistence_proof",
        "git_author_or_committer_timestamp_alone_is_preexistence_proof",
        "self_attested_created_at_alone_is_preexistence_proof",
    ):
        assert contract[key] is False
    assert contract["pool_membership_or_exhaustive_rule_must_be_frozen_before_grammar_seal"]
    assert contract["pool_assembler_must_not_choose_among_multiple_post-hoc-subsets"]
    assert contract["neutral_exhaustive_rule_or_precommitted_seed_required"]
    assert contract["actual_source_pool_identified"] is False
    assert contract["actual_source_pool_read_count"] == 0
    assert contract["actual_source_pool_frozen"] is False
    assert contract["trusted_cutoff_anchor_verified"] is False
    assert contract["pre_d116_membership_verified"] is False


def test_role_visibility_is_default_deny_and_current_actor_is_ineligible(
    built_protocol: dict[str, Any],
) -> None:
    contract = built_protocol["preflight"]["semantic_body"]["role_separation_contract"]
    roles = {row["role"]: row for row in contract["roles"]}

    assert list(roles) == [
        "provenance-verifier",
        "pool-assembler",
        "blinding-broker",
        "selector-a",
        "selector-b",
        "adjudicator",
        "independence-auditor",
        "future-matcher-evaluator",
    ]
    assert (
        contract["current_protocol_author_or_current_conversation_actor_is_blind_role_eligible"]
        is False
    )
    assert contract["same_checkout_subagent_is_technical_isolation"] is False
    assert contract["prompt_only_blinding_or_self_attestation_is_technical_isolation"] is False
    assert contract["one_principal_may_hold_multiple_blind_roles"] is False
    assembler = roles["pool-assembler"]
    assert "d105-rubric" in assembler["forbidden_inputs"]
    assert "d116-grammar-regex-hash-output-or-expectations" in assembler["forbidden_inputs"]
    assert assembler["may_label_applicability"] is False
    exact_blind_inputs = [
        "opaque-control-id",
        "canonical-issue-title-description-language",
        "exact-d105-applicability-rubric",
    ]
    for role_name in ("selector-a", "selector-b", "adjudicator"):
        assert roles[role_name]["allowed_inputs"] == exact_blind_inputs
        assert roles[role_name]["may_label_applicability"] is True
        assert any("d116-grammar" in item for item in roles[role_name]["forbidden_inputs"])
    isolation = contract["isolation_profile"]
    assert isolation["separate_clean_container_vm_or_os_identity_required"] is True
    assert (
        isolation["repository_git_agents_docs_d112_through_d116_trace_patch_index_mount_allowed"]
        is False
    )
    assert isolation["network_mode"] == "none"
    assert isolation["read_only_root_filesystem_required"] is True
    assert isolation["human_prior_knowledge_cryptographically_excluded"] is False
    assert isolation["maximum_honest_claim"] == "process-isolated-not-human-knowledge-proof"
    assert contract["actual_role_assignments"] == 0
    assert contract["actual_role_invocations"] == 0
    assert contract["actual_isolation_sessions"] == 0


def test_chain_of_custody_requires_opaque_packets_and_sealed_first_passes(
    built_protocol: dict[str, Any],
) -> None:
    contract = built_protocol["preflight"]["semantic_body"]["chain_of_custody_contract"]

    assert contract["future_blind_packet_required_fields"] == [
        "opaque_control_id",
        "canonical_public_projection",
        "canonical_projection_sha256",
        "exact_d105_rubric_set_hash",
    ]
    forbidden = set(contract["future_blind_packet_forbidden_fields"])
    assert {
        "task_id",
        "repository_url_or_name",
        "source_anchor_or_expected_group",
        "d112_hypothesis",
        "d116_matcher_grammar_regex_hash_output_or_expectation",
        "private_hidden_reference_patch_trace_or_evaluator_result",
    }.issubset(forbidden)
    assert contract["selector_a_b_and_adjudicator_first_pass_must_be_independently_sealed"]
    assert contract["cross_reveal_before_all_first_pass_seals_allowed"] is False
    assert contract["append_only_correction_chain_required"] is True
    assert contract["existing_pool_or_role_output_in_place_mutation_allowed"] is False
    assert contract["missing_access_log_or_binding_drift_fails_closed"] is True
    assert contract["actual_future_artifact_count"] == 0


def test_independence_fallback_preserves_records_and_never_invents_a_positive(
    built_protocol: dict[str, Any],
) -> None:
    contract = built_protocol["preflight"]["semantic_body"]["independence_and_fallback_contract"]
    fallback = contract["failure_fallback"]

    assert contract["all_logic_terms_required"] is True
    assert len(contract["independent_positive_logic"]) == 9
    assert contract["source_anchor_sanity_case_counts_as_independent"] is False
    assert contract["matcher_author_synthetic_case_counts_as_independent"] is False
    assert contract["abstention_counts_as_negative_failure_class_ground_truth"] is False
    assert fallback == {
        "post_hoc": True,
        "independent": False,
        "eligible_for_independent_calibration": False,
        "reason_code_required": True,
        "records_preserved_append_only": True,
    }
    expected_reasons = {
        "PRE_D116_SOURCE_BYTES_PROOF_MISSING",
        "PRE_D116_MEMBERSHIP_PROOF_MISSING",
        "TRUSTED_CUTOFF_ANCHOR_MISSING",
        "LIVE_CURRENT_FETCH_ONLY",
        "POST_CUTOFF_CONTENT_OR_MEMBERSHIP_CHANGE",
        "POOL_ASSEMBLER_FORBIDDEN_VISIBILITY",
        "SELECTOR_FORBIDDEN_VISIBILITY",
        "ADJUDICATOR_FORBIDDEN_VISIBILITY",
        "ROLE_PRINCIPAL_OVERLAP",
        "CURRENT_GRAMMAR_OBSERVER_USED_IN_BLIND_ROLE",
        "TECHNICAL_ISOLATION_UNVERIFIED",
        "SOURCE_ANCHOR_OR_D116_PANEL_REUSE",
        "DUPLICATE_LINEAGE",
        "CHAIN_OF_CUSTODY_DRIFT",
        "FIRST_PASS_NOT_SEALED_BEFORE_REVEAL",
        "SELECTOR_OR_ADJUDICATOR_DISAGREEMENT",
        "EVIDENCE_SPAN_INVALID",
        "DO_NOT_APPLY_CONTRADICTION",
        "UNKNOWN_OR_INCOMPLETE_INDEPENDENCE_EVIDENCE",
    }
    assert set(contract["failure_reason_code_domain"]) == expected_reasons
    assert contract["pool_scope_failure_downgrades_entire_pool"] is True
    assert contract["role_session_failure_downgrades_all_members_seen_by_session"] is True
    assert contract["member_scope_failure_downgrades_only_member"] is True
    assert contract["unknown_evidence_is_independent"] is False
    assert contract["zero_eligible_controls_is_valid_outcome"] is True
    assert contract["zero_controls_may_weaken_ontology_or_grammar"] is False
    assert contract["one_positive_per_group_establishes_three_class_calibration"] is False
    assert contract["actual_independent_control_count"] == 0
    assert contract["actual_independent_positive_count"] == 0


def test_future_artifacts_and_d118_are_plan_only(
    built_protocol: dict[str, Any],
) -> None:
    preflight = built_protocol["preflight"]["semantic_body"]
    candidate = built_protocol["candidate"]["semantic_body"]
    future = preflight["future_artifact_contracts"]
    plan = preflight["prospective_execution_plan"]
    action = candidate["proposed_next_action"]

    assert future["schemas_are_plan_only"] is True
    assert future["materialized_in_d117"] is False
    assert future["actual_materialized_count"] == 0
    assert len(future["planned_schemas"]) == 6
    assert plan["current_status"] == "plan-only-no-pool-named-read-or-acquired"
    assert plan["actual_pool_or_issue_reads"] == 0
    assert plan["actual_role_sessions"] == 0
    assert plan["actual_matcher_classifier_or_calibration_runs"] == 0
    assert action["future_milestone"] == "D-118"
    assert action["external_source_snapshot_must_be_public_development_only"] is True
    assert action["held_out_task_issue_or_result_membership_or_read_allowed"] is False
    assert action["candidate_preparation_may_run_pool_acquisition"] is False
    assert action["candidate_preparation_may_read_unapproved_pool_or_issue_content"] is False
    assert action["current_process_or_any_d116_grammar_observer_may_be_blind_role"] is False
    assert action["same_checkout_subagent_or_prompt_only_blinding_is_sufficient"] is False
    assert action["unknown_independence_evidence_must_be_post_hoc_and_independent_false"]
    assert action["matcher_grammar_or_ontology_mutation_allowed"] is False
    assert (
        candidate["approval_contract"]["approval_would_authorize_actual_acquisition_or_review"]
        is False
    )


def test_all_pool_runtime_and_policy_authority_remains_closed(
    built_protocol: dict[str, Any],
) -> None:
    preflight_authority = built_protocol["preflight"]["semantic_body"]["authority"]
    candidate_authority = built_protocol["candidate"]["semantic_body"]["authority"]
    gate_authority = built_protocol["gate"]["semantic_body"]["authority"]

    true_keys = {
        "exact_d116_candidate_user_approval_received",
        "blind_control_acquisition_protocol_candidate_preparation_authorized",
        "blind_control_acquisition_protocol_prepared",
        "d116_cutoff_bound",
        "exact_d105_rubric_bound",
    }
    assert all(candidate_authority[key] is True for key in true_keys)
    assert preflight_authority["blind_control_acquisition_protocol_candidate_ready"] is False
    assert candidate_authority["blind_control_acquisition_protocol_candidate_ready"] is True
    false_keys = {
        "source_pool_discovery_authorized",
        "source_pool_acquisition_authorized",
        "source_pool_identified",
        "source_pool_acquired",
        "source_pool_frozen",
        "trusted_cutoff_anchor_verified",
        "pre_d116_membership_verified",
        "matcher_evaluator_implementation_authorized",
        "matcher_evaluator_implemented",
        "classifier_implementation_authorized",
        "classifier_implemented",
        "classifier_execution_authorized",
        "calibration_execution_authorized",
        "calibration_results_present",
        "three_class_calibrated",
        "independent_generalization_validated",
        "true_relevance_established",
        "corrected_policy_selected",
        "score_policy_mutation_authorized",
        "score_weights_or_threshold_changed",
        "runtime_failure_class_signal_changed",
        "ranking_policy_changed",
        "memory_entry_index_or_marker_changed",
        "retrieval_ready",
        "retrieval_experiment_authorized",
        "core_campaign_unlocked",
        "analysis_ready",
        "memory_effect_established",
        "negative_transfer_established",
    }
    zero_keys = {
        "source_pool_public_issue_read_count",
        "held_out_public_issue_or_result_read_count",
        "pool_manifest_count",
        "pool_member_count",
        "role_assignment_count",
        "isolation_session_count",
        "blind_packet_count",
        "selector_result_count",
        "adjudication_result_count",
        "independent_control_count",
        "independent_positive_count",
        "matcher_evaluator_execution_count",
        "classifier_execution_count",
        "calibration_execution_count",
        "runtime_memory_injection_count",
        "agent_runs",
        "provider_calls_made",
        "evaluator_calls_made",
        "network_capable_call_paths_invoked",
    }
    assert all(candidate_authority[key] is False for key in false_keys)
    assert all(candidate_authority[key] == 0 for key in zero_keys)
    assert gate_authority == candidate_authority


def test_deterministic_rebuild_preserves_protected_and_implementation_bytes(
    built_protocol: dict[str, Any],
) -> None:
    before_protected = d117._protected_input_state(REPOSITORY)
    before_implementation = d117._implementation_state(REPOSITORY)

    assert _build_protocol(REPOSITORY) == _build_protocol(REPOSITORY)
    assert d117._protected_input_state(REPOSITORY) == before_protected
    assert d117._implementation_state(REPOSITORY) == before_implementation
    assert built_protocol["gate"]["semantic_body"]["protected_input_integrity"] == {
        "pre_build": before_protected,
        "post_build": before_protected,
        "fingerprints_equal": True,
        "implementation_pre_build": before_implementation,
        "implementation_post_build": before_implementation,
        "implementation_fingerprints_equal": True,
    }


@pytest.mark.parametrize("state_kind", ["protected", "implementation"])
def test_source_gate_rejects_pre_post_state_drift(
    built_protocol: dict[str, Any],
    state_kind: str,
) -> None:
    protected_pre = built_protocol["protected"]
    protected_post = copy.deepcopy(protected_pre)
    implementation_pre = built_protocol["implementation"]
    implementation_post = copy.deepcopy(implementation_pre)
    if state_kind == "protected":
        protected_post["fingerprint"] = "sha256:" + "0" * 64
        message = "protected inputs changed"
    else:
        implementation_post["fingerprint"] = "sha256:" + "0" * 64
        message = "implementation changed"

    with pytest.raises(d117.D117BlindProtocolError, match=message):
        d117.build_d117_source_gate(
            built_protocol["receipt"],
            built_protocol["preflight"],
            built_protocol["candidate"],
            repository=REPOSITORY,
            context=built_protocol["context"],
            protected_pre=protected_pre,
            protected_post=protected_post,
            implementation_pre=implementation_pre,
            implementation_post=implementation_post,
        )


def test_build_path_reads_only_exact_predecessor_rubric_and_implementation_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reads: set[str] = set()
    original_open = Path.open

    def tracked_open(path: Path, *args: Any, **kwargs: Any) -> Any:
        mode = str(args[0]) if args else str(kwargs.get("mode", "r"))
        if "r" in mode:
            resolved = path.resolve()
            try:
                reads.add(resolved.relative_to(REPOSITORY).as_posix())
            except ValueError:
                raise AssertionError(f"D-117 read outside the repository: {resolved}") from None
        return original_open(path, *args, **kwargs)

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("D-117 crossed a protocol-only execution boundary")

    monkeypatch.setattr(Path, "open", tracked_open)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)

    _build_protocol(REPOSITORY)

    expected_reads = {
        *(str(spec["path"]) for spec in d117.PROTECTED_FILE_SPECS),
        *(path.as_posix() for path in d117.D117_IMPLEMENTATION_PATHS),
    }
    assert reads == expected_reads


def test_no_pool_acquisition_reviewer_or_runtime_execution_function_exists(
    built_protocol: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    function_names = {
        name
        for name, value in inspect.getmembers(d117, inspect.isfunction)
        if value.__module__ == d117.__name__
    }
    assert function_names.isdisjoint(
        {
            "discover_pool",
            "acquire_pool",
            "freeze_pool",
            "assemble_pool",
            "create_blind_packet",
            "run_selector",
            "run_adjudicator",
            "classify",
            "execute_matcher",
            "run_calibration",
        }
    )

    original_import = builtins.__import__
    forbidden_imports = (
        "openai",
        "httpx",
        "requests",
        "sentence_transformers",
        "transformers",
        "torch",
        "sklearn",
    )

    def guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.startswith(forbidden_imports):
            raise AssertionError(f"D-117 imported forbidden runtime module: {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    _build_protocol(REPOSITORY)

    boundary = built_protocol["preflight"]["semantic_body"]["evidence_boundary"]
    assert boundary["source_pool_identified_or_read"] is False
    assert boundary["held_out_public_issue_or_result_read_count"] == 0
    assert boundary["pool_manifest_or_member_count"] == 0
    assert boundary["role_or_isolation_session_count"] == 0
    assert boundary["blind_packet_selector_or_adjudication_result_count"] == 0
    assert boundary["matcher_classifier_or_calibration_execution_count"] == 0
    assert boundary["network_capable_call_paths_invoked"] == 0


def test_chronology_rejects_equal_reversed_and_naive_times(
    built_protocol: dict[str, Any],
) -> None:
    receipt = built_protocol["receipt"]
    preflight = copy.deepcopy(built_protocol["preflight"])
    candidate = copy.deepcopy(built_protocol["candidate"])

    preflight["semantic_body"]["recorded_at"] = receipt["semantic_body"]["approval_recorded_at"]
    with pytest.raises(d117.D117BlindProtocolError, match="strictly increasing"):
        d117._validate_chronology(receipt, preflight)

    preflight = copy.deepcopy(built_protocol["preflight"])
    candidate["semantic_body"]["recorded_at"] = "2026-08-07T09:27:15Z"
    with pytest.raises(d117.D117BlindProtocolError, match="strictly increasing"):
        d117._validate_chronology(receipt, preflight, candidate)

    with pytest.raises(d117.D117BlindProtocolError, match="timezone-aware"):
        d117._parse_time("2026-08-07T09:27:15", label="tampered")


def test_partial_artifact_collision_is_never_repaired_or_overwritten(tmp_path: Path) -> None:
    _copy_materialization_repository(tmp_path)
    candidate_path = tmp_path / d117.DEFAULT_CANDIDATE_PATH
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_bytes(b"conflicting-candidate")

    with pytest.raises(d117.D117BlindProtocolError, match="partial artifact set exists"):
        d117.run_d117_protocol_candidate(repository=tmp_path)

    assert candidate_path.read_bytes() == b"conflicting-candidate"
    assert not (tmp_path / d117.DEFAULT_RECEIPT_PATH).exists()
    assert not (tmp_path / d117.DEFAULT_PREFLIGHT_PATH).exists()
    assert not (tmp_path / d117.DEFAULT_SOURCE_GATE_PATH).exists()


def test_temp_materialization_is_exact_idempotent_and_new_only(tmp_path: Path) -> None:
    _copy_materialization_repository(tmp_path)
    before = {
        path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file()
    }

    first = d117.run_d117_protocol_candidate(repository=tmp_path)
    paths = (
        d117.DEFAULT_RECEIPT_PATH,
        d117.DEFAULT_PREFLIGHT_PATH,
        d117.DEFAULT_CANDIDATE_PATH,
        d117.DEFAULT_SOURCE_GATE_PATH,
    )
    first_bytes = {path: (tmp_path / path).read_bytes() for path in paths}
    second = d117.run_d117_protocol_candidate(repository=tmp_path)
    after = {
        path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file()
    }

    assert after - before == {path.as_posix() for path in paths}
    assert first["complete_exact_set_preexisted"] is False
    assert second["complete_exact_set_preexisted"] is True
    first_without_retry = {k: v for k, v in first.items() if k != "complete_exact_set_preexisted"}
    second_without_retry = {k: v for k, v in second.items() if k != "complete_exact_set_preexisted"}
    assert first_without_retry == second_without_retry
    assert first_bytes == {path: (tmp_path / path).read_bytes() for path in paths}
    d117.validate_d117_source_gate(repository=tmp_path)


@pytest.mark.parametrize(
    ("tamper", "message"),
    [
        ("authority-flip", "candidate authority value drifted"),
        ("unknown-field", "key set mismatch"),
        ("full-payload", "full expected payload mismatch"),
        ("noncanonical-bytes", "exact bytes drifted"),
    ],
)
def test_candidate_tamper_fails_after_full_rehash(
    tmp_path: Path,
    tamper: str,
    message: str,
) -> None:
    _copy_materialization_repository(tmp_path)
    d117.run_d117_protocol_candidate(repository=tmp_path)
    path = tmp_path / d117.DEFAULT_CANDIDATE_PATH
    candidate = _json(path)

    if tamper == "noncanonical-bytes":
        path.write_bytes(path.read_bytes() + b" \n")
    else:
        if tamper == "authority-flip":
            candidate["semantic_body"]["authority"]["source_pool_identified"] = True
        elif tamper == "unknown-field":
            candidate["semantic_body"]["authority"]["unknown_authority"] = False
        else:
            candidate["semantic_body"]["candidate_status"] = "pool-acquired"
        _rehash(
            candidate,
            id_field="candidate_id",
            id_prefix="d117blindprotocolcandidate_",
        )
        path.write_bytes(d117._pretty_json(candidate))

    with pytest.raises(d117.D117BlindProtocolError, match=message):
        d117.validate_d117_candidate(repository=tmp_path)


def test_checked_in_d117_artifacts_are_all_or_none_and_exact() -> None:
    paths = (
        d117.DEFAULT_RECEIPT_PATH,
        d117.DEFAULT_PREFLIGHT_PATH,
        d117.DEFAULT_CANDIDATE_PATH,
        d117.DEFAULT_SOURCE_GATE_PATH,
    )
    present = [(REPOSITORY / path).exists() for path in paths]
    assert not any(present) or all(present), "partial checked-in D-117 evidence"
    if all(present):
        d117.validate_d117_receipt(repository=REPOSITORY)
        d117.validate_d117_preflight(repository=REPOSITORY)
        d117.validate_d117_candidate(repository=REPOSITORY)
        d117.validate_d117_source_gate(repository=REPOSITORY)
