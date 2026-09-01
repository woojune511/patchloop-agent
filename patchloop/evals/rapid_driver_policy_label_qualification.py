"""Zero-call qualification for contract-owned Rapid driver policy labels."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.errors import ContractError
from patchloop.evals import rapid_batch_driver as driver_module
from patchloop.evals.rapid_batch_driver import (
    RAPID_BATCH_DRIVER_CONTRACT_SCHEMA,
    RAPID_BATCH_DRIVER_EVENT_SCHEMA,
    RAPID_BATCH_DRIVER_POLICY_VERSION,
    RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION,
    RapidBatchDriverContract,
)
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "rapid-driver-policy-label-public-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/rapid-driver-policy-label-public-qualification-20260827-v1.json"
)
R18_RESULT_PATH = Path(
    "reports/rapid-development/"
    "rapid-public-dev-anyio-v5-terminal-parity-ab-20260827-r18-afcc526c747f.jsonl"
)
R18_CANDIDATE_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-v5-terminal-parity-ab-20260827-r18-candidate-v26.json"
)

IMMUTABLE_PREDECESSORS = {
    "experiments/rapid-append-only-driver-integration-public-qualification-20260827-v1.json": {
        "bytes": 4_510,
        "file_sha256": ("sha256:72b355114b3a92eaf2a281bec6d5778c93c55751927e9cd530ee174c03b1cc5c"),
        "content_hash": ("sha256:e2825a3c5e839764e3e5fc7fd99418575d6971119188e2e36a5dc9ee7012cb6a"),
    },
    "experiments/rapid-terminal-state-parity-public-qualification-20260827-v1.json": {
        "bytes": 3_920,
        "file_sha256": ("sha256:d992159b613c9de86c1c1319eceaac29b54a5ad2adee0d94562e8df6f21de0d6"),
        "content_hash": ("sha256:c316e23c0a295f6c4e5b913104e1db6e6c2f15055b4348b60822527399bc53bd"),
    },
    R18_CANDIDATE_PATH.as_posix(): {
        "bytes": 15_734,
        "file_sha256": ("sha256:f5e3d50d4c4368d1a283d7a0b732397c956077d5e4da6f5b421d205745949a8e"),
        "content_hash": ("sha256:073d744112cf39f1046ef0414f0cf2c22b13abc3dfc76bc84eec110d6283da17"),
    },
}

R18_RESULT_IDENTITY = {
    "path": R18_RESULT_PATH.as_posix(),
    "bytes": 40_736,
    "file_sha256": ("sha256:0731a2ec33329430b981186913385b185b6a172943604727e9b54be35a1798bd"),
    "execution_hash": ("sha256:afcc526c747fd54dbb3dbfcd6660f6dfbeb393e992a5e4837ba31f8185de95de"),
    "final_event_content_hash": (
        "sha256:05bff5ae9e2a2f4bc160453fa9e7ce975f82889f8e0fa0b1b4574962d187e606"
    ),
}

SOURCE_FILES = (
    "patchloop/evals/rapid_batch_driver.py",
    "patchloop/evals/rapid_driver_policy_label_qualification.py",
    "scripts/build_rapid_driver_policy_label_qualification.py",
    "tests/test_rapid_batch_driver.py",
    "tests/test_rapid_driver_policy_label_qualification.py",
)


def _source_identity(root: Path, relative: str) -> dict[str, Any]:
    selected = ensure_within(root, relative)
    if selected.is_symlink() or not selected.is_file():
        raise ContractError(f"Rapid policy-label source is unavailable: {relative}")
    raw = selected.read_bytes()
    return {
        "path": relative,
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }


def _json_predecessor_identity(root: Path, relative: str) -> dict[str, Any]:
    selected = ensure_within(root, relative)
    try:
        raw = selected.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError(f"Rapid policy-label predecessor is unavailable: {relative}") from exc
    observed = {
        "path": relative,
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "content_hash": value.get("content_hash"),
    }
    expected = {"path": relative, **IMMUTABLE_PREDECESSORS[relative]}
    if observed != expected:
        raise ContractError(f"Rapid policy-label predecessor identity differs: {relative}")
    if relative == R18_CANDIDATE_PATH.as_posix():
        driver = value.get("driver_contract")
        if not (
            value.get("execution_hash") == R18_RESULT_IDENTITY["execution_hash"]
            and isinstance(driver, dict)
            and driver.get("policy_version") == RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION
        ):
            raise ContractError("Consumed Rapid R18 candidate driver binding differs")
    return observed


def _derived_r18_contract(
    events: list[dict[str, Any]],
    policy_version: str,
) -> RapidBatchDriverContract:
    started = events[0]
    capabilities = sorted(
        (event for event in events if event.get("event") == "row-capability-issued"),
        key=lambda event: event.get("schedule_order", 0),
    )
    body = {
        "schema_version": RAPID_BATCH_DRIVER_CONTRACT_SCHEMA,
        "policy_version": policy_version,
        "official": False,
        "experiment_id": started.get("experiment_id"),
        "execution_hash": started.get("execution_hash"),
        "plan_hash": started.get("plan_hash"),
        "runtime_build_hash": started.get("runtime_build_hash"),
        "schedule_hash": started.get("schedule_hash"),
        "cost_control_hash": started.get("cost_control_hash"),
        "manifest_hashes": tuple(event.get("manifest_hash") for event in capabilities),
        "schedule_row_ids": tuple(event.get("schedule_row_id") for event in capabilities),
        "run_ids": tuple(event.get("run_id") for event in capabilities),
        "row_reserve_nanos": started.get("row_reserve_nanos"),
        "full_schedule_reserve_nanos": started.get("full_schedule_reserve_nanos"),
        "hard_cap_nanos": started.get("hard_cap_nanos"),
    }
    return RapidBatchDriverContract.model_validate({**body, "content_hash": sha256_json(body)})


def _r18_observation(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    selected = ensure_within(root, R18_RESULT_PATH.as_posix())
    try:
        raw = selected.read_bytes()
        events = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("Consumed Rapid R18 result is unavailable") from exc
    previous: str | None = None
    for event in events:
        if not isinstance(event, dict):
            raise ContractError("Consumed Rapid R18 event is invalid")
        body = {key: value for key, value in event.items() if key != "content_hash"}
        if event.get("previous_event_hash") != previous or event.get("content_hash") != sha256_json(
            body
        ):
            raise ContractError("Consumed Rapid R18 result chain differs")
        previous = event["content_hash"]
    final = events[-1] if events else {}
    identity = {
        "path": R18_RESULT_PATH.as_posix(),
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "execution_hash": final.get("execution_hash"),
        "final_event_content_hash": final.get("content_hash"),
    }
    if identity != R18_RESULT_IDENTITY:
        raise ContractError("Consumed Rapid R18 result identity differs")
    if not (
        len(events) == 20
        and final.get("event") == "batch-completed"
        and final.get("terminal_row_count") == 6
        and final.get("cost_fully_settled") is True
        and final.get("schedule_fully_observed") is True
        and all(
            event.get("schema_version") == RAPID_BATCH_DRIVER_EVENT_SCHEMA
            and event.get("driver_policy_version") == RAPID_BATCH_DRIVER_POLICY_VERSION
            for event in events
        )
    ):
        raise ContractError("Consumed Rapid R18 policy-label observation differs")
    v1 = _derived_r18_contract(events, RAPID_BATCH_DRIVER_POLICY_VERSION)
    v2 = _derived_r18_contract(events, RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION)
    observed_hashes = {event.get("driver_contract_hash") for event in events}
    if observed_hashes != {v2.content_hash} or v1.content_hash == v2.content_hash:
        raise ContractError("Consumed Rapid R18 driver hash attribution differs")
    observation = {
        "event_count": len(events),
        "serialized_policy_labels": [RAPID_BATCH_DRIVER_POLICY_VERSION],
        "driver_contract_hashes": sorted(observed_hashes),
        "recomputed_v1_contract_hash": v1.content_hash,
        "recomputed_v2_contract_hash": v2.content_hash,
        "contract_hash_matches_v1": v1.content_hash in observed_hashes,
        "contract_hash_matches_v2": v2.content_hash in observed_hashes,
        "provenance_mismatch_confirmed": True,
        "historical_result_rewritten": False,
        "retry_allowed": False,
        "promotion_evidence_eligible": False,
    }
    return identity, observation


def _mock_contract(policy_version: str) -> RapidBatchDriverContract:
    body = {
        "schema_version": RAPID_BATCH_DRIVER_CONTRACT_SCHEMA,
        "policy_version": policy_version,
        "official": False,
        "experiment_id": "qualified-policy-label",
        "execution_hash": sha256_json("qualified-execution"),
        "plan_hash": sha256_json("qualified-plan"),
        "runtime_build_hash": sha256_json("qualified-runtime"),
        "schedule_hash": sha256_json("qualified-schedule"),
        "cost_control_hash": sha256_json("qualified-cost"),
        "manifest_hashes": (sha256_json("qualified-manifest"),),
        "schedule_row_ids": ("qualified-row-01",),
        "run_ids": ("run_qualified_policy_label_01",),
        "row_reserve_nanos": 1_200_000_000,
        "full_schedule_reserve_nanos": 1_200_000_000,
        "hard_cap_nanos": 1_250_000_000,
    }
    return RapidBatchDriverContract.model_validate({**body, "content_hash": sha256_json(body)})


def _policy_matrix() -> list[dict[str, Any]]:
    output = []
    for policy in (
        RAPID_BATCH_DRIVER_POLICY_VERSION,
        RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION,
    ):
        contract = _mock_contract(policy)
        binding = driver_module._event_common(contract)
        other = (
            RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION
            if policy == RAPID_BATCH_DRIVER_POLICY_VERSION
            else RAPID_BATCH_DRIVER_POLICY_VERSION
        )
        tampered = {**binding, "driver_policy_version": other}
        output.append(
            {
                "contract_policy_version": policy,
                "serialized_policy_version": binding["driver_policy_version"],
                "driver_contract_hash": binding["driver_contract_hash"],
                "selected_policy_valid": driver_module._event_matches_contract(binding, contract),
                "cross_policy_label_valid": driver_module._event_matches_contract(
                    tampered, contract
                ),
            }
        )
    return output


def build_rapid_driver_policy_label_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    immutable = [_json_predecessor_identity(root, relative) for relative in IMMUTABLE_PREDECESSORS]
    r18_identity, r18_observation = _r18_observation(root)
    matrix = _policy_matrix()
    if any(
        not item["selected_policy_valid"]
        or item["cross_policy_label_valid"]
        or item["serialized_policy_version"] != item["contract_policy_version"]
        for item in matrix
    ):
        raise ContractError("Rapid driver policy-label qualification gate failed")
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 27, tzinfo=UTC).isoformat(),
        "status": "offline-qualified",
        "scope": "rapid-driver-contract-owned-policy-label",
        "driver_contract_schema": RAPID_BATCH_DRIVER_CONTRACT_SCHEMA,
        "driver_event_schema": RAPID_BATCH_DRIVER_EVENT_SCHEMA,
        "serializer_contract": {
            "source_field": "contract.policy_version",
            "event_field": "driver_policy_version",
            "validator_uses_same_binding": True,
            "cross_policy_rehash_fails_closed": True,
        },
        "policy_matrix": matrix,
        "r18_observation": r18_observation,
        "source_files": [_source_identity(root, relative) for relative in SOURCE_FILES],
        "immutable_predecessors": [*immutable, r18_identity],
        "mocked_gate": {
            "production_journal_test_module": "tests/test_rapid_batch_driver.py",
            "v1_serialization_and_round_trip": True,
            "v2_serialization_and_round_trip": True,
            "v1_to_v2_rehashed_label_rejected": True,
            "v2_to_v1_rehashed_label_rejected": True,
        },
        "evidence_boundary": {
            "public_driver_result_and_candidate_only": True,
            "raw_reasoning_read": False,
            "llm_response_text_read": False,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "agent_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "network_calls": 0,
            "added_cost_usd": "0",
        },
        "consumed_r18_modified": False,
        "consumed_r18_retry_allowed": False,
        "candidate_created": False,
        "rehearsal_created": False,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "generalization_established": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("Rapid policy-label qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_rapid_driver_policy_label_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_rapid_driver_policy_label_qualification(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(qualification_bytes(value))
    return value


def load_rapid_driver_policy_label_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("Rapid policy-label qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("Rapid policy-label qualification bytes differ")
    if value != build_rapid_driver_policy_label_qualification(root):
        raise ContractError("Rapid policy-label qualification source binding differs")
    return value


__all__ = [
    "IMMUTABLE_PREDECESSORS",
    "QUALIFICATION_PATH",
    "R18_RESULT_IDENTITY",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_rapid_driver_policy_label_qualification",
    "load_rapid_driver_policy_label_qualification",
    "materialize_rapid_driver_policy_label_qualification",
    "qualification_bytes",
]
