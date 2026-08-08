from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from patchloop.memory import d112_retrieval_readiness_probe as d112
from patchloop.memory import d113_validator_correction_authorization as d113
from patchloop.util import canonical_json, sha256_text

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def exact_context() -> dict:
    return d113._load_exact_d112_inputs(ROOT.resolve())


def _preflight(exact_context: dict) -> dict:
    return d113.build_d113_preflight(repository=ROOT, _context=exact_context)


def _candidate(exact_context: dict) -> tuple[dict, dict]:
    preflight = _preflight(exact_context)
    candidate = d113.build_d113_authorization_candidate(
        preflight,
        repository=ROOT,
        _context=exact_context,
    )
    return preflight, candidate


def _rehash(payload: dict, *, id_field: str, prefix: str) -> None:
    body_hash = sha256_text(canonical_json(payload["semantic_body"]))
    payload["semantic_body_hash"] = body_hash
    payload[id_field] = f"{prefix}{body_hash.removeprefix('sha256:')}"


def test_d113_preflight_exactly_binds_d112_execution_evidence(
    exact_context: dict,
) -> None:
    body = _preflight(exact_context)["semantic_body"]

    assert body["exact_d112_receipt"] == {
        "path": d113.DEFAULT_D112_RECEIPT_PATH.as_posix(),
        "file_bytes": d113.EXPECTED_D112_RECEIPT_BYTES,
        "file_sha256": d113.EXPECTED_D112_RECEIPT_FILE_SHA,
        "receipt_id": d113.EXPECTED_D112_RECEIPT_ID,
        "semantic_body_hash": d113.EXPECTED_D112_RECEIPT_BODY_SHA,
    }
    assert body["exact_d112_completion_gate"] == {
        "path": d113.DEFAULT_D112_GATE_PATH.as_posix(),
        "file_bytes": d113.EXPECTED_D112_GATE_BYTES,
        "file_sha256": d113.EXPECTED_D112_GATE_FILE_SHA,
        "gate_id": d113.EXPECTED_D112_GATE_ID,
        "semantic_body_hash": d113.EXPECTED_D112_GATE_BODY_SHA,
    }
    assert body["executed_d112_implementation_files"] == [
        dict(row) for row in d113.D112_IMPLEMENTATION_SPECS
    ]
    facts = body["actual_execution_facts"]
    assert facts["actual_chronology_valid"] is True
    assert facts["pre_post_input_fingerprint"] == d113.EXPECTED_D112_INPUT_FINGERPRINT
    assert facts["score_row_count"] == 9
    assert facts["all_diagnostic_no_match"] is True


def test_d113_preflight_records_all_known_validator_gaps(exact_context: dict) -> None:
    body = _preflight(exact_context)["semantic_body"]
    findings = body["validator_gap_findings"]

    assert tuple(row["gap_id"] for row in findings) == d113.GAP_IDS
    assert all(row["status"] == "observed" for row in findings)
    assert all(
        row["source_file_sha256"] == d113.D112_IMPLEMENTATION_SPECS[0]["file_sha256"]
        for row in findings
    )
    skip = findings[0]["evidence"]
    assert skip["input_state_call_line"] < skip["verify_current_inputs_branch_line"]
    assert skip["snapshot_requires_local_snapshot_and_exact_dependencies"] is True
    receipt = findings[1]["evidence"]
    assert receipt["full_receipt_rebuild_call_present"] is False
    assert receipt["root_exact_key_set_enforced"] is False
    assert receipt["paired_receipt_and_gate_rehash_not_fail_closed"] is True
    chronology = findings[2]["evidence"]
    assert chronology["actual_checked_in_chronology_valid"] is True
    assert chronology["approval_before_execution_compare_present"] is False
    assert chronology["execution_before_completion_compare_present"] is False
    assert findings[3]["evidence"]["global_ledger_present"] is False
    assert findings[4]["evidence"]["os_socket_block_verified"] is False


