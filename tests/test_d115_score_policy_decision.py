from __future__ import annotations

import builtins
import copy
import json
import shutil
import socket
from pathlib import Path
from typing import Any

import pytest

from patchloop.memory import d114_d112_validator_correction as d114
from patchloop.memory import d115_score_policy_decision as d115
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
    }
    for relative in sorted(paths, key=lambda value: value.as_posix()):
        _copy(relative, destination)


def _policy(preflight: dict[str, Any], policy_id: str) -> dict[str, Any]:
    return next(
        row
        for row in preflight["semantic_body"]["policy_diagnostics"]
        if row["policy_id"] == policy_id
    )


def _candidate_for_repository(repository: Path = REPOSITORY) -> dict[str, Any]:
    preflight = d115.build_d115_preflight(repository=repository)
    return d115.build_d115_candidate(preflight, repository=repository)


def _rehash_candidate(candidate: dict[str, Any]) -> None:
    body_hash = sha256_text(canonical_json(candidate["semantic_body"]))
    candidate["semantic_body_hash"] = body_hash
    candidate["candidate_id"] = "d115scoredecisioncandidate_" + body_hash.removeprefix("sha256:")


def test_exact_d112_public_matrix_and_current_scores_are_preserved() -> None:
    preflight = d115.build_d115_preflight(repository=REPOSITORY)
    body = preflight["semantic_body"]
    rows = body["public_score_matrix"]

    assert body["input_scope"]["public_probe_ids_in_order"] == list(d115.PROBE_IDS)
    assert body["input_scope"]["observed_matrix_uses_stored_d112_components_only"] is True
    assert body["input_scope"]["public_non_acceptance_hypothesis_used_for_counterfactual"] is True
    assert body["input_scope"]["counterfactual_is_runtime_observable"] is False
    assert body["input_scope"]["counterfactual_is_acceptance_evidence"] is False
    assert len(rows) == 9
    assert [
        (
            row["probe_id"],
            row["semantic_group_id"],
            row["recorded_rank"],
            row["recorded_final_score"],
        )
        for row in rows
    ] == [
        (
            "moto-implement-positive-hypothesis",
            "exception-origin-state-conflation",
            1,
            0.3541890713468577,
        ),
        (
            "moto-implement-positive-hypothesis",
            "request-context-propagation-gap",
            2,
            0.33426762171426366,
        ),
        (
            "moto-implement-positive-hypothesis",
            "platform-emulation-matrix-gap",
            3,
            0.30430094253875567,
        ),
        (
            "babel-implement-no-match-control",
            "exception-origin-state-conflation",
            1,
            0.39188659397843584,
        ),
        (
            "babel-implement-no-match-control",
            "request-context-propagation-gap",
            2,
            0.3567936878014567,
        ),
        (
            "babel-implement-no-match-control",
            "platform-emulation-matrix-gap",
            3,
            0.3514907443341587,
        ),
        (
            "moto-reproduce-phase-control",
            "exception-origin-state-conflation",
            1,
            0.20418907134685768,
        ),
        (
            "moto-reproduce-phase-control",
            "request-context-propagation-gap",
            2,
            0.18426762171426364,
        ),
        (
            "moto-reproduce-phase-control",
            "platform-emulation-matrix-gap",
            3,
            0.1543009425387557,
        ),
    ]
    assert all(row["hypothesis_is_acceptance_criterion"] is False for row in rows)
    assert body["current_policy"]["weights"] == d115.CURRENT_WEIGHTS
    assert body["current_policy"]["threshold"] == 0.72


def test_current_and_threshold_only_diagnostics_show_the_expected_failure() -> None:
    preflight = d115.build_d115_preflight(repository=REPOSITORY)
    current = _policy(preflight, "current-policy-v1")
    threshold_only = _policy(preflight, "threshold-only-at-moto-hypothesized-score")

    assert [row["no_match"] for row in current["probe_results"]] == [True, True, True]
    assert current["diagnostic_control_observations"] == {
        "moto_hypothesized_group_top": False,
        "moto_hypothesized_group_passes": False,
        "moto_any_memory_passes": False,
        "negative_control_no_match": True,
        "phase_control_no_match": True,
    }
    positive, negative, phase_control = threshold_only["probe_results"]
    assert threshold_only["threshold"] == 0.30430094253875567
    assert positive["top_group_id"] == "exception-origin-state-conflation"
    assert len(positive["passing_memory_ids"]) == 3
    assert len(negative["passing_memory_ids"]) == 3
    assert negative["no_match"] is False
    assert phase_control["no_match"] is True
    assert threshold_only["disposition"] == (
        "rejected-nonhypothesized-rank-and-negative-control-selection"
    )


