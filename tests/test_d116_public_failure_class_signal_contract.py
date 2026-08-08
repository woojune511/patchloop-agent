from __future__ import annotations

import builtins
import copy
import inspect
import json
import shutil
import socket
from pathlib import Path
from typing import Any

import pytest
import yaml

from patchloop.memory import d114_d112_validator_correction as d114
from patchloop.memory import d115_score_policy_decision as d115
from patchloop.memory import d116_public_failure_class_signal_contract as d116
from patchloop.memory import retrieval
from patchloop.util import canonical_json, sha256_text

REPOSITORY = Path(__file__).resolve().parents[1]


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy(relative: str | Path, destination: Path) -> None:
    source = REPOSITORY / relative
    target = destination / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _copy_materialization_repository(destination: Path) -> None:
    paths = {
        d115.DEFAULT_D114_RECEIPT_PATH,
        d115.DEFAULT_D114_GATE_PATH,
        d115.DEFAULT_D112_GATE_PATH,
        d114.DEFAULT_D113_PREFLIGHT_PATH,
        d114.DEFAULT_D113_CANDIDATE_PATH,
        d114.DEFAULT_D113_SOURCE_GATE_PATH,
        *(Path(spec["path"]) for spec in d114.PROTECTED_FILE_SPECS),
        *(Path(spec["path"]) for spec in d114.PUBLIC_TASK_SPECS.values()),
        *d114.D114_IMPLEMENTATION_PATHS,
        *d115.D115_IMPLEMENTATION_PATHS,
        *(Path(spec["path"]) for spec in d116.PROTECTED_FILE_SPECS),
        *d116.D116_IMPLEMENTATION_PATHS,
    }
    for relative in sorted(paths, key=lambda value: value.as_posix()):
        _copy(relative, destination)


def _rehash(payload: dict[str, Any], *, id_field: str, id_prefix: str) -> None:
    body_hash = sha256_text(canonical_json(payload["semantic_body"]))
    payload["semantic_body_hash"] = body_hash
    payload[id_field] = id_prefix + body_hash.removeprefix("sha256:")