def test_d113_candidate_is_append_only_plan_not_authorization(exact_context: dict) -> None:
    _preflight_payload, candidate = _candidate(exact_context)
    body = candidate["semantic_body"]
    action = body["proposed_action"]
    authority = body["authority"]

    assert action["new_files_only"] is True
    assert action["d112_bound_files_may_be_modified"] is False
    assert action["existing_artifact_or_index_mutation_allowlist"] == []
    assert action["d112_execution_replay_allowed"] is False
    assert action["d112_one_use_capability_recreated"] is False
    assert action["closed_runtime_boundaries"]["score_weights_or_threshold_change_allowed"] is False
    assert action["closed_runtime_boundaries"]["retrieval_execution_allowed"] is False
    assert action["closed_runtime_boundaries"]["model_load_or_encode_allowed"] is False
    assert action["claim_limits"]["clean_clone_portability_already_validated"] is False
    assert authority["validator_correction_candidate_ready"] is True
    assert authority["exact_candidate_user_approval_received"] is False
    assert authority["validator_correction_authorized"] is False
    assert authority["validator_correction_implemented"] is False
    assert authority["core_campaign_unlocked"] is False
    assert body["approval_contract"]["generic_continue_message_is_approval"] is False


def test_d113_future_paths_are_disjoint_from_d112_bound_paths(exact_context: dict) -> None:
    _preflight_payload, candidate = _candidate(exact_context)
    action = candidate["semantic_body"]["proposed_action"]

    assert set(action["future_paths"]).isdisjoint(
        candidate["semantic_body"]["protected_d112_paths"]
    )
    assert set(action["future_paths"]).isdisjoint(
        row["path"] for row in exact_context["protected_evidence"]
    )


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("authority", "validator_correction_authorized"), True),
        (("proposed_action", "d112_bound_files_may_be_modified"), True),
        (
            ("proposed_action", "closed_runtime_boundaries", "retrieval_execution_allowed"),
            True,
        ),
        (
            (
                "proposed_action",
                "closed_runtime_boundaries",
                "score_weights_or_threshold_change_allowed",
            ),
            True,
        ),
    ],
)
def test_d113_rehashed_candidate_scope_widening_fails_closed(
    path: tuple[str, ...],
    value: object,
    exact_context: dict,
) -> None:
    preflight, candidate = _candidate(exact_context)
    tampered = copy.deepcopy(candidate)
    target = tampered["semantic_body"]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    _rehash(tampered, id_field="candidate_id", prefix="d113validatorcandidate_")

    with pytest.raises(d113.D113AuthorizationError, match="candidate semantic content"):
        d113.build_d113_source_gate(
            preflight,
            tampered,
            repository=ROOT,
            _context=exact_context,
        )


@pytest.mark.parametrize(
    "tamper",
    [
        "receipt-sha",
        "gap-list",
        "implementation-sha",
        "unknown-field",
    ],
)
def test_d113_rehashed_preflight_tamper_fails_closed(
    tamper: str,
    exact_context: dict,
) -> None:
    preflight = _preflight(exact_context)
    changed = copy.deepcopy(preflight)
    body = changed["semantic_body"]
    if tamper == "receipt-sha":
        body["exact_d112_receipt"]["file_sha256"] = "sha256:" + "0" * 64
    elif tamper == "gap-list":
        body["validator_gap_findings"] = body["validator_gap_findings"][:-1]
    elif tamper == "implementation-sha":
        body["executed_d112_implementation_files"][0]["file_sha256"] = "sha256:" + "0" * 64
    else:
        body["unexpected"] = True
    _rehash(changed, id_field="preflight_id", prefix="d113preflight_")

    with pytest.raises(d113.D113AuthorizationError, match="preflight semantic content"):
        d113.build_d113_authorization_candidate(
            changed,
            repository=ROOT,
            _context=exact_context,
        )