@pytest.mark.parametrize(
    "weights",
    [
        {
            "semantic": 1.0,
            "failure_class": 0.0,
            "phase": 0.0,
            "language": 0.0,
            "validation": 0.0,
        },
        {
            "semantic": 0.2,
            "failure_class": 0.3,
            "phase": 0.2,
            "language": 0.2,
            "validation": 0.1,
        },
        {
            "semantic": 0.0,
            "failure_class": 0.0,
            "phase": 0.5,
            "language": 0.5,
            "validation": 0.0,
        },
    ],
)
def test_nonnegative_current_feature_weights_cannot_put_hypothesized_group_first(
    weights: dict[str, float],
) -> None:
    preflight = d115.build_d115_preflight(repository=REPOSITORY)
    diagnostic = d115._evaluate_policy(
        preflight["semantic_body"]["public_score_matrix"],
        policy_id="test-current-feature-family",
        weights=weights,
        threshold=0.0,
        runtime_observable=True,
    )

    positive = diagnostic["probe_results"][0]
    hypothesized = next(
        row
        for row in positive["candidates"]
        if row["semantic_group_id"] == d115.HYPOTHESIZED_GROUP_ID
    )
    assert positive["top_group_id"] != d115.HYPOTHESIZED_GROUP_ID
    assert hypothesized["rank"] > 1


def test_structural_impossibility_claims_follow_from_the_exact_rows() -> None:
    preflight = d115.build_d115_preflight(repository=REPOSITORY)
    findings = preflight["semantic_body"]["structural_findings"]

    assert findings["current_failure_class_component_all_zero"] is True
    assert findings["current_validation_component_all_zero"] is True
    assert findings["phase_and_language_equal_within_each_probe"] is True
    assert findings["moto_hypothesized_group_rank"] == 3
    assert findings["moto_hypothesized_group_score"] < findings["babel_lowest_score"]
    assert findings["moto_observed_top_nonhypothesized_group_score"] < findings["babel_top_score"]
    assert findings["threshold_only_separation_interval_exists"] is False
    assert findings["threshold_to_select_hypothesized_moto_selects_all_babel_entries"] is True
    assert findings["nonnegative_current_feature_weights_can_make_hypothesized_group_top"] is False
    assert findings["hypothesis_labels_are_runtime_inputs"] is False
    assert findings["hypothesis_labels_are_acceptance_ground_truth"] is False


def test_conditional_counterfactual_is_useful_but_explicitly_non_authoritative() -> None:
    preflight = d115.build_d115_preflight(repository=REPOSITORY)
    conditional = preflight["semantic_body"]["decision"]["counterfactual_conditional_tuple"]
    diagnostic = _policy(preflight, "counterfactual-class-signal-conditional-tuple")
    candidate = d115.build_d115_candidate(preflight, repository=REPOSITORY)
    candidate_body = candidate["semantic_body"]

    assert diagnostic["runtime_observable_inputs_only"] is False
    assert diagnostic["disposition"] == ("conditional-hypothesis-only-independent-signal-required")
    assert conditional["counterfactual_only"] is True
    assert conditional["corrected_policy_selected"] is False
    assert conditional["implementation_ready"] is False
    assumptions = conditional["counterfactual_signal_assumptions"]
    assert assumptions["source"] == "d112-public-non-acceptance-hypothesis"
    assert assumptions["runtime_classifier_observed"] is False
    assert assumptions["true_relevance_established"] is False
    assert "d112-hypothesized-group-id" in conditional["forbidden_signal_sources"]
    assert "task-id-to-answer-lookup" in conditional["forbidden_signal_sources"]
    observed = conditional["diagnostic_only_counterfactual_results"]
    assert observed["moto_implement_hypothesized_score"] == pytest.approx(0.6530721018133969)
    assert observed["moto_implement_hypothesized_pass"] is True
    assert observed["babel_no_match"] is True
    assert observed["moto_reproduce_no_match"] is True
    assert observed["phase_delta"] == pytest.approx(0.15)
    assert candidate_body["decision_status"] == "policy-mutation-deferred"
    assert candidate_body["conditional_policy_hypothesis"] == conditional
    next_action = candidate_body["proposed_next_action"]
    assert next_action["hypothesized_group_id_as_classifier_input_allowed"] is False
    assert next_action["task_id_answer_lookup_allowed"] is False
    assert next_action["deterministic_abstention_required"] is True
    assert next_action["ambiguous_signal_must_abstain"] is True
    assert next_action["score_policy_mutation_allowed"] is False
    assert next_action["runtime_retrieval_allowed"] is False
    assert next_action["agent_run_allowed"] is False