@pytest.fixture(scope="module")
def built_contract() -> dict[str, Any]:
    context = d116._load_exact_context(REPOSITORY)
    protected = d116._protected_input_state(REPOSITORY)
    implementation = d116._implementation_state(REPOSITORY)
    receipt = d116.build_d116_approval_receipt(
        repository=REPOSITORY,
        context=context,
        protected_pre=protected,
        implementation_pre=implementation,
    )
    preflight = d116.build_d116_preflight(
        receipt,
        repository=REPOSITORY,
        context=context,
    )
    candidate = d116.build_d116_candidate(receipt, preflight, repository=REPOSITORY)
    gate = d116.build_d116_source_gate(
        receipt,
        preflight,
        candidate,
        repository=REPOSITORY,
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


def test_exact_d115_approval_triple_and_action_are_bound(
    built_contract: dict[str, Any],
) -> None:
    context = built_contract["context"]
    receipt_body = built_contract["receipt"]["semantic_body"]

    assert d116.EXPECTED_D115_CANDIDATE_ID == (
        "d115scoredecisioncandidate_"
        "91e3ef5af000fe830483012b5deee4eeb47f5a117fa5904d93d713b03f2308ec"
    )
    assert d116.EXPECTED_D115_CANDIDATE_BODY_SHA == (
        "sha256:91e3ef5af000fe830483012b5deee4eeb47f5a117fa5904d93d713b03f2308ec"
    )
    assert d116.EXPECTED_D115_CANDIDATE_FILE_SHA == (
        "sha256:1fd424eab88c60a9d8480e756642b2c70b03afd03dd777e27bf36a3ea428df7a"
    )
    assert d116.EXPECTED_D115_ACTION_HASH == (
        "sha256:180c9456da225b95f8ddcf8ab4d05df1732d670b43f901e2220d841bfa5cb466"
    )
    assert receipt_body["approval_reference"] == {
        "candidate_id": d116.EXPECTED_D115_CANDIDATE_ID,
        "semantic_body_hash": d116.EXPECTED_D115_CANDIDATE_BODY_SHA,
        "file_sha256": d116.EXPECTED_D115_CANDIDATE_FILE_SHA,
    }
    assert receipt_body["authorized_action_hash"] == d116.EXPECTED_D115_ACTION_HASH
    assert (
        receipt_body["authorized_scope"]
        == context["candidate"]["semantic_body"]["proposed_next_action"]
    )
    assert receipt_body["d115_source_gate"]["gate_id"] == d116.EXPECTED_D115_GATE_ID
    assert receipt_body["execution_result_present"] is False
    assert receipt_body["claim_semantics"]["one_use_classifier_execution_claim"] is False


def test_wrong_expected_d115_action_hash_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(d116, "EXPECTED_D115_ACTION_HASH", "sha256:" + "0" * 64)
    with pytest.raises(d116.D116SignalContractError, match="authorized action hash mismatch"):
        d116._load_exact_context(REPOSITORY)


def test_exact_d105_model_facing_taxonomy_is_bound_in_order(
    built_contract: dict[str, Any],
) -> None:
    preflight_body = built_contract["preflight"]["semantic_body"]
    taxonomy = preflight_body["taxonomy_contract"]

    assert taxonomy["taxonomy_source"] == "exact-leak-scanned-d105-model-facing-render"
    assert taxonomy["d105_gate"]["gate_id"] == d116.EXPECTED_D105_GATE_ID
    assert taxonomy["entry_count"] == 3
    assert taxonomy["taxonomy_is_fallible_process_guidance"] is True
    assert taxonomy["taxonomy_is_failure_cause_ground_truth"] is False
    assert [
        (row["order"], row["memory_id"], row["semantic_group_id"], row["failure_class"])
        for row in taxonomy["entries"]
    ] == [
        (
            spec["order"],
            spec["memory_id"],
            spec["semantic_group_id"],
            spec["failure_class"],
        )
        for spec in d116.TAXONOMY_RENDER_SPECS
    ]
    for row, spec in zip(taxonomy["entries"], d116.TAXONOMY_RENDER_SPECS, strict=True):
        content = (REPOSITORY / spec["path"]).read_bytes()
        assert row["model_facing_text"] == content.decode("ascii")
        assert row["render"] == {
            "path": spec["path"],
            "file_bytes": spec["file_bytes"],
            "file_sha256": spec["file_sha256"],
        }


def test_exact_ten_public_files_have_eight_eligible_and_two_bootstrap_exclusions(
    built_contract: dict[str, Any],
) -> None:
    body = built_contract["preflight"]["semantic_body"]
    inventory = body["public_development_inventory"]
    plan = body["prospective_calibration_plan"]

    assert len(d116.PUBLIC_FILE_SPECS) == 10
    assert len(inventory) == 10
    assert [row["path"] for row in inventory] == [spec["path"] for spec in d116.PUBLIC_FILE_SPECS]
    assert plan["public_inventory_count"] == 10
    assert plan["eligible_case_count"] == 8
    assert plan["bootstrap_excluded_count"] == 2
    assert {row["path"] for row in plan["bootstrap_exclusions"]} == {
        "tasks/dev-train/csv-final-record-flush/public.yaml",
        "tasks/dev-train/duration-minute-boundary/public.yaml",
    }
    assert all(row["eligibility"] == "bootstrap-excluded" for row in plan["bootstrap_exclusions"])
    assert body["input_scope"]["classifier_projection_fields"] == [
        "issue.title",
        "issue.description",
        "repository.language",
    ]


def test_projection_uses_only_title_description_and_language() -> None:
    path = REPOSITORY / "tasks/dev-train/hf-hub-xet-endpoint-propagation/public.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    baseline = d116._public_projection(payload)
    forbidden_mutation = copy.deepcopy(payload)
    forbidden_mutation["task_id"] = "answer-lookup-key"
    forbidden_mutation["split"] = "held-out"
    forbidden_mutation["repository"]["url"] = "https://example.invalid/answer.git"
    forbidden_mutation["repository"]["base_commit"] = "0" * 40
    forbidden_mutation["tags"] = ["platform-emulation-matrix-gap"]
    forbidden_mutation["visible_checks"] = [{"id": "answer", "command": ["answer"]}]
    forbidden_mutation["constraints"] = {"allowed_paths": ["answer.py"]}
    forbidden_mutation["phase"] = "IMPLEMENT"
    forbidden_mutation["source_memory_or_group_association"] = "request-context-propagation-gap"

    assert d116._public_projection(forbidden_mutation) == baseline
    assert list(baseline["projection"]) == [
        "schema_version",
        "issue_title",
        "issue_description",
        "language",
    ]
    for key_path in ("title", "description", "language"):
        changed = copy.deepcopy(payload)
        if key_path == "language":
            changed["repository"]["language"] = "ruby"
        else:
            changed["issue"][key_path] += " changed"
        assert d116._public_projection(changed) != baseline


def test_predicate_result_and_abstention_contracts_are_deterministic(
    built_contract: dict[str, Any],
) -> None:
    body = built_contract["preflight"]["semantic_body"]
    input_contract = body["signal_input_contract"]
    result_contract = body["signal_result_contract"]
    predicates = body["prospective_predicate_contract"]
    abstention = body["deterministic_abstention_contract"]

    assert input_contract["allowed_fields_in_order"] == [
        "issue_title",
        "issue_description",
        "language",
    ]
    assert input_contract["exact_key_set_required"] is True
    assert input_contract["supported_languages"] == ["python"]
    assert input_contract["phase_independent_signal_required"] is True
    assert "task-id" in input_contract["forbidden_classifier_inputs"]
    assert "d112-hypothesized-group" in input_contract["forbidden_classifier_inputs"]
    assert "phase" in input_contract["forbidden_classifier_inputs"]
    assert input_contract["boundary_behavior"] == {
        "raw_manifest_valid_string_values_are_canonicalized": True,
        "classifier_accepts_only_exact_canonical_projection": True,
        "wrong-type-empty-extra-missing-or-noncanonical-projection": "CONTRACT_ERROR",
        "valid-canonical-unsupported-language": "ABSTAIN",
    }
    assert predicates["formal_matcher_grammar_complete"] is True
    assert predicates["matcher_evaluator_implementation_present"] is False
    assert predicates["matcher_evaluator_execution_count"] == 0
    assert predicates["task_specific_branch_allowed"] is False
    assert predicates["embedding_or_llm_judgment_allowed"] is False
    algorithm = predicates["matcher_algorithm"]
    assert algorithm["regex_engine"] == "python-stdlib-re"
    assert algorithm["regex_runtime_contract"] == "CPython-3.12"
    assert algorithm["regex_flags"] == ["ASCII"]
    assert algorithm["classifier_text_fields_in_order"] == [
        "issue_title",
        "issue_description",
    ]
    assert algorithm["pattern_or_match_score_allowed"] is False
    assert algorithm["semantic_fallback_allowed"] is False
    assert algorithm["token_pattern"] == (r"[a-z0-9]+(?:-[a-z0-9]+)*")
    assert algorithm["sentence_boundary_pattern"] == (r"[.!?]+(?:\s+|$)")
    assert algorithm["clause_boundary_patterns"] == [
        r"[,;:]",
        r"\b(?:but|while|whereas|rather than|instead of)\b",
    ]
    assert algorithm["sentence_and_clause_indices"].endswith(
        "clause_index does not reset at sentence boundaries"
    )
    assert (
        "punctuation and following whitespace belong to the preceding sentence"
        in algorithm["sentence_segmentation_contract"]
    )
    assert "half-open adjacency alone is not overlap" in algorithm["clause_segmentation_contract"]
    assert (
        "otherwise assign clause indices globally across the field"
        in algorithm["clause_segmentation_contract"]
    )
    assert (
        "first token index whose end is greater than the match start"
        in algorithm["token_offset_contract"]
    )
    assert "Never choose an invalid tuple and stop" in algorithm["all_atoms_relation"]
    assert (
        "Report only that selected minimum subset" in algorithm["minimum_distinct_atoms_same_field"]
    )
    assert (
        "No global cross-predicate backtracking is performed"
        in algorithm["cross_predicate_span_reuse"]
    )
    assert algorithm["negation_tokens"] == [
        "not",
        "never",
        "without",
        "neither",
    ]
    assert "preceding three tokens" in algorithm["negation_scope"]
    assert algorithm["contradiction_scope"] == ("global-all-groups-before-group-selection")
    assert algorithm["decision_precedence"] == [
        "contract-error-on-invalid-or-noncanonical-projection",
        "abstain-on-unsupported-language",
        "abstain-on-any-matched-group-contradiction",
        "abstain-on-more-than-one-fully-supported-group",
        "select-the-only-fully-supported-group",
        "abstain-on-partial-predicate-evidence",
        "abstain-on-no-match",
    ]
    unsupported = algorithm["unsupported_language_short_circuit"]
    assert "without tokenizing or matching text" in unsupported
    assert "evidence_spans are all empty arrays" in unsupported
    assert sha256_text(canonical_json(predicates)) == (
        "sha256:c9e88df2d48ea1d089da11ec394fd41daa2d3e377b3058899e9f530b51548bf1"
    )
    span_contract = predicates["evidence_span_contract"]
    assert span_contract["field_enum"] == ["issue_title", "issue_description"]
    assert "zero-based Unicode-code-point half-open offsets" in span_contract["coordinate_system"]
    assert span_contract["matched_text_must_equal_canonical_field_slice"] is True
    assert (
        span_contract["duplicate_or_overlapping_selected_spans_within_one_predicate_allowed"]
        is False
    )
    assert span_contract["same_span_reuse_across_different_predicate_ids_allowed"] is True
    assert span_contract["ordering"] == (
        "field-order,start,end,group-order,predicate-order,atom-order,pattern-index ascending"
    )
    assert span_contract["composite_role_exceptions"] == []
    assert [group["semantic_group_id"] for group in predicates["groups"]] == [
        "platform-emulation-matrix-gap",
        "request-context-propagation-gap",
        "exception-origin-state-conflation",
    ]
    assert all(len(group["required_predicates"]) == 3 for group in predicates["groups"])
    d116._validate_matcher_grammar(predicates)
    assert result_contract["decision_enum"] == ["SELECT", "ABSTAIN"]
    assert result_contract["signal_semantics"] == (
        "public-applicability-not-failure-cause-ground-truth"
    )
    assert result_contract["contract_error_is_not_a_signal_result"] is True
    assert result_contract["select_reason_code"] == "SELECT_UNIQUE_FULL_GROUP"
    assert result_contract["abstain_reason_codes_in_precedence_order"] == [
        "UNSUPPORTED_LANGUAGE",
        "CONTRADICTION_PRESENT",
        "MULTIPLE_FULL_GROUPS",
        "PARTIAL_PREDICATE_EVIDENCE",
        "NO_FULL_GROUP",
    ]
    assert result_contract["contract_error_reason_codes"] == [
        "INVALID_PROJECTION_KEY_SET",
        "INVALID_PROJECTION_VALUE_TYPE",
        "EMPTY_PROJECTION_VALUE",
        "NONCANONICAL_PROJECTION_VALUE",
        "PROJECTION_HASH_MISMATCH",
        "INVALID_RESULT_SPAN",
    ]
    collections = result_contract["result_collection_contract"]
    assert "group order then required-predicate order" in collections["matched_required_predicates"]
    assert "group and declaration order" in collections["contradiction_predicates"]
    assert "taxonomy group order" in collections["competing_group_ids"]
    assert "evidence-span ordering contract" in collections["evidence_spans"]
    assert collections["all_collections_are_json_arrays"] is True
    assert collections["duplicate_identifiers_allowed"] is False
    assert collections["null_elements_allowed"] is False
    assert result_contract["select_requires_exactly_one_fully_supported_group"] is True
    assert result_contract["select_establishes_true_relevance"] is False
    assert result_contract["abstain_selected_group_must_be_null"] is True
    assert result_contract["confidence_probability_allowed_before_calibration"] is False
    assert result_contract["numeric_failure_class_component_mapping_authorized"] is False
    assert abstention["abstain_means_unknown_not_negative_ground_truth"] is True
    assert abstention["abstain_to_numeric_zero_mapping_authorized"] is False
    assert abstention["ties_must_abstain"] is True
    assert abstention["fallback_to-semantic-top_allowed"] is False
    assert abstention["invalid_or_noncanonical_input_behavior"] == (
        "CONTRACT_ERROR-before-matching"
    )
    assert "input-is-invalid-or-noncanonical" not in abstention["abstain_when"]
    assert {
        "no-group-satisfies-every-required-predicate",
        "more-than-one-group-satisfies-every-required-predicate",
        "any-required-predicate-has-only-partial-evidence",
        "a-contradiction-predicate-is-present",
    }.issubset(abstention["abstain_when"])
    contract_binding = built_contract["candidate"]["semantic_body"]["contract_binding"]
    assert contract_binding["predicate_contract_hash"] == (
        "sha256:c9e88df2d48ea1d089da11ec394fd41daa2d3e377b3058899e9f530b51548bf1"
    )
    assert contract_binding["signal_input_contract_hash"] == (
        "sha256:24a0d5102b5066dd19b8cc9b68cf8d84bbb70b4f364e604ea804fab120a260b2"
    )
    assert contract_binding["signal_result_contract_hash"] == (
        "sha256:ae1536068aa28142e289feb97045bd289ca1dbf0df70a8d25777a9885df220d9"
    )
    assert contract_binding["abstention_contract_hash"] == (
        "sha256:1ad0614589c555c285befb51f7e28e80f7b3e5c0f155116e05e08295bc09063c"
    )


@pytest.mark.parametrize("tamper", ["invalid-regex", "incomplete-grammar"])
def test_matcher_grammar_tamper_fails_closed(built_contract: dict[str, Any], tamper: str) -> None:
    grammar = copy.deepcopy(
        built_contract["preflight"]["semantic_body"]["prospective_predicate_contract"]
    )
    if tamper == "invalid-regex":
        grammar["groups"][0]["required_predicates"][0]["atoms"][0]["alternatives"] = ["["]
        message = "matcher regex is invalid"
    else:
        grammar["formal_matcher_grammar_complete"] = False
        message = "formal matcher grammar boundary is invalid"

    with pytest.raises(d116.D116SignalContractError, match=message):
        d116._validate_matcher_grammar(grammar)


def test_tox_and_moto_are_explicitly_non_authoritative_non_labels(
    built_contract: dict[str, Any],
) -> None:
    preflight_body = built_contract["preflight"]["semantic_body"]
    inventory = preflight_body["public_development_inventory"]
    plan = preflight_body["prospective_calibration_plan"]
    next_action = built_contract["candidate"]["semantic_body"]["proposed_next_action"]
    tox_input = next(row for row in inventory if "tox-cross-section" in row["path"])
    moto_input = next(row for row in inventory if "moto-query" in row["path"])
    expectation_by_ref = {row["input_ref"]: row for row in plan["review_expectations"]}
    tox = expectation_by_ref[tox_input["classifier_projection"]["projection_sha256"]]
    moto = expectation_by_ref[moto_input["classifier_projection"]["projection_sha256"]]

    assert tox_input["classifier_execution_result_present"] is False
    assert tox["case_role"] == "abstention-control-incomplete-source-overlap"
    assert tox["candidate_expectation"] == "ABSTAIN"
    assert tox["candidate_group_id"] is None
    assert tox["expectation_is_ground_truth"] is False
    assert moto_input["classifier_execution_result_present"] is False
    assert moto["case_role"] == "hypothesis-only-boundary-diagnostic"
    assert moto["candidate_expectation"] == "ABSTAIN"
    assert moto["candidate_group_id"] is None
    assert moto["acceptance_included"] is False
    assert moto["expectation_is_ground_truth"] is False
    assert plan["moto_d112_hypothesis_counts_as_label"] is False
    assert plan["moto_case_included_in_mechanical_acceptance"] is False
    assert next_action["moto_d112_hypothesis_as_label_allowed"] is False
    assert next_action["tox_source_association_as_public_label_allowed"] is False


def test_source_overlap_is_not_independent_and_blocks_three_class_calibration(
    built_contract: dict[str, Any],
) -> None:
    plan = built_contract["preflight"]["semantic_body"]["prospective_calibration_plan"]
    candidate_body = built_contract["candidate"]["semantic_body"]

    assert plan["source_anchor_conformance_count"] == 2
    assert plan["source_anchor_overlap_counts_as_independent_evidence"] is False
    assert plan["independent_positive_count"] == 0
    assert plan["independent_positive_groups_available"] == []
    assert plan["groups_missing_independent_positive"] == [
        "platform-emulation-matrix-gap",
        "request-context-propagation-gap",
        "exception-origin-state-conflation",
    ]
    assert plan["three_class_calibration_ready"] is False
    assert plan["calibration_execution_ready"] is False
    assert candidate_body["calibration_plan_binding"]["independent_positive_count"] == 0
    assert plan["current_panel_used_during_contract_authoring"] is True
    assert plan["current_panel_blind_validation"] is False
    assert plan["future_controls_acquired_after_matcher_contract_hash_is_sealed"] is True
    assert plan["future_control_selection_may_use_matcher_output"] is False
    assert plan["future_control_label_adjudication_may_use_matcher_output"] is False
    assert plan["future_control_acquisition_blinded_to_matcher_output"] is True
    assert plan["future_control_source_pool_must_preexist_d116"] is True
    assert plan["future_control_issue_prose_authoring_or_rewriting_after_d116_allowed"] is False
    assert plan["future_control_pool_cutoff_must_precede"] == d116.APPROVAL_RECORDED_AT
    assert plan["future_control_pool_bytes_cutoff_and_provenance_must_be_hashed"] is True
    assert (
        plan["future_exact_pool_membership_manifest_or_exhaustive_inclusion_rule_must_predate_d116"]
        is True
    )
    assert plan["future_exact_pool_membership_manifest_bytes_and_hash_required"] is True
    assert plan["future_pool_assembler_may_view_matcher_grammar_hash_or_output"] is False
    assert plan["future_pool_assembler_must_be_isolated_from_grammar_observers"] is True
    assert plan["future_selector_and_adjudicator_may_view_matcher_grammar_or_hash"] is False
    assert plan["future_selector_and_adjudicator_receive_only_d105_applicability_rubric"] is True
    assert plan["future_selector_and_adjudicator_must_be_isolated_from_grammar_observers"] is True
    assert plan["current_process_or_agent_is_eligible_as_blind_selector"] is False
    assert (
        plan["if_blinding_cannot_be_enforced_mark_controls_post_hoc_and_independent_false"] is True
    )
    assert plan["pool_assembler_selector_or_adjudicator_blinding_failure_triggers_fallback"] is True
    assert plan["matcher_grammar_change_after_control_acquisition_allowed"] is False
    assert plan["grammar_change_requires_new_contract_version_and_invalidates_blind_status"] is True
    assert candidate_body["candidate_status"] == (
        "formal-matcher-contract-sealed-calibration-blocked-on-grammar-blind-"
        "preexisting-control-protocol-and-public-applicability-positives"
    )
    assert candidate_body["unresolved_prerequisites"][0] == (
        "grammar-blind-preexisting-control-acquisition-protocol-not-yet-materialized"
    )
    action = candidate_body["proposed_next_action"]
    assert action["source_pool_must_preexist_d116"] is True
    assert action["exact_pool_membership_manifest_bytes_and_hash_required"] is True
    assert action["pool_assembler_may_view_matcher_grammar_hash_or_output"] is False
    assert action["pool_assembler_isolation_from_grammar_observers_required"] is True
    assert action["selector_or_adjudicator_may_view_matcher_grammar_or_hash"] is False
    assert action["selector_and_adjudicator_receive_only_d105_applicability_rubric"] is True
    assert action["selector_and_adjudicator_isolation_from_grammar_observers_required"] is True
    assert action["current_process_or_agent_eligible_as_blind_selector"] is False
    assert candidate_body["proposed_next_action_hash"] == (
        "sha256:e368dcb794875064f605a341902b4c27be20fcb3ff9b86d65ca5fb66dbf35e55"
    )
    assert built_contract["gate"]["semantic_body"]["next_gate"] == (
        "exact-d116-candidate-triple-grammar-blind-preexisting-public-control-"
        "acquisition-protocol-candidate-approval"
    )


def test_classifier_inputs_review_expectations_and_synthetic_plan_are_separate(
    built_contract: dict[str, Any],
) -> None:
    plan = built_contract["preflight"]["semantic_body"]["prospective_calibration_plan"]

    assert len(plan["classifier_inputs"]) == 8
    assert len(plan["review_expectations"]) == 8
    assert plan["classifier_executor_receives_review_expectations"] is False
    assert plan["classifier_executor_argument"] == ("classifier_inputs[].classifier_payload-only")
    assert all(
        set(row) == {"input_ref", "classifier_payload", "classifier_payload_sha256"}
        for row in plan["classifier_inputs"]
    )
    assert all(
        set(row["classifier_payload"])
        == {"schema_version", "issue_title", "issue_description", "language"}
        for row in plan["classifier_inputs"]
    )
    assert all("candidate_expectation" not in row for row in plan["classifier_inputs"])
    assert all("classifier_payload" not in row for row in plan["review_expectations"])
    assert all(row["expectation_is_ground_truth"] is False for row in plan["review_expectations"])
    synthetic = plan["synthetic_conformance_plan"]
    assert synthetic["plan_only_no_execution"] is True
    assert synthetic["required_before_any_independent_control_is_scored"] is True
    assert [row["case_id"] for row in synthetic["cases"]] == [
        "platform-conformance-positive",
        "context-conformance-positive",
        "semantic-conformance-positive",
        "tox-like-missing-S3",
        "keyword-salad",
        "negated-emulation-with-contradiction",
        "context-partial",
        "two-full-group-matches",
        "unsupported-language",
        "malformed-or-extra-projection-field",
        "forbidden-field-and-phase-invariance",
        "span-integrity-negative",
    ]
    assert synthetic["cases"][8]["expected_outcome"] == "ABSTAIN-unsupported-language"
    assert synthetic["cases"][9]["expected_outcome"] == "CONTRACT_ERROR"


def test_no_classifier_or_calibration_implementation_or_execution_exists(
    built_contract: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    function_names = {
        name
        for name, value in inspect.getmembers(d116, inspect.isfunction)
        if value.__module__ == d116.__name__
    }
    assert function_names.isdisjoint(
        {
            "classify",
            "classify_public_input",
            "run_classifier",
            "execute_classifier",
            "fit_classifier",
            "calibrate",
            "run_calibration",
            "execute_calibration",
        }
    )

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("D-116 crossed a contract-only boundary")

    monkeypatch.setattr(retrieval, "retrieve_memory", forbidden)
    monkeypatch.setattr(retrieval, "_query_embedding", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    original_import = builtins.__import__
    forbidden_imports = (
        "sentence_transformers",
        "transformers",
        "torch",
        "openai",
        "sklearn",
    )

    def guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.startswith(forbidden_imports):
            raise AssertionError(f"D-116 imported forbidden runtime module: {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    context = d116._load_exact_context(REPOSITORY)
    protected = d116._protected_input_state(REPOSITORY)
    implementation = d116._implementation_state(REPOSITORY)
    receipt = d116.build_d116_approval_receipt(
        repository=REPOSITORY,
        context=context,
        protected_pre=protected,
        implementation_pre=implementation,
    )
    preflight = d116.build_d116_preflight(receipt, repository=REPOSITORY, context=context)
    candidate = d116.build_d116_candidate(receipt, preflight, repository=REPOSITORY)

    boundary = preflight["semantic_body"]["evidence_boundary"]
    assert boundary["classifier_source_code_created"] is False
    assert boundary["classifier_execution_count"] == 0
    assert boundary["task_level_signal_result_count"] == 0
    assert boundary["calibration_result_count"] == 0
    assert boundary["model_or_embedding_load_count"] == 0
    assert boundary["retrieval_calls"] == 0
    assert boundary["runtime_memory_injection_count"] == 0
    assert boundary["agent_runs"] == 0
    assert boundary["provider_calls_made"] == 0
    assert boundary["evaluator_calls_made"] == 0
    assert boundary["network_capable_call_paths_invoked"] == 0
    assert (
        candidate["semantic_body"]["approval_contract"][
            "approval_would_authorize_classifier_or_calibration_execution"
        ]
        is False
    )
    next_action = candidate["semantic_body"]["proposed_next_action"]
    assert next_action["action_kind"] == (
        "prepare-grammar-blind-preexisting-public-applicability-control-acquisition-"
        "protocol-candidate"
    )
    assert next_action["matcher_grammar_mutation_allowed"] is False
    assert next_action["classifier_implementation_allowed"] is False
    assert next_action["classifier_execution_allowed"] is False
    assert next_action["calibration_execution_allowed"] is False


def test_all_runtime_and_policy_authority_remains_closed(
    built_contract: dict[str, Any],
) -> None:
    candidate = built_contract["candidate"]
    gate = built_contract["gate"]
    authority = candidate["semantic_body"]["authority"]

    assert authority["exact_d115_candidate_user_approval_received"] is True
    assert authority["public_failure_class_signal_contract_authorized"] is True
    assert authority["public_applicability_signal_contract_prepared"] is True
    assert authority["formal_matcher_grammar_complete"] is True
    assert authority["prospective_calibration_candidate_ready"] is True
    false_keys = {
        "matcher_evaluator_implementation_authorized",
        "matcher_evaluator_implemented",
        "calibration_execution_candidate_ready",
        "actual_classifier_implementation_authorized",
        "actual_classifier_implemented",
        "classifier_execution_authorized",
        "calibration_execution_authorized",
        "calibration_results_present",
        "three_class_calibrated",
        "independent_generalization_validated",
        "runtime_classifier_observed",
        "true_relevance_established",
        "corrected_policy_selected",
        "score_policy_correction_authorized",
        "score_policy_correction_implemented",
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
        "matcher_evaluator_execution_count",
        "classifier_execution_count",
        "calibration_execution_count",
        "runtime_memory_injection_count",
        "agent_runs",
        "provider_calls_made",
        "evaluator_calls_made",
    }
    assert all(authority[key] is False for key in false_keys)
    assert all(authority[key] == 0 for key in zero_keys)
    assert gate["semantic_body"]["authority"] == authority
    assert (
        gate["semantic_body"]["qualification"]["actual_classifier_or_calibration_executed"] is False
    )


def test_deterministic_build_objects_and_protected_bytes_are_unchanged(
    built_contract: dict[str, Any],
) -> None:
    before = d116._protected_input_state(REPOSITORY)
    context = built_contract["context"]
    implementation = d116._implementation_state(REPOSITORY)

    def rebuild() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        receipt = d116.build_d116_approval_receipt(
            repository=REPOSITORY,
            context=context,
            protected_pre=before,
            implementation_pre=implementation,
        )
        preflight = d116.build_d116_preflight(
            receipt,
            repository=REPOSITORY,
            context=context,
        )
        candidate = d116.build_d116_candidate(receipt, preflight, repository=REPOSITORY)
        return receipt, preflight, candidate

    assert rebuild() == rebuild()
    assert d116._protected_input_state(REPOSITORY) == before


@pytest.mark.parametrize("state_kind", ["protected", "implementation"])
def test_source_gate_rejects_pre_post_state_drift(
    built_contract: dict[str, Any], state_kind: str
) -> None:
    protected_pre = built_contract["protected"]
    protected_post = copy.deepcopy(protected_pre)
    implementation_pre = built_contract["implementation"]
    implementation_post = copy.deepcopy(implementation_pre)
    if state_kind == "protected":
        protected_post["fingerprint"] = "sha256:" + "0" * 64
        message = "protected inputs changed"
    else:
        implementation_post["fingerprint"] = "sha256:" + "0" * 64
        message = "implementation changed"

    with pytest.raises(d116.D116SignalContractError, match=message):
        d116.build_d116_source_gate(
            built_contract["receipt"],
            built_contract["preflight"],
            built_contract["candidate"],
            repository=REPOSITORY,
            context=built_contract["context"],
            protected_pre=protected_pre,
            protected_post=protected_post,
            implementation_pre=implementation_pre,
            implementation_post=implementation_post,
        )


def test_partial_artifact_collision_is_not_overwritten_or_completed(tmp_path: Path) -> None:
    _copy_materialization_repository(tmp_path)
    candidate_path = tmp_path / d116.DEFAULT_CANDIDATE_PATH
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_bytes(b"conflicting-candidate")
    protected_before = d116._protected_input_state(tmp_path)

    with pytest.raises(d116.D116SignalContractError, match="existing output differs"):
        d116.run_d116_contract_candidate(repository=tmp_path)

    assert (tmp_path / d116.DEFAULT_RECEIPT_PATH).exists()
    assert (tmp_path / d116.DEFAULT_PREFLIGHT_PATH).exists()
    assert candidate_path.read_bytes() == b"conflicting-candidate"
    assert not (tmp_path / d116.DEFAULT_SOURCE_GATE_PATH).exists()
    assert d116._protected_input_state(tmp_path) == protected_before
    with pytest.raises(d116.D116SignalContractError, match="existing output differs"):
        d116.run_d116_contract_candidate(repository=tmp_path)


@pytest.mark.parametrize("tamper", ["authority-flip", "unknown-field", "noncanonical-bytes"])
def test_materialization_is_idempotent_and_full_payload_tamper_fails(
    tmp_path: Path, tamper: str
) -> None:
    _copy_materialization_repository(tmp_path)
    first = d116.run_d116_contract_candidate(repository=tmp_path)
    paths = (
        d116.DEFAULT_RECEIPT_PATH,
        d116.DEFAULT_PREFLIGHT_PATH,
        d116.DEFAULT_CANDIDATE_PATH,
        d116.DEFAULT_SOURCE_GATE_PATH,
    )
    first_bytes = {path: (tmp_path / path).read_bytes() for path in paths}
    second = d116.run_d116_contract_candidate(repository=tmp_path)

    assert first == second
    assert first_bytes == {path: (tmp_path / path).read_bytes() for path in paths}
    d116.validate_d116_source_gate(repository=tmp_path)

    candidate_path = tmp_path / d116.DEFAULT_CANDIDATE_PATH
    if tamper == "noncanonical-bytes":
        candidate_path.write_bytes(candidate_path.read_bytes() + b" \n")
        expected = "exact bytes drifted"
    else:
        candidate = _json(candidate_path)
        if tamper == "authority-flip":
            candidate["semantic_body"]["authority"]["retrieval_ready"] = True
            expected = "full expected payload mismatch"
        else:
            candidate["semantic_body"]["authority"]["unknown_authority"] = True
            expected = "key set mismatch"
        _rehash(candidate, id_field="candidate_id", id_prefix="d116classsignalcandidate_")
        candidate_path.write_bytes(d116._pretty_json(candidate))

    with pytest.raises(d116.D116SignalContractError, match=expected):
        d116.validate_d116_candidate(repository=tmp_path)


def test_checked_in_d116_artifacts_are_all_or_none_and_exact() -> None:
    paths = (
        d116.DEFAULT_RECEIPT_PATH,
        d116.DEFAULT_PREFLIGHT_PATH,
        d116.DEFAULT_CANDIDATE_PATH,
        d116.DEFAULT_SOURCE_GATE_PATH,
    )
    present = [(REPOSITORY / path).exists() for path in paths]
    if not any(present):
        pytest.skip("D-116 artifacts have not been materialized yet")
    assert all(present), "partial checked-in D-116 evidence"

    d116.validate_d116_receipt(repository=REPOSITORY)
    d116.validate_d116_preflight(repository=REPOSITORY)
    d116.validate_d116_candidate(repository=REPOSITORY)
    d116.validate_d116_source_gate(repository=REPOSITORY)