def test_current_d112_receipt_validator_accepts_rehashed_unknown_root_field(
    tmp_path: Path,
    exact_context: dict,
) -> None:
    receipt = copy.deepcopy(exact_context["receipt"])
    receipt["unknown_rehashed_field"] = "D-113 gap witness"
    selected = tmp_path / "receipt.json"
    selected.write_bytes((json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    body = receipt["semantic_body"]
    current_input = body["pre_execution_input"]
    current_context = {
        "d111_gate_binding": body["d111_source_gate"],
        "candidate_binding": body["d111_candidate"],
    }

    accepted = d112.validate_d112_probe_receipt(
        selected,
        repository=tmp_path,
        current_input=current_input,
        current_context=current_context,
    )

    assert accepted["receipt_id"] == d113.EXPECTED_D112_RECEIPT_ID


def test_d113_builder_never_calls_d112_or_runtime_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    exact_context: dict,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("D-113 crossed an unapproved boundary")

    for name in (
        "validate_d112_completion_gate",
        "validate_d112_probe_receipt",
        "preflight_d112_execution",
        "execute_d112_scoring_diagnostic",
        "_input_state",
        "_snapshot_evidence",
        "_default_model_loader",
        "_default_batch_encoder",
    ):
        monkeypatch.setattr(d112, name, forbidden)
    monkeypatch.setattr("patchloop.memory.retrieval.retrieve_memory", forbidden)
    monkeypatch.setattr("patchloop.memory.retrieval._query_embedding", forbidden)
    monkeypatch.setattr("patchloop.memory.retrieval._render_raw_trace", forbidden)

    preflight, candidate = _candidate(exact_context)
    gate = d113.build_d113_source_gate(
        preflight,
        candidate,
        repository=ROOT,
        _context=exact_context,
    )

    boundary = preflight["semantic_body"]["evidence_boundary"]
    assert boundary["d112_validator_invoked"] is False
    assert boundary["snapshot_or_model_file_read"] is False
    assert boundary["embedding_model_load_count"] == 0
    assert boundary["retrieval_calls"] == 0
    assert boundary["provider_calls_made"] == 0
    assert boundary["evaluator_calls_made"] == 0
    assert gate["semantic_body"]["authority"]["validator_correction_authorized"] is False


def test_d113_source_gate_binds_current_implementation(exact_context: dict) -> None:
    preflight, candidate = _candidate(exact_context)
    gate = d113.build_d113_source_gate(
        preflight,
        candidate,
        repository=ROOT,
        _context=exact_context,
    )

    assert gate["semantic_body"]["implementation_files"] == [
        d113._file_binding(path, repository=ROOT, label="test D-113 implementation")
        for path in d113.D113_IMPLEMENTATION_PATHS
    ]


def test_d113_exact_retry_rejects_different_existing_bytes(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "candidate.json"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"different\n")

    with pytest.raises(d113.D113AuthorizationError, match="different bytes"):
        d113._preflight_output(
            Path("reports/candidate.json"),
            b"expected\n",
            repository=tmp_path.resolve(),
        )


def test_d113_checked_in_source_gate_rebuilds_exactly() -> None:
    result = d113.validate_d113_source_gate(repository=ROOT)

    assert result["ok"] is True
    assert result["gap_ids"] == list(d113.GAP_IDS)
    assert result["current_implementation_verified"] is True
    assert result["validator_correction_candidate_ready"] is True
    assert result["exact_candidate_user_approval_received"] is False
    assert result["validator_correction_authorized"] is False
    assert result["validator_correction_implemented"] is False
    assert result["retrieval_ready"] is False
    assert result["provider_calls_made"] == 0
    assert result["evaluator_calls_made"] == 0
    assert result["core_campaign_unlocked"] is False


def test_d113_exact_retry_preserves_protected_d112_and_index_bytes() -> None:
    before_context = d113._load_exact_d112_inputs(ROOT.resolve())
    before = d113._protected_fingerprints(before_context)

    result = d113.run_d113_offline_source_gate(repository=ROOT)

    after = d113._protected_fingerprints(d113._load_exact_d112_inputs(ROOT.resolve()))
    assert before == after
    assert result["protected_fingerprints_equal"] is True
    assert result["d112_validator_invoked"] is False
    assert result["model_load_count"] == 0
    assert result["query_encode_call_count"] == 0
    assert result["retrieval_calls"] == 0
    assert result["agent_runs"] == 0