def test_candidate_and_source_gate_keep_every_runtime_authority_closed() -> None:
    preflight = d115.build_d115_preflight(repository=REPOSITORY)
    candidate = d115.build_d115_candidate(preflight, repository=REPOSITORY)
    protected = d115._protected_input_state(REPOSITORY)
    gate = d115.build_d115_source_gate(
        preflight,
        candidate,
        repository=REPOSITORY,
        protected_pre=protected,
        protected_post=protected,
    )

    authority = candidate["semantic_body"]["authority"]
    assert authority["offline_score_policy_decision_candidate_ready"] is True
    assert authority["corrected_policy_selected"] is False
    assert authority["additional_public_relevance_evidence_required"] is True
    assert authority["exact_candidate_user_approval_received"] is False
    assert authority["public_failure_class_signal_contract_authorized"] is False
    assert authority["score_policy_correction_authorized"] is False
    assert authority["score_policy_correction_implemented"] is False
    assert authority["score_weights_or_threshold_changed"] is False
    assert authority["failure_class_signal_changed"] is False
    assert authority["ranking_policy_changed"] is False
    assert authority["retrieval_ready"] is False
    assert authority["retrieval_experiment_authorized"] is False
    assert authority["runtime_memory_injection_count"] == 0
    assert authority["agent_runs"] == 0
    assert authority["core_campaign_unlocked"] is False
    assert authority["analysis_ready"] is False
    assert authority["memory_effect_established"] is False
    assert authority["negative_transfer_established"] is False
    assert gate["semantic_body"]["authority"] == authority
    assert gate["semantic_body"]["qualification"]["corrected_policy_selected"] is False
    assert gate["semantic_body"]["evidence_boundary"]["retrieval_calls"] == 0


@pytest.mark.parametrize(
    ("weights", "threshold", "message"),
    [
        (
            {
                "semantic": -0.1,
                "failure_class": 0.4,
                "phase": 0.3,
                "language": 0.3,
                "validation": 0.1,
            },
            0.5,
            "finite and nonnegative",
        ),
        (
            {
                "semantic": 0.2,
                "failure_class": 0.2,
                "phase": 0.2,
                "language": 0.2,
                "validation": 0.1,
            },
            0.5,
            "sum to one",
        ),
        (d115.CURRENT_WEIGHTS, 1.1, "within zero and one"),
    ],
)
def test_invalid_policy_tuples_fail_closed(
    weights: dict[str, float], threshold: float, message: str
) -> None:
    with pytest.raises(d115.D115DecisionError, match=message):
        d115._validate_policy(weights, threshold, label="tampered-policy")


@pytest.mark.parametrize("mutation", ["score", "hypothesis"])
def test_rehashed_d112_matrix_tamper_is_rejected(mutation: str) -> None:
    gate = copy.deepcopy(_json(REPOSITORY / d115.DEFAULT_D112_GATE_PATH))
    probe = gate["semantic_body"]["diagnostic_scoring"]["probe_results"][0]
    if mutation == "score":
        probe["candidates"][0]["final_score"] += 0.01
        expected = "current score row differs"
    else:
        probe["hypothesis_is_acceptance_criterion"] = True
        expected = "promoted to acceptance ground truth"

    with pytest.raises(d115.D115DecisionError, match=expected):
        d115._public_matrix(gate)


def test_deterministic_rebuild_and_protected_bytes_are_unchanged() -> None:
    before = d115._protected_input_state(REPOSITORY)
    first_preflight = d115.build_d115_preflight(repository=REPOSITORY)
    first_candidate = d115.build_d115_candidate(first_preflight, repository=REPOSITORY)
    second_preflight = d115.build_d115_preflight(repository=REPOSITORY)
    second_candidate = d115.build_d115_candidate(second_preflight, repository=REPOSITORY)
    after = d115._protected_input_state(REPOSITORY)

    assert first_preflight == second_preflight
    assert first_candidate == second_candidate
    assert before == after


def test_build_path_does_not_rehydrate_model_or_cross_runtime_boundaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("D-115 crossed an offline-only boundary")

    monkeypatch.setattr(d114, "_default_current_input_loader", forbidden)
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
    )

    def guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.startswith(forbidden_imports):
            raise AssertionError(f"D-115 imported forbidden runtime module: {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    preflight = d115.build_d115_preflight(repository=REPOSITORY)
    candidate = d115.build_d115_candidate(preflight, repository=REPOSITORY)

    boundary = preflight["semantic_body"]["evidence_boundary"]
    assert boundary["model_load_or_encode_count"] == 0
    assert boundary["retrieval_calls"] == 0
    assert boundary["runtime_memory_injection_count"] == 0
    assert boundary["agent_runs"] == 0
    assert boundary["provider_calls_made"] == 0
    assert boundary["evaluator_calls_made"] == 0
    assert boundary["network_capable_call_paths_invoked"] == 0
    assert boundary["network_evidence_kind"] == "source-path-self-attested"
    assert boundary["os_level_socket_block_or_instrumentation_verified"] is False
    assert candidate["semantic_body"]["authority"]["retrieval_ready"] is False


def test_partial_artifact_collision_is_not_overwritten_or_completed(
    tmp_path: Path,
) -> None:
    _copy_materialization_repository(tmp_path)
    candidate_path = tmp_path / d115.DEFAULT_CANDIDATE_PATH
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_bytes(b"conflicting-candidate")
    protected_before = d115._protected_input_state(tmp_path)

    with pytest.raises(d115.D115DecisionError, match="existing output differs"):
        d115.run_d115_offline_source_gate(repository=tmp_path)

    assert (tmp_path / d115.DEFAULT_PREFLIGHT_PATH).exists()
    assert candidate_path.read_bytes() == b"conflicting-candidate"
    assert not (tmp_path / d115.DEFAULT_SOURCE_GATE_PATH).exists()
    assert d115._protected_input_state(tmp_path) == protected_before
    with pytest.raises(d115.D115DecisionError, match="existing output differs"):
        d115.run_d115_offline_source_gate(repository=tmp_path)


def test_materialized_artifacts_are_repeatably_validated_and_tamper_fails(
    tmp_path: Path,
) -> None:
    _copy_materialization_repository(tmp_path)
    first = d115.run_d115_offline_source_gate(repository=tmp_path)
    paths = (
        d115.DEFAULT_PREFLIGHT_PATH,
        d115.DEFAULT_CANDIDATE_PATH,
        d115.DEFAULT_SOURCE_GATE_PATH,
    )
    first_bytes = {path: (tmp_path / path).read_bytes() for path in paths}
    second = d115.run_d115_offline_source_gate(repository=tmp_path)

    assert first == second
    assert first_bytes == {path: (tmp_path / path).read_bytes() for path in paths}
    d115.validate_d115_preflight(repository=tmp_path)
    d115.validate_d115_candidate(repository=tmp_path)
    d115.validate_d115_source_gate(repository=tmp_path)

    candidate_path = tmp_path / d115.DEFAULT_CANDIDATE_PATH
    candidate = _json(candidate_path)
    candidate["semantic_body"]["authority"]["retrieval_ready"] = True
    _rehash_candidate(candidate)
    candidate_path.write_bytes(d115._pretty_json(candidate))

    with pytest.raises(d115.D115DecisionError, match="full expected payload mismatch"):
        d115.validate_d115_candidate(repository=tmp_path)


def test_rehashed_unknown_candidate_authority_field_is_rejected(
    tmp_path: Path,
) -> None:
    _copy_materialization_repository(tmp_path)
    d115.run_d115_offline_source_gate(repository=tmp_path)
    candidate_path = tmp_path / d115.DEFAULT_CANDIDATE_PATH
    candidate = _json(candidate_path)
    candidate["semantic_body"]["authority"]["unknown_authority"] = True
    _rehash_candidate(candidate)
    candidate_path.write_bytes(d115._pretty_json(candidate))

    with pytest.raises(d115.D115DecisionError, match="key set mismatch"):
        d115.validate_d115_candidate(repository=tmp_path)


def test_checked_in_d115_artifacts_are_complete_and_exact() -> None:
    paths = (
        d115.DEFAULT_PREFLIGHT_PATH,
        d115.DEFAULT_CANDIDATE_PATH,
        d115.DEFAULT_SOURCE_GATE_PATH,
    )
    present = [(REPOSITORY / path).exists() for path in paths]
    if not any(present):
        pytest.skip("D-115 artifacts have not been materialized yet")
    assert all(present), "partial checked-in D-115 evidence"

    d115.validate_d115_preflight(repository=REPOSITORY)
    d115.validate_d115_candidate(repository=REPOSITORY)
    d115.validate_d115_source_gate(repository=REPOSITORY)
